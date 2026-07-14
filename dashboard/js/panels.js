/* ============================================================
   ARGOS · PanelManager (colapsar / expandir)
   Sincroniza panel <-> resizer <-> rail
   ============================================================ */
(function (global) {
  "use strict";

  const NS = (global.ARGOS = global.ARGOS || {});

  class PanelManager {
    constructor() {
      this.panels = new Map(); // id -> { panel, resizer, rail, lastSize }
      this._build();
      this._wire();
    }

    _build() {
      document.querySelectorAll("[data-panel]").forEach((panel) => {
        const id = panel.id;
        const resizer = document.querySelector(`[data-resizer][data-target="${id}"]`);
        const rail = document.querySelector(`[data-rail="${id}"]`);
        this.panels.set(id, { panel, resizer, rail, lastSize: null });
      });
    }

    _wire() {
      // Botones de colapsar (en cabecera y en el rail)
      document.querySelectorAll("[data-collapse]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const rail = btn.closest("[data-rail]");
          const id = rail ? rail.getAttribute("data-rail") : btn.closest("[data-panel]").id;
          this.toggle(id);
        });
      });
    }

    toggle(id) {
      const entry = this.panels.get(id);
      if (!entry) return;
      if (entry.panel.classList.contains("is-collapsed")) this.expand(id);
      else this.collapse(id);
    }

    collapse(id) {
      const { panel, resizer, rail } = this.panels.get(id);
      // guarda tamaño actual para restaurar luego
      const box = panel.getBoundingClientRect();
      entry_lastSize(panel, box);
      panel.classList.add("is-collapsed");
      if (resizer) resizer.classList.add("is-hidden");
      if (rail) rail.classList.add("is-active");
    }

    expand(id) {
      const { panel, resizer, rail } = this.panels.get(id);
      panel.classList.remove("is-collapsed");
      if (resizer) resizer.classList.remove("is-hidden");
      if (rail) rail.classList.remove("is-active");
      const saved = panel.dataset.lastSize;
      if (saved) {
        if (panel.classList.contains("panel--console")) panel.style.height = saved;
        else panel.style.width = saved;
      }
    }
  }

  function entry_lastSize(panel, box) {
    const v = panel.classList.contains("panel--console")
      ? box.height + "px"
      : box.width + "px";
    panel.dataset.lastSize = v;
  }

  NS.initPanels = function () {
    return new PanelManager();
  };

  NS.PanelManager = PanelManager;
})(window);
