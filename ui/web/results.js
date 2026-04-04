/**
 * 太玄智译 - 翻译结果展示页面 v2.0
 * 对接后端 API + 本地JSON数据
 */

// API基础URL
const API_BASE = 'http://127.0.0.1:8000';

// 全局状态
const state = {
    translations: [],
    filtered: [],
    stats: {
        total: 0,
        success: 0,
        failed: 0,
        cached: 0,
        newTranslated: 0,
        totalSourceChars: 0,
        totalTargetChars: 0,
        avgTime: 0,
        engines: {}
    },
    currentPage: 1,
    pageSize: 20,
    currentView: 'bilingual',
    filters: {
        search: '',
        status: '',
        engine: ''
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    initTabs();
    initFilters();
    initPagination();
    initExport();
    await loadData();
});

/**
 * 加载数据
 */
async function loadData() {
    showLoading(true);
    
    // 1. 尝试从API获取
    try {
        const response = await fetch(`${API_BASE}/api/translations/latest`);
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.data?.length > 0) {
                state.translations = result.data;
            }
        }
    } catch (e) {
        console.log('API数据获取失败，使用本地JSON');
    }
    
    // 2. 如果API无数据，加载本地JSON
    if (state.translations.length === 0) {
        await loadLocalData();
    }
    
    // 3. 处理数据
    processTranslations();
    updateStatsDisplay();
    renderList();
    
    showLoading(false);
}

/**
 * 加载本地JSON
 */
async function loadLocalData() {
    const jsonFiles = [
        '../translator/output/translations_demo_20260401_185640.json',
        '../translator/output/translations_demo_20260401_004833.json'
    ];
    
    for (const file of jsonFiles) {
        try {
            const response = await fetch(file);
            if (response.ok) {
                const data = await response.json();
                if (Array.isArray(data) && data.length > 0) {
                    state.translations = data;
                    console.log(`加载本地数据: ${data.length} 条`);
                    break;
                }
            }
        } catch (e) {
            console.warn(`加载 ${file} 失败:`, e);
        }
    }
}

/**
 * 处理翻译数据
 */
function processTranslations() {
    state.filtered = [...state.translations];
    
    // 计算统计
    state.stats = {
        total: state.translations.length,
        success: state.translations.filter(t => t.status === 'success').length,
        failed: state.translations.filter(t => t.status === 'failed').length,
        cached: state.translations.filter(t => t.status === 'cached').length,
        newTranslated: state.translations.filter(t => t.status === 'success' && !t.from_cache).length,
        totalSourceChars: 0,
        totalTargetChars: 0,
        avgTime: 0,
        engines: {}
    };
    
    let totalTime = 0;
    state.translations.forEach(t => {
        state.stats.totalSourceChars += t.char_count_src || 0;
        state.stats.totalTargetChars += t.char_count_tgt || 0;
        totalTime += t.processing_time_ms || 0;
        
        const engine = t.engine || 'unknown';
        state.stats.engines[engine] = (state.stats.engines[engine] || 0) + 1;
    });
    
    state.stats.avgTime = state.translations.length > 0 
        ? totalTime / state.translations.length 
        : 0;
}

/**
 * 更新统计显示
 */
function updateStatsDisplay() {
    document.getElementById('totalCount').textContent = state.stats.total.toLocaleString();
    document.getElementById('successCount').textContent = state.stats.cached.toLocaleString();
    document.getElementById('newCount').textContent = state.stats.newTranslated.toLocaleString();
    document.getElementById('avgTime').textContent = formatTime(state.stats.avgTime);
    document.getElementById('successRate').textContent = 
        Math.round(((state.stats.success + state.stats.cached) / state.stats.total) * 100) + '%';
    
    // 更新引擎分布
    renderEngineDistribution();
    renderTimeStats();
    renderCharChart();
}

/**
 * 渲染引擎分布
 */
function renderEngineDistribution() {
    const container = document.getElementById('engineDist');
    if (!container) return;
    
    const engines = state.stats.engines;
    const max = Math.max(...Object.values(engines), 1);
    
    const colors = {
        'demo': '#94a3b8',
        'deepseek': '#06B6D4',
        'openai': '#4ADE80',
        'claude': '#A78BFA',
        'qwen': '#34D399',
        'minimax': '#FB923C',
        'ollama': '#F472B6'
    };
    
    container.innerHTML = Object.entries(engines)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => `
            <div class="engine-item">
                <span class="engine-name">${name}</span>
                <div class="engine-bar-wrapper">
                    <div class="engine-bar" style="width: ${(count / max) * 100}%; background: ${colors[name] || '#3B82F6'}">
                        <span class="engine-count">${count}</span>
                    </div>
                </div>
            </div>
        `).join('');
}

/**
 * 渲染时间统计
 */
function renderTimeStats() {
    const container = document.getElementById('timeStats');
    if (!container) return;
    
    const times = state.translations
        .map(t => t.processing_time_ms || 0)
        .filter(t => t > 0)
        .sort((a, b) => a - b);
    
    if (times.length === 0) {
        container.innerHTML = '<div class="no-data">暂无时间数据</div>';
        return;
    }
    
    const min = times[0];
    const max = times[times.length - 1];
    const avg = times.reduce((a, b) => a + b, 0) / times.length;
    const median = times[Math.floor(times.length / 2)];
    
    container.innerHTML = `
        <div class="time-item">
            <span class="time-label">最短</span>
            <span class="time-value">${min}ms</span>
        </div>
        <div class="time-item">
            <span class="time-label">平均</span>
            <span class="time-value">${Math.round(avg)}ms</span>
        </div>
        <div class="time-item">
            <span class="time-label">中位数</span>
            <span class="time-value">${median}ms</span>
        </div>
        <div class="time-item">
            <span class="time-label">最长</span>
            <span class="time-value">${max}ms</span>
        </div>
    `;
}

/**
 * 渲染字符图表
 */
function renderCharChart() {
    const container = document.getElementById('charBars');
    if (!container) return;
    
    const sampleSize = Math.min(30, state.translations.length);
    const step = Math.max(1, Math.floor(state.translations.length / sampleSize));
    const maxChars = 2000;
    
    let bars = '';
    for (let i = 0; i < sampleSize; i++) {
        const idx = i * step;
        if (idx >= state.translations.length) break;
        
        const t = state.translations[idx];
        const srcHeight = Math.min((t.char_count_src || 0) / maxChars * 100, 100);
        const tgtHeight = Math.min((t.char_count_tgt || 0) / maxChars * 100, 100);
        
        bars += `
            <div class="chart-bar-wrapper">
                <div style="display:flex;flex-direction:column;height:100%;align-items:center;justify-content:flex-end;">
                    <div style="display:flex;gap:2px;align-items:flex-end;">
                        <div class="chart-bar source" style="height:${srcHeight}px;width:12px;" title="原文: ${t.char_count_src}"></div>
                        <div class="chart-bar target" style="height:${tgtHeight}px;width:12px;" title="译文: ${t.char_count_tgt}"></div>
                    </div>
                </div>
                <span class="chart-label">${i + 1}</span>
            </div>
        `;
    }
    
    container.innerHTML = bars;
}

/**
 * 初始化标签页
 */
function initTabs() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const view = tab.dataset.view;
            state.currentView = view;
            
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            document.querySelectorAll('.view-container').forEach(v => v.classList.remove('active'));
            document.getElementById(`${view}View`)?.classList.add('active');
            
            renderList();
        });
    });
}

/**
 * 初始化过滤器
 */
function initFilters() {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const engineFilter = document.getElementById('engineFilter');
    
    let searchTimeout;
    searchInput?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.filters.search = e.target.value.toLowerCase();
            applyFilters();
        }, 300);
    });
    
    statusFilter?.addEventListener('change', (e) => {
        state.filters.status = e.target.value;
        applyFilters();
    });
    
    engineFilter?.addEventListener('change', (e) => {
        state.filters.engine = e.target.value;
        applyFilters();
    });
}

/**
 * 应用过滤器
 */
function applyFilters() {
    state.filtered = state.translations.filter(t => {
        if (state.filters.search) {
            const search = state.filters.search;
            const matchSource = (t.source_text || '').toLowerCase().includes(search);
            const matchTarget = (t.translated_text || '').toLowerCase().includes(search);
            if (!matchSource && !matchTarget) return false;
        }
        
        if (state.filters.status && t.status !== state.filters.status) return false;
        if (state.filters.engine && t.engine !== state.filters.engine) return false;
        
        return true;
    });
    
    state.currentPage = 1;
    renderList();
    updatePagination();
}

/**
 * 渲染列表
 */
function renderList() {
    const start = (state.currentPage - 1) * state.pageSize;
    const end = start + state.pageSize;
    const pageData = state.filtered.slice(start, end);
    
    document.getElementById('resultCount').textContent = 
        `显示 ${state.filtered.length > 0 ? start + 1 : 0}-${Math.min(end, state.filtered.length)} 条，共 ${state.filtered.length} 条`;
    
    switch (state.currentView) {
        case 'bilingual':
            renderBilingual(pageData);
            break;
        case 'source':
            renderSource(pageData);
            break;
        case 'target':
            renderTarget(pageData);
            break;
        case 'stats':
            // 统计视图已渲染
            break;
    }
}

/**
 * 渲染双语对照
 */
function renderBilingual(data) {
    const container = document.getElementById('bilingualList');
    
    if (data.length === 0) {
        container.innerHTML = renderEmpty();
        return;
    }
    
    container.innerHTML = data.map((t, i) => `
        <div class="bilingual-item ${t.status || ''}">
            <div class="bilingual-header">
                <span class="para-index">#${(state.currentPage - 1) * state.pageSize + i + 1}</span>
                <div class="para-meta">
                    <span class="badge engine">${t.engine || 'demo'}</span>
                    <span class="badge ${t.status}">${getStatusLabel(t.status)}</span>
                    <span class="badge chars">${t.char_count_src || 0} → ${t.char_count_tgt || 0}</span>
                </div>
            </div>
            <div class="bilingual-content">
                <div class="source-text">
                    <span class="text-label">📖 原文</span>
                    <p>${escapeHtml(t.source_text || '')}</p>
                </div>
                <div class="target-text">
                    <span class="text-label">📝 译文</span>
                    <p>${escapeHtml(t.translated_text || '')}</p>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * 渲染原文
 */
function renderSource(data) {
    const container = document.getElementById('sourceList');
    if (data.length === 0) {
        container.innerHTML = renderEmpty();
        return;
    }
    
    container.innerHTML = data.map((t, i) => `
        <div class="source-item">
            <div class="para-id">#${(state.currentPage - 1) * state.pageSize + i + 1} - ${t.para_id || 'unknown'}</div>
            <p class="para-text">${escapeHtml(t.source_text || '')}</p>
        </div>
    `).join('');
}

/**
 * 渲染译文
 */
function renderTarget(data) {
    const container = document.getElementById('targetList');
    if (data.length === 0) {
        container.innerHTML = renderEmpty();
        return;
    }
    
    container.innerHTML = data.map((t, i) => `
        <div class="target-item">
            <div class="para-id">#${(state.currentPage - 1) * state.pageSize + i + 1} - ${t.para_id || 'unknown'}</div>
            <p class="para-text">${escapeHtml(t.translated_text || '')}</p>
        </div>
    `).join('');
}

/**
 * 初始化分页
 */
function initPagination() {
    document.getElementById('prevBtn')?.addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            renderList();
            updatePagination();
            scrollToTop();
        }
    });
    
    document.getElementById('nextBtn')?.addEventListener('click', () => {
        const totalPages = Math.ceil(state.filtered.length / state.pageSize);
        if (state.currentPage < totalPages) {
            state.currentPage++;
            renderList();
            updatePagination();
            scrollToTop();
        }
    });
}

/**
 * 更新分页
 */
function updatePagination() {
    const totalPages = Math.ceil(state.filtered.length / state.pageSize);
    
    document.getElementById('prevBtn').disabled = state.currentPage <= 1;
    document.getElementById('nextBtn').disabled = state.currentPage >= totalPages;
    document.getElementById('pageInfo').textContent = `第 ${state.currentPage} 页 / 共 ${totalPages || 1} 页`;
}

/**
 * 初始化导出
 */
function initExport() {
    document.getElementById('exportBtn')?.addEventListener('click', exportResults);
}

/**
 * 导出结果
 */
function exportResults() {
    const format = prompt('导出格式:\n1. JSON\n2. CSV\n3. TXT (双语对照)', '1');
    
    switch (format) {
        case '1': exportJSON(); break;
        case '2': exportCSV(); break;
        case '3': exportTXT(); break;
    }
}

function exportJSON() {
    const blob = new Blob([JSON.stringify(state.filtered, null, 2)], { type: 'application/json' });
    download(blob, `translations_${Date.now()}.json`);
    showToast('JSON导出成功', 'success');
}

function exportCSV() {
    const header = 'para_id,source_text,translated_text,engine,status,char_count_src,char_count_tgt\n';
    const rows = state.filtered.map(t => [
        t.para_id || '',
        `"${(t.source_text || '').replace(/"/g, '""')}"`,
        `"${(t.translated_text || '').replace(/"/g, '""')}"`,
        t.engine || '',
        t.status || '',
        t.char_count_src || 0,
        t.char_count_tgt || 0
    ].join(','));
    
    const blob = new Blob([header + rows.join('\n')], { type: 'text/csv;charset=utf-8' });
    download(blob, `translations_${Date.now()}.csv`);
    showToast('CSV导出成功', 'success');
}

function exportTXT() {
    const content = state.filtered.map((t, i) => 
        `=== 第 ${i + 1} 段 ===\n【原文】(${t.char_count_src || 0}字)\n${t.source_text}\n\n【译文】(${t.char_count_tgt || 0}字)\n${t.translated_text}`
    ).join('\n\n' + '═'.repeat(50) + '\n\n');
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    download(blob, `translations_${Date.now()}.txt`);
    showToast('TXT导出成功', 'success');
}

// 工具函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(ms) {
    if (!ms || ms < 0) return '0ms';
    if (ms < 1000) return Math.round(ms) + 'ms';
    return (ms / 1000).toFixed(1) + 's';
}

function getStatusLabel(status) {
    const labels = { success: '翻译成功', cached: '缓存命中', failed: '翻译失败' };
    return labels[status] || status || '未知';
}

function renderEmpty() {
    return '<div class="empty-state"><span class="empty-icon">📭</span><span class="empty-text">没有找到匹配的结果</span></div>';
}

function showLoading(show) {
    const overlay = document.querySelector('.loading-overlay');
    if (show && !overlay) {
        const el = document.createElement('div');
        el.className = 'loading-overlay';
        el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        document.body.appendChild(el);
    } else if (!show && overlay) {
        overlay.remove();
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function scrollToTop() {
    document.querySelector('.view-container.active')?.scrollTo(0, 0);
}
