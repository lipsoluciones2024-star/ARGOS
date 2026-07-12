(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const API = (p) => fetch("/api/v1/" + p).then((r) => r.json());
  const POST = (p, b) => fetch("/api/v1/" + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) }).then((r) => r.json());
  const PUT = (p, b) => fetch("/api/v1/" + p, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) }).then((r) => r.json());

  let ws = null;
  let history = [];
  let metricsTimer = null;
  const SEV_COLOR = { critical: "#ff3b5c", high: "#f43f5e", medium: "#f59e0b", low: "#2dd4a7", info: "#60a5fa" };

  /* ---------------- WebSocket ---------------- */
  function connect() {
    ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => setWs(true);
    ws.onclose = () => { setWs(false); setTimeout(connect, 2000); };
    ws.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      if (d.type === "chat_stream") onStream(d);
      else if (d.type === "chat") addMsg("assistant", d.content);
      else if (d.type === "proactive_alert") addMsg("assistant", d.message);
      else if (d.type === "switch") { $("switch-select").value = d.level; setSwitchPill(d.level); }
      else if (d.type === "error") addMsg("assistant", "Error: " + d.content);
    };
  }
  const wsSend = (o) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); };
  function setWs(ok) { const p = $("ws-pill"); p.textContent = ok ? "● live" : "○ offline"; p.style.color = ok ? "var(--ok)" : "var(--danger)"; }

  /* ---------------- Navigation ---------------- */
  const TITLES = {
    overview: ["Security Overview", "Real-time posture across distributed sensors"],
    topology: ["Defense Mesh Topology", "Distributed components and data flow"],
    events: ["Event Stream", "Raw OCSF telemetry with full-text search"],
    alerts: ["Active Alerts", "Detections from Sigma, baseline and threat intel"],
    hosts: ["Monitored Hosts", "Endpoints reporting telemetry"],
    attacks: ["MITRE ATT&CK", "Technique coverage and blind spots"],
    ai: ["AI Security Copilot", "Hybrid reasoning brain with tool use"],
    response: ["Response Orchestration", "Autonomy switch and action proposals"],
    audit: ["Audit Trail", "Immutable, hash-chained response log"],
    settings: ["Platform Settings", "Runtime configuration for brain and core"],
  };
  function showView(name) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === name));
    const v = $("view-" + name); if (v) v.classList.add("active");
    const [t, s] = TITLES[name] || ["ARGOS", ""];
    $("view-title").textContent = t; $("view-sub").textContent = s;
  }

  /* ---------------- Overview ---------------- */
  async function loadOverview() {
    const m = await API("metrics").catch(() => null);
    if (!m) return;
    const sev = m.by_severity || {};
    const crit = (sev.critical || 0) + (sev.high || 0);
    const kpis = [
      { label: "Total Events", value: m.total_events.toLocaleString(), ico: "≣", d: "last 24h window", cls: "" },
      { label: "Critical / High", value: crit.toLocaleString(), ico: "⚠", d: "active severity", cls: crit ? "up" : "down" },
      { label: "Monitored Hosts", value: (m.top_hosts || []).length, ico: "▤", d: "reporting", cls: "" },
      { label: "ATT&CK Coverage", value: `${m.attck_covered}/${m.attck_total}`, ico: "⚑", d: `${m.attck_blind_spots} blind spots`, cls: m.attck_blind_spots ? "up" : "down" },
      { label: "AI Channel", value: (m.ai_channel || "—"), ico: "✸", d: "last inference", cls: "" },
      { label: "Autonomy", value: m.switch || "OBSERVE", ico: "⚙", d: "response mode", cls: "" },
    ];
    $("kpi-grid").innerHTML = kpis.map((k) => `
      <div class="kpi">
        <div class="ico">${k.ico}</div>
        <div class="label">${k.label}</div>
        <div class="value">${k.value}</div>
        <div class="delta ${k.cls}">${k.d}</div>
      </div>`).join("");
    $("tp-total").textContent = (m.total_events || 0).toLocaleString() + " events";
    renderThroughput(m.series_24h || []);
    renderCategory(m.by_category || {});
    renderAttckBar(m);
    const alerts = await API("alerts?limit=6").catch(() => []);
    $("overview-alerts").innerHTML = (alerts.length ? alerts : [{ title: "No active alerts", severity: "low", host: "—", time: "" }]).map(alertCard).join("");
  }

  function renderThroughput(series) {
    const buckets = [...new Set(series.map((s) => s.bucket))].sort();
    if (!buckets.length) { $("chart-throughput").innerHTML = "<p class='muted'>No telemetry yet.</p>"; return; }
    const sevs = ["critical", "high", "medium", "low", "info"];
    const data = buckets.map((b) => {
      const row = { bucket: b };
      sevs.forEach((s) => (row[s] = (series.find((x) => x.bucket === b && x.severity === s) || {}).count || 0));
      return row;
    });
    const W = 600, H = 200, pad = 26, bw = (W - pad * 2) / data.length;
    const max = Math.max(1, ...data.map((d) => sevs.reduce((a, s) => a + d[s], 0)));
    let bars = "", legend = sevs.map((s) => `<span><i class="lg" style="background:${SEV_COLOR[s]}"></i>${s}</span>`).join("  ");
    data.forEach((d, i) => {
      let y = H - pad, x = pad + i * bw + bw * 0.15, w = bw * 0.7;
      sevs.forEach((s) => {
        const h = (d[s] / max) * (H - pad * 2);
        if (h <= 0) return;
        bars += `<rect x="${x}" y="${y - h}" width="${w}" height="${h}" fill="${SEV_COLOR[s]}" rx="2"><title>${s}: ${d[s]}</title></rect>`;
        y -= h;
      });
    });
    $("chart-throughput").innerHTML = `<svg viewBox="0 0 ${W} ${H}">${bars}<line x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}" stroke="#1e2a44"/>${legendSVG(legend, W, 12)}</svg>`;
  }
  function legendSVG(html, W, y) { return `<foreignObject x="0" y="${y}" width="${W}" height="16"><div xmlns="http://www.w3.org/1999/xhtml" style="font-size:10px;color:#8b9bb7">${html}</div></foreignObject>`; }

  function renderCategory(byCat) {
    const entries = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
    if (!entries.length) { $("chart-category").innerHTML = "<p class='muted'>No data.</p>"; return; }
    const max = Math.max(...entries.map((e) => e[1]));
    $("chart-category").innerHTML = `<svg viewBox="0 0 600 220">${entries.map((e, i) => {
      const w = (e[1] / max) * 460, y = 14 + i * 34;
      return `<text x="0" y="${y + 14}" fill="#8b9bb7" font-size="12">${e[0]}</text>
        <rect x="140" y="${y}" width="${w}" height="18" rx="4" fill="url(#g)"/>
        <text x="${140 + w + 8}" y="${y + 14}" fill="#cfe0ff" font-size="12">${e[1]}</text>`;
    }).join("")}<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs></svg>`;
  }

  function renderAttckBar(m) {
    const cov = Math.round((m.attck_covered / Math.max(1, m.attck_total)) * 100);
    $("attck-summary").textContent = `${cov}% covered · ${m.attck_blind_spots} blind spots`;
    $("attck-bar").innerHTML = `<span class="covered" style="width:${cov}%"></span><span class="blind" style="width:${100 - cov}%"></span>`;
  }

  /* ---------------- Topology ---------------- */
  async function loadTopology() {
    const m = await API("metrics").catch(() => null);
    const nodes = [
      { id: "agents", label: "Endpoint Agents", sub: `${(m?.top_hosts || []).length} hosts`, state: "live", metric: (m?.top_hosts || []).length },
      { id: "collector", label: "Collector", sub: "ingest pipeline", state: (m?.total_events || 0) > 0 ? "live" : "warn", metric: (m?.total_events || 0) },
      { id: "core", label: "Detection Core", sub: "sigma + baseline", state: "live", metric: (m?.attck_covered || 0) },
      { id: "brain", label: "AI Brain", sub: m?.ai_channel || "idle", state: "live", metric: m?.ai_channel || "—" },
      { id: "response", label: "Response", sub: m?.switch || "OBSERVE", state: "live", metric: m?.switch || "OBSERVE" },
    ];
    const W = 900, H = 200, x0 = 60, gap = (W - 120) / (nodes.length - 1);
    let links = "", rects = "";
    nodes.forEach((n, i) => {
      const x = x0 + i * gap;
      if (i < nodes.length - 1) links += `<line class="topo-link" x1="${x + 120}" y1="${H / 2}" x2="${x + gap}" y2="${H / 2}"/>`;
      rects += `<g>
        <rect class="topo-node ${n.state}" x="${x}" y="${H / 2 - 34}" width="120" height="68" rx="12"/>
        <text class="topo-label" x="${x + 60}" y="${H / 2 - 10}" text-anchor="middle">${n.label}</text>
        <text class="topo-sub" x="${x + 60}" y="${H / 2 + 10}" text-anchor="middle">${n.metric}</text>
      </g>`;
    });
    $("topology").innerHTML = `<svg viewBox="0 0 ${W} ${H}">${links}${rects}</svg>`;
    $("component-cards").innerHTML = nodes.map((n) => `
      <div class="component-card">
        <div class="ch"><h4>${n.label}</h4><span class="state ${n.state}">${n.state}</span></div>
        <div class="metric">${n.metric}</div>
        <div class="desc">${n.sub}</div>
      </div>`).join("");
  }

  /* ---------------- Events ---------------- */
  async function loadEvents() {
    const cat = $("ev-category").value, sev = $("ev-severity").value, host = $("ev-host").value, q = $("ev-search").value.trim();
    const p = new URLSearchParams({ limit: 200 });
    if (cat) p.set("category", cat); if (sev) p.set("severity", sev); if (host) p.set("host", host); if (q) p.set("text", q);
    const rows = await fetch("/api/v1/events?" + p.toString()).then((r) => r.json());
    $("events-table").querySelector("tbody").innerHTML = rows.slice(0, 300).map((e) => `
      <tr>
        <td>${fmtTime(e.time)}</td>
        <td><span class="sev-dot dot-${e.severity}"></span>${e.severity}</td>
        <td><span class="tag">${e.category}</span></td>
        <td>${e.host}</td>
        <td>${detailOf(e)}</td>
        <td>${e.attack_id ? `<span class="tag">${e.attack_id}</span>` : "—"}</td>
      </tr>`).join("") || `<tr><td colspan="6" class="muted">No events.</td></tr>`;
  }
  const detailOf = (e) => e.process_name || e.dns || e.file_path || e.user || e.src_ip || e.registry_key || "event";

  /* ---------------- Alerts ---------------- */
  async function loadAlerts() {
    const sev = $("al-severity").value;
    const rows = await API("alerts?limit=60" + (sev ? "&severity=" + sev : ""));
    $("alert-grid").innerHTML = (rows.length ? rows : [{ title: "No alerts", severity: "low", host: "—", time: "" }]).map(alertCard).join("");
  }
  function alertCard(a) {
    return `<div class="alert-card ${(a.severity || "low")}">
      <h4>${a.title}</h4>
      <div class="row"><span class="sev" style="color:${SEV_COLOR[a.severity] || "#8b9bb7"}">${a.severity}</span>${a.attack_id ? `<span class="tag">${a.attack_id}</span>` : ""}${a.host ? `<span class="tag">${a.host}</span>` : ""}</div>
      <div class="meta" style="margin-top:6px">${a.summary || ""} · ${fmtTime(a.time)}</div>
    </div>`;
  }

  /* ---------------- Hosts ---------------- */
  async function loadHosts() {
    const rows = await API("hosts?limit=100");
    $("hosts-table").querySelector("tbody").innerHTML = rows.map((h) => `
      <tr><td>${h.host}</td><td>${h.events}</td><td>${fmtTime(h.last_seen)}</td>
      <td><span class="state live">online</span></td></tr>`).join("") || `<tr><td colspan="4" class="muted">No hosts.</td></tr>`;
  }

  /* ---------------- ATT&CK ---------------- */
  async function loadAttacks() {
    const cov = await API("coverage");
    const entries = Object.entries(cov);
    $("attacks-count").textContent = `${entries.length} techniques tracked`;
    $("attck-matrix").innerHTML = entries.map(([tid, v]) => `
      <div class="attck-cell ${v.status}">
        <b>${v.name}</b><span class="tid">${tid} · ${v.tactic}</span>
      </div>`).join("");
  }

  /* ---------------- AI Brain ---------------- */
  async function loadAiStatus() {
    const s = await API("ai/status").catch(() => null);
    if (!s) return;
    $("ai-status-chip").textContent = `${s.enabled ? "enabled" : "disabled"} · ${s.mode_setting} · ${s.model_setting}`;
    $("ai-meta").innerHTML = `
      <div class="item"><b>Mode</b><div class="meta">${s.mode_setting}</div></div>
      <div class="item"><b>Model</b><div class="meta">${s.model_setting}</div></div>
      <div class="item"><b>Last channel</b><div class="meta">${s.last_channel} / ${s.last_model || "—"}</div></div>
      <div class="item"><b>Gateway reachable</b><div class="meta">${s.gateway_available}</div></div>
      <div class="item"><b>Local runtime</b><div class="meta">${s.local_available}</div></div>`;
  }
  function sendAi() {
    const input = $("ai-input"); const text = input.value.trim(); if (!text) return;
    addMsg("user", text); history.push({ role: "user", content: text });
    if (streamSupported()) wsSend({ type: "chat_stream", message: text, history });
    else wsSend({ type: "chat", message: text, history });
    input.value = "";
  }
  function streamSupported() { return true; }
  let currentMsg = null;
  function onStream(d) {
    if (d.type === "begin") { currentMsg = addMsg("assistant", ""); $("ai-tools").prepend(toolItem("thinking…")); }
    else if (d.type === "token") { if (currentMsg) currentMsg.querySelector(".body").insertAdjacentText("beforeend", d.content); scrollAi(); }
    else if (d.type === "tool") { $("ai-tools").prepend(toolItem(`${d.name} ⟶ ${JSON.stringify(d.arguments).slice(0, 80)}`)); }
    else if (d.type === "done") { if (currentMsg) { currentMsg.querySelector(".body").textContent = d.content; history.push({ role: "assistant", content: d.content }); } currentMsg = null; scrollAi(); }
    else if (d.type === "error") { addMsg("assistant", "Error: " + d.content); currentMsg = null; }
  }
  function toolItem(text) { const d = document.createElement("div"); d.className = "item"; d.textContent = "⚒ " + text; return d; }
  function addMsg(role, text) {
    const el = document.createElement("div"); el.className = "msg " + role;
    const who = document.createElement("div"); who.className = "who"; who.textContent = role === "user" ? "You" : "ARGOS AI";
    const body = document.createElement("div"); body.className = "body"; body.textContent = text;
    el.appendChild(who); el.appendChild(body); $("ai-messages").appendChild(el); scrollAi(); return el;
  }
  const scrollAi = () => { const m = $("ai-messages"); m.scrollTop = m.scrollHeight; };

  /* ---------------- Response ---------------- */
  async function loadResponse() {
    const actions = await API("actions");
    $("actions").innerHTML = actions.map((a) => `<div class="item"><b>${a.action}</b> <span class="tag">risk: ${a.risk}</span></div>`).join("");
    const sel = $("propose-action");
    if (!sel.options.length) actions.forEach((a) => { const o = document.createElement("option"); o.value = a.action; o.textContent = `${a.action} (${a.risk})`; sel.appendChild(o); });
    const props = await API("proposals");
    $("proposals").innerHTML = props.length ? props.map((p) => `
      <div class="item"><b>${p.action}</b> → ${p.target} <span class="tag">${p.status}</span>
      ${p.status === "pending" ? `<button class="ghost" onclick="confirmP('${p.id}')">Confirm</button>` : ""}</div>`).join("")
      : `<div class="item">No pending proposals.</div>`;
  }
  window.confirmP = async (id) => { await POST("confirm", { id, approved_by: "soc-ui" }); loadResponse(); };

  /* ---------------- Audit ---------------- */
  async function loadAudit() {
    const rows = await API("audit?limit=200");
    $("audit-table").querySelector("tbody").innerHTML = rows.map((a) => `
      <tr><td>${a.seq ?? ""}</td><td>${fmtTime(a.time)}</td><td>${a.action}</td><td>${a.proposed_by}</td>
      <td><span class="state ${a.status === "executed" ? "live" : a.status === "denied" ? "down" : "warn"}">${a.status}</span></td></tr>`).join("")
      || `<tr><td colspan="5" class="muted">No audit entries.</td></tr>`;
  }

  /* ---------------- Settings ---------------- */
  async function loadSettings() {
    const s = await API("settings");
    const aiFields = [
      { k: "ai.enabled", l: "AI enabled", t: "bool" },
      { k: "ai.mode", l: "Mode (hybrid/remote/local)", t: "text" },
      { k: "ai.model", l: "Model override (blank=auto)", t: "text" },
      { k: "ai.temperature", l: "Temperature", t: "num" },
      { k: "ai.max_tokens", l: "Max tokens", t: "num" },
      { k: "ai.streaming", l: "Stream responses", t: "bool" },
    ];
    const platFields = [
      { k: "switch.default", l: "Default autonomy", t: "text" },
      { k: "retention_days", l: "Retention (days)", t: "num" },
      { k: "scheduler.enabled", l: "Scheduler enabled", t: "bool" },
      { k: "scheduler.interval_sec", l: "Scheduler interval (s)", t: "num" },
      { k: "ui.refresh_sec", l: "UI refresh (s)", t: "num" },
      { k: "ui.theme", l: "Theme", t: "text" },
    ];
    const render = (f) => f.map((f) => {
      const v = s[f.k];
      if (f.t === "bool") return `<label class="list"><span>${f.l}</span><input type="checkbox" data-k="${f.k}" ${v ? "checked" : ""}></label>`;
      return `<label class="list"><span>${f.l}</span><input type="${f.t === "num" ? "number" : "text"}" data-k="${f.k}" value="${v ?? ""}"></label>`;
    }).join("");
    $("ai-settings").innerHTML = render(aiFields);
    $("plat-settings").innerHTML = render(platFields);
  }
  function collectSettings(scope) {
    const out = {};
    document.querySelectorAll(`#${scope} input[data-k]`).forEach((inp) => {
      const k = inp.dataset.k;
      out[k] = inp.type === "checkbox" ? inp.checked : (inp.type === "number" ? Number(inp.value) : inp.value);
    });
    return out;
  }

  /* ---------------- helpers ---------------- */
  function fmtTime(t) { if (!t) return "—"; return String(t).replace("T", " ").slice(0, 19); }
  function setSwitchPill(level) { /* placeholder for future */ }
  function tickClock() { const d = new Date(); $("clock").textContent = d.toLocaleTimeString(); }

  async function refreshAll() {
    await Promise.all([loadOverview(), loadTopology(), loadAttacks(), loadAiStatus()]);
    const active = document.querySelector(".view.active")?.id;
    if (active === "view-events") loadEvents();
    else if (active === "view-alerts") loadAlerts();
    else if (active === "view-hosts") loadHosts();
    else if (active === "view-response") loadResponse();
    else if (active === "view-audit") loadAudit();
    const h = await API("health").catch(() => null);
    const chip = $("health-chip");
    if (h && h.status === "ok") { chip.classList.remove("bad"); chip.innerHTML = '<span class="dot"></span> Healthy'; }
    else { chip.classList.add("bad"); chip.innerHTML = '<span class="dot"></span> Degraded'; }
  }

  /* ---------------- wiring ---------------- */
  function init() {
    document.querySelectorAll(".nav-item").forEach((b) => b.onclick = () => showView(b.dataset.view));
    document.querySelectorAll(".link[data-jump]").forEach((a) => a.onclick = () => showView(a.dataset.jump));
    $("switch-select").onchange = (e) => { wsSend({ type: "switch", level: e.target.value }); };
    $("ai-send").onclick = sendAi;
    $("ai-input").addEventListener("keydown", (e) => { if (e.key === "Enter") sendAi(); });
    $("ev-refresh").onclick = loadEvents;
    $("ev-search").addEventListener("keydown", (e) => { if (e.key === "Enter") loadEvents(); });
    $("ev-category").onchange = loadEvents; $("ev-severity").onchange = loadEvents; $("ev-host").onchange = loadEvents;
    $("al-refresh").onclick = loadAlerts; $("al-severity").onchange = loadAlerts;
    $("propose-btn").onclick = async () => {
      const action = $("propose-action").value, target = $("propose-target").value.trim(); if (!target) return;
      await POST("propose", { action, target, proposed_by: "soc-ui" }); $("propose-target").value = ""; loadResponse();
    };
    $("ai-settings-save").onclick = async () => { await PUT("settings", collectSettings("ai-settings")); loadAiStatus(); toast("AI settings saved"); };
    $("plat-settings-save").onclick = async () => { await PUT("settings", collectSettings("plat-settings")); toast("Platform settings saved"); };

    connect(); tickClock(); setInterval(tickClock, 1000);
    refreshAll();
    const refresh = () => { const sec = 5; metricsTimer = setInterval(refreshAll, sec * 1000); };
    refresh();
    // seed filter options
    API("events?limit=1").catch(() => {});
  }
  function toast(msg) {
    const t = document.createElement("div"); t.textContent = msg;
    t.style.cssText = "position:fixed;bottom:20px;right:20px;background:#16203a;border:1px solid #2b4d77;color:#cfe0ff;padding:10px 16px;border-radius:10px;z-index:99;box-shadow:0 8px 30px rgba(0,0,0,.4)";
    document.body.appendChild(t); setTimeout(() => t.remove(), 2200);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
