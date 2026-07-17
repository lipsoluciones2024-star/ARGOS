// websocket.js — Cliente WebSocket con reconexion automatica.
(function (global) {
  "use strict";

  function connect(onMessage, onStatus) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = proto + "://" + location.host + "/ws";
    let ws, retry = 0, closed = false;

    function open() {
      ws = new WebSocket(url);
      ws.onopen = () => { retry = 0; onStatus(true); };
      ws.onclose = () => { onStatus(false); if (!closed) setTimeout(open, Math.min(5000, 500 * ++retry)); };
      ws.onerror = () => ws.close();
      ws.onmessage = (ev) => {
        try { onMessage(JSON.parse(ev.data)); } catch (e) { /* ignore */ }
      };
    }
    open();
    return {
      close() { closed = true; ws && ws.close(); },
      send: (data) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(data)); },
    };
  }

  global.ArgosWS = { connect };
})(window);
