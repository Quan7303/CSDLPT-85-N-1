document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    loadOverview();
    loadBenchmark();

    document.getElementById("run-query").addEventListener("click", runComparison);
});

function initTabs() {
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById(tab.dataset.tab).classList.add("active");
        });
    });
}

async function loadOverview() {
    try {
        const resp = await fetch("/api/overview");
        const data = await resp.json();
        const grid = document.getElementById("node-grid");
        grid.innerHTML = data.nodes.map(node => `
            <div class="node-card">
                <div class="node-header">
                    <span class="node-name">${node.name}</span>
                    <span class="status-badge status-${node.status}">${node.status}</span>
                </div>
                <div class="node-detail"><span>Site ID</span><span>${node.site_id}</span></div>
                <div class="node-detail"><span>Letter Range</span><span>${node.letter_range}</span></div>
                <div class="node-detail"><span>URL</span><span>${node.url}</span></div>
                ${node.cache ? `
                    <div class="node-detail"><span>Cache Entries</span><span>${node.cache.entries}/${node.cache.max_entries}</span></div>
                    <div class="node-detail"><span>Cache Hit Rate</span><span>${node.cache.hit_rate_pct}%</span></div>
                ` : ""}
            </div>
        `).join("");
    } catch (e) {
        document.getElementById("node-grid").innerHTML = '<p class="loading">Cannot connect to dashboard API. Make sure nodes are running.</p>';
    }
}

async function runComparison() {
    const btn = document.getElementById("run-query");
    btn.disabled = true;
    btn.textContent = "Running...";

    const country = document.getElementById("country-select").value;
    const limit = document.getElementById("limit-input").value;
    const latency = document.getElementById("latency-select").value;

    document.getElementById("lazy-stats").innerHTML = '<p class="loading">Loading...</p>';
    document.getElementById("eager-stats").innerHTML = '<p class="loading">Loading...</p>';
    document.getElementById("lazy-authors").innerHTML = "";
    document.getElementById("eager-authors").innerHTML = "";

    try {
        await fetch("/api/set_latency", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ latency_ms: parseInt(latency) })
        });

        const params = `country=${encodeURIComponent(country)}&limit=${limit}`;

        const [lazyResp, eagerResp] = await Promise.all([
            fetch(`/api/query/lazy?${params}`),
            fetch(`/api/query/eager?${params}`)
        ]);

        const lazyData = await lazyResp.json();
        const eagerData = await eagerResp.json();

        renderStats("lazy-stats", lazyData.stats, "lazy");
        renderStats("eager-stats", eagerData.stats, "eager");
        renderAuthors("lazy-authors", lazyData.authors);
        renderAuthors("eager-authors", eagerData.authors);

    } catch (e) {
        document.getElementById("lazy-stats").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Run Comparison";
    }
}

function renderStats(elementId, stats, type) {
    const el = document.getElementById(elementId);
    const colorClass = type === "lazy" ? "text-red" : "text-green";
    el.innerHTML = `
        <div>Total Time: <span class="stat-highlight ${colorClass}">${stats.total_time_ms.toFixed(1)}ms</span></div>
        <div>Network Calls: <span class="stat-value">${stats.network_calls}</span></div>
        <div>Network Time: <span class="stat-value">${stats.total_network_ms.toFixed(1)}ms</span></div>
        <div>Serialization: <span class="stat-value">${stats.total_serialization_ms.toFixed(1)}ms</span></div>
        <div>Authors Loaded: <span class="stat-value">${stats.total_authors}</span></div>
        ${stats.failed_nodes.length ? `<div class="text-red">Failed Nodes: ${stats.failed_nodes.length}</div>` : ""}
    `;
}

function renderAuthors(elementId, authors) {
    const el = document.getElementById(elementId);
    if (!authors || !authors.length) {
        el.innerHTML = '<p class="loading">No authors found</p>';
        return;
    }
    el.innerHTML = authors.slice(0, 10).map(a => `
        <div class="author-item">
            <div class="author-name">${a.name}</div>
            <div class="author-meta">${a.country || ""} | Born: ${a.birth_year || "N/A"} | Books: <span class="book-count">${(a.books || []).length}</span></div>
            ${a.books && a.books.length ? `
                <div class="book-list">
                    ${a.books.slice(0, 5).map(b => `<div>- ${b.title} (${b.average_rating || "N/A"})</div>`).join("")}
                    ${a.books.length > 5 ? `<div>... and ${a.books.length - 5} more</div>` : ""}
                </div>
            ` : ""}
        </div>
    `).join("");
}

async function loadBenchmark() {
    try {
        const resp = await fetch("/api/benchmark_results");
        if (!resp.ok) {
            document.getElementById("benchmark-chart").innerHTML = '<p class="loading">No benchmark results yet. Run benchmark/run_benchmark.py first.</p>';
            return;
        }
        const data = await resp.json();
        renderBenchmarkChart(data);
        renderBenchmarkTable(data);
    } catch (e) {
        document.getElementById("benchmark-chart").innerHTML = '<p class="loading">Cannot load benchmark results.</p>';
    }
}

function renderBenchmarkChart(data) {
    const container = document.getElementById("benchmark-chart");
    if (!data.results || !data.results.length) {
        container.innerHTML = '<p class="loading">No results available</p>';
        return;
    }

    const maxTime = Math.max(...data.results.map(r => Math.max(r.lazy.avg_total_ms, r.eager.avg_total_ms)));
    const barHeight = 30;
    const gap = 8;

    let html = '<h3>Lazy vs Eager Loading - Response Time by Latency</h3>';
    html += '<div style="margin-top: 1rem;">';

    data.results.forEach(r => {
        const lazyW = (r.lazy.avg_total_ms / maxTime * 100).toFixed(1);
        const eagerW = (r.eager.avg_total_ms / maxTime * 100).toFixed(1);

        html += `
            <div style="margin-bottom: ${gap}px; display: flex; align-items: center; gap: 8px;">
                <span style="width: 60px; text-align: right; font-size: 0.8rem; color: var(--text-secondary);">${r.latency_ms}ms</span>
                <div style="flex: 1;">
                    <div style="background: var(--accent-red); height: ${barHeight/2}px; width: ${lazyW}%; border-radius: 3px; margin-bottom: 2px; min-width: 2px;"></div>
                    <div style="background: var(--accent-green); height: ${barHeight/2}px; width: ${eagerW}%; border-radius: 3px; min-width: 2px;"></div>
                </div>
                <span style="width: 100px; font-size: 0.75rem; color: var(--text-secondary);">${r.lazy.avg_total_ms.toFixed(0)} / ${r.eager.avg_total_ms.toFixed(0)}ms</span>
            </div>
        `;
    });

    html += '</div>';
    html += '<div style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-secondary);">';
    html += '<span style="color: var(--accent-red);">Red = Lazy Loading</span> | <span style="color: var(--accent-green);">Green = Eager Loading</span>';
    html += '</div>';

    container.innerHTML = html;
}

function renderBenchmarkTable(data) {
    const container = document.getElementById("benchmark-table");
    if (!data.results || !data.results.length) return;

    let html = `<table>
        <thead><tr>
            <th>Latency</th>
            <th>Lazy Total</th>
            <th>Eager Total</th>
            <th>Lazy Calls</th>
            <th>Eager Calls</th>
            <th>Speedup</th>
        </tr></thead><tbody>`;

    data.results.forEach(r => {
        html += `<tr>
            <td>${r.latency_ms}ms</td>
            <td class="text-red">${r.lazy.avg_total_ms.toFixed(1)}ms</td>
            <td class="text-green">${r.eager.avg_total_ms.toFixed(1)}ms</td>
            <td>${r.lazy.avg_network_calls}</td>
            <td>${r.eager.avg_network_calls}</td>
            <td class="text-blue">${r.speedup}x</td>
        </tr>`;
    });

    html += "</tbody></table>";
    container.innerHTML = html;
}
