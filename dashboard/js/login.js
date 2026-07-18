// login.js — Pantalla de autenticación (login por usuario/clave).
(function (global) {
  "use strict";

  const { el, toast } = global.UI;

  function renderLogin(onSuccess) {
    const Api = global.ArgosApi;
    const root = document.getElementById("view");
    const nav = document.getElementById("nav");
    const title = document.getElementById("view-title");
    const topbar = document.getElementById("topbar");
    if (nav) nav.style.display = "none";
    if (topbar) topbar.style.display = "none";

    const userInput = el("input", { type: "text", id: "login-user", placeholder: "usuario", autocomplete: "username" });
    const passInput = el("input", { type: "password", id: "login-pass", placeholder: "contraseña", autocomplete: "current-password" });
    const errBox = el("div", { class: "login-error", id: "login-error" });
    const submit = el("button", { class: "btn primary", type: "submit" }, ["Ingresar"]);

    const form = el("form", { class: "login-form", onsubmit: async (e) => {
      e.preventDefault();
      errBox.textContent = "";
      submit.disabled = true;
      submit.textContent = "Validando...";
      try {
        const res = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: userInput.value.trim(), password: passInput.value }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          errBox.textContent = data.error || "Credenciales inválidas";
          submit.disabled = false;
          submit.textContent = "Ingresar";
          return;
        }
        Api.setToken(data.token);
        global.ArgosStore.set({ user: { username: data.username, role: data.role } });
        if (nav) nav.style.display = "";
        if (topbar) topbar.style.display = "";
        onSuccess(data);
      } catch (err) {
        errBox.textContent = "No se pudo conectar con el servidor";
        submit.disabled = false;
        submit.textContent = "Ingresar";
      }
    } }, [
      el("h2", {}, ["ARGOS Enterprise"]),
      el("p", { class: "muted" }, ["Inicie sesión para continuar"]),
      el("label", {}, ["Usuario"]), userInput,
      el("label", {}, ["Contraseña"]), passInput,
      errBox, submit,
    ]);

    const wrap = el("div", { class: "login-wrap" }, [form]);
    root.innerHTML = "";
    root.appendChild(wrap);
    if (title) title.textContent = "Ingreso";
    setTimeout(() => userInput.focus(), 0);
  }

  global.ArgosLogin = { render: renderLogin };
})(window);
