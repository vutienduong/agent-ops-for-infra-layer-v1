from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


DASHBOARD_HTML = """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>AgentOps MVP Dashboard</title>
    <style>
      :root {
        --bg: #f3efe6;
        --ink: #1f2937;
        --muted: #5d6472;
        --accent: #0f766e;
        --card: #fffaf2;
        --line: #d6ccb8;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at 20% 20%, #f9e7cb 0%, rgba(249, 231, 203, 0) 40%),
          radial-gradient(circle at 90% 10%, #d1f2eb 0%, rgba(209, 242, 235, 0) 35%),
          var(--bg);
      }
      .layout {
        max-width: 1160px;
        margin: 0 auto;
        padding: 22px;
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      .title {
        font-size: 30px;
        font-weight: 700;
        letter-spacing: 0.01em;
      }
      .sub {
        color: var(--muted);
        font-size: 14px;
      }
      .toolbar {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      input, button {
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 14px;
      }
      input {
        min-width: 260px;
        background: #fff;
      }
      button {
        background: var(--accent);
        color: #fff;
        border: none;
        cursor: pointer;
      }
      .grid {
        display: grid;
        gap: 14px;
        grid-template-columns: minmax(280px, 420px) 1fr;
      }
      .card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px;
      }
      .card h2 {
        margin: 0 0 10px;
        font-size: 16px;
      }
      .list {
        display: grid;
        gap: 8px;
      }
      .run-item {
        width: 100%;
        text-align: left;
        border: 1px solid var(--line);
        background: #fff;
        color: var(--ink);
      }
      .run-item strong {
        display: block;
      }
      .tiny {
        font-size: 12px;
        color: var(--muted);
      }
      .pill {
        display: inline-block;
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 999px;
        background: #e6fffa;
        color: #0f766e;
      }
      .timeline {
        display: grid;
        gap: 8px;
      }
      .span-row {
        border-left: 4px solid var(--accent);
        padding: 8px 10px;
        background: #fff;
        border-radius: 8px;
      }
      .metrics {
        margin-top: 12px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
      }
      .metric {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px;
      }
      @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
        input { min-width: 180px; }
      }
    </style>
  </head>
  <body>
    <div class=\"layout\">
      <div class=\"head\">
        <div>
          <div class=\"title\">AgentOps MVP Dashboard</div>
          <div class=\"sub\">Runs, spans, and cost from your current project key.</div>
        </div>
        <div class=\"toolbar\">
          <input id=\"apiKey\" placeholder=\"X-AgentOps-Key\" />
          <button id=\"load\">Load</button>
        </div>
      </div>

      <div class=\"grid\">
        <section class=\"card\">
          <h2>Runs</h2>
          <div id=\"runs\" class=\"list\"></div>
        </section>

        <section class=\"card\">
          <h2>Run Detail</h2>
          <div id=\"runSummary\" class=\"tiny\">Select a run to view timeline.</div>
          <div id=\"timeline\" class=\"timeline\"></div>
          <div class=\"metrics\" id=\"costMetrics\"></div>
        </section>
      </div>
    </div>

    <script>
      const apiKeyInput = document.getElementById('apiKey');
      const loadBtn = document.getElementById('load');
      const runsEl = document.getElementById('runs');
      const summaryEl = document.getElementById('runSummary');
      const timelineEl = document.getElementById('timeline');
      const costMetricsEl = document.getElementById('costMetrics');

      apiKeyInput.value = localStorage.getItem('agentops_key') || '';

      async function api(path) {
        const key = apiKeyInput.value.trim();
        if (!key) {
          throw new Error('Missing API key');
        }
        const res = await fetch(path, {
          headers: { 'X-AgentOps-Key': key },
        });
        if (!res.ok) {
          throw new Error(`Request failed: ${res.status}`);
        }
        return res.json();
      }

      function renderRuns(items) {
        runsEl.innerHTML = '';
        if (!items.length) {
          runsEl.innerHTML = '<div class="tiny">No runs yet.</div>';
          return;
        }

        for (const run of items) {
          const btn = document.createElement('button');
          btn.className = 'run-item';
          btn.innerHTML = `
            <strong>${run.name || run.id}</strong>
            <span class="tiny">${run.id}</span><br />
            <span class="pill">${run.status}</span>
          `;
          btn.onclick = () => loadRunDetail(run.id);
          runsEl.appendChild(btn);
        }
      }

      function renderRunDetail(data) {
        summaryEl.innerHTML = `
          <div><strong>${data.run.name || data.run.id}</strong></div>
          <div class="tiny">status=${data.run.status}, cost=$${Number(data.run.total_cost_usd || 0).toFixed(6)}</div>
        `;

        timelineEl.innerHTML = '';
        for (const span of data.spans) {
          const row = document.createElement('div');
          row.className = 'span-row';
          row.innerHTML = `
            <div><strong>${span.name || span.id}</strong> <span class="tiny">(${span.type})</span></div>
            <div class="tiny">status=${span.status}, model=${span.model || 'n/a'}, prompt=${span.tokens_prompt}, completion=${span.tokens_completion}, cost=$${Number(span.cost_usd || 0).toFixed(6)}</div>
          `;
          timelineEl.appendChild(row);
        }
      }

      function renderCostMetrics(items) {
        costMetricsEl.innerHTML = '';
        for (const item of items.slice(0, 3)) {
          const el = document.createElement('div');
          el.className = 'metric';
          el.innerHTML = `
            <div class="tiny">${item.group}</div>
            <div><strong>$${Number(item.total_cost_usd || 0).toFixed(6)}</strong></div>
          `;
          costMetricsEl.appendChild(el);
        }
      }

      async function loadRunDetail(runId) {
        const data = await api(`/v1/runs/${runId}`);
        renderRunDetail(data);
      }

      async function loadDashboard() {
        localStorage.setItem('agentops_key', apiKeyInput.value.trim());
        runsEl.innerHTML = '<div class="tiny">Loading runs...</div>';
        summaryEl.textContent = 'Loading details...';
        timelineEl.innerHTML = '';
        costMetricsEl.innerHTML = '';

        try {
          const [runsData, costData] = await Promise.all([
            api('/v1/runs?limit=20'),
            api('/v1/metrics/cost?group_by=model'),
          ]);
          renderRuns(runsData.items || []);
          renderCostMetrics(costData.items || []);
          summaryEl.textContent = 'Select a run to view timeline.';
        } catch (err) {
          runsEl.innerHTML = `<div class="tiny">${err.message}</div>`;
          summaryEl.textContent = 'Failed to load.';
        }
      }

      loadBtn.onclick = loadDashboard;
      if (apiKeyInput.value) {
        loadDashboard();
      }
    </script>
  </body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML
