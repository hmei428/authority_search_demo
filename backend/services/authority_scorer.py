"""
权威性打分服务
评估网站域名(host)的权威性: 1(极低权威), 2(一般权威), 3(中高权威), 4(顶级权威)
"""
from openai import OpenAI
import json
import re
import ast
import time
import traceback
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from authority_whitelist import get_whitelist

# API配置
API_KEY = "MAAS680934ffb1a349259ed7beae4272175b"
BASE_URL = "http://redservingapi.devops.xiaohongshu.com/v1"
MODEL = "qwen3-30b-a3b"


def get_response(messages):
    """调用LLM获取响应"""
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=False,
        max_tokens=1024,
        temperature=0.1
    )
    reasoning_content = completion.choices[0].message.reasoning_content if hasattr(completion.choices[0].message, 'reasoning_content') else None
    content = completion.choices[0].message.content
    return reasoning_content, content


def parse_json_block(txt: str) -> dict:
    """从文本中提取JSON对象"""
    seg = txt
    json_start = seg.find('```json')
    if json_start != -1:
        json_start += 7
        json_end = seg.find('```', json_start)
        if json_end != -1:
            json_str = seg[json_start:json_end].strip()
        else:
            json_str = ""
    else:
        json_str = extract_json_from_text(seg)

    if not json_str:
        return {}

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(json_str)
        except Exception:
            return {}


def extract_json_from_text(text: str) -> str:
    """从文本中提取完整的JSON字符串"""
    start = text.find('{')
    if start == -1:
        return ""

    brace_count = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]

    return ""


# System Prompt - 权威性打分
SYSTEM_PROMPT = '''
# 任务说明
任务背景：在AI搜索和内容召回中，不同网站（Host）的内容质量、可信度和专业性差异较大。为了帮助搜索团队更好地筛选出高质量、权威的站点，建立可靠的白名单体系，需要你判断输入网站在所属领域（Taxonomy1_name）中的权威程度等级。

你的任务：你是一个AI助手，专门帮助搜索团队判断给定网站的权威程度。请依据输入的 URL、Host 和可选类目 Taxonomy1_name，判断该网站在领域内的**权威程度等级**，分为 1、2、3、4 四个档位。

网站权威程度主要从三个维度评估：
1. **知名度（Popularity）**：是否被主流搜索引擎广泛收录与引用。
2. **专业性（Expertise）**：内容是否集中于特定领域、是否具备系统性与深度。
3. **可信度（Trustworthiness）**：是否为官方主体、是否长期维护、内容是否可靠真实。

## 输入字段
1. URL：完整网页链接
2. Host：网址域名（如 www.pku.edu.cn）
3. Taxonomy1_name：网站所属领域（可能为空）

## 输出四档
1档 极低权威 —— 垃圾或无可信度网站，内容混乱、死链、盗版、色情、AIGC生成或非法搬运，无被搜索引擎收录。
2档 一般权威 —— 内容较专一但知名度低，通常为个人博客、小众社区或地方站点，有部分原创但无权威背书。
3档 中高权威 —— 领域内有影响力的行业门户或垂直网站，内容体系完整、来源稳定、有一定代表性。
4档 顶级权威 —— 官方或唯一指定来源，具有政府、大学、标准机构等身份，内容权威且不可替代。

## 典型示例

### 1档（极低权威）
- Host: douyin311.com
- Host: willhoumoe.github.io
- Host: dazh.cbpt.cnki.net
- Host: www.yuwen.net
说明：内容无可信度，站点无公信力或为非法/搬运/AIGC生成页面。

### 2档（一般权威）
- Host: www.verym.com
- Host: jms.jrzp.com
- Host: t.shejidaren.com
说明：内容相对专一但缺乏影响力或权威来源支撑。

### 3档（中高权威）
- Host: tj.bendibao.com
- Host: www.autohome.com.cn
- Host: www.pconline.com.cn
- Host: chest.dxy.cn
说明：领域内有较高知名度和内容深度，属于行业代表性网站。

### 4档（顶级权威）
- Host: support.microsoft.com
- Host: www.beijing.gov.cn
- Host: www.pku.edu.cn
- Host: culture.people.com.cn
说明：官方机构或政府唯一发布源，具备最高可信度与公认权威性。

## 输出格式
请严格按照以下格式输出：
```json
{
    "标签": 1、2、3、4,
    "判断依据": "简要说明分类理由，不超过15个字"
}
'''

USER_PROMPT_TEMPLATE = '''现在，请你分析Url对应的host，给出网站Host的权威性分档结果。
host:{host}
'''


def score_authority(host: str, max_retries: int = 3, auto_add_to_whitelist: bool = True) -> Tuple[int, str]:
    """
    评估单个host的权威性（支持白名单）

    Args:
        host: 网站域名
        max_retries: 最大重试次数
        auto_add_to_whitelist: 是否自动添加到白名单

    Returns:
        (权威性分数 1/2/3/4, 判断依据)
    """
    # 1. 先查白名单
    whitelist = get_whitelist()
    cached_score, cached_reason = whitelist.get_score(host)
    if cached_score is not None:
        print(f"✓ 白名单命中: {host} -> {cached_score}")
        return cached_score, cached_reason

    # 2. 白名单未命中，调用LLM
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': USER_PROMPT_TEMPLATE.format(host=host)}
    ]

    for attempt in range(max_retries):
        try:
            reasoning_content, response_text = get_response(messages)

            parsed_result = parse_json_block(response_text)
            score = parsed_result.get("标签", -1)
            reason = parsed_result.get("判断依据", "解析失败")

            if score in [1, 2, 3, 4]:
                # 3. 自动添加到白名单
                if auto_add_to_whitelist:
                    whitelist.add_host(host, score, reason)
                return score, reason
            else:
                raise ValueError(f"无效的标签值: {score}")

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                print(f"权威性打分失败 (host={host}): {str(e)}")
                return -1, "打分失败"

    return -1, "打分失败"


def score_authority_batch(results: list, max_workers: int = 128) -> list:
    """
    批量评估权威性（使用缓存避免重复评估相同host）

    Args:
        results: 搜索结果列表，每个包含 {url, title, content, engine, host, relevance_score, relevance_reason}
        max_workers: 最大并发数

    Returns:
        添加了权威性分数的结果列表
    """
    print(f"\n开始权威性打分...")

    # 提取所有唯一的host
    unique_hosts = list(set([r['host'] for r in results]))
    print(f"  共 {len(unique_hosts)} 个不同的host需要评分")

    # 缓存host的权威性分数
    host_scores = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_host = {
            executor.submit(score_authority, host): host
            for host in unique_hosts
        }

        completed = 0
        for future in as_completed(future_to_host):
            host = future_to_host[future]
            try:
                score, reason = future.result()
                host_scores[host] = {'score': score, 'reason': reason}

                completed += 1
                if completed % 10 == 0:
                    print(f"  进度: {completed}/{len(unique_hosts)}")

            except Exception as e:
                print(f"  处理host {host} 失败: {str(e)}")
                host_scores[host] = {'score': -1, 'reason': "打分失败"}

    # 将权威性分数添加到结果中
    scored_results = []
    for result in results:
        result_copy = result.copy()
        host = result_copy['host']
        result_copy['authority_score'] = host_scores[host]['score']
        result_copy['authority_reason'] = host_scores[host]['reason']
        scored_results.append(result_copy)

    # 统计
    score_counts = {1: 0, 2: 0, 3: 0, 4: 0, -1: 0}
    for r in scored_results:
        score_counts[r['authority_score']] = score_counts.get(r['authority_score'], 0) + 1

    print(f"\n权威性打分完成!")
    print(f"  顶级权威(4): {score_counts[4]}")
    print(f"  中高权威(3): {score_counts[3]}")
    print(f"  一般权威(2): {score_counts[2]}")
    print(f"  极低权威(1): {score_counts[1]}")
    print(f"  失败(-1): {score_counts[-1]}")

    return scored_results


# 测试代码
if __name__ == '__main__':
    # 测试单个打分
    test_host = "www.pku.edu.cn"
    score, reason = score_authority(test_host)
    print(f"测试结果: host={test_host}, 分数={score}, 理由={reason}")
