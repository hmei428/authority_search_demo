"""
权威网站白名单管理
支持动态添加和持久化存储
"""
import json
import os
from typing import Dict, Tuple

# 白名单文件路径
WHITELIST_FILE = os.path.join(os.path.dirname(__file__), 'authority_whitelist.json')

# 默认白名单（初始化）
DEFAULT_WHITELIST = {
    # 政府机构（分数4）
    'www.gov.cn': {'score': 4, 'reason': '中国政府官网'},
    'www.beijing.gov.cn': {'score': 4, 'reason': '北京市政府'},
    'www.shanghai.gov.cn': {'score': 4, 'reason': '上海市政府'},

    # 知名大学（分数4）
    'www.pku.edu.cn': {'score': 4, 'reason': '北京大学'},
    'www.tsinghua.edu.cn': {'score': 4, 'reason': '清华大学'},
    'www.fudan.edu.cn': {'score': 4, 'reason': '复旦大学'},
    'www.zju.edu.cn': {'score': 4, 'reason': '浙江大学'},

    # 官方平台（分数4）
    'support.microsoft.com': {'score': 4, 'reason': 'Microsoft官方支持'},
    'developer.mozilla.org': {'score': 4, 'reason': 'MDN官方文档'},
    'docs.python.org': {'score': 4, 'reason': 'Python官方文档'},
    'nodejs.org': {'score': 4, 'reason': 'Node.js官网'},

    # 权威媒体（分数4）
    'www.xinhuanet.com': {'score': 4, 'reason': '新华网'},
    'www.people.com.cn': {'score': 4, 'reason': '人民网'},
    'www.chinanews.com.cn': {'score': 4, 'reason': '中国新闻网'},

    # 学术资源（分数4）
    'scholar.google.com': {'score': 4, 'reason': 'Google学术'},
    'www.ncbi.nlm.nih.gov': {'score': 4, 'reason': 'NCBI'},
    'www.nature.com': {'score': 4, 'reason': 'Nature'},

    # 知名行业网站（分数3）
    'www.zhihu.com': {'score': 3, 'reason': '知乎'},
    'www.csdn.net': {'score': 3, 'reason': 'CSDN'},
    'stackoverflow.com': {'score': 3, 'reason': 'Stack Overflow'},
}


class AuthorityWhitelist:
    """权威网站白名单管理器"""

    def __init__(self):
        self.whitelist = self._load_whitelist()

    def _load_whitelist(self) -> Dict:
        """从文件加载白名单"""
        if os.path.exists(WHITELIST_FILE):
            try:
                with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载白名单失败: {e}，使用默认白名单")
                return DEFAULT_WHITELIST.copy()
        else:
            # 首次运行，保存默认白名单
            self._save_whitelist(DEFAULT_WHITELIST)
            return DEFAULT_WHITELIST.copy()

    def _save_whitelist(self, whitelist: Dict):
        """保存白名单到文件"""
        try:
            with open(WHITELIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(whitelist, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存白名单失败: {e}")

    def get_score(self, host: str) -> Tuple[int, str]:
        """
        获取host的权威性分数

        Returns:
            (分数, 理由) 如果不在白名单中返回 (None, None)
        """
        if host in self.whitelist:
            entry = self.whitelist[host]
            return entry['score'], entry['reason']
        return None, None

    def add_host(self, host: str, score: int, reason: str):
        """
        添加新的host到白名单

        Args:
            host: 域名
            score: 权威性分数 (1-4)
            reason: 理由
        """
        if score not in [1, 2, 3, 4]:
            print(f"无效的分数: {score}，必须在1-4之间")
            return

        self.whitelist[host] = {
            'score': score,
            'reason': reason
        }
        self._save_whitelist(self.whitelist)
        print(f"✓ 已添加到白名单: {host} -> {score} ({reason})")

    def get_stats(self) -> Dict:
        """获取白名单统计信息"""
        stats = {1: 0, 2: 0, 3: 0, 4: 0}
        for entry in self.whitelist.values():
            stats[entry['score']] = stats.get(entry['score'], 0) + 1
        return {
            'total': len(self.whitelist),
            'distribution': stats
        }


# 全局单例
_whitelist_instance = None

def get_whitelist() -> AuthorityWhitelist:
    """获取白名单单例"""
    global _whitelist_instance
    if _whitelist_instance is None:
        _whitelist_instance = AuthorityWhitelist()
    return _whitelist_instance


# 测试代码
if __name__ == '__main__':
    whitelist = get_whitelist()

    print("白名单统计:")
    stats = whitelist.get_stats()
    print(f"  总数: {stats['total']}")
    print(f"  分布: {stats['distribution']}")

    print("\n测试查询:")
    test_hosts = ['www.pku.edu.cn', 'www.baidu.com', 'unknown.com']
    for host in test_hosts:
        score, reason = whitelist.get_score(host)
        if score:
            print(f"  {host}: {score} ({reason})")
        else:
            print(f"  {host}: 不在白名单")

    print("\n测试添加:")
    whitelist.add_host('www.mit.edu', 4, 'MIT官网')
