/* ============================================================
   ARGOS · App (cliente vivo del backend: WS + REST + auth + voz)
   ============================================================ */
(function (global) {
  "use strict";

  const NS = (global.ARGOS = global.ARGOS || {});
  const $ = (id) => document.getElementById(id);

  const API = "/api/v1";
  const host = location.host;
  const proto = location.protocol === "https:" ? "wss" : "ws";

  let ws = null;
  let wsReady = false;
  let reconnectTimer = null;
  let session = null;
  let switchLevel = "OBSERVE";
  let streamBubble = null;
  let speaking = false;
  let token = "";
  let authRequired = false;
  let currentView = "resumen";
  let pollTimer = null;

  /* ---------- helpers compartidos ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }
  NS.esc = esc;

  /* ---------- fetch centralizado con auth ---------- */
  function coreFetch(path, opts) {
    opts = opts || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (token) headers["Authorization"] = "Bearer " + token;
    return fetch(API + path, Object.assign({}, opts, { headers })).then((r) => {
      if (r.status === 401) { onAuthRequired(); throw new Error("unauthorized"); }
      if (!r.ok) throw new Error("HTTP " + r.status + " " + path);
      const ct = r.headers.get("content-type") || "";
      if (ct.indexOf("application/json") < 0) return null;
      return r.json().catch(() => null);
    });
  }
  NS.api = {
    get: (p, o) => coreFetch(p, Object.assign({ method: "GET" }, o)),
    post: (p, b) => coreFetch(p, { method: "POST", body: JSON.stringify(b == null ? {} : b) }),
    put: (p, b) => coreFetch(p, { method: "PUT", body: JSON.stringify(b == null ? {} : b) }),
    del: (p, o) => coreFetch(p, Object.assign({ method: "DELETE" }, o)),
  };

  /* ============================================================
     ARRANQUE
     ============================================================ */
  document.addEventListener("DOMContentLoaded", function () {
    NS.initSplitters();
    NS.initPanels();
    NS.initCharts();
    if (NS.views && NS.views.init) NS.views.init();

    initNav();
    initChat();
    initConsole();
    initClock();
    initVoice();
    initLogin();
    initLogout();

    try { token = sessionStorage.getItem("argos_token") || ""; } catch (_) { token = ""; }
    updateAuthBadge();

    connectWS();
    boot();
  });

  function boot() {
    // Sondeo para detectar si el servidor exige token.
    NS.api.get("/switch")
      .then((d) => { if (d && d.level) setSwitchLevel(d.level); startApp(); })
      .catch(() => { if (!authRequired) startApp(); });
  }

  function startApp() {
    showView(currentView);
    startPolling();
  }

  /* ============================================================
     AUTH / LOGIN
     ============================================================ */
  function initLogin() {
    const form = $("login-form");
    if (!form) return;
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const tok = $("login-token").value.trim();
      if (!tok) { $("login-error").textContent = "Ingresa un token."; return; }
      submitLogin(tok);
    });
  }

  function initLogout() {
    const b = $("logout-btn");
    if (!b) return;
    b.addEventListener("click", () => {
      token = "";
      try { sessionStorage.removeItem("argos_token"); } catch (_) {}
      authRequired = false;
      updateAuthBadge();
      if (ws) { ws.__manualClose = true; ws.close(); }
      connectWS();
      log("info", "Sesión cerrada (token limpiado).");
    });
  }

  function showLogin(msg) {
    const ov = $("login-overlay");
    if (!ov) return;
    ov.hidden = false;
    const err = $("login-error");
    if (err) err.textContent = msg || "";
    const t = $("login-token");
    if (t) t.focus();
  }
  function hideLogin() { const ov = $("login-overlay"); if (ov) ov.hidden = true; }

  function submitLogin(tok) {
    token = tok;
    try { sessionStorage.setItem("argos_token", token); } catch (_) {}
    authRequired = false;
    const err = $("login-error");
    if (err) err.textContent = "";
    hideLogin();
    updateAuthBadge();
    if (ws) { ws.__manualClose = true; ws.close(); }
    connectWS();
    startApp();
  }

  function onAuthRequired() {
    if (authRequired) return;
    authRequired = true;
    stopPolling();
    showLogin("Se requiere autenticación. Ingresa tu token de API (Bearer).");
  }

  function updateAuthBadge() {
    const b = $("sb-auth");
    if (!b) return;
    b.textContent = authRequired ? "Auth: requerido" : (token ? "Auth: token" : "Auth: abierto");
  }

  /* ============================================================
     WEBSOCKET
     ============================================================ */
  function connectWS() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    const url = proto + "://" + host + "/ws" + (token ? "?token=" + encodeURIComponent(token) : "");
    ws = new WebSocket(url);
    ws.onopen = () => {
      wsReady = true;
      setConn(true);
      if (!session) newSession();
    };
    ws.onclose = (ev) => {
      wsReady = false;
      setConn(false);
      if (ws.__manualClose) { ws.__manualClose = false; return; }
      if (ev.code === 1008) { onAuthRequired(); return; }   // token inválido / requerido
      scheduleReconnect();
    };
    ws.onerror = () => { wsReady = false; setConn(false); };
    ws.onmessage = (ev) => {
      try { handleMessage(JSON.parse(ev.data)); } catch (e) { log("err", "Mensaje WS inválido"); }
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => { reconnectTimer = null; connectWS(); }, 1500);
  }

  function sendWS(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify(obj)); return true; }
    log("warn", "WS no disponible; reintentando conexión…");
    return false;
  }

  function newSession() {
    NS.api.post("/chat/session", { title: "chat" })
      .then((d) => { if (d) session = d.session; })
      .catch(() => {});
  }

  /* ---------- manejo de mensajes WS ---------- */
  function handleMessage(m) {
    switch (m.type) {
      case "chat":
        if (m.role === "assistant") { finalizeStream(); addMsg("bot", m.content || ""); speak(m.content || ""); }
        break;
      case "chat_stream":
      case "begin":
      case "token":
      case "tool":
      case "done":
        applyStream(m);
        break;
      case "proposal":
        chatUpsertProposal(m);
        if (NS.views && NS.views.onProposal) NS.views.onProposal(m);
        break;
      case "proactive_alert":
        addMsg("system", m.message || "Alerta");
        log("warn", m.message || "Alerta");
        if (NS.views && NS.views.onProactive) NS.views.onProactive(m);
        break;
      case "autonomy_event":
        log("info", m.message || "Evento de autonomía");
        break;
      case "switch":
        setSwitchLevel(m.level);
        break;
      case "error":
        log("err", m.content || "Error");
        break;
      default:
        break;
    }
  }

  function applyStream(m) {
    const st = m.stream_type || m.type;
    if (st === "begin") {
      streamBubble = addMsg("bot", "", true);
    } else if (st === "token") {
      if (streamBubble) { streamBubble.textContent += m.content || ""; scrollChat(); }
    } else if (st === "done") {
      finalizeStream();
      if (m.content) speak(m.content);
    }
    // "tool" se ignora en la UI (paso interno del agente)
  }

  function finalizeStream() { streamBubble = null; }

  /* ============================================================
     ROUTER DE VISTAS
     ============================================================ */
  const VIEW_TITLES = {
    resumen: "Resumen", seguridad: "Seguridad", red: "Red",
    hosts: "Hosts", auditoria: "Auditoría", config: "Configuración",
    admin: "Administración",
  };

  function initNav() {
    document.querySelectorAll("[data-nav]").forEach((b) =>
      b.addEventListener("click", () => showView(b.getAttribute("data-nav")))
    );
  }

  function showView(name) {
    if (!name || !document.querySelector('.view[data-view="' + name + '"]')) name = "resumen";
    currentView = name;
    document.querySelectorAll("[data-nav]").forEach((b) =>
      b.classList.toggle("is-active", b.getAttribute("data-nav") === name)
    );
    document.querySelectorAll(".view").forEach((v) =>
      v.classList.toggle("is-active", v.getAttribute("data-view") === name)
    );
    const t = $("view-title");
    if (t) t.textContent = VIEW_TITLES[name] || name;
    if (NS.views && NS.views.load) NS.views.load(name);
  }

  /* ============================================================
     SWITCH DE AUTONOMÍA
     ============================================================ */
  function initSwitch() {
    const wrap = document.createElement("div");
    wrap.className = "switch-bar";
    wrap.id = "switch-bar";
    wrap.innerHTML =
      '<span class="switch-bar__label">Autonomía:</span>' +
      ["OBSERVE", "SUGGEST", "SEMI-AUTO", "FULL_AUTO"]
        .map((l) => `<button class="switch-bar__btn" data-level="${l}">${l}</button>`)
        .join("");
    const chat = $("chat-messages");
    chat.parentNode.insertBefore(wrap, chat);
    wrap.querySelectorAll(".switch-bar__btn").forEach((b) =>
      b.addEventListener("click", () => NS.setSwitch(b.getAttribute("data-level")))
    );
  }

  NS.setSwitch = function (level) {
    NS.api.post("/switch", { level })
      .then((d) => { if (d && d.level) setSwitchLevel(d.level); log("ok", "Autonomía → " + (d ? d.level : level)); })
      .catch((err) => {
        if (err.message !== "unauthorized") log("warn", "No se pudo cambiar autonomía (¿rol admin?): " + err.message);
      });
  };

  function setSwitchLevel(level) {
    switchLevel = level;
    document.querySelectorAll("[data-level]").forEach((b) =>
      b.classList.toggle("is-active", b.getAttribute("data-level") === level)
    );
  }

  /* ============================================================
     CHAT
     ============================================================ */
  function initChat() {
    initSwitch();
    const form = $("chat-form");
    const field = $("chat-field");
    addMsg("bot", "Hola. Soy ARGOS. Pregúntame o dame una orden; en SUGGEST solo propongo, no actúo sin tu sí.");

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = field.value.trim();
      if (!text) return;
      addMsg("user", text);
      field.value = "";
      finalizeStream();
      sendWS({ type: "chat_stream", message: text, session: session });
    });
  }

  function addMsg(role, text, streaming) {
    const box = $("chat-messages");
    const el = document.createElement("div");
    el.className = "msg msg--" + role;
    const roleName = role === "bot" ? "ARGOS" : role === "system" ? "SISTEMA" : "Tú";
    const r = document.createElement("div");
    r.className = "msg__role";
    r.textContent = roleName;
    const body = document.createElement("div");
    body.className = "msg__text";
    body.textContent = text || "";
    el.appendChild(r);
    el.appendChild(body);
    box.appendChild(el);
    scrollChat();
    return body;
  }

  function scrollChat() {
    const box = $("chat-messages");
    if (box) box.scrollTop = box.scrollHeight;
  }

  /* ---------- propuestas en el chat (human-in-the-loop) ---------- */
  function chatUpsertProposal(p) {
    const box = $("chat-messages");
    let el = box.querySelector('.msg--proposal[data-pid="' + (p.id || "") + '"]');
    if (!el) {
      el = document.createElement("div");
      el.className = "msg msg--proposal";
      el.dataset.pid = p.id || "";
      box.appendChild(el);
      scrollChat();
    }
    el.innerHTML = "";
    const head = document.createElement("div");
    head.className = "msg__role";
    head.textContent = "PROPUESTA (" + (p.status || "pending") + ")";
    const body = document.createElement("div");
    body.className = "msg__text";
    body.textContent = "Acción: " + (p.action || "?") + "  →  " + (p.target || "");
    const actions = document.createElement("div");
    actions.className = "proposal__actions";
    const confirm = document.createElement("button");
    confirm.className = "proposal__btn proposal__btn--ok";
    confirm.textContent = "Confirmar";
    confirm.disabled = (p.status || "pending") !== "pending";
    confirm.addEventListener("click", () => { NS.confirmProposal(p.id); confirm.disabled = true; });
    const dismiss = document.createElement("button");
    dismiss.className = "proposal__btn";
    dismiss.textContent = "Descartar";
    dismiss.addEventListener("click", () => el.remove());
    actions.appendChild(confirm);
    actions.appendChild(dismiss);
    el.appendChild(head);
    el.appendChild(body);
    el.appendChild(actions);
    if (p.result) {
      const r = document.createElement("div");
      r.className = "msg__text msg__text--muted";
      r.textContent = "Resultado: " + JSON.stringify(p.result);
      el.appendChild(r);
    }
  }

  NS.confirmProposal = function (id) {
    if (!sendWS({ type: "confirm", id: id, approved_by: "operator" }))
      log("warn", "WS no disponible para confirmar.");
  };

  /* ============================================================
     CONSOLA
     ============================================================ */
  const LOG_LEVELS = ["info", "ok", "warn", "err"];
  function log(level, text) {
    const box = $("console-body");
    if (!box) return;
    const line = document.createElement("div");
    line.className = "log-line log-line--" + level;
    const ts = new Date().toLocaleTimeString("es-ES", { hour12: false });
    const t = document.createElement("span"); t.className = "log-line__ts"; t.textContent = ts;
    const l = document.createElement("span"); l.className = "log-line__lvl"; l.textContent = level.toUpperCase();
    const m = document.createElement("span"); m.textContent = text;
    line.appendChild(t); line.appendChild(l); line.appendChild(m);
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
  }
  NS.log = log;

  function initConsole() {
    NS.api.get("/logs?tail=60")
      .then((lines) => { if (lines) lines.forEach((ln) => log("info", ln)); })
      .catch(() => {});
  }

  /* ============================================================
     POLLING (datos en vivo + vista actual)
     ============================================================ */
  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(() => {
      refreshAll();
      if (!authRequired && NS.views && currentView) NS.views.load(currentView);
    }, 6000);
    refreshAll();
  }
  function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  function refreshAll() {
    if (authRequired) return;
    Promise.all([
      NS.api.get("/stats").catch(() => null),
      NS.api.get("/hosts").catch(() => []),
      NS.api.get("/alerts?limit=50").catch(() => []),
      NS.api.get("/events?limit=200").catch(() => []),
    ]).then(([stats, hosts, alerts, events]) => {
      if (stats) {
        setSwitchLevel(stats.switch);
        const c = $("throughput-val");
        if (c) c.textContent = String(stats.total_events);
        NS.renderThroughput(stats.series);
      }
      if ($("sb-hosts")) $("sb-hosts").textContent = "Hosts: " + (hosts ? hosts.length : 0);
      if ($("sb-alerts")) $("sb-alerts").textContent = "Alertas: " + (alerts ? alerts.length : 0);
      const chip = $("chip-alerts");
      if (chip) {
        if (alerts && alerts.length) { chip.style.display = ""; chip.textContent = alerts.length + " alerta(s)"; }
        else chip.style.display = "none";
      }
      renderSide(hosts, events, alerts);
    }).catch(() => {});
  }

  /* ---------- panel izquierdo (datos reales) ---------- */
  function block(title, rowsHtml) {
    return '<div class="side-block"><div class="side-block__title">' + esc(title) + "</div>" + rowsHtml + "</div>";
  }
  function emptyRow() { return '<div class="side-empty">Sin datos</div>'; }
  function rows(arr) {
    if (!arr.length) return emptyRow();
    const max = Math.max.apply(null, arr.map((r) => r[1]).concat([1]));
    return arr.map((r, i) =>
      '<div class="side-row"><span class="side-row__idx">' + (i + 1) + "</span>" +
      '<span style="overflow:hidden;text-overflow:ellipsis">' + esc(r[0]) + "</span>" +
      '<span class="side-row__val">' + esc(r[1]) + "</span>" +
      '<span class="side-row__bar"><i style="width:' + Math.round((r[1] / max) * 100) + '%"></i></span></div>'
    ).join("");
  }

  function renderSide(hosts, events, alerts) {
    const box = $("left-body");
    if (!box) return;
    const topHosts = (hosts || []).slice().sort((a, b) => b.events - a.events).slice(0, 6)
      .map((h) => [h.host, h.events]);
    const byCat = {};
    (events || []).forEach((e) => { const c = e.category || "unknown"; byCat[c] = (byCat[c] || 0) + 1; });
    const catArr = Object.entries(byCat).sort((a, b) => b[1] - a[1]).slice(0, 6);
    const bySev = {};
    (alerts || []).forEach((a) => { const s = a.severity || "unknown"; bySev[s] = (bySev[s] || 0) + 1; });
    const sevArr = Object.entries(bySev).sort((a, b) => b[1] - a[1]);
    box.innerHTML =
      block("Top hosts", rows(topHosts)) +
      block("Eventos por categoría", rows(catArr)) +
      block("Alertas por severidad", rows(sevArr));
  }

  /* ============================================================
     RELOJ / CONEXIÓN
     ============================================================ */
  function initClock() {
    const el = $("status-clock");
    const tick = () => (el.textContent = new Date().toLocaleTimeString("es-ES", { hour12: false }));
    tick();
    setInterval(tick, 1000);
  }

  function setConn(ok) {
    const c = $("conn-status");
    if (!c) return;
    c.textContent = ok ? "● Conectado" : "● Desconectado";
    c.className = "status-bar__item " + (ok ? "status-bar__item--ok" : "status-bar__item--warn");
  }

  /* ============================================================
     VOZ (Jarvis)
     ============================================================ */
  function initVoice() {
    NS.voice = { supported: false, listening: false, recognizer: null };
    const SR = global.SpeechRecognition || global.webkitSpeechRecognition;
    const btn = $("chat-voice");
    if (!SR) {
      if (btn) { btn.disabled = true; btn.title = "Reconocimiento de voz no soportado (usa Chrome)"; }
      log("warn", "Web Speech API no disponible; usa Chrome para voz.");
      return;
    }
    const rec = new SR();
    rec.lang = "es-ES";
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript.trim();
      if (text) {
        addMsg("user", text);
        finalizeStream();
        sendWS({ type: "chat_stream", message: text, session: session });
      }
    };
    rec.onerror = () => stopListen();
    rec.onend = () => stopListen();
    NS.voice.recognizer = rec;
    NS.voice.supported = true;

    function startListen() {
      if (!NS.voice.supported || NS.voice.listening) return;
      try { rec.start(); NS.voice.listening = true; if (btn) btn.classList.add("is-active"); log("info", "Escuchando…"); } catch (_) {}
    }
    function stopListen() {
      NS.voice.listening = false;
      if (btn) btn.classList.remove("is-active");
    }
    if (btn) {
      btn.addEventListener("mousedown", startListen);
      btn.addEventListener("touchstart", (e) => { e.preventDefault(); startListen(); });
      btn.addEventListener("mouseup", () => rec.stop());
      btn.addEventListener("mouseleave", () => { if (NS.voice.listening) rec.stop(); });
      btn.addEventListener("touchend", () => rec.stop());
    }
    NS.voice.start = startListen;
    NS.voice.stop = stopListen;
  }

  function speak(text) {
    if (!text || !global.speechSynthesis) return;
    try {
      global.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "es-ES";
      u.onstart = () => (speaking = true);
      u.onend = () => (speaking = false);
      global.speechSynthesis.speak(u);
    } catch (_) {}
  }
})(window);
