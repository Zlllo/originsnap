/**
 * Originsnap - Frontend Application
 */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// State
let selectedFile = null;

// Elements
const uploadArea = $('#uploadArea');
const uploadPrompt = $('#uploadPrompt');
const previewContainer = $('#previewContainer');
const previewImage = $('#previewImage');
const removeBtn = $('#removeBtn');
const fileInput = $('#fileInput');
const searchBtn = $('#searchBtn');
const loadingSection = $('#loadingSection');
const loadingText = $('#loadingText');
const engineStatus = $('#engineStatus');
const resultsSection = $('#resultsSection');

// ===== Upload Handling =====

uploadArea.addEventListener('click', (e) => {
    if (e.target === removeBtn || removeBtn.contains(e.target)) return;
    if (!selectedFile) fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
});

// Drag & Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) handleFile(file);
});

// Paste
document.addEventListener('paste', (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            handleFile(item.getAsFile());
            break;
        }
    }
});

// Remove
removeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearImage();
});

function handleFile(file) {
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        uploadPrompt.style.display = 'none';
        previewContainer.classList.add('active');
        uploadArea.classList.add('has-image');
        searchBtn.classList.add('active');
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    selectedFile = null;
    previewImage.src = '';
    uploadPrompt.style.display = '';
    previewContainer.classList.remove('active');
    uploadArea.classList.remove('has-image');
    searchBtn.classList.remove('active');
    fileInput.value = '';
    resultsSection.classList.remove('active');
    resultsSection.innerHTML = '';
}

// ===== Search =====

searchBtn.addEventListener('click', startSearch);

async function startSearch() {
    if (!selectedFile) return;

    // UI: show loading
    searchBtn.disabled = true;
    searchBtn.textContent = '搜索中...';
    loadingSection.classList.add('active');
    resultsSection.classList.remove('active');
    resultsSection.innerHTML = '';

    // Reset engine badges
    engineStatus.querySelectorAll('.engine-badge').forEach((b) => {
        b.className = 'engine-badge searching';
    });

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const resp = await fetch('/api/search', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();

        // Update engine badges
        const badges = engineStatus.querySelectorAll('.engine-badge');
        const engines = data.search_results || [];
        engines.forEach((eng, i) => {
            if (i < badges.length) {
                badges[i].className = eng.error
                    ? 'engine-badge error'
                    : 'engine-badge done';
            }
        });
        // AI badge
        const aiBadge = badges[badges.length - 1];
        aiBadge.className = data.ai_error
            ? 'engine-badge error'
            : 'engine-badge done';

        // Short delay for visual feedback
        await sleep(500);

        renderResults(data);
    } catch (err) {
        resultsSection.innerHTML = `
            <div class="analysis-card">
                <div class="conclusion" style="color: var(--error)">
                    ❌ 搜索失败: ${escapeHtml(err.message)}
                </div>
            </div>`;
        resultsSection.classList.add('active');
    } finally {
        loadingSection.classList.remove('active');
        searchBtn.disabled = false;
        searchBtn.textContent = '🔍 开始溯源搜索';
    }
}

// ===== Render Results =====

function renderResults(data) {
    let html = '';

    // AI Analysis Card
    const analysis = data.analysis;
    if (analysis) {
        html += renderAnalysis(analysis);
    }

    // Anime info
    if (analysis?.is_anime_screenshot && analysis?.anime_info) {
        html += renderAnimeInfo(analysis.anime_info);
    }

    // Engine results
    const engines = data.search_results || [];
    for (const eng of engines) {
        html += renderEngineResults(eng);
    }

    // External links
    const extLinks = data.external_links;
    if (extLinks?.links?.length) {
        html += renderExternalLinks(extLinks.links);
    }

    resultsSection.innerHTML = html;
    resultsSection.classList.add('active');

    // Bind toggle events
    resultsSection.querySelectorAll('.engine-header').forEach((header) => {
        header.addEventListener('click', () => {
            header.classList.toggle('collapsed');
            const body = header.nextElementSibling;
            body.classList.toggle('collapsed');
        });
    });
}

function renderAnalysis(a) {
    const confClass = a.confidence || 'low';
    const confLabel = { high: '高', medium: '中', low: '低' }[confClass] || confClass;

    let sourceHtml = '未能确定';
    if (a.original_source?.url) {
        sourceHtml = `<a href="${escapeHtml(a.original_source.url)}" target="_blank" rel="noopener">${escapeHtml(a.original_source.platform || a.original_source.url)}</a>`;
        if (a.original_source.title) {
            sourceHtml += `<br><span style="font-size:12px;color:var(--text-secondary)">${escapeHtml(a.original_source.title)}</span>`;
        }
    }

    let authorHtml = '未知';
    if (a.author?.name) {
        authorHtml = a.author.profile_url
            ? `<a href="${escapeHtml(a.author.profile_url)}" target="_blank" rel="noopener">${escapeHtml(a.author.name)}</a>`
            : escapeHtml(a.author.name);
    }

    return `
    <div class="analysis-card">
        <div class="analysis-header">
            <h2>🎯 溯源分析</h2>
            <span class="ai-badge">AI</span>
        </div>
        <div class="conclusion">${escapeHtml(a.conclusion || '')}</div>
        <div class="analysis-details">
            <div class="detail-item">
                <div class="label">原始来源</div>
                <div class="value">${sourceHtml}</div>
            </div>
            <div class="detail-item">
                <div class="label">原作者</div>
                <div class="value">${authorHtml}</div>
            </div>
            <div class="detail-item">
                <div class="label">置信度</div>
                <div class="value"><span class="confidence-badge ${confClass}">${confLabel}</span></div>
            </div>
            <div class="detail-item">
                <div class="label">推理</div>
                <div class="value" style="font-size:12px;color:var(--text-secondary)">${escapeHtml(a.reasoning || '')}</div>
            </div>
        </div>
    </div>`;
}

function renderAnimeInfo(info) {
    return `
    <div class="anime-card">
        <h3>🎬 动漫截图识别</h3>
        <div class="anime-meta">
            <span>📺 ${escapeHtml(info.title || '未知')}</span>
            ${info.episode ? `<span>📋 第 ${escapeHtml(info.episode)} 集</span>` : ''}
            ${info.timestamp ? `<span>⏱️ ${escapeHtml(info.timestamp)}</span>` : ''}
        </div>
    </div>`;
}

function renderEngineResults(eng) {
    const name = escapeHtml(eng.engine || 'Unknown');
    const results = eng.results || [];
    const error = eng.error;
    const count = results.length;

    let bodyHtml = '';
    if (error) {
        bodyHtml = `<div class="engine-error">⚠️ ${escapeHtml(error)}</div>`;
    } else if (count === 0) {
        bodyHtml = `<div class="no-results">无匹配结果</div>`;
    } else {
        bodyHtml = results.map((r) => renderResultItem(r, eng.engine)).join('');
    }

    // Auto-collapse engines with no results
    const collapsed = count === 0 && !error;

    return `
    <div class="engine-section">
        <div class="engine-header ${collapsed ? 'collapsed' : ''}">
            <h3>${getEngineIcon(eng.engine)} ${name} <span class="count">${count} 条结果</span></h3>
            <span class="toggle-icon">▼</span>
        </div>
        <div class="engine-body ${collapsed ? 'collapsed' : ''}">
            ${bodyHtml}
        </div>
    </div>`;
}

function renderResultItem(r, engine) {
    // Determine primary URL
    const url = r.ext_urls?.[0] || r.source_url || r.anilist_url || '';
    const title = r.title || r.source_site || r.index_name || (url ? new URL(url).hostname : '未知来源');

    // Similarity
    let simHtml = '';
    if (r.similarity != null) {
        simHtml = `
        <div class="result-similarity">
            <div class="similarity-value">${r.similarity}%</div>
            <div class="similarity-label">相似度</div>
        </div>`;
    }

    // Thumbnail
    let thumbHtml = '';
    if (r.thumbnail || r.preview_image) {
        const thumbSrc = r.thumbnail || r.preview_image;
        thumbHtml = `<img class="result-thumbnail" src="${escapeHtml(thumbSrc)}" alt="" loading="lazy" onerror="this.style.display='none'">`;
    }

    // Meta line
    let meta = [];
    if (r.author) meta.push(`作者: ${r.author}`);
    if (r.resolution) meta.push(r.resolution);
    if (r.episode) meta.push(`第 ${r.episode} 集`);
    if (r.timestamp) meta.push(r.timestamp);
    if (r.source_site) meta.push(r.source_site);

    // Author URL
    let authorLink = '';
    if (r.author_url) {
        authorLink = ` · <a href="${escapeHtml(r.author_url)}" class="source-link" target="_blank" rel="noopener">作者主页 →</a>`;
    }

    return `
    <div class="result-item">
        ${thumbHtml}
        <div class="result-info">
            <div class="title">${escapeHtml(title)}</div>
            ${meta.length ? `<div class="meta">${escapeHtml(meta.join(' · '))}${authorLink}</div>` : ''}
            ${url ? `<a href="${escapeHtml(url)}" class="source-link" target="_blank" rel="noopener">${escapeHtml(url)}</a>` : ''}
        </div>
        ${simHtml}
    </div>`;
}

function renderExternalLinks(links) {
    const items = links.map((l) => `
        <a href="${escapeHtml(l.url)}" class="ext-link" target="_blank" rel="noopener">
            <span class="icon">${l.icon || '🔗'}</span>
            <div>
                <div class="name">${escapeHtml(l.engine)}</div>
                <div class="desc">${escapeHtml(l.description || '')}</div>
            </div>
        </a>`).join('');

    return `
    <div class="external-links">
        <h3>🌐 在其他引擎中搜索</h3>
        <div class="links-grid">${items}</div>
    </div>`;
}

// ===== Utilities =====

function getEngineIcon(engine) {
    const icons = {
        'SauceNAO': '🍶',
        'IQDB': '🗃️',
        'ASCII2D': '🔤',
        'trace.moe': '🎬',
    };
    return icons[engine] || '🔍';
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
}
