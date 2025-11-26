# 权威Query查询系统 Demo

## 项目简介

这是一个基于多搜索引擎和AI打分的权威query查询系统。系统通过以下流程，为主管提供高质量、权威的搜索结果：

1. **并行调用6个搜索引擎**：获取每个引擎的top10结果（共60条）
2. **相关性打分**：使用AI模型评估内容与query的相关性（0/1/2）
3. **权威性打分**：使用AI模型评估网站host的权威性（1/2/3/4）
4. **智能筛选**：只保留相关性=2且权威性=4的结果
5. **结果展示**：以网页形式展示筛选后的权威结果

## 项目结构

```
authority-query-demo/
├── backend/                    # 后端服务
│   ├── services/              # 核心服务模块
│   │   ├── websearch_service.py      # 搜索引擎调用（6个引擎并行）
│   │   ├── relevance_scorer.py       # 相关性打分（0/1/2）
│   │   ├── authority_scorer.py       # 权威性打分（1/2/3/4）
│   │   └── result_processor.py       # 结果处理和筛选
│   ├── api/                   # API路由
│   └── app.py                 # Flask主应用
├── frontend/                  # 前端界面
│   ├── templates/
│   │   └── index.html        # 主页面
│   ├── static/
│   │   ├── css/style.css     # 样式
│   │   └── js/main.js        # 前端逻辑
├── requirements.txt           # Python依赖
├── start.sh                   # 启动脚本
└── README.md                  # 说明文档
```

## 技术架构

### 后端技术
- **Flask**: Web框架
- **OpenAI Client**: 调用小红书内部LLM服务（qwen3-30b-a3b）
- **多线程并发**: ThreadPoolExecutor实现高并发处理
- **智能重试机制**: 自动重试失败的API调用

### 前端技术
- **原生HTML/CSS/JavaScript**: 简洁高效
- **响应式设计**: 支持PC和移动端
- **实时反馈**: 展示处理进度和统计信息

### 搜索引擎配置
| 引擎名称 | 引擎代码 | 说明 |
|---------|---------|------|
| Jina | search_pro_jina | Jina搜索引擎 |
| Google | search_prime | Google搜索 |
| Bing | search_pro_ms | Bing搜索 |
| Sogou | search_live | 搜狗搜索 |
| Quark | search_lite | 夸克搜索 |
| Baidu | search_plus | 百度搜索 |

## 快速开始

### 环境要求
- Python 3.8+
- pip
- 访问小红书内网（需要访问内部API）

### 安装步骤

1. **克隆或下载项目**
   ```bash
   cd /Users/meihaojie/Desktop/demo/authority-query-demo
   ```

2. **使用启动脚本（推荐）**
   ```bash
   ./start.sh
   ```

   启动脚本会自动：
   - 创建Python虚拟环境
   - 安装所有依赖
   - 启动Flask服务

3. **手动启动（可选）**
   ```bash
   # 创建虚拟环境
   python3 -m venv venv

   # 激活虚拟环境
   source venv/bin/activate

   # 安装依赖
   pip install -r requirements.txt

   # 启动服务
   cd backend
   python app.py
   ```

4. **访问系统**

   打开浏览器访问：`http://localhost:5000`

## 使用说明

### 基本使用流程

1. 在搜索框输入查询词（如："考研数学二大纲"）
2. 点击"搜索"按钮或按回车键
3. 等待系统处理（约15-30秒）：
   - ⏳ 调用6个搜索引擎...
   - ⏳ 相关性打分...
   - ⏳ 权威性打分...
   - ⏳ 筛选结果...
4. 查看筛选后的权威结果

### 结果说明

每个结果卡片包含：
- **标题**：网页标题（可点击跳转）
- **URL和Host**：完整URL和域名
- **内容摘要**：网页内容预览
- **来源引擎**：该结果来自哪个搜索引擎
- **相关性分数**：0/1/2（系统只展示分数=2的结果）
- **权威性分数**：1/2/3/4（系统只展示分数=4的结果）
- **评分理由**：AI给出的打分依据

### 统计信息

页面顶部显示：
- **查询词**：当前搜索的query
- **原始结果数**：从搜索引擎获取的总结果数（通常60条）
- **筛选后数量**：符合条件的权威结果数

## API接口

### POST /api/query

处理查询请求

**请求体：**
```json
{
  "query": "考研数学二大纲"
}
```

**响应体：**
```json
{
  "success": true,
  "query": "考研数学二大纲",
  "total_raw_results": 60,
  "total_filtered_results": 5,
  "results": [
    {
      "url": "https://...",
      "title": "...",
      "content": "...",
      "host": "www.example.com",
      "engine": "google",
      "relevance_score": 2,
      "relevance_reason": "完整回答问题",
      "authority_score": 4,
      "authority_reason": "官方网站"
    }
  ],
  "stats": {
    "search_engines": {...},
    "relevance_distribution": {...},
    "authority_distribution": {...}
  }
}
```

### GET /api/health

健康检查接口

**响应体：**
```json
{
  "status": "ok",
  "service": "authority-query-demo"
}
```

## 配置说明

### API配置

所有API密钥和地址都在各服务模块中配置：

**搜索引擎API** (`backend/services/websearch_service.py`)
```python
API_URL = 'https://runway.devops.xiaohongshu.com/openai/zhipu/paas/v4/web_search'
API_KEY = '83834a049770445a912608da03702901'
```

**LLM服务API** (`backend/services/relevance_scorer.py` 和 `authority_scorer.py`)
```python
API_KEY = "MAAS680934ffb1a349259ed7beae4272175b"
BASE_URL = "http://redservingapi.devops.xiaohongshu.com/v1"
MODEL = "qwen3-30b-a3b"
```

### 筛选阈值配置

在 `backend/app.py` 中可以修改筛选条件：
```python
filtered = filter_results(scored_results,
                         relevance_threshold=2,    # 相关性阈值
                         authority_threshold=4)     # 权威性阈值
```

### 并发配置

可以在各服务模块中调整并发数：
```python
# websearch_service.py
search_all_engines(query, max_workers=6)

# relevance_scorer.py
score_relevance_batch(results, query, max_workers=32)

# authority_scorer.py
score_authority_batch(results, max_workers=32)
```

## 性能说明

### 处理时间
- **搜索引擎调用**：3-5秒（6个引擎并行）
- **相关性打分**：5-10秒（60个结果，32并发）
- **权威性打分**：3-5秒（去重后的host，32并发）
- **总耗时**：约15-30秒

### 优化建议
1. 增加LLM API并发数（修改 `max_workers`）
2. 使用缓存机制存储host的权威性分数
3. 对相同query的结果进行缓存
4. 使用更快的LLM模型（如需要）

## 故障排查

### 常见问题

1. **端口被占用**
   ```
   Error: Address already in use
   ```
   解决：修改 `backend/app.py` 中的端口号，或杀掉占用5000端口的进程

2. **依赖安装失败**
   ```
   pip install error
   ```
   解决：更新pip版本 `pip install --upgrade pip`，然后重新安装

3. **API调用失败**
   ```
   HTTP 401/403
   ```
   解决：检查API key是否正确，确保在小红书内网环境

4. **结果为空**
   - 检查搜索引擎API是否正常
   - 尝试降低筛选阈值
   - 查看后端日志了解详细错误

### 查看日志

后端运行时会在终端输出详细日志：
```
[步骤 1/5] 搜索引擎查询...
✓ google: 获取到 10 条结果
✓ baidu: 获取到 10 条结果
...
[步骤 3/5] 相关性打分...
  进度: 10/60
...
```

## 后续优化方向

1. **性能优化**
   - 添加Redis缓存
   - 实现异步处理
   - 使用消息队列处理长任务

2. **功能增强**
   - 支持批量查询
   - 导出结果为Excel/CSV
   - 添加查询历史记录
   - 支持自定义筛选阈值

3. **界面改进**
   - 添加实时进度条
   - 支持结果对比
   - 添加数据可视化图表

4. **模型优化**
   - 微调prompt提高打分准确率
   - 使用更强的模型
   - 添加人工反馈循环

## 联系方式

如有问题或建议，请联系开发者。

---

**Powered by Claude Code** 🚀
