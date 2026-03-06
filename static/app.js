/**
 * AI Product Inventor — Frontend Application
 * Handles API calls, dynamic rendering, Chart.js radar charts,
 * and animated UI state transitions.
 */

// ── State ──
let currentJobId = null;
let pollInterval = null;
let resultData = null;
const radarCharts = {};

// ── Category Input ──
function fillCategory(category) {
    document.getElementById('categoryInput').value = category;
    document.getElementById('categoryInput').focus();
}

document.getElementById('categoryInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startAnalysis();
});

// ── Start Analysis ──
async function startAnalysis() {
    const input = document.getElementById('categoryInput');
    const category = input.value.trim();

    if (!category) {
        input.style.borderColor = 'var(--accent-3)';
        setTimeout(() => input.style.borderColor = '', 1000);
        return;
    }

    // Switch to loading state
    document.getElementById('hero').style.display = 'none';
    document.getElementById('results').classList.remove('active');
    document.getElementById('loading').classList.add('active');
    resetProgress();

    try {
        const resp = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, region: 'India' }),
        });

        if (!resp.ok) throw new Error(`API error: ${resp.status}`);

        const data = await resp.json();
        currentJobId = data.job_id;

        // Start polling
        pollInterval = setInterval(() => pollStatus(currentJobId), 2000);
    } catch (err) {
        showError(err.message);
    }
}

// ── Poll Job Status ──
async function pollStatus(jobId) {
    try {
        const resp = await fetch(`/api/status/${jobId}`);
        if (!resp.ok) throw new Error('Status check failed');

        const data = await resp.json();
        updateProgress(data);

        if (data.status === 'complete') {
            clearInterval(pollInterval);
            await fetchResults(jobId);
        } else if (data.status === 'error') {
            clearInterval(pollInterval);
            showError(data.message);
        }
    } catch (err) {
        clearInterval(pollInterval);
        showError(err.message);
    }
}

// ── Update Progress UI ──
function resetProgress() {
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('loadingStatus').textContent = 'Starting analysis pipeline...';
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach(s => {
        s.classList.remove('active', 'done');
    });
}

function updateProgress(data) {
    const bar = document.getElementById('progressBar');
    const status = document.getElementById('loadingStatus');

    bar.style.width = `${data.progress}%`;
    status.textContent = data.message;

    // Update step indicators
    const stepMap = {
        'scraping': ['step-scraping', 'step-reddit', 'step-trends'],
        'analyzing': ['step-analyzing'],
        'generating': ['step-gaps', 'step-generating'],
        'scoring': ['step-scoring'],
    };

    // Mark completed steps
    const statusOrder = ['scraping', 'analyzing', 'generating', 'scoring'];
    const currentIdx = statusOrder.indexOf(data.status);

    for (let i = 0; i < statusOrder.length; i++) {
        const stepIds = stepMap[statusOrder[i]];
        if (stepIds) {
            stepIds.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    if (i < currentIdx) {
                        el.classList.remove('active');
                        el.classList.add('done');
                        el.querySelector('.step-icon').textContent = '✓';
                    } else if (i === currentIdx) {
                        el.classList.add('active');
                        el.classList.remove('done');
                    }
                }
            });
        }
    }

    // Handle sub-step progress within scraping
    if (data.status === 'scraping') {
        if (data.progress > 35) {
            setStepDone('step-scraping');
            setStepDone('step-reddit');
            setStepActive('step-trends');
        } else if (data.progress > 25) {
            setStepDone('step-scraping');
            setStepActive('step-reddit');
        } else {
            setStepActive('step-scraping');
        }
    }
}

function setStepActive(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.add('active');
        el.classList.remove('done');
    }
}

function setStepDone(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove('active');
        el.classList.add('done');
        el.querySelector('.step-icon').textContent = '✓';
    }
}

// ── Fetch Results ──
async function fetchResults(jobId) {
    try {
        const resp = await fetch(`/api/results/${jobId}`);
        if (!resp.ok) throw new Error('Failed to fetch results');

        const data = await resp.json();
        resultData = data.result;

        // Transition to results
        document.getElementById('loading').classList.remove('active');
        renderResults(resultData);
        document.getElementById('results').classList.add('active');
    } catch (err) {
        showError(err.message);
    }
}

// ── Render Results ──
function renderResults(data) {
    // Header
    document.getElementById('resultCategory').textContent = data.category;
    document.getElementById('resultSubtitle').textContent =
        `Analyzed ${data.data_summary.total_data_points} data points from ${Object.keys(data.data_summary).filter(k => k !== 'total_data_points').length} sources`;

    // Stats
    renderStats(data);

    // Tabs
    renderConcepts(data.concepts);
    renderPainPoints(data.pain_points);
    renderGaps(data.market_gaps);
    renderTrends(data.trends);
}

// ── Stats Strip ──
function renderStats(data) {
    const strip = document.getElementById('statsStrip');
    const stats = [
        { value: data.data_summary.total_data_points, label: 'Data Points' },
        { value: data.pain_points.length, label: 'Pain Points' },
        { value: data.market_gaps.length, label: 'Market Gaps' },
        { value: data.concepts.length, label: 'Concepts' },
        { value: data.data_summary.total_reviews, label: 'Reviews' },
        { value: data.data_summary.reddit_posts, label: 'Reddit Posts' },
    ];

    strip.innerHTML = stats.map(s => `
        <div class="stat-card">
            <div class="stat-value">${s.value}</div>
            <div class="stat-label">${s.label}</div>
        </div>
    `).join('');
}

// ── Concepts Tab ──
function renderConcepts(concepts) {
    const grid = document.getElementById('conceptsGrid');
    grid.innerHTML = concepts.map((c, i) => {
        const verdictClass = getVerdictClass(c.verdict);
        const features = (c.key_features || []).map(f => `<span class="feature-tag">${f}</span>`).join('');

        const evidence = c.evidence || {};
        const quotes = (evidence.consumer_quotes || []).map(q => `<div class="evidence-quote">"${q}"</div>`).join('');
        const trends = (evidence.trend_signals || []).map(t => `<span class="trend-tag">📈 ${t}</span>`).join('');

        const scores = c.scores || {};

        return `
        <div class="concept-card">
            <div class="concept-header">
                <div class="concept-rank">#${i + 1}</div>
                <div class="concept-title-area">
                    <div class="concept-name">${c.concept_name || 'Untitled'}</div>
                    <div class="concept-tagline">${c.tagline || ''}</div>
                </div>
                <span class="concept-verdict ${verdictClass}">${c.verdict || '🟡 Worth Exploring'}</span>
            </div>

            <p class="concept-description">${c.description || ''}</p>

            <div class="concept-details">
                <div class="detail-group">
                    <h4>Target Audience</h4>
                    <div class="value">${c.target_audience || 'N/A'}</div>
                </div>
                <div class="detail-group">
                    <h4>Price Range</h4>
                    <div class="value">${c.price_range || 'N/A'}</div>
                </div>
                <div class="detail-group">
                    <h4>Innovation Type</h4>
                    <div class="value" style="text-transform: capitalize">${c.innovation_type || 'N/A'}</div>
                </div>
                <div class="detail-group">
                    <h4>Differentiator</h4>
                    <div class="value">${c.differentiator || 'N/A'}</div>
                </div>
            </div>

            <div class="detail-group" style="margin-bottom: var(--space-lg)">
                <h4>Key Features</h4>
                <div class="features-list">${features}</div>
            </div>

            <div class="evidence-section">
                <h4>📋 Supporting Evidence</h4>
                <div class="evidence-quotes">${quotes || '<div class="evidence-quote">No direct quotes available</div>'}</div>
                ${trends ? `<div class="evidence-trends">${trends}</div>` : ''}
            </div>

            ${c.go_to_market ? `
            <div class="detail-group" style="margin-bottom: var(--space-lg)">
                <h4>Go-to-Market Strategy</h4>
                <div class="value">${c.go_to_market}</div>
            </div>
            ` : ''}

            ${c.risk_factors ? `
            <div class="detail-group" style="margin-bottom: var(--space-lg)">
                <h4>⚠️ Risk Factors</h4>
                <div class="value">${(c.risk_factors || []).join(' · ')}</div>
            </div>
            ` : ''}

            <div class="concept-scores">
                <div class="score-chart-container">
                    <canvas id="radar-${i}"></canvas>
                </div>
                <div class="score-bars">
                    ${renderScoreBar('Market Size', scores.market_size, '#7c3aed')}
                    ${renderScoreBar('Competition', scores.competition, '#06b6d4')}
                    ${renderScoreBar('Urgency', scores.consumer_urgency, '#f43f5e')}
                    ${renderScoreBar('Trends', scores.trend_momentum, '#10b981')}
                    ${renderScoreBar('Feasibility', scores.feasibility, '#f59e0b')}
                </div>
                <div class="overall-score">
                    <div class="big-number">${c.overall_score || '—'}</div>
                    <div class="label">Overall</div>
                </div>
            </div>
        </div>
        `;
    }).join('');

    // Create radar charts for each concept
    setTimeout(() => {
        concepts.forEach((c, i) => {
            createRadarChart(`radar-${i}`, c.scores);
        });
    }, 100);
}

function renderScoreBar(label, value, color) {
    const val = value || 0;
    return `
    <div class="score-bar-item">
        <span class="score-bar-label">${label}</span>
        <div class="score-bar-track">
            <div class="score-bar-fill" style="width: ${val}%; background: ${color}"></div>
        </div>
        <span class="score-bar-value" style="color: ${color}">${val}</span>
    </div>
    `;
}

function getVerdictClass(verdict) {
    if (!verdict) return 'verdict-moderate';
    if (verdict.includes('Strong')) return 'verdict-strong';
    if (verdict.includes('Weak')) return 'verdict-weak';
    return 'verdict-moderate';
}

function createRadarChart(canvasId, scores) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !scores) return;

    if (radarCharts[canvasId]) {
        radarCharts[canvasId].destroy();
    }

    const ctx = canvas.getContext('2d');
    radarCharts[canvasId] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Market', 'Competition', 'Urgency', 'Trends', 'Feasibility'],
            datasets: [{
                data: [
                    scores.market_size || 0,
                    scores.competition || 0,
                    scores.consumer_urgency || 0,
                    scores.trend_momentum || 0,
                    scores.feasibility || 0,
                ],
                backgroundColor: 'rgba(124, 58, 237, 0.15)',
                borderColor: 'rgba(124, 58, 237, 0.6)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(124, 58, 237, 0.8)',
                pointBorderColor: '#fff',
                pointBorderWidth: 1,
                pointRadius: 3,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        display: false,
                        stepSize: 25,
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.06)',
                    },
                    angleLines: {
                        color: 'rgba(255, 255, 255, 0.06)',
                    },
                    pointLabels: {
                        color: 'rgba(255, 255, 255, 0.4)',
                        font: { size: 9, family: 'Inter' },
                    },
                },
            },
        },
    });
}

// ── Pain Points Tab ──
function renderPainPoints(painPoints) {
    const grid = document.getElementById('painPointsGrid');
    grid.innerHTML = (painPoints || []).map(pp => {
        const category = pp.category || 'functionality';
        const severity = pp.severity || 3;
        const dots = Array.from({ length: 5 }, (_, i) =>
            `<span class="severity-dot ${i < severity ? 'filled' : ''}"></span>`
        ).join('');

        const evidence = (pp.evidence || []).slice(0, 2).map(e =>
            `<div class="pain-point-evidence">"${e}"</div>`
        ).join('');

        const hack = pp.consumer_hack
            ? `<div class="pain-point-meta" style="color: var(--accent-2)">🔧 Workaround: ${pp.consumer_hack}</div>`
            : '';

        return `
        <div class="pain-point-card">
            <div class="pain-point-header">
                <span class="pain-point-category cat-${category}">${category.replace('_', ' ')}</span>
                <div class="severity-dots" title="Severity: ${severity}/5">${dots}</div>
            </div>
            <p class="pain-point-text">${pp.pain_point}</p>
            ${evidence}
            ${hack}
            <div class="pain-point-meta">
                <span>📊 ~${pp.frequency || '?'} mentions</span>
                <span>📦 ${(pp.source_products || []).slice(0, 2).join(', ') || 'Various products'}</span>
            </div>
        </div>
        `;
    }).join('');
}

// ── Market Gaps Tab ──
function renderGaps(gaps) {
    const grid = document.getElementById('gapsGrid');
    grid.innerHTML = (gaps || []).map(gap => {
        const confidence = gap.confidence_score || 5;
        const confColor = confidence >= 7 ? 'var(--accent-4)' : confidence >= 4 ? '#f59e0b' : 'var(--accent-3)';

        const signals = (gap.demand_signals || []).map(s =>
            `<div style="padding: 4px 0; font-size: 0.85rem; color: var(--text-secondary)">• ${s}</div>`
        ).join('');

        return `
        <div class="gap-card">
            <div class="gap-header">
                <div class="gap-title">${gap.gap_title || 'Untitled Gap'}</div>
                <span class="gap-confidence" style="background: ${confColor}20; color: ${confColor}; border: 1px solid ${confColor}40">
                    Confidence: ${confidence}/10
                </span>
            </div>
            <p class="gap-description">${gap.gap_description || ''}</p>

            <div style="margin-bottom: var(--space-lg)">
                <h4 style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: var(--space-sm)">
                    Demand Signals
                </h4>
                ${signals}
            </div>

            ${gap.current_supply_failure ? `
            <div style="margin-bottom: var(--space-lg); padding: var(--space-md); background: rgba(244, 63, 94, 0.06); border-radius: var(--radius-sm); border-left: 2px solid var(--accent-3)">
                <h4 style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent-3); margin-bottom: 4px">Why Current Products Fail</h4>
                <div style="font-size: 0.88rem; color: var(--text-secondary)">${gap.current_supply_failure}</div>
            </div>
            ` : ''}

            <div class="gap-meta-grid">
                <div class="gap-meta-item">
                    <div class="label">Opportunity Size</div>
                    <div class="value" style="text-transform: capitalize">${gap.opportunity_size || 'N/A'}</div>
                </div>
                <div class="gap-meta-item">
                    <div class="label">Trend Direction</div>
                    <div class="value" style="text-transform: capitalize">${gap.trend_direction || 'N/A'}</div>
                </div>
                <div class="gap-meta-item">
                    <div class="label">Target Audience</div>
                    <div class="value">${gap.target_audience || 'N/A'}</div>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

// ── Trends Tab ──
function renderTrends(trends) {
    const grid = document.getElementById('trendsGrid');
    if (!trends) {
        grid.innerHTML = '<p style="color: var(--text-muted)">No trends data available.</p>';
        return;
    }

    let html = '';

    // Rising Queries
    if (trends.related_queries_rising && trends.related_queries_rising.length > 0) {
        html += `
        <div class="trends-card">
            <h3>🚀 Rising Searches</h3>
            <div class="trends-list">
                ${trends.related_queries_rising.map(q => `
                    <div class="trend-item">
                        <span class="query">${q.query}</span>
                        <span class="value">+${q.value}%</span>
                    </div>
                `).join('')}
            </div>
        </div>
        `;
    }

    // Top Queries
    if (trends.related_queries_top && trends.related_queries_top.length > 0) {
        html += `
        <div class="trends-card">
            <h3>🔍 Top Searches</h3>
            <div class="trends-list">
                ${trends.related_queries_top.map(q => `
                    <div class="trend-item">
                        <span class="query">${q.query}</span>
                        <span class="value">${q.value}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        `;
    }

    // Rising Topics
    if (trends.related_topics_rising && trends.related_topics_rising.length > 0) {
        html += `
        <div class="trends-card">
            <h3>🔥 Trending Topics</h3>
            <div class="trends-list">
                ${trends.related_topics_rising.map(t => `
                    <div class="trend-item">
                        <span class="query">${t.title} <small style="color: var(--text-muted)">(${t.type})</small></span>
                        <span class="value">+${t.value}%</span>
                    </div>
                `).join('')}
            </div>
        </div>
        `;
    }

    // Interest Over Time Chart
    if (trends.interest_over_time && trends.interest_over_time.length > 0) {
        html += `
        <div class="trends-card" style="grid-column: 1 / -1">
            <h3>📊 Interest Over Time (12 months)</h3>
            <div class="trend-chart-container">
                <canvas id="trendsChart"></canvas>
            </div>
        </div>
        `;
    }

    grid.innerHTML = html || '<p style="color: var(--text-muted)">No trends data available.</p>';

    // Create interest-over-time line chart
    if (trends.interest_over_time && trends.interest_over_time.length > 0) {
        setTimeout(() => createTrendsChart(trends.interest_over_time), 100);
    }
}

function createTrendsChart(data) {
    const canvas = document.getElementById('trendsChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date),
            datasets: [{
                label: 'Search Interest',
                data: data.map(d => d.interest),
                borderColor: 'rgba(124, 58, 237, 0.8)',
                backgroundColor: 'rgba(124, 58, 237, 0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.3)',
                        maxTicksLimit: 12,
                        font: { size: 10 },
                    },
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.3)',
                        font: { size: 10 },
                    },
                    beginAtZero: true,
                },
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
        },
    });
}

// ── Tab Switching ──
function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(tabName.slice(0, 4))) {
            btn.classList.add('active');
        }
    });

    // Update panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    const targetPanel = document.getElementById(`panel-${tabName}`);
    if (targetPanel) targetPanel.classList.add('active');
}

// ── Error Handling ──
function showError(message) {
    document.getElementById('loading').classList.remove('active');
    document.getElementById('hero').style.display = '';

    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed; top: 80px; left: 50%; transform: translateX(-50%);
        background: rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.3);
        padding: 12px 24px; border-radius: 12px; color: #fb7185;
        font-size: 0.9rem; z-index: 1000; backdrop-filter: blur(10px);
        animation: fadeInUp 0.3s ease-out;
    `;
    errorDiv.textContent = `⚠️ ${message}`;
    document.body.appendChild(errorDiv);

    setTimeout(() => {
        errorDiv.style.opacity = '0';
        errorDiv.style.transition = 'opacity 0.3s ease';
        setTimeout(() => errorDiv.remove(), 300);
    }, 5000);
}

// ── New Analysis ──
function newAnalysis() {
    document.getElementById('results').classList.remove('active');
    document.getElementById('loading').classList.remove('active');
    document.getElementById('hero').style.display = '';
    document.getElementById('categoryInput').value = '';
    document.getElementById('categoryInput').focus();

    // Destroy existing charts
    Object.values(radarCharts).forEach(c => c.destroy());
    for (const key in radarCharts) delete radarCharts[key];
}
