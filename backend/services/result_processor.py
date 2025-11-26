"""
结果处理器
包含URL解析和结果筛选功能
"""
from urllib.parse import urlparse
from typing import List, Dict


def extract_host(url: str) -> str:
    """
    从URL中提取host

    Args:
        url: 完整的URL

    Returns:
        host域名
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else url
    except Exception as e:
        print(f"URL解析失败: {url}, 错误: {str(e)}")
        return url


def add_host_to_results(results: List[Dict]) -> List[Dict]:
    """
    为每个结果添加host字段

    Args:
        results: 搜索结果列表

    Returns:
        添加了host字段的结果列表
    """
    for result in results:
        result['host'] = extract_host(result['url'])
    return results


def filter_results(results: List[Dict], relevance_threshold: int = 2, authority_threshold: int = 4) -> List[Dict]:
    """
    筛选结果：相关性=2且权威性=4

    Args:
        results: 包含所有打分信息的结果列表
        relevance_threshold: 相关性阈值（默认2）
        authority_threshold: 权威性阈值（默认4）

    Returns:
        筛选后的结果列表
    """
    print(f"\n开始筛选结果...")
    print(f"  筛选条件: 相关性={relevance_threshold} 且 权威性={authority_threshold}")
    print(f"  输入总数: {len(results)}")

    filtered = [
        r for r in results
        if r.get('relevance_score') == relevance_threshold and r.get('authority_score') == authority_threshold
    ]

    print(f"  筛选后数量: {len(filtered)}")

    return filtered


def deduplicate_by_url(results: List[Dict]) -> List[Dict]:
    """
    根据URL去重，保留第一次出现的结果

    Args:
        results: 结果列表

    Returns:
        去重后的结果列表
    """
    seen_urls = set()
    deduplicated = []

    for r in results:
        url = r.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduplicated.append(r)

    if len(results) > len(deduplicated):
        print(f"  URL去重: {len(results)} -> {len(deduplicated)} (移除 {len(results) - len(deduplicated)} 个重复)")

    return deduplicated


def deduplicate_by_url_keep_longest(results: List[Dict]) -> List[Dict]:
    """
    根据URL去重，保留content最长的那个

    Args:
        results: 结果列表

    Returns:
        去重后的结果列表
    """
    url_dict = {}

    for r in results:
        url = r.get('url', '')
        if not url:
            continue

        content = r.get('content', '')
        content_length = len(content) if content else 0

        # 如果URL已存在，比较content长度
        if url in url_dict:
            existing_length = len(url_dict[url].get('content', ''))
            if content_length > existing_length:
                url_dict[url] = r  # 保留content更长的
        else:
            url_dict[url] = r

    deduplicated = list(url_dict.values())

    if len(results) > len(deduplicated):
        print(f"  URL去重(保留最长): {len(results)} -> {len(deduplicated)} (移除 {len(results) - len(deduplicated)} 个重复)")

    return deduplicated


def format_final_results(results: List[Dict]) -> List[Dict]:
    """
    格式化最终返回给前端的结果（包含URL去重）

    Args:
        results: 筛选后的结果列表

    Returns:
        格式化后的结果列表，包含 {url, title, content, host, engine, relevance_score, authority_score}
    """
    # 先进行URL去重
    results = deduplicate_by_url(results)

    formatted = []
    for r in results:
        formatted.append({
            'url': r['url'],
            'title': r['title'],
            'content': r['content'],
            'host': r['host'],
            'engine': r['engine'],
            'relevance_score': r['relevance_score'],
            'relevance_reason': r.get('relevance_reason', ''),
            'authority_score': r['authority_score'],
            'authority_reason': r.get('authority_reason', '')
        })
    return formatted


# 测试代码
if __name__ == '__main__':
    # 测试URL解析
    test_urls = [
        "https://www.pku.edu.cn/news/article123",
        "http://www.baidu.com/search?q=test",
        "www.example.com/path",
        "invalid-url"
    ]

    print("测试URL解析:")
    for url in test_urls:
        host = extract_host(url)
        print(f"  {url} -> {host}")

    # 测试结果筛选
    test_results = [
        {'url': 'url1', 'relevance_score': 2, 'authority_score': 4},
        {'url': 'url2', 'relevance_score': 2, 'authority_score': 3},
        {'url': 'url3', 'relevance_score': 1, 'authority_score': 4},
        {'url': 'url4', 'relevance_score': 2, 'authority_score': 4},
    ]

    print("\n测试结果筛选:")
    filtered = filter_results(test_results)
    print(f"筛选后结果: {filtered}")

    # 测试URL去重
    print("\n测试URL去重:")
    test_dup_results = [
        {'url': 'http://example.com/1', 'title': 'Title 1'},
        {'url': 'http://example.com/2', 'title': 'Title 2'},
        {'url': 'http://example.com/1', 'title': 'Title 1 Duplicate'},  # 重复
        {'url': 'http://example.com/3', 'title': 'Title 3'},
    ]
    dedup_results = deduplicate_by_url(test_dup_results)
    print(f"去重前: {len(test_dup_results)}, 去重后: {len(dedup_results)}")
