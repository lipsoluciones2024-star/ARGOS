// store.js — Estado global con pub/sub (patron Observer).
(function (global) {
  "use strict";

  function createStore(initial) {
    let state = initial || {};
    const listeners = new Set();
    return {
      get(key) { return key === undefined ? state : state[key]; },
      set(patch) {
        state = Object.assign({}, state, patch);
        listeners.forEach((fn) => fn(state));
      },
      subscribe(fn) {
        listeners.add(fn);
        return () => listeners.delete(fn);
      },
    };
  }

  global.ArgosStore = createStore({
    view: "monitor",
    metrics: {},
    alerts: [],
    plugins: [],
    connected: false,
    theme: localStorage.getItem("argos-theme") || "dark",
    user: null,
  });
})(window);
