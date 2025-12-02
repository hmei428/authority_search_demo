// 全局变量
let currentQuery = '';

// 页面加载完成后绑定事件
document.addEventListener('DOMContentLoaded', function() {
    // 绑定回车键搜索
    document.getElementById('queryInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
});

// 处理搜索
async function handleSearch() {
    const queryInput = document.getElementById('queryInput');
    const query = queryInput.value.trim();
    const selectedEngines = Array.from(
        document.querySelectorAll('.engine-checkboxes input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    if (!query) {
        alert('请输入查询内容');
        return;
    }

    if (selectedEngines.length === 0) {
        alert('请至少选择一个搜索引擎');
        return;
    }

    currentQuery = query;

    // 隐藏之前的结果和错误
    hideSection('resultsSection');
    hideSection('rawResultsSection');
    hideSection('statsSection');
    hideSection('errorSection');

    // 显示加载状态
    showSection('loadingSection');
    setButtonLoading(true);

    // 重置加载步骤
    resetLoadingSteps();

    try {
        // 发送请求
        // 使用相对路径以兼容 WebIDE 等有代理前缀的环境
        const response = await fetch('api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                selected_engines: selectedEngines
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success) {
            // 显示结果
            displayResults(data);
        } else {
            throw new Error(data.error || '未知错误');
        }

    } catch (error) {
        console.error('搜索失败:', error);
        showError(error.message);
    } finally {
        hideSection('loadingSection');
        setButtonLoading(false);
    }
}

// 显示结果
function displayResults(data) {
    // 显示统计信息
    document.getElementById('queryText').textContent = data.query;
    document.getElementById('rawCount').textContent = data.total_raw_results;
    document.getElementById('filteredCount').textContent = data.total_filtered_results;
    showSection('statsSection');

    // 显示结果列表
    const resultsList = document.getElementById('resultsList');
    resultsList.innerHTML = '';

    if (data.results.length === 0) {
        resultsList.innerHTML = `
            <div style="text-align: center; padding: 40px; background: white; border-radius: 12px;">
                <div style="font-size: 3rem; margin-bottom: 20px;">📭</div>
                <h3 style="color: #666; margin-bottom: 10px;">未找到符合条件的结果</h3>
                <p style="color: #999;">尝试换个查询词，或者降低筛选标准</p>
            </div>
        `;
    } else {
        data.results.forEach((result, index) => {
            const resultItem = createResultItem(result, index + 1);
            resultsList.appendChild(resultItem);
        });
    }

    showSection('resultsSection');

    // 显示原始结果
    if (data.raw_results_by_engine) {
        displayRawResults(data.raw_results_by_engine);
        showSection('rawResultsSection');
    }

    // 滚动到结果区域
    setTimeout(() => {
        document.getElementById('resultsSection').scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }, 100);
}

// 创建结果项
function createResultItem(result, index) {
    const div = document.createElement('div');
    div.className = 'result-item';
    div.style.animationDelay = `${index * 0.1}s`;

    div.innerHTML = `
        <div class="result-header">
            <div style="flex: 1;">
                <a href="${escapeHtml(result.url)}" target="_blank" class="result-title">
                    ${index}. ${escapeHtml(result.title)}
                </a>
                <div class="result-url">
                    <span class="result-host">${escapeHtml(result.host)}</span> › ${escapeHtml(result.url)}
                </div>
            </div>
            <div class="result-badges">
                <span class="badge badge-engine">${escapeHtml(result.engine)}</span>
            </div>
        </div>

        <div class="result-content">
            ${escapeHtml(result.content || '无内容摘要')}
        </div>

        <div class="result-scores">
            <div class="score-item">
                <span class="badge badge-relevance">
                    相关性: ${result.relevance_score}
                </span>
                <span style="color: #999; margin-left: 8px;">${escapeHtml(result.relevance_reason)}</span>
            </div>
            <div class="score-item">
                <span class="badge badge-authority">
                    权威性: ${result.authority_score}
                </span>
                <span style="color: #999; margin-left: 8px;">${escapeHtml(result.authority_reason)}</span>
            </div>
        </div>
    `;

    return div;
}

// 显示错误
function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    showSection('errorSection');
}

// 工具函数：显示section
function showSection(id) {
    document.getElementById(id).style.display = 'block';
}

// 工具函数：隐藏section
function hideSection(id) {
    document.getElementById(id).style.display = 'none';
}

// 设置按钮加载状态
function setButtonLoading(isLoading) {
    const btn = document.getElementById('searchBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');

    if (isLoading) {
        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoading.style.display = 'inline';
    } else {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

// 重置加载步骤
function resetLoadingSteps() {
    const steps = ['step1', 'step2', 'step3', 'step4'];
    steps.forEach(stepId => {
        const step = document.getElementById(stepId);
        step.classList.remove('active', 'completed');
    });

    // 模拟步骤进度（实际应该由后端推送）
    setTimeout(() => document.getElementById('step1').classList.add('active'), 100);
    setTimeout(() => {
        document.getElementById('step1').classList.remove('active');
        document.getElementById('step1').classList.add('completed');
        document.getElementById('step2').classList.add('active');
    }, 3000);
    setTimeout(() => {
        document.getElementById('step2').classList.remove('active');
        document.getElementById('step2').classList.add('completed');
        document.getElementById('step3').classList.add('active');
    }, 8000);
    setTimeout(() => {
        document.getElementById('step3').classList.remove('active');
        document.getElementById('step3').classList.add('completed');
        document.getElementById('step4').classList.add('active');
    }, 13000);
}

// HTML转义
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// 显示原始搜索结果
let currentEngine = null;
let allRawResults = {};

function displayRawResults(rawResultsByEngine) {
    allRawResults = rawResultsByEngine;
    const engines = Object.keys(rawResultsByEngine);

    // 渲染引擎标签
    const tabsContainer = document.getElementById('engineTabs');
    tabsContainer.innerHTML = '';

    engines.forEach((engine, index) => {
        const tab = document.createElement('div');
        tab.className = 'engine-tab';
        tab.textContent = `${getEngineDisplayName(engine)} (${rawResultsByEngine[engine].length})`;
        tab.onclick = () => switchEngine(engine);

        // 默认显示第一个引擎
        if (index === 0) {
            tab.classList.add('active');
            currentEngine = engine;
        }

        tabsContainer.appendChild(tab);
    });

    // 显示第一个引擎的结果
    if (engines.length > 0) {
        renderRawResults(rawResultsByEngine[engines[0]]);
    }
}

// 切换引擎
function switchEngine(engine) {
    currentEngine = engine;

    // 更新标签样式
    const tabs = document.querySelectorAll('.engine-tab');
    tabs.forEach(tab => {
        if (tab.textContent.startsWith(getEngineDisplayName(engine))) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    // 渲染该引擎的结果
    renderRawResults(allRawResults[engine]);
}

// 渲染原始结果列表
function renderRawResults(results) {
    const container = document.getElementById('rawResultsList');
    container.innerHTML = '';

    if (!results || results.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; background: white; border-radius: 12px;">
                <div style="font-size: 2rem; margin-bottom: 15px;">📭</div>
                <p style="color: #999;">该搜索引擎暂无结果</p>
            </div>
        `;
        return;
    }

    results.forEach((result, index) => {
        const item = createRawResultItem(result, index + 1);
        container.appendChild(item);
    });

    // 滚动到原始结果区域
    setTimeout(() => {
        document.getElementById('rawResultsSection').scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }, 100);
}

// 创建原始结果项
function createRawResultItem(result, index) {
    const div = document.createElement('div');
    div.className = 'raw-result-item';

    div.innerHTML = `
        <div class="raw-result-header">
            <a href="${escapeHtml(result.url)}" target="_blank" class="raw-result-title">
                ${index}. ${escapeHtml(result.title)}
            </a>
            <div class="raw-result-url">
                <span style="font-weight: 500;">${escapeHtml(result.host)}</span> › ${escapeHtml(result.url)}
            </div>
        </div>

        <div class="raw-result-content">
            ${escapeHtml(result.content || '无内容摘要')}
        </div>

        <div class="raw-result-scores">
            <div class="raw-score-badge">
                <span class="label">相关性:</span>
                <span class="value score-${result.relevance_score}">${result.relevance_score}</span>
                <span style="color: #999; font-size: 0.8rem;">${escapeHtml(result.relevance_reason || '')}</span>
            </div>
            <div class="raw-score-badge">
                <span class="label">权威性:</span>
                <span class="value score-${result.authority_score}">${result.authority_score}</span>
                <span style="color: #999; font-size: 0.8rem;">${escapeHtml(result.authority_reason || '')}</span>
            </div>
        </div>
    `;

    return div;
}

// 获取引擎显示名称
function getEngineDisplayName(engine) {
    const names = {
        'google': '🔍 Google',
        'bing': '🔍 Bing',
        'baidu': '🔍 Baidu',
        'sogou': '🔍 Sogou',
        'quark': '🔍 Quark',
        'jina': '🔍 Jina'
    };
    return names[engine] || engine;
}
