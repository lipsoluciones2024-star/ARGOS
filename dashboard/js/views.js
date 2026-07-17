// views.js — Vistas del dashboard cableadas a la API de ARGOS.
(function (global) {
  "use strict";

  const { el, card, metricCard, table, badge, toast, spinner } = global.UI;
  const Api = global.ArgosApi;

  async function renderMonitor(root) {
    root.innerHTML = "";
    const grid = el("div", { class: "grid" });
    root.appendChild(grid);
    grid.appendChild(metricCard("Salud", "...", "cargando"));
    grid.appendChild(metricCard("Eventos", "...", ""));
    grid.appendChild(metricCard("Alertas", "...", ""));
    grid.appendChild(metricCard("Plugings", "...", ""));
    try {
      const [health, metrics, obs, plugins] = await Promise.all([
        Api.health(), Api.metrics(), Api.observabilityMetrics().catch(() => ({})), Api.plugins(),
      ]);
      const counters = (obs && obs.metrics && obs.metrics.counters) || {};
      grid.innerHTML = "";
      grid.appendChild(metricCard("Estado", badge(health.status, "online"), "switch: " + health.switch));
      grid.appendChild(metricCard("Eventos", counters.argos_events_processed_total || 0, "procesados"));
      grid.appendChild(metricCard("Alertas activas", counters.argos_active_alerts || 0, "gauge"));
      grid.appendChild(metricCard("Plugins", (plugins || []).length, "instalados"));
      const charts = el("div", { class: "card", style: "grid-column:1/-1" }, [
        el("h3", {}, ["Latencia de deteccion (s)"]),
        el("div", { class: "chart-box" }, [el("canvas", { id: "chart-latency" })]),
      ]);
      grid.appendChild(charts);
      drawChart("chart-latency", [counters.argos_detection_latency_seconds || 0]);
    } catch (e) {
      toast("Error monitor: " + e.message, "err");
    }
  }

  function drawChart(id, dataPoints) {
    const canvas = document.getElementById(id);
    if (!canvas || !global.Chart) return;
    new global.Chart(canvas, {
      type: "line",
      data: { labels: dataPoints.map((_, i) => i), datasets: [{ data: dataPoints, borderColor: "#2f81f7", fill: false }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
    });
  }

  async function renderAlerts(root) {
    root.innerHTML = "";
    root.appendChild(el("div", { class: "panel-actions" }, [el("h3", { style: "margin:0" }, ["Alertas activas"])]));
    const wrap = el("div", { class: "card" }, [spinner()]);
    root.appendChild(wrap);
    try {
      const alerts = await Api.alerts(100);
      wrap.innerHTML = "";
      if (!alerts.length) { wrap.appendChild(el("div", { class: "empty" }, ["Sin alertas"])); return; }
      wrap.appendChild(table(
        ["Severidad", "Titulo", "Host", "Fuente", "Accion"],
        alerts.map((a) => [
          badge(a.severity, "sev-" + a.severity),
          a.title,
          a.host,
          a.source,
          el("button", { class: "btn ghost", onclick: async () => {
            try { await Api.ackAlert(a.id); toast("Alerta reconocida", "ok"); renderAlerts(root); }
            catch (e) { toast(e.message, "err"); }
          } }, ["Ack"]),
        ])
      ));
    } catch (e) { toast("Error alertas: " + e.message, "err"); }
  }

  async function renderPlugins(root) {
    root.innerHTML = "";
    root.appendChild(el("div", { class: "panel-actions" }, [el("h3", { style: "margin:0" }, ["Plugins / Marketplace"])]));
    const wrap = el("div", { class: "card" }, [spinner()]);
    root.appendChild(wrap);
    try {
      const plugins = await Api.plugins();
      wrap.innerHTML = "";
      if (!plugins.length) { wrap.appendChild(el("div", { class: "empty" }, ["Sin plugins"])); return; }
      wrap.appendChild(table(
        ["Nombre", "Version", "Categoria", "Estado", "Acciones"],
        plugins.map((p) => [
          p.name, p.version, p.category,
          badge(p.enabled ? "activo" : "inactivo", p.enabled ? "online" : "offline"),
          el("div", { class: "row", style: "gap:6px" }, [
            p.enabled
              ? el("button", { class: "btn ghost", onclick: () => act("disable", p.name, root) }, ["Desactivar"])
              : el("button", { class: "btn", onclick: () => act("enable", p.name, root) }, ["Activar"]),
            el("button", { class: "btn danger", onclick: () => act("uninstall", p.name, root) }, ["Quitar"]),
          ]),
        ])
      ));
    } catch (e) { toast("Error plugins: " + e.message, "err"); }
  }

  async function act(action, name, root) {
    try {
      if (action === "enable") await Api.enablePlugin(name);
      else if (action === "disable") await Api.disablePlugin(name);
      else if (action === "uninstall") await Api.uninstallPlugin(name);
      toast("Plugin " + action + ": " + name, "ok");
      renderPlugins(root);
    } catch (e) { toast(e.message, "err"); }
  }

  async function renderAnalytics(root) {
    root.innerHTML = "";
    const grid = el("div", { class: "grid" });
    root.appendChild(grid);
    grid.appendChild(card("Tool Gateway", el("div", { id: "gw-metrics", class: "muted" }, ["cargando..."])));
    grid.appendChild(card("MCP", el("div", { id: "mcp-metrics", class: "muted" }, ["cargando..."])));
    try {
      const [gw, mcp] = await Promise.all([Api.gatewayMetrics(), Api.mcp({ jsonrpc: "2.0", id: 1, method: "tools/list" })]);
      const g = document.getElementById("gw-metrics");
      const tools = (gw && gw.tools) || {};
      g.innerHTML = "<div class='kv'>" + Object.keys(tools).map((k) =>
        "<dt>" + k + "</dt><dd>" + (tools[k].calls || 0) + " llamadas</dd>").join("") + "</div>";
      const m = document.getElementById("mcp-metrics");
      const list = (mcp && mcp.result && mcp.result.tools) || [];
      m.innerHTML = "<div class='kv'>" + list.map((t) => "<dt>" + t.name + "</dt><dd>" + (t.description || "").slice(0, 60) + "</dd>").join("") + "</div>";
    } catch (e) { toast("Error analytics: " + e.message, "err"); }
  }

  async function renderAdmin(root) {
    root.innerHTML = "";
    const grid = el("div", { class: "grid" });
    root.appendChild(grid);
    const prefsCard = card("Preferencias de UI", el("div", { id: "ui-prefs" }, [spinner()]));
    grid.appendChild(prefsCard);
    const usersCard = card("Usuarios", el("div", { id: "ui-users" }, [spinner()]));
    grid.appendChild(usersCard);
    try {
      const prefs = await Api.uiPrefs().catch(() => ({}));
      const pf = document.getElementById("ui-prefs");
      pf.innerHTML = "";
      const density = el("select", {}, [el("option", { value: "comfortable" }, ["Confort"]), el("option", { value: "compact" }, ["Compacto"])]);
      density.value = (prefs && prefs.density) || "comfortable";
      const save = el("button", { class: "btn", style: "margin-top:10px", onclick: async () => {
        try { await Api.saveUiPrefs({ density: density.value }); toast("Preferencias guardadas", "ok"); }
        catch (e) { toast(e.message, "err"); }
      } }, ["Guardar layout"]);
      pf.appendChild(el("div", { class: "row" }, [el("label", {}, ["Densidad"]), density]));
      pf.appendChild(save);
      const users = await Api.users().catch(() => []);
      const u = document.getElementById("ui-users");
      u.innerHTML = "";
      if (!users.length) u.appendChild(el("div", { class: "muted" }, ["No disponible"]));
      else u.appendChild(table(["Usuario", "Rol"], users.map((x) => [x.username, badge(x.role, x.role === "admin" ? "online" : "offline")])));
    } catch (e) { toast("Error admin: " + e.message, "err"); }
  }

  const VIEWS = {
    monitor: renderMonitor,
    alerts: renderAlerts,
    plugins: renderPlugins,
    analytics: renderAnalytics,
    admin: renderAdmin,
  };

  global.ArgosViews = {
    list: VIEWS,
    titles: { monitor: "Monitoreo", alerts: "Alertas", plugins: "Plugins", analytics: "Analitica", admin: "Administracion" },
    nav: ["monitor", "alerts", "plugins", "analytics", "admin"],
  };
})(window);
