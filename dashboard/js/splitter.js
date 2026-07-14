/* ============================================================
   ARGOS · Splitter (redimensionado por arrastre)
   Vanilla JS · sin dependencias
   ============================================================ */
(function (global) {
  "use strict";

  const NS = (global.ARGOS = global.ARGOS || {});

  const MIN_DEFAULT = 120;
  const MAX_DEFAULT = 800;

  class Splitter {
    /**
     * @param {HTMLElement} handle  elemento divisor (resizer)
     * @param {Object} opts
     *   dir: 'left' | 'right' | 'bottom'
     *   target: id del panel redimensionado
     *   min / max en px
     */
    constructor(handle, opts) {
      this.handle = handle;
      this.target = document.getElementById(opts.target);
      this.dir = opts.dir;
      this.min = opts.min ?? MIN_DEFAULT;
      this.max = opts.max ?? MAX_DEFAULT;

      this.dragging = false;
      this.start = 0;
      this.startSize = 0;

      this._onDown = this._onDown.bind(this);
      this._onMove = this._onMove.bind(this);
      this._onUp = this._onUp.bind(this);

      this.handle.addEventListener("mousedown", this._onDown);
      this.handle.addEventListener("touchstart", this._onDown, { passive: false });
    }

    _size() {
      return this.dir === "bottom"
        ? this.target.getBoundingClientRect().height
        : this.target.getBoundingClientRect().width;
    }

    _apply(size) {
      const px = Math.round(size) + "px";
      if (this.dir === "bottom") this.target.style.height = px;
      else this.target.style.width = px;
    }

    _onDown(e) {
      if (this.target.classList.contains("is-collapsed")) return;
      e.preventDefault();
      this.dragging = true;
      this.handle.classList.add("is-dragging");
      this.start = this.dir === "bottom" ? e.clientY : e.clientX;
      this.startSize = this._size();
      document.body.style.cursor = this.dir === "bottom" ? "row-resize" : "col-resize";
      document.body.style.userSelect = "none";
      window.addEventListener("mousemove", this._onMove);
      window.addEventListener("mouseup", this._onUp);
      window.addEventListener("touchmove", this._onMove, { passive: false });
      window.addEventListener("touchend", this._onUp);
    }

    _onMove(e) {
      if (!this.dragging) return;
      e.preventDefault();
      const cur = this.dir === "bottom" ? e.clientY : e.clientX;
      const delta = cur - this.start;
      // dirección del crecimiento: 'right' y 'bottom' crecen al arrastrar hacia atrás
      const grow = this.dir === "left" ? delta : -delta;
      const next = Math.min(this.max, Math.max(this.min, this.startSize + grow));
      this._apply(next);
    }

    _onUp() {
      if (!this.dragging) return;
      this.dragging = false;
      this.handle.classList.remove("is-dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", this._onMove);
      window.removeEventListener("mouseup", this._onUp);
      window.removeEventListener("touchmove", this._onMove);
      window.removeEventListener("touchend", this._onUp);
    }
  }

  /** Inicializa todos los [data-resizer] del documento. */
  NS.initSplitters = function () {
    document.querySelectorAll("[data-resizer]").forEach((el) => {
      const target = el.getAttribute("data-target");
      const dir = el.getAttribute("data-dir");
      const panel = document.getElementById(target);
      new Splitter(el, {
        target,
        dir,
        min: panel ? parseInt(panel.dataset.min || MIN_DEFAULT, 10) : MIN_DEFAULT,
        max: panel ? parseInt(panel.dataset.max || MAX_DEFAULT, 10) : MAX_DEFAULT,
      });
    });
  };

  NS.Splitter = Splitter;
})(window);
