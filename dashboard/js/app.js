// app.js — Arranque de la aplicacion (router cliente + WebSocket + tema).
(function (global) {
  "use strict";

  const store = global.ArgosStore;
  const { el, toast } = global.UI;
  const Views = global.ArgosViews;

  function renderNav() {
    const nav = document.getElementById("nav");
    nav.innerHTML = "";
    Views.nav.forEach((key) => {
      const a = el("a", { href: "#" + key, class: store.get("view") === key ? "active" : "" }, [Views.titles[key]]);
      a.addEventListener("click", (e) => { e.preventDefault(); navigate(key); });
      nav.appendChild(a);
    });
  }

  function navigate(view) {
    store.set({ view });
    renderNav();
    document.getElementById("view-title").textContent = Views.titles[view] || "Panel";
    const root = document.getElementById("view");
    const fn = Views.list[view];
    if (fn) fn(root);
  }

  function applyTheme() {
    const t = store.get("theme");
    document.body.className = t === "light" ? "theme-light" : "";
    localStorage.setItem("argos-theme", t);
  }

  function init() {
    applyTheme();
    renderNav();
    document.getElementById("btn-theme").addEventListener("click", () => {
      store.set({ theme: store.get("theme") === "light" ? "dark" : "light" });
      applyTheme();
    });

    if (!global.ArgosApi.getToken()) {
      global.ArgosLogin.render(() => {
        navigate(store.get("view") || "monitor");
        const badge = document.getElementById("user-badge");
        const u = store.get("user");
        if (badge && u) badge.textContent = u.username + " (" + u.role + ")";
      });
      return;
    }

    global.ArgosWS.connect(
      (msg) => {
        if (msg.type === "proactive_alert" || msg.type === "alert") {
          toast("Nueva alerta: " + (msg.message || msg.alert && msg.alert.title || ""), "err");
          if (store.get("view") === "alerts") navigate("alerts");
        }
      },
      (connected) => {
        store.set({ connected });
        const badge = document.getElementById("conn-status");
        badge.textContent = connected ? "online" : "offline";
        badge.className = "badge " + (connected ? "online" : "offline");
      }
    );
    navigate(store.get("view") || "monitor");
    const badge = document.getElementById("user-badge");
    const u = store.get("user");
    if (badge && u) badge.textContent = u.username + " (" + u.role + ")";
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})(window);
