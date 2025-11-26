"""
WebSearch服务 - 并行调用6个搜索引擎获取结果
"""
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import time

# 6个搜索引擎配置
SEARCH_ENGINES = {
    "jina": "search_pro_jina",
    "google": "search_prime",
    "bing": "search_pro_ms",
    "sogou": "search_live",
    "quark": "search_lite",
    "baidu": "search_plus"
}

# API配置
API_URL = 'https://runway.devops.xiaohongshu.com/openai/zhipu/paas/v4/web_search'
API_KEY = '83834a049770445a912608da03702901'


def call_single_engine(query: str, engine_name: str, engine_code: str, max_retries: int = 3) -> List[Dict]:
    """
    调用单个搜索引擎获取结果

    Args:
        query: 搜索查询
        engine_name: 引擎名称（用于标识）
        engine_code: 引擎代码（API参数）
        max_retries: 最大重试次数

    Returns:
        搜索结果列表，每个结果包含 {url, title, content, engine}
    """
    headers = {
        'api-key': API_KEY
    }
    data = {
        "search_engine": engine_code,
        "search_query": query,
        "query_rewrite": "false",
        "request_id": f"authority_query_{engine_name}",
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(data), timeout=30)
            result = json.loads(response.content.decode())

            items = result.get("search_result", [])

            # 格式化结果
            results = []
            for item in items[:10]:  # 只取top10
                results.append({
                    'url': item.get('link', ''),
                    'title': item.get('title', ''),
                    'content': item.get('content', ''),
                    'engine': engine_name
                })

            print(f"✓ {engine_name}: 获取到 {len(results)} 条结果")
            return results

        except Exception as e:
            print(f"✗ {engine_name} 第{attempt+1}次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # 重试前等待1秒
            else:
                print(f"✗ {engine_name} 所有重试失败，跳过该引擎")
                return []

    return []


def search_all_engines(query: str, selected_engines: List[str] = None, max_workers: int = 6) -> List[Dict]:
    """
    并行调用搜索引擎获取结果

    Args:
        query: 搜索查询
        selected_engines: 选中的搜索引擎列表，如 ['google', 'bing']。如果为None则调用所有引擎
        max_workers: 最大并发数

    Returns:
        搜索引擎的结果列表
    """
    # 确定要调用哪些引擎
    engines_to_use = SEARCH_ENGINES
    if selected_engines:
        engines_to_use = {k: v for k, v in SEARCH_ENGINES.items() if k in selected_engines}

    print(f"\n开始搜索: '{query}'")
    print(f"并行调用 {len(engines_to_use)} 个搜索引擎...")
    if selected_engines:
        print(f"选中引擎: {', '.join(engines_to_use.keys())}")

    all_results = []

    # 使用线程池并行调用
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_engine = {
            executor.submit(call_single_engine, query, name, code): name
            for name, code in engines_to_use.items()
        }

        # 收集结果
        for future in as_completed(future_to_engine):
            engine_name = future_to_engine[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"✗ {engine_name} 执行失败: {str(e)}")

    print(f"\n搜索完成! 共获取 {len(all_results)} 条结果")
    return all_results


def get_search_results(query: str, selected_engines: List[str] = None) -> Tuple[List[Dict], Dict]:
    """
    获取搜索结果并返回统计信息

    Args:
        query: 搜索查询
        selected_engines: 选中的搜索引擎列表，如 ['google', 'bing']

    Returns:
        (结果列表, 统计信息字典)
    """
    results = search_all_engines(query, selected_engines)

    # 统计信息
    stats = {
        'total_results': len(results),
        'engines': {}
    }

    for result in results:
        engine = result['engine']
        if engine not in stats['engines']:
            stats['engines'][engine] = 0
        stats['engines'][engine] += 1

    return results, stats


# 测试代码
if __name__ == '__main__':
    # 测试单个查询
    test_query = "考研数学二大纲"
    results, stats = get_search_results(test_query)

    print("\n" + "="*50)
    print("统计信息:")
    print(f"总结果数: {stats['total_results']}")
    print("各引擎结果数:")
    for engine, count in stats['engines'].items():
        print(f"  {engine}: {count}")

    print("\n前3条结果:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n{i}. [{result['engine']}] {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   内容: {result['content'][:100]}...")
