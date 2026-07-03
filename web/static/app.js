/**
 * AI File Manager - Frontend Application
 * 
 * All communication with the Python backend happens through fetch() calls.
 * No filesystem access from the browser — everything goes through the API.
 */

// ═══════════════════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════════════════

let state = {
    results: [],
    errors: [],
    summary: null,
    selectedFile: null,
    sortColumn: 'file',
    sortAsc: true,
    scanId: null,
    darkMode: localStorage.getItem('theme') !== 'light',
};

// ═══════════════════════════════════════════════════════════════════════════
// Initialization
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Apply saved theme
    if (!state.darkMode) {
        document.documentElement.setAttribute('data-theme', 'light');
        document.getElementById('darkModeBtn').textContent = '☀️';
    }
    
    // Check server status
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            console.log('Server connected:', data);
            if (data.results_count > 0) {
                loadResults();
            }
        })
        .catch(err => console.error('Server not ready:', err));
});

// ═══════════════════════════════════════════════════════════════════════════
// Theme
// ═══════════════════════════════════════════════════════════════════════════

function toggleDarkMode() {
    state.darkMode = !state.darkMode;
    const theme = state.darkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    document.getElementById('darkModeBtn').textContent = state.darkMode ? '🌙' : '☀️';
}

// ═══════════════════════════════════════════════════════════════════════════
// Modals
// ═══════════════════════════════════════════════════════════════════════════

function openModal(id) {
    document.getElementById(id).style.display = 'flex';
    // Focus the input
    const input = document.querySelector(`#${id} .modal-input`);
    if (input) setTimeout(() => input.focus(), 100);
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

// ═══════════════════════════════════════════════════════════════════════════
// Folder / File Selection
// ═══════════════════════════════════════════════════════════════════════════

function pickFolder() {
    openModal('folderModal');
}

function pickFile() {
    openModal('fileModal');
}

function loadReport() {
    openModal('reportModal');
}

function startScan() {
    const path = document.getElementById('folderPathInput').value.trim();
    if (!path) return;
    closeModal('folderModal');
    document.getElementById('pathDisplay').textContent = path;
    beginScan(path);
}

function startFileAnalysis() {
    const path = document.getElementById('filePathInput').value.trim();
    if (!path) return;
    closeModal('fileModal');
    document.getElementById('pathDisplay').textContent = path;
    analyzeSingleFile(path);
}

function startLoadReport() {
    const path = document.getElementById('reportPathInput').value.trim();
    if (!path) return;
    closeModal('reportModal');
    loadReportFile(path);
}

// ═══════════════════════════════════════════════════════════════════════════
// Scanning
// ═══════════════════════════════════════════════════════════════════════════

function beginScan(directory) {
    showProgress('Scanning...');
    
    fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: directory }),
    })
    .then(r => r.json())
    .then(data => {
        state.scanId = data.scan_id;
        pollScanProgress(data.scan_id);
    })
    .catch(err => {
        hideProgress();
        showError('Scan failed: ' + err.message);
    });
}

function pollScanProgress(scanId) {
    const poll = () => {
        fetch(`/api/scan/status/${scanId}`)
            .then(r => r.json())
            .then(data => {
                updateProgress(data);
                
                if (data.status === 'done') {
                    // Scan complete — load results
                    if (data.results) {
                        state.results = data.results;
                        state.errors = data.error_details || [];
                        state.summary = data.summary || null;
                        renderAll();
                    }
                    setTimeout(hideProgress, 1500);
                    updateFileCount(state.results.length);
                } else if (data.status === 'error') {
                    hideProgress();
                    showError('Scan error');
                } else {
                    // Still scanning — poll again
                    setTimeout(poll, 500);
                }
            })
            .catch(() => setTimeout(poll, 1000));
    };
    poll();
}

// ═══════════════════════════════════════════════════════════════════════════
// Single File Analysis
// ═══════════════════════════════════════════════════════════════════════════

function analyzeSingleFile(filePath) {
    showProgress('Analyzing...');
    
    fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath }),
    })
    .then(r => r.json())
    .then(data => {
        hideProgress();
        if (data.analysis) {
            state.results = [{
                file: filePath.split('/').pop().split('\\').pop(),
                path: filePath,
                ...data.analysis
            }];
            renderAll();
            updateFileCount(1);
        }
    })
    .catch(err => {
        hideProgress();
        showError('Analysis failed: ' + err.message);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// Reports
// ═══════════════════════════════════════════════════════════════════════════

function loadReportFile(filePath) {
    fetch('/api/reports/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath }),
    })
    .then(r => r.json())
    .then(data => {
        state.results = data.results || [];
        state.errors = data.errors || [];
        state.summary = data.summary || null;
        renderAll();
        updateFileCount(state.results.length);
        document.getElementById('pathDisplay').textContent = filePath;
    })
    .catch(err => showError('Failed to load report: ' + err.message));
}

function saveReport() {
    fetch('/api/reports/save', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.path) {
                showQueryResult(`✅ Report saved: ${data.filename}`);
            }
        })
        .catch(err => showError('Failed to save: ' + err.message));
}

// ═══════════════════════════════════════════════════════════════════════════
// Load Results
// ═══════════════════════════════════════════════════════════════════════════

function loadResults() {
    fetch('/api/results')
        .then(r => r.json())
        .then(data => {
            state.results = data.results || [];
            state.errors = data.errors || [];
            state.summary = data.summary || null;
            renderAll();
            updateFileCount(state.results.length);
        })
        .catch(err => console.error('Failed to load results:', err));
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering
// ═══════════════════════════════════════════════════════════════════════════

function renderAll() {
    renderDashboard();
    renderTable(state.results);
    updateCategoryFilter();
}

function renderDashboard() {
    const empty = document.getElementById('dashboardEmpty');
    const cards = document.getElementById('dashboardCards');
    const sections = document.querySelectorAll('.dashboard-section');
    
    if (!state.results || state.results.length === 0) {
        empty.style.display = 'block';
        cards.style.display = 'none';
        sections.forEach(s => s.style.display = 'none');
        return;
    }
    
    empty.style.display = 'none';
    cards.style.display = 'grid';
    sections.forEach(s => s.style.display = 'block');
    
    // Fetch dashboard data
    fetch('/api/dashboard')
        .then(r => r.json())
        .then(data => {
            if (data.empty) return;
            
            document.getElementById('dashTotalFiles').textContent = data.total_files || 0;
            document.getElementById('dashSafeDelete').textContent = data.safe_to_delete || 0;
            document.getElementById('dashNeedsReview').textContent = data.needs_review || 0;
            
            // Fetch duplicates count
            fetch('/api/duplicates')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('dashDuplicates').textContent = d.duplicate_groups?.length || 0;
                })
                .catch(() => {});
            
            // Action breakdown
            renderStatBars('dashActions', data.action_breakdown || {}, {
                'Keep': 'var(--green)',
                'Delete': 'var(--red)',
                'Archive': 'var(--blue)',
                'Review': 'var(--orange)',
            });
            
            // Categories
            const catContainer = document.getElementById('dashCategories');
            catContainer.innerHTML = '';
            const cats = data.categories || {};
            Object.entries(cats).slice(0, 8).forEach(([cat, count]) => {
                const div = document.createElement('div');
                div.className = 'category-item';
                div.innerHTML = `<span>${getCategoryIcon(cat)} ${cat}</span><span class="cat-count">${count}</span>`;
                catContainer.appendChild(div);
            });
            
            // Confidence
            renderStatBars('dashConfidence', {
                'High (85-100)': data.confidence_distribution?.high || 0,
                'Medium (60-84)': data.confidence_distribution?.medium || 0,
                'Low (0-59)': data.confidence_distribution?.low || 0,
            }, {
                'High (85-100)': 'var(--green)',
                'Medium (60-84)': 'var(--orange)',
                'Low (0-59)': 'var(--red)',
            });
            
            // Tags
            const tagContainer = document.getElementById('dashTags');
            tagContainer.innerHTML = '';
            const tags = data.tag_cloud || {};
            Object.entries(tags).slice(0, 20).forEach(([tag, count]) => {
                const display = tag.includes(':') ? tag.split(':')[1].replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : tag;
                const span = document.createElement('span');
                span.className = 'tag';
                span.textContent = `${display} (${count})`;
                tagContainer.appendChild(span);
            });
        })
        .catch(err => console.error('Dashboard error:', err));
}

function renderStatBars(containerId, data, colors) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
    
    Object.entries(data).forEach(([label, count]) => {
        const pct = Math.round(count / total * 100);
        const color = colors[label] || 'var(--accent)';
        
        const item = document.createElement('div');
        item.className = 'stat-bar-item';
        item.innerHTML = `
            <span class="stat-bar-label">${label}</span>
            <div class="stat-bar-track"><div class="stat-bar-fill" style="width:${pct}%;background:${color}"></div></div>
            <span class="stat-bar-count">${count}</span>
        `;
        container.appendChild(item);
    });
}

function renderTable(results) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    
    if (!results || results.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="9">
                    <div class="empty-state">
                        <div class="empty-icon">📂</div>
                        <div class="empty-text">No files analyzed yet</div>
                        <div class="empty-subtext">Click "Scan Folder" to get started</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    results.forEach((entry, index) => {
        const tr = document.createElement('tr');
        tr.dataset.index = index;
        tr.onclick = () => selectFile(index);
        tr.ondblclick = () => showDetailModal(entry);
        
        const action = entry.action || 'Review';
        const confidence = entry.confidence || 0;
        const confClass = confidence >= 85 ? 'conf-high' : confidence >= 60 ? 'conf-medium' : 'conf-low';
        
        const tags = Array.isArray(entry.tags) ? entry.tags.slice(0, 3).map(t => {
            return t.includes(':') ? t.split(':')[1].replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : t;
        }).join(', ') : '';
        if (Array.isArray(entry.tags) && entry.tags.length > 3) tags += ` +${entry.tags.length - 3}`;
        
        tr.innerHTML = `
            <td title="${escapeHtml(entry.file || '')}">${escapeHtml(entry.file || '')}</td>
            <td>${getCategoryIcon(entry.category)} ${escapeHtml(entry.category || '')}</td>
            <td>${escapeHtml(entry.subcategory || '')}</td>
            <td>${escapeHtml(entry.project || '')}</td>
            <td><span class="action-badge action-${action}">${getActionIcon(action)} ${action}</span></td>
            <td>${entry.importance || '-'}/10</td>
            <td>${getLifecycleIcon(entry.lifecycle)} ${escapeHtml(entry.lifecycle || '')}</td>
            <td><span class="conf-badge ${confClass}">${confidence}%</span></td>
            <td style="font-size:11px;color:var(--text-muted)">${tags}</td>
        `;
        tbody.appendChild(tr);
    });
    
    updateResultCount(results.length);
}

function selectFile(index) {
    const entry = state.results[index];
    if (!entry) return;
    
    state.selectedFile = entry;
    
    // Highlight row
    document.querySelectorAll('#resultsBody tr').forEach((tr, i) => {
        tr.classList.toggle('selected', i === index);
    });
    
    // Show in detail panel
    showDetail(entry);
}

function showDetail(entry) {
    document.getElementById('detailEmpty').style.display = 'none';
    document.getElementById('detailContent').style.display = 'block';
    
    document.getElementById('detailFilename').textContent = entry.file || 'Unknown';
    document.getElementById('detailPath').textContent = entry.path || '-';
    document.getElementById('detailSize').textContent = entry.size_human || '-';
    document.getElementById('detailType').textContent = entry.extension || '-';
    document.getElementById('detailSummary').textContent = entry.summary || 'No summary';
    document.getElementById('detailCategory').textContent = `${getCategoryIcon(entry.category)} ${entry.category || 'Other'}`;
    document.getElementById('detailProject').textContent = entry.project || 'Not detected';
    
    const action = entry.action || 'Review';
    document.getElementById('detailAction').innerHTML = `<span class="action-badge action-${action}">${getActionIcon(action)} ${action}</span>`;
    
    const conf = entry.confidence || 0;
    const confClass = conf >= 85 ? 'conf-high' : conf >= 60 ? 'conf-medium' : 'conf-low';
    document.getElementById('detailConfidence').innerHTML = `<span class="conf-badge ${confClass}">${conf}%</span>`;
    
    document.getElementById('detailLifecycle').textContent = `${getLifecycleIcon(entry.lifecycle)} ${entry.lifecycle || 'Unknown'}`;
    document.getElementById('detailImportance').textContent = `${entry.importance || '-'}/10`;
    document.getElementById('detailSentimental').textContent = `${entry.sentimental_value || '-'}/10`;
    
    // Tags
    const tagContainer = document.getElementById('detailTags');
    tagContainer.innerHTML = '';
    const tags = Array.isArray(entry.tags) ? entry.tags : [];
    if (tags.length === 0) {
        tagContainer.innerHTML = '<span class="text-muted">No tags</span>';
    } else {
        tags.forEach(tag => {
            const display = tag.includes(':') ? tag.split(':')[1].replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : tag;
            const span = document.createElement('span');
            span.className = 'tag';
            span.textContent = display;
            tagContainer.appendChild(span);
        });
    }
    
    document.getElementById('detailReasoning').textContent = entry.reasoning || 'No reasoning provided.';
    
    // Preview (fetch file content via API)
    const preview = document.getElementById('detailPreview');
    preview.textContent = '[Loading preview...]';
    if (entry.path) {
        // We can't read files from browser — show a note
        preview.textContent = '[File preview available for text files via the API]\n\n' + 
            JSON.stringify(entry, null, 2).slice(0, 1000);
    }
}

function showDetailModal(entry) {
    const body = document.getElementById('queryResultBody');
    body.textContent = JSON.stringify(entry, null, 2);
    document.getElementById('queryResultModal').querySelector('h3').textContent = `📄 ${entry.file || 'File Details'}`;
    openModal('queryResultModal');
}

// ═══════════════════════════════════════════════════════════════════════════
// Filtering
// ═══════════════════════════════════════════════════════════════════════════

function applyFilters() {
    const search = document.getElementById('searchInput').value;
    const category = document.getElementById('filterCategory').value;
    const action = document.getElementById('filterAction').value;
    const lifecycle = document.getElementById('filterLifecycle').value;
    
    const body = {};
    if (search) body.search = search;
    if (category) body.category = category;
    if (action) body.action = action;
    if (lifecycle) body.lifecycle = lifecycle;
    
    fetch('/api/filter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
    .then(r => r.json())
    .then(data => {
        renderTable(data.results || []);
    })
    .catch(err => console.error('Filter error:', err));
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterAction').value = '';
    document.getElementById('filterLifecycle').value = '';
    renderTable(state.results);
    updateResultCount(state.results.length);
}

function updateCategoryFilter() {
    const select = document.getElementById('filterCategory');
    const current = select.value;
    
    const categories = new Set();
    state.results.forEach(r => {
        if (r.category) categories.add(r.category);
    });
    
    select.innerHTML = '<option value="">All</option>';
    [...categories].sort().forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        select.appendChild(opt);
    });
    select.value = current;
}

// ═══════════════════════════════════════════════════════════════════════════
// Sorting
// ═══════════════════════════════════════════════════════════════════════════

function sortBy(column) {
    if (state.sortColumn === column) {
        state.sortAsc = !state.sortAsc;
    } else {
        state.sortColumn = column;
        state.sortAsc = true;
    }
    
    // Update sort arrows
    document.querySelectorAll('.sort-arrow').forEach(el => el.textContent = '');
    const arrow = document.getElementById(`sort${column.charAt(0).toUpperCase() + column.slice(1)}`);
    if (arrow) arrow.textContent = state.sortAsc ? '▲' : '▼';
    
    const sorted = [...state.results].sort((a, b) => {
        let va = a[column] ?? '';
        let vb = b[column] ?? '';
        
        if (column === 'confidence' || column === 'importance') {
            va = Number(va) || 0;
            vb = Number(vb) || 0;
        } else {
            va = String(va).toLowerCase();
            vb = String(vb).toLowerCase();
        }
        
        if (va < vb) return state.sortAsc ? -1 : 1;
        if (va > vb) return state.sortAsc ? 1 : -1;
        return 0;
    });
    
    renderTable(sorted);
}

// ═══════════════════════════════════════════════════════════════════════════
// Query
// ═══════════════════════════════════════════════════════════════════════════

function setQuery(text) {
    document.getElementById('queryInput').value = text;
    submitQuery();
}

function submitQuery() {
    const question = document.getElementById('queryInput').value.trim();
    if (!question) return;
    
    const resultDiv = document.getElementById('queryResult');
    resultDiv.style.display = 'block';
    resultDiv.textContent = '🤔 Thinking...';
    
    fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
    })
    .then(r => r.json())
    .then(data => {
        let text = data.answer || 'No answer.';
        if (data.matching_files && data.matching_files.length > 0) {
            text += '\n\nMatching files:\n' + data.matching_files.map(f => `  • ${f}`).join('\n');
        }
        resultDiv.textContent = text;
    })
    .catch(err => {
        resultDiv.textContent = '⚠ Error: ' + err.message;
    });
}

function showQueryResult(text) {
    const body = document.getElementById('queryResultBody');
    body.textContent = text;
    document.getElementById('queryResultModal').querySelector('h3').textContent = '🤖 Query Result';
    openModal('queryResultModal');
}

// ═══════════════════════════════════════════════════════════════════════════
// Detail Actions
// ═══════════════════════════════════════════════════════════════════════════

function explainRecommendation() {
    const entry = state.selectedFile;
    if (!entry) return;
    
    const text = `Recommendation: ${entry.action}\nConfidence: ${entry.confidence}%\n\nReasoning:\n${entry.reasoning || 'No reasoning provided.'}\n\nSuggested filename: ${entry.suggested_filename || 'N/A'}`;
    showQueryResult(text);
}

function findSimilar() {
    const entry = state.selectedFile;
    if (!entry || !entry.path) return;
    
    fetch('/api/similar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: entry.path }),
    })
    .then(r => r.json())
    .then(data => {
        const similar = data.similar || [];
        if (similar.length === 0) {
            showQueryResult(`No similar files found for "${entry.file}".`);
        } else {
            let text = `Files similar to "${entry.file}":\n\n`;
            similar.forEach(([a, b, score]) => {
                const other = a.file === entry.file ? b : a;
                text += `  • ${other.file} (score: ${(score * 100).toFixed(0)}%)\n`;
            });
            showQueryResult(text);
        }
    })
    .catch(err => showQueryResult('Error: ' + err.message));
}

function showInExplorer() {
    const entry = state.selectedFile;
    if (!entry || !entry.path) return;
    // This would need a special API endpoint to open Explorer
    showQueryResult(`📂 File location:\n${entry.path}\n\n(Open in Explorer requires a desktop API call)`);
}

function copyPath() {
    const entry = state.selectedFile;
    if (!entry || !entry.path) return;
    navigator.clipboard.writeText(entry.path).then(() => {
        showQueryResult('📋 Path copied to clipboard!');
    }).catch(() => {
        showQueryResult('📋 ' + entry.path);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// Progress
// ═══════════════════════════════════════════════════════════════════════════

function showProgress(title) {
    document.getElementById('progressOverlay').style.display = 'flex';
    document.getElementById('progressTitle').textContent = title;
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressCount').textContent = 'Starting...';
    document.getElementById('progressFile').textContent = '';
    document.getElementById('progressTime').textContent = '⏱ 0s';
    document.getElementById('progressCached').textContent = '⚡ 0 cached';
    document.getElementById('progressNew').textContent = '🆕 0 new';
    document.getElementById('progressErrors').textContent = '✕ 0 errors';
}

function updateProgress(data) {
    const total = data.total || 1;
    const pct = Math.round((data.current || 0) / total * 100);
    
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressCount').textContent = `${data.current || 0} of ${total} files (${pct}%)`;
    
    if (data.current_file) {
        const name = data.current_file.length > 50 ? '...' + data.current_file.slice(-47) : data.current_file;
        document.getElementById('progressFile').textContent = `📄 ${name}`;
    }
    
    const elapsed = data.elapsed_seconds || 0;
    document.getElementById('progressTime').textContent = `⏱ ${elapsed < 60 ? Math.round(elapsed) + 's' : Math.floor(elapsed / 60) + 'm ' + Math.round(elapsed % 60) + 's'}`;
    
    document.getElementById('progressCached').textContent = `⚡ ${data.cached || 0} cached`;
    document.getElementById('progressNew').textContent = `🆕 ${data.scanned || 0} new`;
    document.getElementById('progressErrors').textContent = `✕ ${data.errors || 0} errors`;
}

function hideProgress() {
    document.getElementById('progressOverlay').style.display = 'none';
}

// ═══════════════════════════════════════════════════════════════════════════
// Utilities
// ═══════════════════════════════════════════════════════════════════════════

function updateFileCount(count) {
    document.getElementById('fileCount').textContent = `${count} files`;
}

function updateResultCount(count) {
    const total = state.results.length;
    const el = document.getElementById('resultCount');
    if (count === total) {
        el.textContent = `${total} files`;
    } else {
        el.textContent = `${count} of ${total} files`;
    }
}

function showError(message) {
    const resultDiv = document.getElementById('queryResult');
    resultDiv.style.display = 'block';
    resultDiv.textContent = '⚠ ' + message;
    resultDiv.style.color = 'var(--red)';
    setTimeout(() => { resultDiv.style.color = ''; }, 3000);
}

function getCategoryIcon(category) {
    const icons = {
        'Programming': '💻', 'Documents': '📄', 'Finance': '💰',
        'School': '🎓', 'Personal': '👤', 'Media': '🎵',
        'Data': '📊', 'Installer': '📦', 'System': '⚙️',
        'Work': '💼', 'Other': '📁',
    };
    return icons[category] || '📁';
}

function getActionIcon(action) {
    return { 'Keep': '✓', 'Delete': '✕', 'Archive': '↓', 'Review': '⚠' }[action] || '?';
}

function getLifecycleIcon(lifecycle) {
    return { 'Active': '🟢', 'Dormant': '🟡', 'Archived': '🔵', 'Transient': '⚪', 'Unknown': '⚫' }[lifecycle] || '⚫';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}