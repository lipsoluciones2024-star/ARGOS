/* ============================================================
   ARGOS · Views (router interno + renderizado con datos reales)
   Consume TODOS los endpoints /api/v1. Sin datos falsos.
   ============================================================ */
(function (global) {
  "use strict";

  const NS = (global.ARGOS = global.ARGOS || {});
  const $ = (id) => document.getElementById(id);
  const api = () => NS.api;

  const state = { selectedHost: null, alertSev: "" };

  /* ---------- utilidades compartidas ---------- */
  function esc(s) { return NS.esc(s); }
  function sev(sev) { return "sev--" + (sev || "unknown"); }
  function fmtTime(t) {
    if (!t) return "—";
    const s = String(t);
    return s.length > 19 ? s.slice(0, 19).replace("T", " ") : s;
  }
  function sevBadge(s) {
    return `<span class="sev ${sev(s)}">${esc(s || "unknown")}</span>`;
  }

  /* ============================================================
     RESUMEN
     ============================================================ */
  function loadResumen() {
    Promise.all([
      api().get("/stats").catch(() => null),
      api().get("/hosts").catch(() => []),
      api().get("/alerts?limit=10").catch(() => []),
      api().get("/events?limit=12").catch(() => []),
      api().get("/coverage").catch(() => null),
    ]).then(([stats, hosts, alerts, events, cov]) => {
      renderResumenMetrics(stats, hosts, alerts, cov);
      NS.renderThroughput(stats ? stats.series : []);
      renderResumenAlerts(alerts);
      renderResumenEvents(events);
    }).catch(() => {});
  }

  function renderResumenMetrics(stats, hosts, alerts, cov) {
    const grid = $("resumen-metrics");
    if (!grid) return;
    let coveragePct = "—";
    if (cov && cov.total) coveragePct = Math.round((cov.covered / cov.total) * 100) + "%";
    else if (stats && typeof stats.coverage_pct === "number") coveragePct = stats.coverage_pct + "%";
    const defs = [
      { label: "Eventos", value: stats ? String(stats.total_events) : "—", sub: "ingestados" },
      { label: "Hosts", value: hosts ? String(hosts.length) : "—", sub: "monitoreados" },
      { label: "Alertas", value: alerts ? String(alerts.length) : "—", sub: "recientes" },
      { label: "Reglas", value: stats ? String(stats.rules) : "—", sub: "detección" },
      { label: "Cobertura", value: coveragePct, sub: "ATT&CK" },
      { label: "Autonomía", value: stats ? stats.switch : "—", sub: "switch" },
    ];
    grid.innerHTML = defs
      .map((d) => `<div class="metric"><div class="metric__label">${d.label}</div>` +
        `<div class="metric__value">${esc(d.value)}</div><div class="metric__sub">${esc(d.sub)}</div></div>`)
      .join("");
  }

  function renderResumenAlerts(alerts) {
    const box = $("resumen-alerts");
    if (!box) return;
    if (!alerts || !alerts.length) { box.innerHTML = '<div class="empty">Sin alertas</div>'; return; }
    box.innerHTML = alerts.slice(0, 6).map((a) =>
      `<div class="side-row"><span class="side-row__idx">•</span>` +
      `${sevBadge(a.severity)} <span style="overflow:hidden;text-overflow:ellipsis">${esc(a.title || "")}</span>` +
      `<span class="side-row__val">${esc(a.host || "")}</span></div>`
    ).join("");
  }

  function renderResumenEvents(events) {
    const box = $("resumen-events");
    if (!box) return;
    if (!events || !events.length) { box.innerHTML = '<div class="empty">Sin eventos</div>'; return; }
    box.innerHTML = events.slice(0, 8).map((e) =>
      `<div class="side-row"><span class="side-row__idx">•</span>` +
      `<span style="overflow:hidden;text-overflow:ellipsis">${esc(e.category || "?")}</span>` +
      `<span class="side-row__val">${esc(e.host || "")}</span></div>`
    ).join("");
  }

  /* ============================================================
     SEGURIDAD
     ============================================================ */
  function loadSeguridad() {
    Promise.all([
      api().get("/coverage").catch(() => null),
      api().get("/rules").catch(() => []),
      api().get("/actions").catch(() => []),
      api().get("/alerts" + (state.alertSev ? "?severity=" + encodeURIComponent(state.alertSev) : "")).catch(() => []),
    ]).then(([cov, rules, actions, alerts]) => {
      renderCoverage(cov);
      renderRules(rules);
      renderActions(actions);
      renderAlerts(alerts);
    }).catch(() => {});
  }

  function renderCoverage(cov) {
    const box = $("coverage-matrix");
    if (!box) return;
    if (!cov || !cov.matrix) { box.innerHTML = '<div class="empty">Sin datos</div>'; return; }
    const entries = Object.entries(cov.matrix);
    const pct = cov.total ? Math.round((cov.covered / cov.total) * 100) + "%" : "—";
    const badge = $("coverage-pct");
    if (badge) badge.textContent = pct + " (" + (cov.covered || 0) + "/" + (cov.total || 0) + ")";
    box.innerHTML = '<div class="coverage-grid">' + entries.map(([tid, m]) => {
      const blind = m.status !== "covered";
      return `<div class="coverage-cell ${blind ? "is-blind" : "is-covered"}">` +
        `<div class="coverage-cell__tid">${esc(tid)}</div>` +
        `<div class="coverage-cell__name">${esc(m.name || "")}</div>` +
        `<div class="coverage-cell__status">${blind ? "blind-spot" : "covered"}</div></div>`;
    }).join("") + "</div>";
  }

  function renderRules(rules) {
    const t = $("rules-table");
    if (!t) return;
    const badge = $("rules-count");
    if (badge) badge.textContent = rules ? rules.length : "—";
    if (!rules || !rules.length) { t.innerHTML = '<thead><tr><th>Sin reglas</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>Regla</th><th>Nivel</th><th>ATT&CK</th><th>Logsource</th></tr></thead><tbody>" +
      rules.map((r) => `<tr><td>${esc(r.title || "")}</td><td>${sevBadge(r.level)}</td>` +
        `<td>${esc(r.attack_id || "—")}</td><td>${esc((r.logsource && (r.logsource.category || r.logsource)) || "—")}</td></tr>`).join("") +
      "</tbody>";
  }

  function renderActions(actions) {
    const t = $("actions-table");
    if (!t) return;
    const badge = $("actions-count");
    if (badge) badge.textContent = actions ? actions.length : "—";
    if (!actions || !actions.length) { t.innerHTML = ""; return; }
    t.innerHTML =
      "<thead><tr><th>Acción</th><th>Riesgo</th></tr></thead><tbody>" +
      actions.map((a) => {
        const risk = (a.risk || "low").toString().toLowerCase();
        const cls = risk === "high" || risk === "critical" ? "tag--risk" : "tag--warn";
        return `<tr><td>${esc(a.action || "")}</td><td><span class="tag ${cls}">${esc(a.risk || "—")}</span></td></tr>`;
      }).join("") + "</tbody>";
  }

  function renderAlerts(alerts) {
    const t = $("alerts-table");
    if (!t) return;
    if (!alerts || !alerts.length) { t.innerHTML = '<thead><tr><th>Sin datos</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>Hora</th><th>Sev</th><th>Título</th><th>Host</th><th>ATT&CK</th><th>Ack</th></tr></thead><tbody>" +
      alerts.map((a) => {
        const acked = a.acknowledged;
        const ackCell = acked
          ? '<span class="tag tag--ok">✓ ' + esc(a.acknowledged_by || "") + "</span>"
          : '<button class="btn btn--small" data-ack="' + esc(a.id) + '">Ack</button>';
        return `<tr><td>${esc(fmtTime(a.time))}</td><td>${sevBadge(a.severity)}</td>` +
          `<td>${esc(a.title || "")}</td><td>${esc(a.host || "")}</td><td>${esc(a.attack_id || "—")}</td>` +
          `<td>${ackCell}</td></tr>`;
      }).join("") + "</tbody>";
    t.querySelectorAll("[data-ack]").forEach((b) =>
      b.addEventListener("click", () => {
        const id = b.getAttribute("data-ack");
        api().post("/alerts/" + encodeURIComponent(id) + "/ack", {})
          .then(() => loadSeguridad())
          .catch(() => { loadSeguridad(); });
      })
    );
  }

  /* ============================================================
     RED
     ============================================================ */
  function loadRed() {
    api().get("/events?category=network&limit=200").then((events) => {
      renderRed(events || []);
    }).catch(() => {});
  }

  function renderRed(events) {
    const t = $("net-table");
    if (!t) return;
    const badge = $("net-count");
    if (badge) badge.textContent = events.length;
    if (!events.length) { t.innerHTML = '<thead><tr><th>Sin datos</th></tr></thead>'; renderRedSummary({}); return; }
    t.innerHTML =
      "<thead><tr><th>Hora</th><th>Host</th><th>Origen</th><th>Destino</th><th>Proceso</th><th>Sev</th><th>ATT&CK</th></tr></thead><tbody>" +
      events.map((e) => {
        const src = [e.src_ip, e.src_port].filter(Boolean).join(":");
        const dst = [e.dst_ip, e.dst_port].filter(Boolean).join(":");
        const proc = e.process_name || (e.process_image ? e.process_image.split(/[\\/]/).pop() : "—");
        return `<tr><td>${esc(fmtTime(e.time))}</td><td>${esc(e.host || "")}</td>` +
          `<td class="num">${esc(src || "—")}</td><td class="num">${esc(dst || "—")}</td>` +
          `<td>${esc(proc)}</td><td>${sevBadge(e.severity)}</td><td>${esc(e.attack_technique || e.attack_id || "—")}</td></tr>`;
      }).join("") + "</tbody>";

    const srcIps = new Set(events.map((e) => e.src_ip).filter(Boolean));
    const dstIps = new Set(events.map((e) => e.dst_ip).filter(Boolean));
    const prots = new Set(events.map((e) => e.protocol).filter(Boolean));
    const hosts = new Set(events.map((e) => e.host).filter(Boolean));
    renderRedSummary({
      "Conexiones": events.length,
      "Hosts": hosts.size,
      "IPs origen": srcIps.size,
      "IPs destino": dstIps.size,
      "Protocolos": prots.size,
    });
  }

  function renderRedSummary(map) {
    const box = $("red-summary");
    if (!box) return;
    box.innerHTML = Object.entries(map).map(([k, v]) =>
      `<div class="metric"><div class="metric__label">${esc(k)}</div>` +
      `<div class="metric__value">${esc(v)}</div></div>`
    ).join("");
  }

  /* ============================================================
     HOSTS
     ============================================================ */
  function loadHosts() {
    api().get("/hosts?limit=100").then((hosts) => {
      renderHosts(hosts || []);
    }).catch(() => {});
  }

  function renderHosts(hosts) {
    const t = $("hosts-table");
    if (!t) return;
    const badge = $("hosts-count");
    if (badge) badge.textContent = hosts.length;
    if (!hosts.length) { t.innerHTML = '<thead><tr><th>Sin datos</th></tr></thead>'; return; }
    t.className = "tbl tbl--click";
    t.innerHTML =
      "<thead><tr><th>Host</th><th class='num'>Eventos</th><th>Último visto</th></tr></thead><tbody>" +
      hosts.map((h, i) => `<tr data-host="${esc(h.host)}" class="${h.host === state.selectedHost ? "is-selected" : ""}">` +
        `<td>${esc(h.host)}</td><td class="num">${esc(h.events)}</td><td>${esc(fmtTime(h.last_seen))}</td></tr>`).join("") +
      "</tbody>";
    t.querySelectorAll("tbody tr").forEach((tr) =>
      tr.addEventListener("click", () => loadHostDetail(tr.getAttribute("data-host")))
    );
    if (state.selectedHost) loadHostDetail(state.selectedHost);
  }

  function loadHostDetail(host) {
    state.selectedHost = host;
    const name = $("host-detail-name");
    if (name) name.textContent = host;
    Promise.all([
      api().get("/events?host=" + encodeURIComponent(host) + "&limit=100").catch(() => []),
      api().get("/alerts?limit=100").catch(() => []),
    ]).then(([events, alerts]) => {
      const hostAlerts = (alerts || []).filter((a) => a.host === host);
      renderHostDetail(host, events || [], hostAlerts);
    }).catch(() => {});
  }

  function renderHostDetail(host, events, alerts) {
    const box = $("host-detail");
    if (!box) return;
    let html = `<div class="kv">` +
      `<dt>Host</dt><dd>${esc(host)}</dd>` +
      `<dt>Eventos</dt><dd>${events.length}</dd>` +
      `<dt>Alertas</dt><dd>${alerts.length}</dd></div>`;
    if (alerts.length) {
      html += '<div style="margin-top:10px;font-size:11px;color:var(--text-dim)">Alertas</div>';
      html += alerts.slice(0, 8).map((a) =>
        `<div class="side-row"><span class="side-row__idx">•</span>${sevBadge(a.severity)}` +
        `<span style="overflow:hidden;text-overflow:ellipsis">${esc(a.title || "")}</span></div>`
      ).join("");
    }
    html += '<div style="margin-top:10px;font-size:11px;color:var(--text-dim)">Últimos eventos</div>';
    if (!events.length) html += '<div class="empty">Sin eventos</div>';
    else html += '<table class="tbl"><thead><tr><th>Hora</th><th>Cat</th><th>Sev</th><th>Detalle</th></tr></thead><tbody>' +
      events.slice(0, 15).map((e) => {
        const det = e.process_name || e.file_path || e.registry_key || e.dns || e.src_ip || "—";
        return `<tr><td>${esc(fmtTime(e.time))}</td><td>${esc(e.category || "")}</td>` +
          `<td>${sevBadge(e.severity)}</td><td>${esc(det)}</td></tr>`;
      }).join("") + "</tbody></table>";
    box.innerHTML = html;
  }

  /* ============================================================
     AUDITORÍA
     ============================================================ */
  function loadAuditoria() {
    Promise.all([
      api().get("/proposals").catch(() => []),
      api().get("/audit").catch(() => []),
      api().get("/memory/investigations?limit=50").catch(() => []),
    ]).then(([props, audit, invest]) => {
      renderProposals(props);
      renderAudit(audit);
      renderInvestigations(invest);
    }).catch(() => {});
    renderFeedbackForm();
  }

  function renderProposals(props) {
    const box = $("proposals-list");
    if (!box) return;
    const badge = $("proposals-count");
    if (badge) badge.textContent = props ? props.length : "—";
    if (!props || !props.length) { box.innerHTML = '<div class="empty">Sin propuestas pendientes</div>'; return; }
    box.innerHTML = props.map((p) => proposalCard(p)).join("");
    wireProposalCards(box);
  }

  function proposalCard(p) {
    const pending = (p.status || "pending") === "pending";
    return `<div class="proposal-card" data-pid="${esc(p.id)}">` +
      `<div class="proposal-card__head">PROPUESTA (${esc(p.status || "pending")})</div>` +
      `<div class="proposal-card__body">Acción: <b>${esc(p.action || "?")}</b> → ${esc(p.target || "")}` +
      (p.proposed_by ? ` <span class="tag">${esc(p.proposed_by)}</span>` : "") + `</div>` +
      `<div class="proposal-card__actions">` +
      `<button class="btn btn--ok btn--small" data-confirm ${pending ? "" : "disabled"}>Confirmar</button>` +
      `</div>` +
      (p.result ? `<div class="proposal-card__result">Resultado: ${esc(JSON.stringify(p.result))}</div>` : "") +
      `</div>`;
  }

  function wireProposalCards(box) {
    box.querySelectorAll("[data-confirm]").forEach((b) =>
      b.addEventListener("click", () => {
        const id = b.closest(".proposal-card").getAttribute("data-pid");
        NS.confirmProposal(id);
        b.disabled = true;
      })
    );
  }

  function onProposal(m) {
    const box = $("proposals-list");
    if (!box) return;
    const card = box.querySelector('.proposal-card[data-pid="' + (m.id || "") + '"]');
    if (card) {
      const head = card.querySelector(".proposal-card__head");
      if (head) head.textContent = "PROPUESTA (" + (m.status || "pending") + ")";
      const confirm = card.querySelector("[data-confirm]");
      if (confirm) confirm.disabled = true;
      if (m.result) {
        const r = card.querySelector(".proposal-card__result");
        if (r) r.textContent = "Resultado: " + JSON.stringify(m.result);
        else card.insertAdjacentHTML("beforeend", '<div class="proposal-card__result">Resultado: ' + esc(JSON.stringify(m.result)) + "</div>");
      }
    }
    // refrescar la lista para reflejar cambios
    api().get("/proposals").then(renderProposals).catch(() => {});
  }

  function renderAudit(audit) {
    const t = $("audit-table");
    if (!t) return;
    const badge = $("audit-count");
    if (badge) badge.textContent = audit ? audit.length : "—";
    if (!audit || !audit.length) { t.innerHTML = '<thead><tr><th>Sin datos</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>#</th><th>Hora</th><th>Acción</th><th>Propuesto por</th><th>Aprobado por</th><th>Estado</th><th>Detalle</th></tr></thead><tbody>" +
      audit.slice().reverse().slice(0, 100).map((a) => {
        const ok = (a.status || "").toLowerCase().indexOf("approv") >= 0 || (a.status || "").toLowerCase().indexOf("ok") >= 0;
        return `<tr><td class="num">${esc(a.seq)}</td><td>${esc(fmtTime(a.time))}</td>` +
          `<td>${esc(a.action || "")}</td><td>${esc(a.proposed_by || "—")}</td><td>${esc(a.approved_by || "—")}</td>` +
          `<td><span class="tag ${ok ? "tag--ok" : "tag--warn"}">${esc(a.status || "—")}</span></td>` +
          `<td style="max-width:280px">${esc(a.detail || "")}</td></tr>`;
      }).join("") + "</tbody>";
  }

  function renderInvestigations(invest) {
    const t = $("investigations-table");
    if (!t) return;
    const badge = $("invest-count");
    if (badge) badge.textContent = invest ? invest.length : "—";
    if (!invest || !invest.length) { t.innerHTML = '<thead><tr><th>Sin datos</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>ID</th><th>Título</th><th>Estado</th><th>Sev</th></tr></thead><tbody>" +
      invest.map((i) => `<tr><td>${esc(i.id || "")}</td><td>${esc(i.title || i.summary || "")}</td>` +
        `<td>${esc(i.status || "—")}</td><td>${sevBadge(i.severity)}</td></tr>`).join("") + "</tbody>";
  }

  function renderFeedbackForm() {
    const box = $("feedback-form");
    if (!box || box.dataset.ready) return;
    box.dataset.ready = "1";
    box.innerHTML =
      '<form class="form-grid" id="feedback-form-el">' +
      '<div class="form-row"><select class="form-select" name="target_type">' +
      '<option value="action">action</option><option value="rule">rule</option>' +
      '<option value="agent">agent</option><option value="model">model</option></select>' +
      '<input class="form-input" name="target_id" placeholder="ID del objetivo" required></div>' +
      '<div class="form-row"><select class="form-select" name="rating">' +
      '<option value="positive">positive</option><option value="neutral">neutral</option>' +
      '<option value="negative">negative</option></select>' +
      '<button class="btn btn--ok" type="submit">Enviar</button></div>' +
      '<textarea class="form-textarea" name="note" rows="2" placeholder="Nota (opcional)"></textarea>' +
      '<div class="login-card__err" id="feedback-msg"></div></form>';
    box.querySelector("#feedback-form-el").addEventListener("submit", (e) => {
      e.preventDefault();
      const f = e.target;
      const payload = {
        target_type: f.target_type.value, target_id: f.target_id.value.trim(),
        rating: f.rating.value, note: f.note.value.trim(),
      };
      api().post("/feedback", payload).then(() => {
        $("feedback-msg").textContent = "Feedback enviado.";
        $("feedback-msg").style.color = "var(--ok)";
        f.reset();
      }).catch((err) => {
        $("feedback-msg").textContent = "Error: " + err.message;
        $("feedback-msg").style.color = "var(--danger)";
      });
    });
  }

  function onProactive(m) {
    const box = $("proactive-feed");
    if (!box) return;
    const empty = box.querySelector(".empty");
    if (empty) empty.remove();
    const line = document.createElement("div");
    line.className = "feed-line";
    line.textContent = "• " + (m.message || "Alerta");
    box.insertBefore(line, box.firstChild);
    while (box.children.length > 50) box.removeChild(box.lastChild);
  }

  /* ============================================================
     CONFIGURACIÓN
     ============================================================ */
  function loadConfig() {
    Promise.all([
      api().get("/switch").catch(() => null),
      api().get("/ai/status").catch(() => null),
      api().get("/models").catch(() => null),
      api().get("/settings").catch(() => null),
      api().get("/metrics").catch(() => null),
      api().get("/agents").catch(() => null),
    ]).then(([sw, ai, models, settings, metrics, agents]) => {
      renderSwitchControl(sw);
      renderAiStatus(ai);
      renderModels(models);
      renderSettings(settings);
      renderMetrics(metrics);
      renderAgents(agents);
    }).catch(() => {});
    loadChatHistory();
  }

  function renderSwitchControl(sw) {
    const box = $("switch-control");
    if (!box) return;
    const level = sw ? sw.level : "OBSERVE";
    box.innerHTML =
      '<div class="switch-control">' +
      ["OBSERVE", "SUGGEST", "SEMI-AUTO", "FULL_AUTO"].map((l) =>
        `<button class="switch-control__btn ${l === level ? "is-active" : ""}" data-level="${l}">${l}</button>`
      ).join("") +
      '<div class="switch-control__note">Cambiar el nivel requiere rol <b>admin</b>. En OBSERVE/SUGGEST no se ejecuta ninguna acción.</div></div>';
    box.querySelectorAll("[data-level]").forEach((b) =>
      b.addEventListener("click", () => NS.setSwitch(b.getAttribute("data-level")))
    );
  }

  function renderAiStatus(ai) {
    const box = $("ai-status");
    if (!box) return;
    if (!ai) { box.innerHTML = '<div class="empty">Sin datos</div>'; return; }
    box.innerHTML = '<dl class="kv">' + Object.entries(ai).map(([k, v]) =>
      `<dt>${esc(k)}</dt><dd>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</dd>`
    ).join("") + "</dl>";
  }

  function renderModels(models) {
    const box = $("models-list");
    if (!box) return;
    if (!models || models.error) { box.innerHTML = '<div class="empty">' + esc(models ? models.error : "Sin datos") + "</div>"; return; }
    const list = models.models || [];
    if (!list.length) { box.innerHTML = '<div class="empty">Sin modelos</div>'; return; }
    box.innerHTML = list.slice(0, 30).map((m) => {
      const name = m.name || m.id || m;
      const desc = m.description || "";
      return `<div class="side-row"><span class="side-row__idx">•</span><span style="overflow:hidden;text-overflow:ellipsis">${esc(name)}</span>` +
        (desc ? `<span class="side-row__val" style="max-width:120px;overflow:hidden;text-overflow:ellipsis">${esc(desc)}</span>` : "") + "</div>";
    }).join("");
  }

  function renderSettings(settings) {
    const box = $("settings-form");
    if (!box) return;
    if (!settings || !Object.keys(settings).length) { box.innerHTML = '<div class="empty">Sin ajustes</div>'; return; }
    const entries = Object.entries(settings);
    box.innerHTML =
      '<form class="form-grid" id="settings-form-el">' +
      entries.map(([k, v]) =>
        `<div class="form-row"><label style="color:var(--text-dim);font-size:11px">${esc(k)}</label>` +
        `<input class="form-input" name="${esc(k)}" value="${esc(typeof v === "object" ? JSON.stringify(v) : v)}"></div>`
      ).join("") +
      '<button class="btn btn--ok" type="submit">Guardar ajustes</button>' +
      '<div class="login-card__err" id="settings-msg"></div></form>';
    box.querySelector("#settings-form-el").addEventListener("submit", (e) => {
      e.preventDefault();
      const f = e.target;
      const payload = {};
      entries.forEach(([k]) => (payload[k] = f[k].value));
      api().put("/settings", payload).then(() => {
        const msg = $("settings-msg");
        if (msg) { msg.textContent = "Ajustes guardados."; msg.style.color = "var(--ok)"; }
      }).catch((err) => {
        const msg = $("settings-msg");
        if (msg) { msg.textContent = "Error: " + err.message; msg.style.color = "var(--danger)"; }
      });
    });
  }

  function renderMetrics(metrics) {
    const box = $("metrics-view");
    if (!box) return;
    if (!metrics || !Object.keys(metrics).length) { box.innerHTML = '<div class="empty">Sin métricas</div>'; return; }
    box.innerHTML = '<dl class="kv">' + Object.entries(metrics).map(([k, v]) =>
      `<dt>${esc(k)}</dt><dd>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</dd>`
    ).join("") + "</dl>";
  }

  function renderAgents(agents) {
    const box = $("agents-list");
    if (!box) return;
    const badge = $("agents-count");
    const list = (agents && agents.agents) || [];
    if (badge) badge.textContent = list.length;
    if (!list.length) { box.innerHTML = '<div class="empty">Sin datos</div>'; return; }
    const roles = (agents && agents.roles) ? agents.roles.join(", ") : "operator, admin";
    box.innerHTML =
      `<div class="side-row" style="color:var(--text-dim);font-size:11px">Roles con permisos mínimos: ${esc(roles)}</div>` +
      list.map((a) => {
        const tools = (a.tools && a.tools.length) ? a.tools.join(", ") : "todas (Commander)";
        return `<div class="proposal-card" style="margin-bottom:6px"><div class="proposal-card__head">${esc(a.name)} <span class="tag">${esc(a.id)}</span></div>` +
          `<div class="proposal-card__body">${esc(a.mission)}</div>` +
          `<div class="proposal-card__body" style="color:var(--text-dim);font-size:11px">tools: ${esc(tools)}</div></div>`;
      }).join("");
  }

  function loadChatHistory() {
    const box = $("chat-history");
    if (!box) return;
    api().get("/chat/sessions").then((sessions) => {
      if (!sessions || !sessions.length) { box.innerHTML = '<div class="empty">Sin conversaciones</div>'; return; }
      box.innerHTML = sessions.slice(0, 20).map((s) =>
        `<div class="side-row" style="cursor:pointer" data-session="${esc(s.id || s)}">` +
        `<span class="side-row__idx">💬</span><span style="overflow:hidden;text-overflow:ellipsis">${esc(s.title || s.id || s)}</span>` +
        `<span class="side-row__val">ver</span></div>`
      ).join("");
      box.querySelectorAll("[data-session]").forEach((el) =>
        el.addEventListener("click", () => {
          const sid = el.getAttribute("data-session");
          api().get("/chat/history?session=" + encodeURIComponent(sid) + "&limit=30").then((hist) => {
            const lines = (hist || []).map((h) =>
              `<div class="side-row"><span class="side-row__idx">${esc(h.role || "?")}</span>` +
              `<span style="overflow:hidden;text-overflow:ellipsis;white-space:normal">${esc(h.content || "")}</span></div>`
            ).join("");
            el.insertAdjacentHTML("afterend", '<div style="padding:4px 0 8px 18px">' + (lines || "vacío") + "</div>");
          }).catch(() => {});
        })
      );
    }).catch(() => { box.innerHTML = '<div class="empty">Sin datos</div>'; });
  }

  /* ============================================================
      ADMINISTRACIÓN (Fase D: CRUD usuarios, reglas gestionadas,
      procesos, escaneo YARA, salud profunda, auditoría de switch,
      export, logs filtrables)
      ============================================================ */
  function loadUsers() {
    api().get("/users").then(renderUsers).catch(() => {
      const t = $("users-table");
      if (t) t.innerHTML = '<thead><tr><th colspan="4">Acceso denegado (se requiere rol admin)</th></tr></thead>';
    });
  }

  function showUserErr(e) {
    const m = $("user-msg");
    if (m) { m.textContent = "Error: " + e.message; m.style.color = "var(--danger)"; }
  }
  function showRuleErr(e) {
    const m = $("rule-msg");
    if (m) { m.textContent = "Error: " + e.message; m.style.color = "var(--danger)"; }
  }

  function renderUsers(users) {
    const t = $("users-table");
    if (!t) return;
    if (!users || !users.length) { t.innerHTML = '<thead><tr><th colspan="4">Sin usuarios</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>" +
      users.map((u) => {
        const en = u.enabled;
        return `<tr data-uid="${esc(u.id)}">` +
          `<td>${esc(u.username)}</td>` +
          `<td><select class="form-select" data-role>${["operator", "admin"].map((r) => `<option ${r === u.role ? "selected" : ""}>${r}</option>`).join("")}</select></td>` +
          `<td>${en ? '<span class="tag tag--ok">activo</span>' : '<span class="tag tag--warn">inactivo</span>'}</td>` +
          `<td><button class="btn btn--small" data-toggle>${en ? "Desactivar" : "Activar"}</button> ` +
          `<button class="btn btn--small" data-del>Eliminar</button></td></tr>`;
      }).join("") + "</tbody>";
    t.querySelectorAll("tbody tr").forEach((tr) => {
      const id = tr.getAttribute("data-uid");
      const roleSel = tr.querySelector("[data-role]");
      roleSel.addEventListener("change", () => {
        api().put("/users", { id, role: roleSel.value }).then(loadUsers).catch(showUserErr);
      });
      tr.querySelector("[data-toggle]").addEventListener("click", () => {
        const cur = users.find((x) => x.id === id);
        api().put("/users", { id, enabled: !cur.enabled }).then(loadUsers).catch(showUserErr);
      });
      tr.querySelector("[data-del]").addEventListener("click", () => {
        api().del("/users?id=" + encodeURIComponent(id)).then(loadUsers).catch(showUserErr);
      });
    });
  }

  function refreshManagedRules() {
    api().get("/rules/managed").then(renderManagedRules).catch(showRuleErr);
  }

  function renderManagedRules(rules) {
    const t = $("rules-table2");
    if (!t) return;
    if (!rules || !rules.length) { t.innerHTML = '<thead><tr><th colspan="5">Sin reglas gestionadas</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>Nombre</th><th>Tipo</th><th>Origen</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>" +
      rules.map((r) => `<tr data-rid="${esc(r.id)}">` +
        `<td>${esc(r.name)}</td><td>${esc(r.type)}</td><td>${esc(r.origin || "api")}</td>` +
        `<td>${r.enabled ? '<span class="tag tag--ok">on</span>' : '<span class="tag tag--warn">off</span>'}</td>` +
        `<td><button class="btn btn--small" data-toggle>${r.enabled ? "Desactivar" : "Activar"}</button> ` +
        `<button class="btn btn--small" data-del>Eliminar</button></td></tr>`).join("") + "</tbody>";
    t.querySelectorAll("tbody tr").forEach((tr) => {
      const id = tr.getAttribute("data-rid");
      tr.querySelector("[data-toggle]").addEventListener("click", () => {
        const cur = rules.find((x) => x.id === id);
        api().put("/rules", { id, enabled: !cur.enabled }).then(refreshManagedRules).catch(showRuleErr);
      });
      tr.querySelector("[data-del]").addEventListener("click", () => {
        api().del("/rules?id=" + encodeURIComponent(id)).then(refreshManagedRules).catch(showRuleErr);
      });
    });
  }

  function renderProcesses(procs) {
    const t = $("proc-table");
    if (!t) return;
    const badge = $("proc-count");
    if (badge) badge.textContent = procs ? procs.length : "—";
    if (!procs || !procs.length) { t.innerHTML = '<thead><tr><th>Sin procesos</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>Host</th><th>Proceso</th><th>PID</th><th>Imagen</th><th>Avist.</th><th>Último</th></tr></thead><tbody>" +
      procs.map((p) =>
        `<tr><td>${esc(p.host || "")}</td><td>${esc(p.process_name || "")}</td><td class="num">${esc(p.process_pid || "")}</td>` +
        `<td style="max-width:220px;overflow:hidden;text-overflow:ellipsis">${esc(p.process_image || "")}</td>` +
        `<td class="num">${esc(p.sightings || 0)}</td><td>${esc(fmtTime(p.last_seen))}</td></tr>`
      ).join("") + "</tbody>";
  }

  function renderYaraNative(health, version) {
    const b = $("yara-native");
    if (!b) return;
    const nat = health && health.engine ? health.engine.yara_native : null;
    b.textContent = nat === true ? "nativo" : (nat === false ? "python puro" : "—");
  }

  function renderYaraResults(d) {
    const box = $("yara-results");
    if (!box) return;
    if (!d) { box.innerHTML = '<div class="empty">Sin resultado</div>'; return; }
    const hits = d.hits || [];
    let html = '<div style="margin:6px 0"><b>Escaneado:</b> ' + esc(d.scanned || "") +
      ' · <b>Coincidencias:</b> ' + hits.length + "</div>";
    if (hits.length) {
      html += '<table class="tbl"><thead><tr><th>Archivo</th><th>Regla</th><th>Strings</th></tr></thead><tbody>' +
        hits.map((h) =>
          `<tr><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis">${esc(h.file || "")}</td>` +
          `<td>${esc(h.rule || "")}</td><td>${esc((h.strings || []).join(", "))}</td></tr>`
        ).join("") + "</tbody></table>";
    } else {
      html += '<div class="empty">Sin coincidencias.</div>';
    }
    box.innerHTML = html;
  }

  function renderHealthDeep(health) {
    const box = $("health-deep");
    if (!box) return;
    if (!health) { box.innerHTML = '<div class="empty">Sin datos</div>'; return; }
    const db = health.database || {};
    const adb = health.audit_db || {};
    const eng = health.engine || {};
    const ag = health.agent || {};
    const gw = health.gateway || {};
    const dsk = health.disk || {};
    const rows = [
      ["Estado", health.status],
      ["DB eventos", db.path + " · " + (db.exists ? "existe" : "NO") + " · " + (db.writable ? "W" : "RO")],
      ["DB auditoría", adb.path + " · " + (adb.exists ? "existe" : "NO")],
      ["Reglas Sigma", eng.sigma_rules],
      ["Reglas YARA", eng.yara_rules],
      ["YARA nativo", String(eng.yara_native)],
      ["Agente", ag.mode],
      ["Gateway", gw.base_url],
      ["Disco libre", dsk.free_mb !== undefined ? dsk.free_mb + " MB" : "—"],
    ];
    box.innerHTML = '<dl class="kv">' + rows.map(([k, v]) =>
      `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") + "</dl>";
  }

  function renderSwitchAudit(rows) {
    const t = $("switch-audit-table");
    if (!t) return;
    if (!rows || !rows.length) { t.innerHTML = '<thead><tr><th>Sin cambios de switch</th></tr></thead>'; return; }
    t.innerHTML =
      "<thead><tr><th>Hora</th><th>Acción</th><th>Por</th><th>Estado</th><th>Detalle</th></tr></thead><tbody>" +
      rows.map((a) =>
        `<tr><td>${esc(fmtTime(a.time))}</td><td>${esc(a.action || "")}</td><td>${esc(a.approved_by || "")}</td>` +
        `<td><span class="tag tag--warn">${esc(a.status || "")}</span></td>` +
        `<td style="max-width:260px;overflow:hidden;text-overflow:ellipsis">${esc(a.detail || "")}</td></tr>`
      ).join("") + "</tbody>";
  }

  function loadAdmin() {
    Promise.all([
      api().get("/rules/managed").catch(() => []),
      api().get("/processes?limit=200").catch(() => []),
      api().get("/health/deep").catch(() => null),
      api().get("/switch/audit?limit=100").catch(() => []),
      api().get("/version").catch(() => null),
    ]).then(([managed, procs, health, swaudit, version]) => {
      renderManagedRules(managed);
      renderProcesses(procs);
      renderHealthDeep(health);
      renderSwitchAudit(swaaudit);
      renderYaraNative(health, version);
    }).catch(() => {});
    loadUsers();
  }

  function wireAdminForms() {
    const uf = $("user-form");
    if (uf && !uf.dataset.ready) {
      uf.dataset.ready = "1";
      uf.addEventListener("submit", (e) => {
        e.preventDefault();
        const f = e.target;
        api().post("/users", { username: f.username.value.trim(), password: f.password.value, role: f.role.value })
          .then(() => {
            f.reset();
            loadUsers();
            const m = $("user-msg");
            if (m) { m.textContent = "Usuario creado."; m.style.color = "var(--ok)"; }
          })
          .catch(showUserErr);
      });
    }
    const rf = $("rule-form");
    if (rf && !rf.dataset.ready) {
      rf.dataset.ready = "1";
      rf.addEventListener("submit", (e) => {
        e.preventDefault();
        const f = e.target;
        api().post("/rules", { name: f.name.value.trim(), type: f.type.value, content: f.content.value })
          .then(() => {
            f.reset();
            refreshManagedRules();
            const m = $("rule-msg");
            if (m) { m.textContent = "Regla creada."; m.style.color = "var(--ok)"; }
          })
          .catch(showRuleErr);
      });
    }
    const rr = $("rules-reload");
    if (rr && !rr.dataset.ready) {
      rr.dataset.ready = "1";
      rr.addEventListener("click", () => {
        api().post("/rules/reload", {}).then(loadAdmin).catch(showRuleErr);
      });
    }
    const yr = $("user-refresh");
    if (yr && !yr.dataset.ready) {
      yr.dataset.ready = "1";
      yr.addEventListener("click", () => loadUsers());
    }
    const yf = $("yara-form");
    if (yf && !yf.dataset.ready) {
      yf.dataset.ready = "1";
      yf.addEventListener("submit", (e) => {
        e.preventDefault();
        const f = e.target;
        const msg = $("yara-msg");
        if (msg) { msg.textContent = "Escaneando…"; msg.style.color = "var(--text-dim)"; }
        api().post("/scan/yara", { path: f.path.value.trim() })
          .then((d) => {
            renderYaraResults(d);
            if (msg) { msg.textContent = "Listo."; msg.style.color = "var(--ok)"; }
          })
          .catch((err) => { if (msg) { msg.textContent = "Error: " + err.message; msg.style.color = "var(--danger)"; } });
      });
    }
    const xf = $("export-form");
    if (xf && !xf.dataset.ready) {
      xf.dataset.ready = "1";
      xf.addEventListener("submit", (e) => {
        e.preventDefault();
        const kind = $("export-kind").value;
        const fmt = $("export-fmt").value;
        const url = API + "/export?kind=" + encodeURIComponent(kind) +
          "&fmt=" + encodeURIComponent(fmt) + "&limit=1000";
        const headers = token ? { Authorization: "Bearer " + token } : {};
        fetch(url, { headers }).then((r) => r.blob()).then((b) => {
          const a = document.createElement("a");
          a.href = URL.createObjectURL(b);
          a.download = kind + "." + fmt;
          a.click();
          URL.revokeObjectURL(a.href);
        }).catch(() => {});
      });
    }
    const lf = $("logs-form");
    if (lf && !lf.dataset.ready) {
      lf.dataset.ready = "1";
      lf.addEventListener("submit", (e) => {
        e.preventDefault();
        const f = e.target;
        const params = new URLSearchParams();
        if (f.level.value.trim()) params.set("level", f.level.value.trim());
        if (f.contains.value.trim()) params.set("contains", f.contains.value.trim());
        params.set("limit", "2000");
        api().get("/logs?" + params.toString()).then((lines) => {
          const out = $("logs-out");
          if (!out) return;
          const cnt = $("logs-count");
          if (cnt) cnt.textContent = lines ? lines.length : 0;
          out.textContent = lines && lines.length ? lines.join("\n") : "Sin resultados.";
        }).catch((err) => {
          const out = $("logs-out");
          if (out) out.textContent = "Error: " + err.message;
        });
      });
    }
  }

  /* ============================================================
      ROUTER DE VISTAS
      ============================================================ */
  const loaders = {
    resumen: loadResumen,
    seguridad: loadSeguridad,
    red: loadRed,
    hosts: loadHosts,
    auditoria: loadAuditoria,
    config: loadConfig,
    admin: loadAdmin,
  };

  NS.views = {
    load(name) { if (loaders[name]) loaders[name](); },
    onProposal,
    onProactive,
    init() {
      wireAdminForms();
      const sel = $("alert-sev-filter");
      if (sel) sel.addEventListener("change", () => {
        state.alertSev = sel.value;
        loadSeguridad();
      });
    },
  };
})(window);
