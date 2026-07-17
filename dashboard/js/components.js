// components.js — Sistema de componentes reutilizables (sin frameworks).
(function (global) {
  "use strict";

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach((k) => {
      if (k === "class") node.className = attrs[k];
      else if (k === "html") node.innerHTML = attrs[k];
      else if (k.startsWith("on") && typeof attrs[k] === "function")
        node.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach((c) => node.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
    return node;
  }

  function card(title, body) {
    const c = el("div", { class: "card" }, [el("h3", {}, [title])]);
    if (body) c.appendChild(typeof body === "string" ? el("div", { html: body }) : body);
    return c;
  }

  function metricCard(title, value, sub) {
    const v = el("div", { class: "metric" }, [String(value)]);
    const c = card(title, el("div", {}, [v, sub ? el("div", { class: "muted" }, [sub]) : null]));
    return c;
  }

  function table(headers, rows) {
    const thead = el("thead", {}, [el("tr", {}, headers.map((h) => el("th", {}, [h])))]);
    const tbody = el("tbody", {}, rows.map((r) => el("tr", {}, r.map((cell) => el("td", {}, [cell])))));
    return el("table", {}, [thead, tbody]);
  }

  function badge(text, cls) { return el("span", { class: "badge " + (cls || "") }, [text]); }

  function toast(msg, kind) {
    let t = document.querySelector(".toast");
    if (!t) { t = el("div", { class: "toast" }); document.body.appendChild(t); }
    t.className = "toast show " + (kind || "");
    t.textContent = msg;
    setTimeout(() => t.classList.remove("show"), 2600);
  }

  function spinner() { return el("div", { class: "spinner" }); }

  function modal(title, content, onConfirm) {
    const backdrop = el("div", { class: "modal-backdrop open" });
    const close = () => backdrop.remove();
    const m = el("div", { class: "modal" }, [
      el("h3", {}, [title]),
      content,
      el("div", { class: "panel-actions", style: "justify-content:flex-end;margin-top:16px" }, [
        el("button", { class: "btn ghost", onclick: close }, ["Cancelar"]),
        onConfirm ? el("button", { class: "btn", onclick: () => { onConfirm(); close(); } }, ["Aceptar"]) : null,
      ]),
    ]);
    backdrop.appendChild(m);
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(); });
    document.body.appendChild(backdrop);
  }

  global.UI = { el, card, metricCard, table, badge, toast, spinner, modal };
})(window);
