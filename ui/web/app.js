/**
 * 太玄智译 - 前端交互脚本 v2.0
 * 对接后端 FastAPI 服务
 */

// API基础URL
const API_BASE = 'http://127.0.0.1:8000';

// 全局错误捕获 - 防止 JS 错误导致翻译中断
window.addEventListener('error', function(e) {
    console.error('[全局错误]', e.message, e.filename, e.lineno);
});
window.addEventListener('unhandledrejection', function(e) {
    console.error('[未捕获的Promise异常]', e.reason);
});

// 全局状态
const state = {
    // 当前配置
    currentEngine: 'deepseek',
    targetLanguage: 'zh-Hans',
    // bilingualMode removed - now using multiple checkboxes
    
    // 任务数据
    taskId: null,
    fileName: null,
    segments: [],  // {index, page, type, text, translated, status}
    chapters: [],
    
    // 翻译状态
    isTranslating: false,
    isPaused: false,
    currentIndex: 0,
    translatedCount: 0,
    
    // 性能追踪
    startTime: null,
    avgTimePerSegment: 0,
    
    // API配置
    config: {
        deepseek: { apiKey: 'sk-91e1657b4d8c4b0daea2095914590531', model: 'deepseek-chat' },
        claude: { apiKey: '', model: 'claude-sonnet-4-20250514' },
        qwen: { apiKey: '', model: 'qwen-turbo' },
        minimax: { apiKey: '', model: 'abab6.5s-chat' },
        ollama: { url: 'http://localhost:11434', model: 'qwen2.5:27b' },
        openai: { apiKey: '', model: 'gpt-4o-mini' }
    }
};

// ========== 动效和状态管理函数 ==========

/**
 * 更新段落状态（支持动效）
 * @param {number} index - 段落索引
 * @param {string} status - 状态: pending/translating/translated/error
 */
function updateParagraphStatus(index, status) {
    // 在源文本和译文面板中都更新
    const items = document.querySelectorAll(`[data-index="${index}"]`);
    
    items.forEach(item => {
        // 移除旧状态类
        item.classList.remove('pending', 'translating', 'translated', 'error');
        
        // 添加新状态类（触发CSS动画）
        item.classList.add(status);
        
        // 更新状态徽章
        const badge = item.querySelector('.status-badge');
        if (badge) {
            badge.classList.remove('pending', 'translating', 'success', 'error');
            
            const statusMap = {
                'pending': { class: 'pending', text: '待翻译' },
                'translating': { class: 'translating', text: '翻译中...' },
                'translated': { class: 'success', text: '已翻译' },
                'error': { class: 'error', text: '翻译失败' }
            };
            
            const statusInfo = statusMap[status];
            if (statusInfo) {
                badge.classList.add(statusInfo.class);
                badge.textContent = statusInfo.text;
            }
        }
    });
}

/**
 * 显示 Toast 通知（带动效）
 * @param {string} message - 通知消息
 * @param {string} type - 类型: success/error/warning/info
 * @param {number} duration - 显示时长(ms)
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // 触发入场动画
    setTimeout(() => toast.classList.add('show'), 10);
    
    // 自动移除
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * 更新引擎卡片状态
 * @param {string} engine - 引擎名称
 * @param {string} status - 状态: 未配置/已配置/已连接/连接中/错误
 */
function updateEngineCardStatus(engine, status) {
    const statusElement = document.getElementById(`${engine}Status`);
    if (!statusElement) return;
    
    statusElement.classList.remove('connected', 'error', 'testing');
    
    const statusMap = {
        '未配置': { class: '', text: '未配置' },
        '已配置': { class: '', text: '已配置' },
        '已连接': { class: 'connected', text: '已连接' },
        '连接中': { class: 'testing', text: '连接中...' },
        '错误': { class: 'error', text: '连接失败' }
    };
    
    const statusInfo = statusMap[status];
    if (statusInfo) {
        if (statusInfo.class) statusElement.classList.add(statusInfo.class);
        statusElement.textContent = status;
    }
}

/**
 * 初始化所有动效
 */
function initAnimations() {
    // 引擎卡片悬停效果已在 CSS 中实现
    // 这里可以添加额外的 JS 交互
    
    const cards = document.querySelectorAll('.config-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            // 可选：添加额外的 JS 效果
        });
    });
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initUpload();
    initEngineSelect();
    initButtons();
    initAnimations();
    loadConfig();
    checkApiStatus();
    // 每30秒检测一次API状态
    setInterval(checkApiStatus, 30000);
});

/**
 * 标签页切换
 */
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.getElementById(`${tabName}Panel`).classList.add('active');
            
            // 更新状态页面
            if (tabName === 'status') {
                updateStatusPanel();
            }
        });
    });
}

/**
 * 文件上传
 */
function initUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    // 点击上传
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // 拖拽上传
    let rippleAnimation = null;  // 记录当前波纹动画实例，避免重叠

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!uploadArea.classList.contains('dragover')) {
            uploadArea.classList.add('dragover');
            // Bug #001 修复：每次进入拖拽区域时用 Web Animation API 重新播放波纹
            triggerRippleAnimation(uploadArea);
        }
    });

    uploadArea.addEventListener('dragleave', (e) => {
        // 只在真正离开上传区域时移除（排除子元素触发的 dragleave）
        if (!uploadArea.contains(e.relatedTarget)) {
            uploadArea.classList.remove('dragover');
            if (rippleAnimation) {
                rippleAnimation.cancel();
                rippleAnimation = null;
            }
        }
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (rippleAnimation) {
            rippleAnimation.cancel();
            rippleAnimation = null;
        }
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    /**
     * Bug #001 修复方案B：用 Web Animation API 触发波纹动画
     * 每次调用都创建新动画实例，解决 CSS animation 不重播问题
     */
    function triggerRippleAnimation(target) {
        // 创建波纹元素（不依赖 ::after 伪元素，避免与段落状态伪元素冲突）
        const ripple = document.createElement('span');
        ripple.style.cssText = `
            position: absolute;
            top: 50%; left: 50%;
            width: 100px; height: 100px;
            border: 2px solid var(--primary);
            border-radius: 50%;
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
            pointer-events: none;
            z-index: 0;
        `;
        target.appendChild(ripple);

        rippleAnimation = ripple.animate([
            { width: '100px', height: '100px', opacity: 1,
              transform: 'translate(-50%, -50%) scale(1)' },
            { width: '300px', height: '300px', opacity: 0,
              transform: 'translate(-50%, -50%) scale(1)' }
        ], {
            duration: 600,
            easing: 'ease-out',
            fill: 'forwards'
        });

        rippleAnimation.onfinish = () => {
            ripple.remove();
            rippleAnimation = null;
        };
    }
    
    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            // Prevent double trigger by checking if already processing
            const uploadProgress = document.getElementById('uploadProgress');
            if (uploadProgress && uploadProgress.style.display === 'block') {
                return; // Already processing
            }
            handleFileUpload(e.target.files[0]);
            // Clear input to prevent re-trigger on same file
            e.target.value = '';
        }
    });
}

/**
 * 处理文件上传
 */
async function handleFileUpload(file) {
    const uploadArea = document.getElementById('uploadArea');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadPercent = document.getElementById('uploadPercent');
    const uploadProgressFill = document.getElementById('uploadProgressFill');
    const uploadFileName = document.getElementById('uploadFileName');
    
    uploadArea.style.display = 'none';
    uploadProgress.style.display = 'block';
    uploadFileName.textContent = file.name;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // 模拟进度（实际进度需要从服务端获取）
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress = Math.min(progress + 10, 90);
            uploadPercent.textContent = `${progress}%`;
            uploadProgressFill.style.width = `${progress}%`;
        }, 200);
        
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        clearInterval(progressInterval);
        
        if (!response.ok) {
            throw new Error(`上传失败: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            state.taskId = data.task_id;
            state.fileName = data.file_name;
            state.segments = data.segments.map(s => ({
                ...s,
                translated: '',
                status: 'pending'
            }));
            
            // 提取章节信息
            extractChapters();
            
            // 显示结果
            uploadPercent.textContent = '100%';
            uploadProgressFill.style.width = '100%';
            
            setTimeout(() => {
                uploadProgress.style.display = 'none';
                showUploadResult(data);
                renderChapterList();
                showToast('文件上传成功', 'success');
            }, 500);
            
            // 切换到翻译面板
            document.querySelector('[data-tab="translate"]').click();
        } else {
            throw new Error(result.message || '解析失败');
        }
    } catch (error) {
        console.error('上传错误:', error);
        uploadProgress.style.display = 'none';
        uploadArea.style.display = 'block';
        showToast('上传失败: ' + error.message, 'error');
    }
}

/**
 * 显示上传结果
 */
function showUploadResult(data) {
    const uploadResult = document.getElementById('uploadResult');
    const resultStats = document.getElementById('resultStats');
    
    uploadResult.style.display = 'block';
    resultStats.innerHTML = `
        <div class="stat">
            <span class="stat-value">${data.file_name}</span>
            <span class="stat-label">文件名</span>
        </div>
        <div class="stat">
            <span class="stat-value">${data.total_segments}</span>
            <span class="stat-label">段落数</span>
        </div>
        <div class="stat">
            <span class="stat-value">${data.total_pages || '-'}</span>
            <span class="stat-label">页数</span>
        </div>
        <div class="stat">
            <span class="stat-value">${data.parse_duration_ms}ms</span>
            <span class="stat-label">解析耗时</span>
        </div>
    `;
}

/**
 * 提取章节信息
 */
function extractChapters() {
    const chapterMap = new Map();
    
    state.segments.forEach(seg => {
        // 假设标题类型为 'title' 或文本包含 'CHAPTER'
        if (seg.type === 'title' || (seg.text && seg.text.match(/^CHAPTER\s+\d+/i))) {
            const match = seg.text.match(/CHAPTER\s+(\d+)/i);
            if (match) {
                const num = parseInt(match[1]);
                chapterMap.set(num, {
                    num,
                    title: seg.text,
                    startIndex: seg.index
                });
            }
        }
    });
    
    state.chapters = Array.from(chapterMap.values());
}

/**
 * 渲染章节列表
 */
function renderChapterList() {
    const container = document.getElementById('chapterList');
    
    if (state.chapters.length === 0) {
        // 如果没有检测到章节，显示所有段落
        container.innerHTML = '<div class="chapter-item active" data-index="0"><div class="chapter-title">全部内容</div><div class="chapter-meta">共 ' + state.segments.length + ' 段</div></div>';
    } else {
        container.innerHTML = state.chapters.map((ch, i) => `
            <div class="chapter-item" data-chapter="${ch.num}">
                <div class="chapter-title">${ch.title.substring(0, 40)}...</div>
                <div class="chapter-meta">第${ch.num}章</div>
            </div>
        `).join('');
    }
    
    // 点击事件
    container.querySelectorAll('.chapter-item').forEach(item => {
        item.addEventListener('click', () => {
            container.querySelectorAll('.chapter-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const startIndex = parseInt(item.dataset.index || 0);
            renderParagraphs(startIndex);
        });
    });
    
    // 默认显示第一页
    renderParagraphs(0);
}

/**
 * 渲染段落列表
 */
function renderParagraphs(startIndex = 0) {
    const pageSize = 10;
    const endIndex = Math.min(startIndex + pageSize, state.segments.length);
    const pageSegments = state.segments.slice(startIndex, endIndex);
    
    // 原文面板
    const sourceContainer = document.getElementById('sourceContent');
    sourceContainer.innerHTML = pageSegments.map((seg, i) => `
        <div class="paragraph-item ${seg.status === 'translated' ? 'translated' : 'pending'}" data-index="${startIndex + i}">
            <div class="para-header">
                <span>段落 ${startIndex + i + 1}</span>
                <span>${seg.page || '-'}页 | ${seg.text?.length || 0}字符</span>
            </div>
            <div class="para-text">${escapeHtml(seg.text || '')}</div>
        </div>
    `).join('');
    
    document.getElementById('sourceCount').textContent = `${state.segments.length} 段落`;
    
    // 译文面板
    const targetContainer = document.getElementById('targetContent');
    targetContainer.innerHTML = pageSegments.map((seg, i) => `
        <div class="paragraph-item ${seg.status === 'translated' ? 'translated' : 'pending'}" data-index="${startIndex + i}">
            <div class="para-header">
                <span>段落 ${startIndex + i + 1}</span>
                <span class="status-badge ${seg.status === 'translated' ? 'success' : 'pending'}">${seg.status === 'translated' ? '已翻译' : '待翻译'}</span>
            </div>
            <div class="para-text ${seg.status !== 'translated' ? 'muted' : ''}">${seg.status === 'translated' ? escapeHtml(seg.translated) : '点击"翻译全部"开始翻译'}</div>
        </div>
    `).join('');
    
    document.getElementById('targetCount').textContent = `${state.translatedCount} 已翻译`;
    
    // 更新统计
    updateStats();
}

/**
 * 引擎选择
 */
function initEngineSelect() {
    const engineSelect = document.getElementById('engineSelect');
    const langSelect = document.getElementById('targetLangSelect');
    // bilingualModeSelect removed - using checkboxes now
    
    engineSelect.addEventListener('change', (e) => {
        state.currentEngine = e.target.value;
        document.getElementById('currentEngine').textContent = `引擎: ${getEngineName(e.target.value)}`;
    });
    
    langSelect.addEventListener('change', (e) => {
        state.targetLanguage = e.target.value;
    });
    
    
}

/**
 * 按钮事件
 */
function initButtons() {
    // Upload button -> jump to upload page
    document.getElementById('translateBtn').addEventListener('click', function() {
        startTranslation();
    });
    // Pause button
    document.getElementById('pauseBtn').addEventListener('click', toggleTranslation);
    // Export button
    document.getElementById('exportBtn').addEventListener('click', exportDocument);
}

/**
 * 开始翻译
 */
async function startTranslation() {
    if (state.segments.length === 0) {
        showToast('请先上传文件', 'warning');
        return;
    }
    
    if (state.isTranslating) return;
    
    const btn = document.getElementById('translateBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const exportBtn = document.getElementById('exportBtn');
    
    state.isTranslating = true;
    state.isPaused = false;
    state.startTime = Date.now();
    state.avgTimePerSegment = 0;
    
    btn.textContent = '翻译中...';
    btn.disabled = true;
    pauseBtn.disabled = false;
    exportBtn.disabled = true;
    
    // 显示进度条
    const progressBar = document.getElementById('progressBar');
    progressBar.style.display = 'block';
    
    // 待翻译的段落
    const pendingSegments = state.segments.filter(s => s.status !== 'translated');
    let processed = 0;
    let failed = 0;
    
    for (let i = state.currentIndex; i < state.segments.length; i++) {
        try {
        if (!state.isTranslating) break;
        if (state.isPaused) {
            state.currentIndex = i;
            break;
        }
        
        const seg = state.segments[i];
        if (seg.status === 'translated') continue;
        
        // 更新段落状态为翻译中
        updateParagraphStatus(i, 'translating');
        
        const startTime = Date.now();
        
        try {
            const result = await translateSegment(seg.text, state.currentEngine);
            
            // 翻译完成后立即检查暂停状态
            if (state.isPaused) {
                state.currentIndex = i;
                seg.status = 'pending';
                document.getElementById('translateBtn').textContent = '继续翻译';
                document.getElementById('translateBtn').disabled = false;
                showToast('翻译已暂停', 'info');
                return;
            }
            
            seg.translated = result;
            seg.status = 'translated';
            state.translatedCount++;
            processed++;
            
            // 更新段落状态为已完成
            updateParagraphStatus(i, 'translated');
        } catch (error) {
            console.error(`翻译失败 [${i}]:`, error);
            seg.status = 'error';
            failed++;
            
            // 更新段落状态为错误
            updateParagraphStatus(i, 'error');
        }
        
        // 计算预估时间
        const elapsed = Date.now() - state.startTime;
        const avgTime = elapsed / (processed + failed);
        const remaining = pendingSegments.length - processed - failed;
        const estimatedRemaining = Math.round(avgTime * remaining / 1000);
        
        // 更新进度
        const progress = Math.round(((i + 1) / state.segments.length) * 100);
        document.getElementById('progressFill').style.width = `${progress}%`;
        document.getElementById('progressText').textContent = `${progress}%`;
        document.getElementById('progressStats').textContent = `已翻译 ${state.translatedCount}/${state.segments.length}`;
        document.getElementById('progressTime').textContent = `预计剩余: ${estimatedRemaining}秒`;
        
        // 更新显示
        renderParagraphs(Math.floor(i / 10) * 10);
        updateStats();
        
        // 延迟避免API限流
        await delay(300);
        } catch (loopError) {
            console.error('翻译循环异常 [' + i + ']:', loopError);
            // 跳过当前段落，继续下一段
            failed++;
            await delay(500);
        }
    }
    
    // 完成
    state.isTranslating = false;
    state.currentIndex = 0;
    btn.textContent = '翻译全部';
    btn.disabled = false;
    pauseBtn.disabled = true;
    exportBtn.disabled = false;
    
    setTimeout(() => {
        progressBar.style.display = 'none';
    }, 2000);
    
    showToast(`翻译完成！成功: ${processed}, 失败: ${failed}`, failed > 0 ? 'warning' : 'success');
}

/**
 * 调用翻译API
 */
async function translateSegment(text, engine) {
    const response = await fetch(`${API_BASE}/api/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            segments: [{ index: 0, text }],
            engine: engine,
            source_language: 'en',
            target_language: state.targetLanguage
        })
    });
    
    if (!response.ok) {
        throw new Error(`API错误: ${response.status}`);
    }
    
    const result = await response.json();
    
    if (!result.success) {
        throw new Error(result.message || '翻译失败');
    }
    
    return result.data.results[0]?.translated || '';
}

/**
 * 暂停/继续翻译
 */
function toggleTranslation() {
    state.isPaused = !state.isPaused;
    document.getElementById('pauseBtn').textContent = state.isPaused ? '继续' : '暂停';
    showToast(state.isPaused ? '已暂停' : '继续翻译', 'info');
}

/**
 * 导出文档
 */
async function exportDocument() {
    if (state.translatedCount === 0) {
        showToast('没有可导出的译文', 'warning');
        return;
    }
    
    // 获取选中的导出模式
    const modes = [];
    if (document.getElementById('modeInterleaved').checked) modes.push('interleaved');
    if (document.getElementById('modeSideBySide').checked) modes.push('side_by_side');
    if (document.getElementById('modeTranslatedOnly').checked) modes.push('translated_only');
    if (document.getElementById('modeFootnote').checked) modes.push('footnote');
    
    if (modes.length === 0) {
        showToast('请至少选择一个导出模式', 'warning');
        return;
    }
    
    const exportBtn = document.getElementById('exportBtn');
    const originalText = exportBtn.textContent;
    let successCount = 0;
    let failCount = 0;
    
    // 逐个导出
    for (const mode of modes) {
        exportBtn.textContent = '导出中 ' + (modes.indexOf(mode) + 1) + '/' + modes.length + '...';
        exportBtn.disabled = true;
        
        try {
            const response = await fetch(`${API_BASE}/api/export/docx`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_name: state.fileName || 'document.pdf',
                    segments: state.segments
                        .filter(s => s.status === 'translated')
                        .map(s => ({
                            index: s.index,
                            source_text: s.text,
                            translated_text: s.translated,
                            type: s.type || 'text',
                            page: s.page || 1
                        })),
                    bilingual_mode: mode,
                    source_language: 'en',
                    target_language: state.targetLanguage
                })
            });

            if (!response.ok) {
                throw new Error('导出失败: ' + response.status);
            }

            const result = await response.json();

            if (result.success) {
                const baseName = (state.fileName || 'document').replace(/\.[^.]+$/, '');
                const a = document.createElement('a');
                a.href = `${API_BASE}/api/downloads/${encodeURIComponent(result.data.file_name)}`;
                            const modeNames = {
                'interleaved': '段落交替',
                'side_by_side': '左右分栏',
                'translated_only': '仅译文',
                'footnote': '脚注模式'
            };
                a.download = baseName + '_' + modeNames[mode] + '.docx';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                successCount++;
            } else {
                throw new Error(result.message || '导出失败');
            }
        } catch (error) {
            console.error('导出失败 (' + mode + '):', error);
            failCount++;
        }
        
        // 每次导出后稍作延迟，避免文件下载冲突
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    exportBtn.textContent = originalText;
    exportBtn.disabled = false;
    
    if (failCount === 0) {
        showToast('导出完成！成功 ' + successCount + ' 个文件', 'success');
    } else {
        showToast('导出完成：成功 ' + successCount + '，失败 ' + failCount, 'warning');
    }
}
async function checkApiStatus() {
    const statusDot = document.getElementById('apiStatus');
    const apiIndicator = document.getElementById('apiIndicator');
    const apiLatency = document.getElementById('apiLatency');
    
    try {
        const start = Date.now();
        const response = await fetch(`${API_BASE}/health`, {
            method: 'GET',
            timeout: 5000
        });
        const latency = Date.now() - start;
        
        if (response.ok) {
            statusDot.className = 'status-dot online';
            apiIndicator.innerHTML = '<span class="status-badge success">在线</span>';
            apiLatency.textContent = `${latency}ms`;
        } else {
            statusDot.className = 'status-dot offline';
            apiIndicator.innerHTML = '<span class="status-badge error">离线</span>';
        }
    } catch (error) {
        statusDot.className = 'status-dot offline';
        apiIndicator.innerHTML = '<span class="status-badge error">离线</span>';
        apiLatency.textContent = '-';
    }
}

/**
 * 测试引擎配置
 */
async function testEngineConfig(engine) {
    const statusEl = document.getElementById(`${engine}Status`);
    statusEl.textContent = '测试中...';
    statusEl.className = 'config-status testing';
    
    showToast(`正在测试 ${getEngineName(engine)}...`, 'info');
    
    try {
        if (engine === 'ollama') {
            const url = document.getElementById('ollamaUrl').value;
            const response = await fetch(`${url}/api/tags`, { timeout: 5000 });
            
            if (response.ok) {
                statusEl.textContent = '已连接';
                statusEl.className = 'config-status connected';
                showToast(`${getEngineName(engine)} 连接成功！`, 'success');
            } else {
                throw new Error();
            }
        } else {
            // API密钥测试 - 调用翻译接口
            const apiKey = document.getElementById(`${engine}ApiKey`).value;
            if (!apiKey) {
                throw new Error('请输入API Key');
            }
            
            // 保存配置
            state.config[engine].apiKey = apiKey;
            saveConfig();
            
            // 测试翻译
            await translateSegment('Hello, this is a test.', engine);
            
            statusEl.textContent = '已配置';
            statusEl.className = 'config-status connected';
            showToast(`${getEngineName(engine)} 配置成功！`, 'success');
        }
    } catch (error) {
        statusEl.textContent = '配置错误';
        statusEl.className = 'config-status error';
        showToast(`${getEngineName(engine)} 测试失败: ${error.message}`, 'error');
    }
}

/**
 * 保存配置
 */
function saveConfig() {
    // 读取所有输入
    state.config.deepseek.apiKey = document.getElementById('deepseekApiKey').value;
    state.config.deepseek.model = document.getElementById('deepseekModel').value;
    
    state.config.claude.apiKey = document.getElementById('claudeApiKey').value;
    state.config.claude.model = document.getElementById('claudeModel').value;
    
    state.config.qwen.apiKey = document.getElementById('qwenApiKey').value;
    state.config.qwen.model = document.getElementById('qwenModel').value;
    
    state.config.minimax.apiKey = document.getElementById('minimaxApiKey').value;
    state.config.minimax.model = document.getElementById('minimaxModel').value;
    
    state.config.ollama.url = document.getElementById('ollamaUrl').value;
    state.config.ollama.model = document.getElementById('ollamaModel').value;
    
    state.config.openai.apiKey = document.getElementById('openaiApiKey').value;
    state.config.openai.model = document.getElementById('openaiModel').value;
    
    // 保存到localStorage
    localStorage.setItem('taixuan_config', JSON.stringify(state.config));
    
    showToast('配置已保存', 'success');
}

/**
 * 加载配置
 */
function loadConfig() {
    const saved = localStorage.getItem('taixuan_config');
    if (saved) {
        try {
            const config = JSON.parse(saved);
            Object.assign(state.config, config);
            
            // 填充表单
            document.getElementById('deepseekApiKey').value = config.deepseek?.apiKey || '';
            document.getElementById('deepseekModel').value = config.deepseek?.model || 'deepseek-chat';
            document.getElementById('claudeApiKey').value = config.claude?.apiKey || '';
            document.getElementById('claudeModel').value = config.claude?.model || 'claude-sonnet-4-20250514';
            document.getElementById('qwenApiKey').value = config.qwen?.apiKey || '';
            document.getElementById('qwenModel').value = config.qwen?.model || 'qwen-turbo';
            document.getElementById('minimaxApiKey').value = config.minimax?.apiKey || '';
            document.getElementById('minimaxModel').value = config.minimax?.model || 'abab6.5s-chat';
            document.getElementById('ollamaUrl').value = config.ollama?.url || 'http://localhost:11434';
            document.getElementById('ollamaModel').value = config.ollama?.model || 'qwen2.5:27b';
            document.getElementById('openaiApiKey').value = config.openai?.apiKey || '';
            document.getElementById('openaiModel').value = config.openai?.model || 'gpt-4o-mini';
            
            // 更新配置状态
            updateConfigStatus();
        } catch (e) {
            console.error('加载配置失败:', e);
        }
    }
}

/**
 * 更新配置状态显示
 */
function updateConfigStatus() {
    Object.keys(state.config).forEach(engine => {
        const el = document.getElementById(`${engine}Status`);
        if (el) {
            const config = state.config[engine];
            if (engine === 'ollama') {
                el.textContent = '未连接';
                el.className = 'config-status';
            } else if (config?.apiKey) {
                el.textContent = '已配置';
                el.className = 'config-status connected';
            } else {
                el.textContent = '未配置';
                el.className = 'config-status';
            }
        }
    });
}

/**
 * 重置配置
 */
function resetConfig() {
    if (confirm('确定要重置所有配置吗？')) {
        localStorage.removeItem('taixuan_config');
        location.reload();
    }
}

/**
 * 更新状态面板
 */
function updateStatusPanel() {
    // 更新项目统计
    document.getElementById('statFileName').textContent = state.fileName || '-';
    document.getElementById('statFileType').textContent = state.fileName ? state.fileName.split('.').pop().toUpperCase() : '-';
    document.getElementById('statTotalPages').textContent = state.segments.length > 0 ? '-' : '0';
    document.getElementById('statTotalParagraphs').textContent = state.segments.length || '0';
    
    const totalChars = state.segments.reduce((sum, s) => sum + (s.text?.length || 0), 0);
    document.getElementById('statTotalChars').textContent = totalChars.toLocaleString() || '0';
    
    // 更新翻译进度
    const progress = state.segments.length > 0 ? Math.round((state.translatedCount / state.segments.length) * 100) : 0;
    const dashOffset = 283 - (283 * progress / 100);
    document.getElementById('progressRing').style.strokeDashoffset = dashOffset;
    document.getElementById('progressRingText').textContent = `${progress}%`;
    
    document.getElementById('statTranslated').textContent = state.translatedCount;
    document.getElementById('statPending').textContent = state.segments.length - state.translatedCount;
    
    // 更新引擎信息
    document.getElementById('engineName').textContent = getEngineName(state.currentEngine);
    document.getElementById('engineModel').textContent = state.config[state.currentEngine]?.model || '-';
    document.getElementById('engineIcon').textContent = getEngineIcon(state.currentEngine);
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function getEngineName(engine) {
    const names = {
        deepseek: 'DeepSeek',
        claude: 'Claude',
        qwen: '千问',
        minimax: 'Minimax',
        ollama: 'Ollama本地',
        openai: 'OpenAI'
    };
    return names[engine] || engine;
}

function getEngineIcon(engine) {
    const icons = {
        deepseek: '🔮',
        claude: '🧠',
        qwen: '🐉',
        minimax: '⚡',
        ollama: '🏠',
        openai: '🤖'
    };
    return icons[engine] || '🔧';
}

function updateStats() {
    // 更新统计信息
    const totalChars = state.segments.reduce((sum, s) => sum + (s.text?.length || 0), 0);
    const translatedChars = state.segments
        .filter(s => s.status === 'translated')
        .reduce((sum, s) => sum + (s.text?.length || 0), 0);
    
    // 可以在这里更新其他统计信息
}
