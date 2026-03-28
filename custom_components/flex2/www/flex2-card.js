/**
 * flex2-card.js
 *
 * Card YAML:
 *   type: custom:flex2-card
 *   entity: sensor.flex2_r_opt
 *   title: Flex2                 # optional
 */

class Flex2Card extends HTMLElement {

    setConfig(config) {
        this._config = config;
        if (!this.shadowRoot) {
            this.attachShadow({ mode: "open" });
            this._build();
        } else {
            // Update title if config changes
            const t = this.shadowRoot.querySelector(".title");
            if (t) t.textContent = config.title || "Flex2";
        }
    }

    set hass(hass) {
        this._hass = hass;
        if (!this._config?.entity) return;
        const s = hass.states[this._config.entity];
        if (s) this._render(s.attributes);
    }

    getCardSize() { return 4; }

    static getStubConfig() {
        return { entity: "sensor.flex2_r_opt" };
    }

    _build() {
        this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; font-family: var(--primary-font-family, sans-serif); }
        ha-card { padding: 16px; }
        .title { font-size: 14px; font-weight: 500; color: var(--primary-text-color); margin-bottom: 12px; }
        canvas { width: 100%; height: 240px; display: block; }
        .legend { display: flex; gap: 16px; margin-top: 8px; font-size: 11px; color: var(--secondary-text-color); flex-wrap: wrap; }
        .li { display: flex; align-items: center; gap: 5px; }
        .sw { height: 2px; width: 18px; border-radius: 1px; }
        .stats { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color); }
        .stats strong { color: var(--primary-text-color); font-weight: 500; }
        .badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
        .interior { background: var(--success-color, #4caf50); color: #fff; }
        .at_min   { background: var(--warning-color, #ff9800); color: #fff; }
        .at_max   { background: var(--info-color,    #2196f3); color: #fff; }
        .unconfigured { padding: 16px; font-size: 13px; color: var(--secondary-text-color); }
      </style>
      <ha-card>
        <div class="title">${this._config?.title || "Flex2"}</div>
        <canvas id="c"></canvas>
        <div class="legend">
          <div class="li"><div class="sw" style="background:#7F77DD"></div>total obj</div>
          <div class="li"><div class="sw" style="background:#BA7517"></div>cost(r)</div>
          <div class="li"><div class="sw" style="background:#378ADD"></div>λ·r</div>
          <div class="li"><div style="width:1px;height:12px;background:#1D9E75"></div>r*</div>
        </div>
        <div class="stats" id="st"></div>
      </ha-card>`;
        this._canvas = this.shadowRoot.getElementById("c");
        this._st = this.shadowRoot.getElementById("st");
    }

    _render(a) {
        if (!a || !a.curve_xs) return;

        const {
            curve_xs: xs, curve_total: total,
            curve_cost: cost, curve_energy: energy,
            r_opt, lambda: lam, p_l, p_h, regime,
        } = a;

        const canvas = this._canvas;
        const dpr = window.devicePixelRatio || 1;
        const W = canvas.offsetWidth || 400;
        const H = canvas.offsetHeight || 240;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const cs = getComputedStyle(this.shadowRoot.host);
        const fg2 = cs.getPropertyValue("--secondary-text-color").trim() || "#888";
        const div = cs.getPropertyValue("--divider-color").trim() || "#ddd";
        const bg = cs.getPropertyValue("--card-background-color").trim() || "#fff";
        const ff = cs.getPropertyValue("--primary-font-family") || "sans-serif";

        const PAD = { t: 16, r: 16, b: 36, l: 48 };
        const cW = W - PAD.l - PAD.r;
        const cH = H - PAD.t - PAD.b;

        const allY = [...total, ...cost, ...energy];
        const yMin = Math.min(...allY);
        const yMax = Math.max(...allY);
        const yPad = (yMax - yMin) * 0.08 || 0.1;
        const yLo = yMin - yPad;
        const yHi = yMax + yPad;
        const yR = yHi - yLo;

        const cx = x => PAD.l + x * cW;
        const cy = y => PAD.t + cH - ((y - yLo) / yR) * cH;

        ctx.clearRect(0, 0, W, H);

        // grid
        ctx.strokeStyle = div; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3]);
        for (let i = 0; i <= 4; i++) {
            const gy = PAD.t + cH * i / 4;
            ctx.beginPath(); ctx.moveTo(PAD.l, gy); ctx.lineTo(PAD.l + cW, gy); ctx.stroke();
        }
        ctx.setLineDash([]);

        // zero line
        if (yLo < 0 && yHi > 0) {
            const zy = cy(0);
            ctx.beginPath(); ctx.strokeStyle = div; ctx.lineWidth = 1;
            ctx.moveTo(PAD.l, zy); ctx.lineTo(PAD.l + cW, zy); ctx.stroke();
        }

        const drawLine = (ys, color, width, dash = []) => {
            ctx.beginPath();
            ctx.strokeStyle = color; ctx.lineWidth = width;
            ctx.setLineDash(dash); ctx.lineJoin = "round";
            xs.forEach((x, i) => {
                const px = cx(x), py = cy(ys[i]);
                i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
            });
            ctx.stroke();
            ctx.setLineDash([]);
        };

        drawLine(cost, "#BA7517", 1.5, [5, 3]);
        drawLine(energy, "#378ADD", 1.2, [4, 3]);
        drawLine(total, "#7F77DD", 2.5);

        // r* vertical line
        const ox = cx(r_opt);
        ctx.beginPath(); ctx.strokeStyle = "#1D9E75"; ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 3]);
        ctx.moveTo(ox, PAD.t); ctx.lineTo(ox, PAD.t + cH);
        ctx.stroke(); ctx.setLineDash([]);

        // dot on total curve
        const oi = Math.min(Math.round(r_opt * (xs.length - 1)), xs.length - 1);
        const oy = cy(total[oi]);
        ctx.beginPath(); ctx.arc(ox, oy, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#1D9E75"; ctx.fill();
        ctx.strokeStyle = bg; ctx.lineWidth = 2; ctx.stroke();

        // r* label
        ctx.font = `500 11px ${ff}`;
        ctx.fillStyle = "#1D9E75";
        const labelX = (ox + 60 > PAD.l + cW) ? ox - 6 : ox + 6;
        ctx.textAlign = (ox + 60 > PAD.l + cW) ? "right" : "left";
        ctx.fillText(`r*=${(r_opt * 100).toFixed(0)}%`, labelX, oy - 8);

        // axes
        ctx.strokeStyle = fg2; ctx.lineWidth = 0.8;
        ctx.beginPath(); ctx.moveTo(PAD.l, PAD.t); ctx.lineTo(PAD.l, PAD.t + cH); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(PAD.l, PAD.t + cH); ctx.lineTo(PAD.l + cW, PAD.t + cH); ctx.stroke();

        ctx.fillStyle = fg2; ctx.font = `11px ${ff}`; ctx.textAlign = "right";
        for (let i = 0; i <= 4; i++) {
            const v = yLo + yR * (1 - i / 4);
            ctx.fillText(v.toFixed(2), PAD.l - 4, PAD.t + cH * i / 4 + 4);
        }

        ctx.textAlign = "center";
        [0, 0.25, 0.5, 0.75, 1.0].forEach(v => {
            ctx.fillText(`${(v * 100).toFixed(0)}%`, cx(v), PAD.t + cH + 16);
        });
        ctx.fillText("r (consumption)", PAD.l + cW / 2, PAD.t + cH + 30);

        const regimeLabel = { interior: "interior", at_min: "at min", at_max: "at max" }[regime] || regime;
        this._st.innerHTML =
            `<span class="badge ${regime}">${regimeLabel}</span>` +
            `<span>λ <strong>${(+lam).toFixed(4)}</strong></span>` +
            `<span>p_l <strong>${(+p_l).toFixed(3)}</strong></span>` +
            `<span>p_h <strong>${(+p_h).toFixed(3)}</strong></span>` +
            `<span>r* <strong>${((+r_opt) * 100).toFixed(1)}%</strong></span>`;
    }
}

customElements.define("flex2-card", Flex2Card);
window.customCards = window.customCards || [];
window.customCards.push({
    type: "flex2-card",
    name: "Flex2 card",
    description: "Demand-response curve with current operating point",
});