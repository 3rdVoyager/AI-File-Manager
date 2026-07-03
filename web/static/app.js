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
    queryHistory: [],
};

// ═══════════════════════════════════════════════════════════════════════════
// Initialization
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Apply saved theme
    if (!state.darkMode) {
        document.documentElement.setAttribute('data-theme', 'light');
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
    
    // Load dashboard data
    loadDashboardData();
    loadRecentActivity();
    loadRecommendations();
    loadCategoryDistribution();
    
    // Load reports for the reports view
    loadReportsList();
});

// ═══════════════════════════════════════════════════════════════════════════
// Navigation & View Management
// ═══════════════════════════════════════════════════════════════════════════

let currentView = 'dashboard';

function setView(view) {
    currentView = view;
    console.log('Switching to view:', view);
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        const onclick = item.getAttribute('onclick');
        if (onclick && onclick.includes(`'${view}'`)) {
            item.classList.add('active');
        }
    });
    
    // Hide all views
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
    });
    
    // Show the selected view
    const viewEl = document.getElementById(`view-${view}`);
    if (viewEl) {
        viewEl.classList.add('active');
    }
    
    // Load view-specific data
    switch(view) {
        case 'dashboard':
            loadDashboardData();
            loadRecentActivity();
            loadRecommendations();
            loadCategoryDistribution();
            break;
        case 'files':
            renderTable(state.results);
            break;
        case 'projects':
            renderProjects();
            break;
        case 'duplicates':
            renderDuplicates();
            break;
        case 'large':
            renderLargeFiles();
            break;
        case 'recent':
            renderRecentFiles();
            break;
        case 'trash':
            renderTrashCandidates();
            break;
        case 'queries':
            renderQueriesHistory();
            break;
        case 'reports':
            loadReportsList();
            break;
        case 'settings':
            // Settings are static, no dynamic loading needed
            break;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// Dashboard Data
// ═══════════════════════════════════════════════════════════════════════════

function loadDashboardData() {
    fetch('/api/dashboard')
        .then(r => r.json())
        .then(data => {
            if (data.empty) return;
            
            // Update stats cards
            document.getElementById('statFilesAnalyzed').textContent = (data.total_files || 0).toLocaleString();
            document.getElementById('statProjects').textContent = data.projects_detected || data.projects || 0;
            document.getElementById('statDuplicates').textContent = data.duplicate_files || data.duplicates || 0;
            document.getElementById('statTrash').textContent = data.trash_candidates || 0;
            
            if (data.average_importance) {
                document.getElementById('statImportance').textContent = data.average_importance.toFixed(1) + '/10';
            }
            
            // Update storage widget
            if (data.total_size_bytes) {
                document.getElementById('storageTotal').textContent = formatSize(data.total_size_bytes);
            }
            if (data.duplicates_size_bytes) {
                document.getElementById('storageDuplicates').textContent = formatSize(data.duplicates_size_bytes) + ' saved';
            }
            if (data.trash_size_bytes) {
                const trashPct = ((data.trash_size_bytes / (data.total_size_bytes || 1)) * 100).toFixed(0);
                document.getElementById('storageRecommended').textContent = formatSize(data.trash_size_bytes) + ` (${trashPct}%)`;
            }
            
            // Update changes with dynamic data
            if (data.files_change) {
                document.getElementById('statFilesChange').textContent = `+${data.files_change} since last scan`;
            }
            if (data.projects_change) {
                const projectsChangeEl = document.querySelector('#view-dashboard .stat-card:nth-child(2) .stat-change');
                if (projectsChangeEl) projectsChangeEl.textContent = `+${data.projects_change} new projects`;
            }
            if (data.duplicates_size) {
                document.querySelector('#view-dashboard .stat-card:nth-child(3) .stat-change').textContent = 
                    formatSize(data.duplicates_size);
            }
            if (data.trash_size) {
                document.querySelector('#view-dashboard .stat-card:nth-child(4) .stat-change').textContent = 
                    formatSize(data.trash_size);
            }
        })
        .catch(err => console.error('Dashboard error:', err));
}

function formatSize(bytes) {
    if (!bytes) return '0 GB';
    const gb = bytes / (1024 * 1024 * 1024);
    if (gb >= 1) return gb.toFixed(1) + ' GB';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return mb.toFixed(1) + ' MB';
    const kb = bytes / 1024;
    return kb.toFixed(1) + ' KB';
}

function loadRecentActivity() {
    // Simulate loading recent activity (replace with actual API call if needed)
    const activities = [
        { type: 'success', title: 'Scan completed', desc: 'Documents • 2,483 files', time: '2m ago' },
        { type: 'info', title: 'Report saved', desc: 'My Files Report.json', time: '15m ago' },
        { type: 'primary', title: 'Query executed', desc: 'Inactive Python projects', time: '1h ago' },
        { type: 'warning', title: 'Files renamed', desc: '8 files renamed', time: '2h ago' },
        { type: 'secondary', title: 'Duplicates found', desc: '293 duplicates (28 GB)', time: '3h ago' },
    ];
    
    const container = document.getElementById('activityList');
    if (!container) return;
    
    container.innerHTML = activities.map(act => `
        <div class="activity-item">
            <div class="activity-icon ${act.type}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${getActivityIcon(act.type)}
                </svg>
            </div>
            <div class="activity-content">
                <div class="activity-title">${act.title}</div>
                <div class="activity-desc">${act.desc}</div>
            </div>
            <div class="activity-time">${act.time}</div>
        </div>
    `).join('');
}

function getActivityIcon(type) {
    const icons = {
        success: '<polyline points="20 6 9 17 4 12"/>',
        info: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
        primary: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
        warning: '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 4 21l.5-3.5L17 3z"/>',
        secondary: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/>'
    };
    return icons[type] || '<circle cx="12" cy="12" r="10"/>';
}

function loadRecommendations() {
    // Simulate loading recommendations (replace with actual API call if needed)
    const recommendations = [
        { 
            type: 'red', 
            title: '17 duplicate screenshots', 
            desc: 'You can save 4.2 GB',
            icon: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
        },
        { 
            type: 'blue', 
            title: '8 inactive coding projects', 
            desc: 'Not accessed in 6+ months',
            icon: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'
        },
        { 
            type: 'orange', 
            title: '43 temporary downloads', 
            desc: 'You can save 3.1 GB',
            icon: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'
        },
        { 
            type: 'green', 
            title: '2 large video files', 
            desc: 'You can save 8.7 GB',
            icon: '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>'
        },
    ];
    
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    container.innerHTML = recommendations.map(rec => `
        <div class="recommendation-item" onclick="showRecommendationDetail('${escapeHtml(rec.title)}', '${escapeHtml(rec.desc)}')">
            <div class="rec-icon" style="background: var(--${rec.type}-bg)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${rec.icon}</svg>
            </div>
            <div class="rec-content">
                <div class="rec-title">${rec.title}</div>
                <div class="rec-desc">${rec.desc}</div>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="rec-arrow">
                <polyline points="9 18 15 12 9 6"/>
            </svg>
        </div>
    `).join('');
}

function loadCategoryDistribution() {
    fetch('/api/dashboard/categories')
        .then(r => r.json())
        .then(data => {
            if (data.categories && data.categories.length > 0) {
                const table = document.getElementById('categoriesTable');
                if (table) {
                    const total = data.categories.reduce((sum, cat) => sum + cat.size_bytes, 0);
                    table.innerHTML = data.categories.map((cat, idx) => {
                        const pct = total > 0 ? Math.round((cat.size_bytes / total) * 100) : 0;
                        return `
                            <div class="category-row">
                                <span class="cat-color" style="background: ${cat.color || '#888'}"></span>
                                <span class="cat-name">${cat.name}</span>
                                <span class="cat-files">${cat.files?.toLocaleString() || '-'}</span>
                                <span class="cat-size">${formatSize(cat.size_bytes)}</span>
                                <div class="cat-bar"><div class="cat-bar-fill" style="width: ${pct}%"></div></div>
                                <span class="cat-pct">${pct}%</span>
                            </div>
                        `;
                    }).join('');
                    
                    document.getElementById('donutTotal').textContent = Math.round(total / (1024 * 1024 * 1024));
                }
            }
        })
        .catch(err => console.error('Categories error:', err));
}

function updateCategoryView(value) {
    // Toggle between size and count view
    console.log('Category view changed:', value);
}

// ═══════════════════════════════════════════════════════════════════════════
// Theme
// ═══════════════════════════════════════════════════════════════════════════

function toggleDarkMode() {
    state.darkMode = !state.darkMode;
    const theme = state.darkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

// ═══════════════════════════════════════════════════════════════════════════
// Modals
// ═══════════════════════════════════════════════════════════════════════════

function openModal(id) {
    document.getElementById(id).style.display = 'flex';
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

function startScan() {
    const path = document.getElementById('folderPathInput').value.trim();
    if (!path) return;
    closeModal('folderModal');
    beginScan(path);
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
                    setTimeout(poll, 500);
                }
            })
            .catch(() => setTimeout(poll, 1000));
    };
    poll();
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
// Rendering - Table
// ═══════════════════════════════════════════════════════════════════════════

function renderTable(results) {
    const tbody = document.getElementById('resultsBody');
    if (!tbody) return;
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
        
        const action = entry.action || 'Review';
        const confidence = entry.confidence || 0;
        const confClass = confidence >= 85 ? 'conf-high' : confidence >= 60 ? 'conf-medium' : 'conf-low';
        
        const tags = Array.isArray(entry.tags) ? entry.tags.slice(0, 3).map(t => {
            return t.includes(':') ? t.split(':')[1].replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : t;
        }).join(', ') : '';
        
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

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Projects View
// ═══════════════════════════════════════════════════════════════════════════

function renderProjects() {
    const container = document.getElementById('projectsGrid');
    if (!container) return;
    
    // Group files by project
    const projects = {};
    state.results.forEach(r => {
        if (r.project && r.project !== 'Unknown' && r.project !== '') {
            if (!projects[r.project]) {
                projects[r.project] = [];
            }
            projects[r.project].push(r);
        }
    });
    
    if (Object.keys(projects).length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📁</div>
                <div class="empty-text">No projects detected yet</div>
                <div class="empty-subtext">Scan a folder to detect projects</div>
            </div>
        `;
        document.getElementById('projectCount').textContent = '0 projects';
        return;
    }
    
    document.getElementById('projectCount').textContent = `${Object.keys(projects).length} projects`;
    
    container.innerHTML = Object.entries(projects).map(([name, files]) => {
        const size = files.reduce((sum, f) => sum + (f.size_bytes || 0), 0);
        return `
            <div class="project-card">
                <div class="project-header">
                    <div class="project-icon">📁</div>
                    <div class="project-info">
                        <div class="project-name">${escapeHtml(name)}</div>
                        <div class="project-stats">${files.length} files • ${formatSize(size)}</div>
                    </div>
                </div>
                <div class="project-files">
                    ${files.slice(0, 5).map(f => `
                        <div class="project-file-item" title="${escapeHtml(f.file)}">
                            <span class="file-icon">${getCategoryIcon(f.category)}</span>
                            <span class="file-name">${escapeHtml(f.file)}</span>
                        </div>
                    `).join('')}
                    ${files.length > 5 ? `<div class="more-files">+${files.length - 5} more files</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Duplicates View
// ═══════════════════════════════════════════════════════════════════════════

function renderDuplicates() {
    const tbody = document.getElementById('duplicatesBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    fetch('/api/duplicates')
        .then(r => r.json())
        .then(data => {
            const groups = data.duplicate_groups || [];
            document.getElementById('duplicateCount').textContent = `${groups.length} duplicate groups`;
            
            if (groups.length === 0) {
                tbody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="4">
                            <div class="empty-state">
                                <div class="empty-icon">📄</div>
                                <div class="empty-text">No duplicates found</div>
                                <div class="empty-subtext">Analyze files to detect duplicates</div>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            groups.forEach((group, idx) => {
                const tr = document.createElement('tr');
                const totalSize = group.files.reduce((sum, f) => sum + (f.size_bytes || 0), 0) / group.count;
                tr.innerHTML = `
                    <td><span class="conf-badge">Group ${idx + 1}</span></td>
                    <td>${group.count} files</td>
                    <td>${formatSize(totalSize * group.count)}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-icon-sm" title="View files" onclick="showQueryResult('Files: ${group.files.map(f => f.name).join(', ')}')">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="4">
                        <div class="empty-state">
                            <div class="empty-icon">⚠</div>
                            <div class="empty-text">Error loading duplicates</div>
                        </div>
                    </td>
                </tr>
            `;
        });
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Large Files View
// ═══════════════════════════════════════════════════════════════════════════

function renderLargeFiles() {
    const tbody = document.getElementById('largeFilesBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    // Sort by size, get top 50
    const sorted = [...state.results]
        .filter(r => r.size_bytes)
        .sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))
        .slice(0, 50);
    
    document.getElementById('largeFileStats').textContent = `${sorted.length} large files`;
    
    if (sorted.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="5">
                    <div class="empty-state">
                        <div class="empty-icon">💾</div>
                        <div class="empty-text">No files analyzed yet</div>
                        <div class="empty-subtext">Scan a folder to see large files</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    sorted.forEach(entry => {
        const tr = document.createElement('tr');
        const action = entry.action || 'Review';
        const confidence = entry.confidence || 0;
        const confClass = confidence >= 85 ? 'conf-high' : confidence >= 60 ? 'conf-medium' : 'conf-low';
        
        tr.innerHTML = `
            <td title="${escapeHtml(entry.file || '')}">${escapeHtml(entry.file || '')}</td>
            <td>${getCategoryIcon(entry.category)} ${escapeHtml(entry.category || '')}</td>
            <td>${formatSize(entry.size_bytes)}</td>
            <td>${entry.importance || '-'}/10</td>
            <td><span class="conf-badge ${confClass}">${confidence}%</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Recent Files View
// ═══════════════════════════════════════════════════════════════════════════

function renderRecentFiles() {
    const tbody = document.getElementById('recentFilesBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    // Files sorted by modification time (simulated - would use mtime from API)
    const sorted = [...state.results].slice(0, 50);
    
    if (sorted.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="5">
                    <div class="empty-state">
                        <div class="empty-icon">⏱</div>
                        <div class="empty-text">No files analyzed yet</div>
                        <div class="empty-subtext">Scan a folder to see recent files</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    sorted.forEach(entry => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(entry.file || '')}</td>
            <td>${getCategoryIcon(entry.category)} ${escapeHtml(entry.category || '')}</td>
            <td>Today</td>
            <td>${formatSize(entry.size_bytes)}</td>
            <td>${entry.importance || '-'}/10</td>
        `;
        tbody.appendChild(tr);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Trash Candidates View
// ═══════════════════════════════════════════════════════════════════════════

function renderTrashCandidates() {
    const tbody = document.getElementById('trashBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    // Get files marked for deletion or review with high confidence
    const trash = state.results.filter(r => {
        const action = r.action || '';
        const conf = r.confidence || 0;
        return (action === 'Delete' || action === 'Review') && conf >= 70;
    }).sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0));
    
    const totalSize = trash.reduce((sum, r) => sum + (r.size_bytes || 0), 0);
    document.getElementById('trashStats').textContent = `${trash.length} candidates • ${formatSize(totalSize)}`;
    
    if (trash.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="6">
                    <div class="empty-state">
                        <div class="empty-icon">🗑</div>
                        <div class="empty-text">No trash candidates found</div>
                        <div class="empty-subtext">Files with high confidence Delete/Review will appear here</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    trash.forEach(entry => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(entry.file || '')}</td>
            <td>${getCategoryIcon(entry.category)} ${escapeHtml(entry.category || '')}</td>
            <td><span class="conf-badge ${entry.confidence >= 85 ? 'conf-high' : 'conf-medium'}">${entry.confidence || 0}%</span></td>
            <td title="${escapeHtml(entry.reasoning || '')}">${escapeHtml(entry.reasoning || '').substring(0, 60)}${entry.reasoning && entry.reasoning.length > 60 ? '...' : ''}</td>
            <td>${formatSize(entry.size_bytes)}</td>
            <td><span class="action-badge action-${entry.action}">${getActionIcon(entry.action)} ${entry.action}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Queries History View
// ═══════════════════════════════════════════════════════════════════════════

function renderQueriesHistory() {
    const container = document.getElementById('queriesHistory');
    if (!container) return;
    
    if (state.queryHistory.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❓</div>
                <div class="empty-text">No queries yet</div>
                <div class="empty-subtext">Use the query bar at the bottom to ask questions</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.queryHistory.map(q => `
        <div class="query-history-item">
            <div class="query-question">"${escapeHtml(q.question)}"</div>
            <div class="query-answer">${escapeHtml(q.answer)}</div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// Rendering - Reports View
// ═══════════════════════════════════════════════════════════════════════════

function loadReportsList() {
    fetch('/api/reports/list')
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('reportsBody');
            if (!tbody) return;
            
            const reports = data.reports || [];
            
            if (reports.length === 0) {
                tbody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="4">
                            <div class="empty-state">
                                <div class="empty-icon">📄</div>
                                <div class="empty-text">No saved reports</div>
                                <div class="empty-subtext">Run a scan and save the report to see it here</div>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            tbody.innerHTML = reports.map(report => {
                const date = new Date(report.modified * 1000);
                return `
                    <tr>
                        <td>${escapeHtml(report.filename)}</td>
                        <td>${formatSize(report.size)}</td>
                        <td>${date.toLocaleDateString()} ${date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn-icon-sm" title="Load" onclick="loadReportFile('${escapeHtml(report.path)}')">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M5 3a2 2 0 1 0 4 0 2 0 1 0 0-4 0"/>
                                        <path d="M19 19V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v14"/>
                                    </svg>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => console.error('Failed to load reports:', err));
}

// ═══════════════════════════════════════════════════════════════════════════
// Filtering
// ═══════════════════════════════════════════════════════════════════════════

let filterTimeout;

function debounceFilter() {
    clearTimeout(filterTimeout);
    filterTimeout = setTimeout(applyFilters, 300);
}

function applyFilters() {
    const search = document.getElementById('searchInput').value;
    const category = document.getElementById('filterCategory')?.value || '';
    const action = document.getElementById('filterAction')?.value || '';
    const lifecycle = document.getElementById('filterLifecycle')?.value || '';
    
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
    document.getElementById('filterCategory')?.setAttribute('value', '');
    document.getElementById('filterAction')?.setAttribute('value', '');
    document.getElementById('filterLifecycle')?.setAttribute('value', '');
    renderTable(state.results);
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
        
        if (column === 'confidence' || column === 'importance' || column === 'size_bytes') {
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
// Query Functions
// ═══════════════════════════════════════════════════════════════════════════

function setQuery(text) {
    // If this is called with a view parameter, use setView instead
    if (['dashboard', 'files', 'projects', 'duplicates', 'large', 'recent', 'trash', 'queries', 'reports', 'settings'].includes(text)) {
        setView(text);
        return;
    }
    
    document.getElementById('queryInput').value = text;
    submitQuery();
}

function submitQuery() {
    const question = document.getElementById('queryInput').value.trim();
    if (!question) return;
    
    const resultDiv = document.getElementById('queryResult');
    resultDiv.style.display = 'block';
    resultDiv.textContent = '🤖 Thinking...';
    
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
        
        // Add to query history
        state.queryHistory.unshift({
            question: question,
            answer: data.answer || 'No answer.'
        });
        if (currentView === 'queries') {
            renderQueriesHistory();
        }
    })
    .catch(err => {
        resultDiv.textContent = '⚠ Error: ' + err.message;
    });
}

function showQueryResult(text) {
    const body = document.getElementById('queryResultBody');
    body.textContent = text;
    document.getElementById('queryResultModal').querySelector('h3').textContent = '🤖 Result';
    openModal('queryResultModal');
}

function showRecommendationDetail(title, desc) {
    showQueryResult(`${title}\n\n${desc}`);
}

// ═══════════════════════════════════════════════════════════════════════════
// File Actions
// ═══════════════════════════════════════════════════════════════════════════

function selectFile(index) {
    const entry = state.results[index];
    if (!entry) return;
    
    state.selectedFile = entry;
    
    // Highlight row
    document.querySelectorAll('#resultsBody tr').forEach((tr, i) => {
        tr.classList.toggle('selected', i === index);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// Reports
// ═══════════════════════════════════════════════════════════════════════════

function saveReport() {
    fetch('/api/reports/save', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.path) {
                showQueryResult(`✅ Report saved: ${data.filename}`);
                loadReportsList();
            }
        })
        .catch(err => showError('Failed to save: ' + err.message));
}

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
        setView('dashboard');
        showQueryResult(`✅ Report loaded: ${filePath.split('/').pop()}`);
    })
    .catch(err => showError('Failed to load report: ' + err.message));
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
    const fileCountEl = document.getElementById('fileCount');
    if (fileCountEl) {
        fileCountEl.textContent = `${count} files`;
    }
}

function updateResultCount(count) {
    const resultCountEl = document.getElementById('resultCount');
    if (resultCountEl) {
        const total = state.results.length;
        if (count === total) {
            resultCountEl.textContent = `${total} files`;
        } else {
            resultCountEl.textContent = `${count} of ${total} files`;
        }
    }
}

function showError(message) {
    const resultDiv = document.getElementById('queryResult');
    resultDiv.style.display = 'block';
    resultDiv.textContent = '⚠ ' + message;
    resultDiv.style.color = 'var(--red)';
    setTimeout(() => { resultDiv.style.color = ''; }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

function renderAll() {
    renderTable(state.results);
}

// ═══════════════════════════════════════════════════════════════════════════
// Settings
// ═══════════════════════════════════════════════════════════════════════════

function updateSetting(key, value) {
    console.log('Setting changed:', key, value);
    // Settings would be sent to backend API to be saved
}