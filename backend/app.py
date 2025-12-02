"""
Flask后端API
提供权威query查询服务
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# 添加服务路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from services.websearch_service import get_search_results
from services.relevance_scorer import score_relevance_batch
from services.authority_scorer import score_authority_batch
from services.result_processor import add_host_to_results, filter_results, format_final_results, deduplicate_by_url_keep_longest

app = Flask(__name__,
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/query', methods=['POST'])
def process_query():
    """
    处理查询请求

    请求格式:
    {
        "query": "考研数学二大纲"
    }

    返回格式:
    {
        "success": true,
        "query": "考研数学二大纲",
        "total_raw_results": 60,
        "total_filtered_results": 5,
        "results": [
            {
                "url": "...",
                "title": "...",
                "content": "...",
                "host": "...",
                "engine": "google",
                "relevance_score": 2,
                "relevance_reason": "...",
                "authority_score": 4,
                "authority_reason": "..."
            }
        ],
        "stats": {
            "search_engines": {...},
            "relevance_distribution": {...},
            "authority_distribution": {...}
        }
    }
    """
    try:
        # 1. 获取query和选中的搜索引擎
        data = request.get_json()
        query = data.get('query', '').strip()
        selected_engines = data.get('selected_engines', [])  # 新增：前端传来的引擎列表

        if not query:
            return jsonify({
                'success': False,
                'error': 'Query不能为空'
            }), 400

        print(f"\n{'='*60}")
        print(f"收到查询: {query}")
        if selected_engines:
            print(f"选中引擎: {', '.join(selected_engines)}")
        print(f"{'='*60}")

        # 2. 调用搜索引擎获取结果（支持引擎筛选）
        print("\n[步骤 1/6] 搜索引擎查询...")
        search_results, search_stats = get_search_results(query, selected_engines)

        if not search_results:
            return jsonify({
                'success': False,
                'error': '未获取到搜索结果'
            }), 500

        # 3. 提取host
        print("\n[步骤 2/6] 提取URL的host...")
        search_results = add_host_to_results(search_results)

        # 4. 早期URL去重（保留content最长的）
        print("\n[步骤 3/6] URL去重(保留content最长)...")
        search_results = deduplicate_by_url_keep_longest(search_results)

        # 5. 并行进行权威性与相关性打分
        print("\n[步骤 4/6] 权威性与相关性打分(并行)...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            authority_future = executor.submit(score_authority_batch, search_results)
            relevance_future = executor.submit(score_relevance_batch, search_results, query)
            authority_scored = authority_future.result()
            relevance_scored = relevance_future.result()

        if len(authority_scored) != len(relevance_scored):
            raise ValueError("权威性和相关性结果数量不一致")

        combined_results = []
        for auth_result, rel_result in zip(authority_scored, relevance_scored):
            combined = auth_result.copy()
            combined['relevance_score'] = rel_result.get('relevance_score', -1)
            combined['relevance_reason'] = rel_result.get('relevance_reason', '')
            combined_results.append(combined)

        # 6. 排序结果（权威性降序 -> 相关性降序）
        print("\n[步骤 5/6] 排序结果...")
        # 先按权威性降序，再按相关性降序
        sorted_results = sorted(
            combined_results,
            key=lambda x: (
                -x.get('authority_score', -1),  # 权威性降序（4->3->2->1）
                -x.get('relevance_score', -1)   # 相关性降序（2->1->0）
            )
        )

        # 7. 格式化结果
        print("\n[步骤 6/6] 格式化输出...")
        final_results = format_final_results(sorted_results)

        # 8. 统计信息（包含所有打分结果）
        stats = {
            'search_engines': search_stats['engines'],
            'relevance_distribution': {},
            'authority_distribution': {}
        }

        for r in combined_results:
            rel_score = r.get('relevance_score', -1)
            auth_score = r.get('authority_score', -1)
            stats['relevance_distribution'][rel_score] = stats['relevance_distribution'].get(rel_score, 0) + 1
            stats['authority_distribution'][auth_score] = stats['authority_distribution'].get(auth_score, 0) + 1

        # 9. 按引擎分组原始结果
        raw_results_by_engine = {}
        for r in combined_results:
            engine = r.get('engine', 'unknown')
            if engine not in raw_results_by_engine:
                raw_results_by_engine[engine] = []
            raw_results_by_engine[engine].append({
                'url': r['url'],
                'title': r['title'],
                'content': r['content'],
                'host': r['host'],
                'relevance_score': r.get('relevance_score', -1),
                'relevance_reason': r.get('relevance_reason', ''),
                'authority_score': r.get('authority_score', -1),
                'authority_reason': r.get('authority_reason', '')
            })

        print(f"\n{'='*60}")
        print(f"处理完成!")
        print(f"  原始结果数: {len(search_results)}")
        print(f"  排序后数量: {len(final_results)}")
        print(f"  排序规则: 权威性(4→3→2→1) -> 相关性(2→1→0)")
        print(f"{'='*60}\n")

        # 10. 返回结果
        return jsonify({
            'success': True,
            'query': query,
            'total_raw_results': len(search_results),
            'total_filtered_results': len(final_results),
            'results': final_results,
            'raw_results_by_engine': raw_results_by_engine,  # 新增：按引擎分组的原始结果
            'stats': stats
        })

    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'service': 'authority-query-demo'
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("权威Query查询系统启动中...")
    print("="*60)
    print("\n访问地址: http://localhost:5000")
    print("API文档: http://localhost:5000/api/health\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
