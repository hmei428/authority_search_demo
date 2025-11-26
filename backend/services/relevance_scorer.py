"""
相关性打分服务
评估URL内容与查询的相关性: 0(无关), 1(弱相关), 2(高相关)
"""
from openai import OpenAI
import json
import re
import ast
import time
import traceback
from typing import Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

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


# System Prompt - 相关性打分
SYSTEM_PROMPT = '''
# 任务说明
任务背景：在搜索与内容匹配场景中，我们需要判断搜索 Query 与候选网页（包含标题和正文内容）之间的语义相关程度。
你的任务是：你是一个AI助手，负责帮助搜索团队判断给定 Query 与对应网页内容（Title + Content）的相关性强度。
请依据网页能否有效回答或满足 Query 的搜索意图，将其分为三个等级：0、1、2。

## 输入字段
1. Query：用户搜索词或问题
2. Title：网页标题
3. Content：网页正文内容（可能为空）

## 输出三档
2 高相关 —— 标题与内容能完整、准确地回答或满足 Query 的信息需求。用户阅读该网页后，其问题可被完全解决。
1 弱相关 —— 标题与内容部分涉及 Query 的主题、背景或相关知识，但不能完整回答问题，仅提供部分参考或片段信息。
0 无关 —— 标题与内容与 Query 无明显关联，或完全无法提供相关信息，或内容为空、泛泛而谈、偏题。

## 分类标准与示例

### 高相关 (2)
**判断标准：**
- 标题与正文共同能直接回答 Query 提出的问题；
- 内容完整、准确、针对性强；
- 用户无需再查找其他信息即可解决需求。

**正例：**
- Query: "考研数学二大纲"
  Title: "2025年考研数学二考试大纲完整版下载"
  Content: "本文提供2025考研数学二考试大纲全文，包含所有章节要求。"
  → **标签: 2（网页内容完整覆盖问题）**

### 弱相关 (1)
**判断标准：**
- 内容只覆盖了 Query 主题的一部分；
- 或者内容仅提供背景、案例、部分知识点；
- 用户可能仍需查找其他网页来得到完整答案。

### 无关 (0)
**判断标准：**
- 标题和内容与 Query 完全无关；
- 或仅包含通用词汇、广告、无实质内容；
- 或内容为空。

## 提示
关于打分我希望你严格一点 一定要是明确url的title和content一定可以回答用户的query才可以给两分
为保证标签体系的可靠性，应坚持"宁可错杀，不可放过"的保守策略。
在打分时，宁可多判为 1，也要确保标为 2 的 URL 质量过硬、与 Query 高度相关，能完整、准确地回答用户问题

## 输出格式
请严格按照以下格式输出：
```json
{
  "标签": 0、1、2,
  "判断依据": "简要说明理由，不超过15个字"
}
'''

USER_PROMPT_TEMPLATE = '''现在，请你分析下面Url和Url对应的host，给出网站的权威性分档结果。
Query为: {query}
对应Url的Title为:{title},对应Url的Content为:{content}
'''


def score_relevance(query: str, title: str, content: str, max_retries: int = 3) -> Tuple[int, str]:
    """
    评估单个URL的相关性

    Args:
        query: 搜索查询
        title: 网页标题
        content: 网页内容
        max_retries: 最大重试次数

    Returns:
        (相关性分数 0/1/2, 判断依据)
    """
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': USER_PROMPT_TEMPLATE.format(query=query, title=title, content=content)}
    ]

    for attempt in range(max_retries):
        try:
            reasoning_content, response_text = get_response(messages)

            parsed_result = parse_json_block(response_text)
            score = parsed_result.get("标签", -1)
            reason = parsed_result.get("判断依据", "解析失败")

            if score in [0, 1, 2]:
                return score, reason
            else:
                raise ValueError(f"无效的标签值: {score}")

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                print(f"相关性打分失败: {str(e)}")
                return -1, "打分失败"

    return -1, "打分失败"


def score_relevance_batch(results: list, query: str, max_workers: int = 128) -> list:
    """
    批量评估相关性

    Args:
        results: 搜索结果列表，每个包含 {url, title, content, engine}
        query: 搜索查询
        max_workers: 最大并发数

    Returns:
        添加了相关性分数的结果列表
    """
    print(f"\n开始相关性打分，共 {len(results)} 条结果...")

    scored_results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(score_relevance, query, result['title'], result['content']): i
            for i, result in enumerate(results)
        }

        completed = 0
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                score, reason = future.result()
                result = results[index].copy()
                result['relevance_score'] = score
                result['relevance_reason'] = reason
                scored_results.append((index, result))

                completed += 1
                if completed % 10 == 0:
                    print(f"  进度: {completed}/{len(results)}")

            except Exception as e:
                print(f"  处理索引 {index} 失败: {str(e)}")
                result = results[index].copy()
                result['relevance_score'] = -1
                result['relevance_reason'] = "打分失败"
                scored_results.append((index, result))

    # 按原始顺序排序
    scored_results.sort(key=lambda x: x[0])
    final_results = [r[1] for r in scored_results]

    # 统计
    score_counts = {0: 0, 1: 0, 2: 0, -1: 0}
    for r in final_results:
        score_counts[r['relevance_score']] = score_counts.get(r['relevance_score'], 0) + 1

    print(f"\n相关性打分完成!")
    print(f"  高相关(2): {score_counts[2]}")
    print(f"  弱相关(1): {score_counts[1]}")
    print(f"  无关(0): {score_counts[0]}")
    print(f"  失败(-1): {score_counts[-1]}")

    return final_results


# 测试代码
if __name__ == '__main__':
    # 测试单个打分
    test_query = "考研数学二大纲"
    test_title = "2025年考研数学二考试大纲完整版"
    test_content = "本文提供2025考研数学二考试大纲全文，包含所有章节要求。"

    score, reason = score_relevance(test_query, test_title, test_content)
    print(f"测试结果: 分数={score}, 理由={reason}")
