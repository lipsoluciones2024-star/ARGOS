// api.js — Cliente de la API REST de ARGOS.
(function (global) {
  "use strict";

  const TOKEN_KEY = "argos-token";

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch("/api/v1" + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(path + " -> " + res.status + " " + text.slice(0, 200));
    }
    if (res.status === 204) return null;
    return res.json();
  }

  const Api = {
    setToken: (t) => localStorage.setItem(TOKEN_KEY, t),
    getToken: () => localStorage.getItem(TOKEN_KEY),
    login: (user, pass) =>
      fetch("/api/v1/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user, password: pass }),
      }).then((r) => r.json()),
    health: () => request("GET", "/health"),
    metrics: () => request("GET", "/metrics"),
    observabilityMetrics: () => request("GET", "/observability/metrics"),
    events: (limit = 100) => request("GET", "/events?limit=" + limit),
    alerts: (limit = 50) => request("GET", "/alerts?limit=" + limit),
    ackAlert: (id) => request("POST", "/alerts/" + id + "/ack", { by: "dashboard" }),
    plugins: () => request("GET", "/plugins"),
    installPlugin: (name) => request("POST", "/plugins/install", { name }),
    enablePlugin: (name) => request("POST", "/plugins/" + name + "/enable"),
    disablePlugin: (name) => request("POST", "/plugins/" + name + "/disable"),
    uninstallPlugin: (name) => request("POST", "/plugins/uninstall", { name }),
    gatewayMetrics: () => request("GET", "/gateway/metrics"),
    mcp: (payload) => request("POST", "/mcp", payload),
    version: () => request("GET", "/version"),
    uiPrefs: () => request("GET", "/ui/preferences"),
    saveUiPrefs: (prefs) => request("PUT", "/ui/preferences", prefs),
    users: () => request("GET", "/users"),
  };

  global.ArgosApi = Api;
})(window);
