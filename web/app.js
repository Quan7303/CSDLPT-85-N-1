document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("run-query").addEventListener("click", executeSequence);
    
    // Toggle Mode Listener
    const toggle = document.getElementById("mode-toggle");
    const modeText = document.getElementById("mode-text");
    toggle.addEventListener("change", (e) => {
        if (e.target.checked) {
            modeText.textContent = "[ EAGER_LOADING | JOIN ]";
            modeText.className = "status-eager";
        } else {
            modeText.textContent = "[ LAZY_LOADING | N+1 ]";
            modeText.className = "status-lazy";
        }
    });
});

async function executeSequence() {
    const btn = document.getElementById("run-query");
    btn.disabled = true;
    btn.textContent = "EXECUTING...";

    const country = document.getElementById("country-select").value;
    const limit = document.getElementById("limit-input").value;
    const latency = document.getElementById("latency-select").value;
    
    // Check mode
    const isEager = document.getElementById("mode-toggle").checked;
    const mode = isEager ? "eager" : "lazy";

    // Show Glitch Loader
    document.getElementById("query-stats").innerHTML = `
        <div class="stat-row">
            <span>STATUS</span>
            <span class="stat-val text-lazy">FETCHING_DATA...</span>
        </div>
    `;
    renderGlitchLoader("query-results");

    try {
        await fetch("/api/set_latency", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ latency_ms: parseInt(latency) })
        });

        const params = `country=${encodeURIComponent(country)}&limit=${limit}`;
        const resp = await fetch(`/api/query/${mode}?${params}`);
        const data = await resp.json();

        renderStats("query-stats", data.stats, mode);
        renderAuthors("query-results", data.authors, mode);

    } catch (e) {
        document.getElementById("query-stats").innerHTML = `
            <div class="stat-row text-err">
                <span>ERROR</span>
                <span class="stat-val">SYS_FAILURE</span>
            </div>
            <div style="margin-top: 0.5rem; font-size: 0.75rem;">${e.message}</div>
        `;
        document.getElementById("query-results").innerHTML = '<div class="giant-bg">SYS_ERR</div>';
    } finally {
        btn.disabled = false;
        btn.textContent = "EXECUTE SEQUENCE";
    }
}

function renderStats(elementId, stats, type) {
    const el = document.getElementById(elementId);
    const colorClass = type === "lazy" ? "text-lazy" : "text-eager";
    
    el.innerHTML = `
        <div class="stat-row">
            <span>TOTAL_TIME</span>
            <span class="stat-val ${colorClass}">${stats.total_time_ms.toFixed(1)} MS</span>
        </div>
        <div class="stat-row">
            <span>NET_CALLS</span>
            <span class="stat-val">${stats.network_calls} REQ</span>
        </div>
        <div class="stat-row">
            <span>NET_LATENCY</span>
            <span class="stat-val">${stats.total_network_ms.toFixed(1)} MS</span>
        </div>
        <div class="stat-row">
            <span>SERVER_CPU(SERIALIZE)</span>
            <span class="stat-val">${stats.total_serialization_ms.toFixed(1)} MS</span>
        </div>
        <div class="stat-row">
            <span>CLIENT_CPU(DESERIALIZE)</span>
            <span class="stat-val">${stats.total_deserialization_ms.toFixed(1)} MS</span>
        </div>
        <div class="stat-row">
            <span>PAYLOAD_SIZE(AUTHORS)</span>
            <span class="stat-val">${stats.total_authors} REC</span>
        </div>
        ${stats.failed_nodes && stats.failed_nodes.length ? `
        <div class="stat-row text-err">
            <span>NODE_FAILURES</span>
            <span class="stat-val">${stats.failed_nodes.length} DOWN</span>
        </div>` : ""}
    `;
}

function renderGlitchLoader(elementId) {
    const el = document.getElementById(elementId);
    const html = Array(4).fill(0).map(() => `
        <div class="glitch-block">
            <div class="glitch-line title"></div>
            <div class="glitch-line meta"></div>
            <div class="glitch-box-container">
                ${Array(5).fill(0).map(() => `<div class="glitch-box"></div>`).join("")}
            </div>
        </div>
    `).join("");
    el.innerHTML = html;
}

function renderAuthors(elementId, authors, mode) {
    const el = document.getElementById(elementId);
    if (!authors || !authors.length) {
        el.innerHTML = '<div class="giant-bg">NO_DATA</div>';
        return;
    }
    
    const bgClass = mode === "lazy" ? "DATA_STREAM [N+1]" : "DATA_STREAM [JOIN]";
    
    let html = `<div class="giant-bg">${bgClass}</div>`;
    
    html += authors.map((a, i) => `
        <div class="author-block" style="animation-delay: ${i * 0.05}s">
            <div class="author-name">${a.name}</div>
            <div class="author-meta">> LOCATION: ${a.country || "UNKNOWN"} | YOB: ${a.birth_year || "N/A"} | RECORDS: <span class="book-count">${(a.books || []).length}</span></div>
            ${a.books && a.books.length ? `
                <div class="ribbon-wrapper">
                    <button class="ribbon-btn btn-left" onclick="scrollRibbon('ribbon-${i}', -400)"><</button>
                    <div class="book-ribbon" id="ribbon-${i}">
                        ${a.books.map(b => `
                            <div class="book-card">
                                ${b.cover_image_uri ? `<img src="${b.cover_image_uri}" alt="Cover" class="book-cover" loading="lazy">` : `<div class="book-cover-placeholder">NO_IMG</div>`}
                                <div class="book-card-content">
                                    <div class="book-title" title="${b.title}">${b.title}</div>
                                    <div class="book-rating">RATING: ${b.average_rating || "N/A"}</div>
                                </div>
                            </div>
                        `).join("")}
                    </div>
                    <button class="ribbon-btn btn-right" onclick="scrollRibbon('ribbon-${i}', 400)">></button>
                </div>
            ` : ""}
        </div>
    `).join("");
    
    el.innerHTML = html;
}

window.scrollRibbon = function(id, offset) {
    const container = document.getElementById(id);
    if (container) {
        container.scrollBy({ left: offset, behavior: 'smooth' });
    }
};
