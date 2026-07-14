/* ============================================================
   ARGOS · Charts (series de tiempo en canvas, sin librerías)
   Sin datos falsos: el throughput se alimenta desde /stats.series.
   ============================================================ */
(function (global) {
  "use strict";

  const NS = (global.ARGOS = global.ARGOS || {});

  const SEV_COLORS = {
    critical: "#ff5d5d", high: "#e0a83b", medium: "#3d7eff",
    low: "#2ecc71", info: "#8593a8", unknown: "#5a6678",
  };
  const SEV_ORDER = ["critical", "high", "medium", "low", "info", "unknown"];

  /* ---- Gráfico multi-serie (throughput por severidad) ---- */
  class ThroughputChart {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.buckets = [];
      this.datasets = [];
      this._observe();
      this._resize();
    }

    _observe() {
      const self = this;
      const ro = () => self._resize();
      if (typeof ResizeObserver !== "undefined") {
        new ResizeObserver(ro).observe(this.canvas);
      } else {
        window.addEventListener("resize", ro);
      }
    }

    _resize() {
      const dpr = window.devicePixelRatio || 1;
      const r = this.canvas.getBoundingClientRect();
      this.w = Math.max(1, r.width);
      this.h = Math.max(1, r.height);
      this.canvas.width = this.w * dpr;
      this.canvas.height = this.h * dpr;
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.draw();
    }

    setData(series) {
      const data = series || [];
      const buckets = [...new Set(data.map((s) => s.bucket))].sort();
      const bySev = {};
      SEV_ORDER.forEach((s) => (bySev[s] = new Array(buckets.length).fill(0)));
      data.forEach((s) => {
        const i = buckets.indexOf(s.bucket);
        const sev = bySev[s.severity] ? s.severity : "unknown";
        if (i >= 0) bySev[sev][i] = (bySev[sev][i] || 0) + (s.count || 0);
      });
      this.buckets = buckets;
      this.datasets = SEV_ORDER.map((sev) => ({
        severity: sev, color: SEV_COLORS[sev], data: bySev[sev],
      }));
      this.draw();
    }

    _fmt(b) {
      if (!b) return "";
      const s = String(b);
      return s.length > 16 ? s.slice(11, 16) : s;
    }

    draw() {
      const { ctx, w, h } = this;
      ctx.clearRect(0, 0, w, h);
      if (!this.buckets.length) {
        ctx.fillStyle = "#5a6678";
        ctx.font = "12px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Sin datos", w / 2, h / 2);
        return;
      }
      const padL = 6, padR = 6, padT = 10, padB = 16;
      const plotW = w - padL - padR;
      const plotH = h - padT - padB;
      const n = this.buckets.length;
      const max = Math.max(1, ...this.datasets.flatMap((d) => d.data));
      const xAt = (i) => padL + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW);
      const yAt = (v) => padT + plotH - (v / max) * plotH;

      // líneas de rejilla
      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;
      for (let g = 0; g <= 2; g++) {
        const y = padT + (g / 2) * plotH;
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(w - padR, y);
        ctx.stroke();
      }

      // series (low -> high para que critical quede encima)
      [...this.datasets].reverse().forEach((d) => {
        const pts = d.data.map((v, i) => [xAt(i), yAt(v)]);
        ctx.beginPath();
        pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
        ctx.lineTo(xAt(n - 1), padT + plotH);
        ctx.lineTo(xAt(0), padT + plotH);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
        grad.addColorStop(0, d.color + "33");
        grad.addColorStop(1, d.color + "00");
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.beginPath();
        pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
        ctx.strokeStyle = d.color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      });

      // etiquetas de ejes
      ctx.fillStyle = "#5a6678";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(this._fmt(this.buckets[0]), padL, h - 4);
      ctx.textAlign = "right";
      ctx.fillText(this._fmt(this.buckets[n - 1]), w - padR, h - 4);
    }
  }

  NS.SEV_COLORS = SEV_COLORS;
  NS.SEV_ORDER = SEV_ORDER;

  NS.initCharts = function () {
    const c = document.getElementById("throughput-canvas");
    NS._throughput = c ? new ThroughputChart(c) : null;
  };

  NS.renderThroughput = function (series) {
    if (NS._throughput) NS._throughput.setData(series || []);
  };
})(window);
