/* =========================================================================
   Météo des Marchés — logique du site
   Charge data/data.json (produit par compute.py) et dessine :
   la jauge animée, les 8 cartes d'indicateurs et la courbe d'historique.
   ========================================================================= */

"use strict";

// Couleurs (identiques à styles.css) — utilisées pour SVG & Chart.js.
const C = {
  off: "#ff5d61", neutral: "#e3a93d", on: "#2fcf92",
  fg: "#e8eef6", muted: "#9aa6b6", dim: "#5f6b7c",
  border: "#212b3b", panel: "#111723", bg: "#0a0d12",
};
const OFF_MAX = 35, NEUTRAL_MAX = 65;

function zoneFor(v) {
  if (v == null || isNaN(v)) return { label: "—", color: C.dim };
  if (v < OFF_MAX) return { label: "Risk-off", color: C.off };
  if (v < NEUTRAL_MAX) return { label: "Neutre", color: C.neutral };
  return { label: "Risk-on", color: C.on };
}
const fmtSigned = (x) => (x == null ? "—" : (x > 0 ? "+" : "") + x.toFixed(1));
const $ = (sel) => document.querySelector(sel);

// ----- démarrage --------------------------------------------------------
init();

async function init() {
  let data;
  try {
    const res = await fetch("data/data.json", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    data = await res.json();
  } catch (err) {
    showLoadError(err);
    return;
  }
  render(data);
}

function showLoadError(err) {
  const b = $("#banner-warn");
  b.hidden = false;
  b.innerHTML = "<span>⚠</span><div><strong>Impossible de charger les données.</strong> " +
    "Le fichier <code>data/data.json</code> est introuvable (" + err.message + "). " +
    "En local, ouvre le site via un petit serveur (voir le guide) plutôt qu'en double-cliquant le fichier.</div>";
}

function render(d) {
  // Bandeaux -------------------------------------------------------------
  if (d.placeholder) {
    const b = $("#banner-demo");
    b.hidden = false;
    b.innerHTML = "<span>●</span><div><strong>Données de démonstration.</strong> " +
      "En attente du premier calcul réel (il se lancera automatiquement via GitHub Actions). " +
      "Les chiffres ci-dessous illustrent le fonctionnement, ce ne sont pas encore les vraies valeurs de marché.</div>";
  }
  if (d.missing_tickers && d.missing_tickers.length) {
    const b = $("#banner-warn");
    b.hidden = false;
    b.innerHTML = "<span>⚠</span><div><strong>Calcul partiel.</strong> Indicateur(s) indisponible(s) ce jour : " +
      "<span class='mono'>" + d.missing_tickers.join(", ") + "</span>. Le score est calculé sur les indicateurs restants.</div>";
  }

  // Date de mise à jour --------------------------------------------------
  $("#updated").innerHTML = "<span class='dot'></span>Données au " + frDate(d.as_of_date);

  // Accueil --------------------------------------------------------------
  const z = zoneFor(d.score);
  buildGauge(d.score, z.color);

  const pill = $("#zone-pill");
  pill.style.color = z.color;
  pill.style.borderColor = z.color;
  pill.innerHTML = "<span class='pip'></span>" + d.zone;

  $("#verdict").textContent = d.verdict;

  setStat("#stat-1d", d.change_1d);
  setStat("#stat-1w", d.change_1w);
  $("#stat-maj").textContent = frDate(d.as_of_date);

  // Indicateurs ----------------------------------------------------------
  const grid = $("#cards");
  grid.innerHTML = "";
  d.indicators.forEach((ind) => grid.appendChild(card(ind)));

  // Historique -----------------------------------------------------------
  buildHistory(d);
  buildEventChips(d.events);
}

// ----- utilitaires format ----------------------------------------------
function frDate(iso) {
  if (!iso) return "—";
  const [y, m, day] = iso.split("-");
  const mois = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  return parseInt(day, 10) + " " + mois[parseInt(m, 10) - 1] + " " + y;
}
function setStat(sel, val) {
  const el = $(sel);
  el.textContent = fmtSigned(val) + " pts";
  el.classList.remove("up", "down", "flat-c");
  el.classList.add(val == null ? "flat-c" : val > 0.05 ? "up" : val < -0.05 ? "down" : "flat-c");
}

// =========================================================================
//  JAUGE (SVG demi-cercle + aiguille animée)
// =========================================================================
const G = { cx: 200, cy: 208, r: 162, th: 24 };

function angForScore(s) { return 180 - (s / 100) * 180; }          // 0->180°, 100->0°
function polar(cx, cy, r, deg) {
  const a = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) };
}
function arcPath(r, sStart, sEnd) {
  const p0 = polar(G.cx, G.cy, r, angForScore(sStart));
  const p1 = polar(G.cx, G.cy, r, angForScore(sEnd));
  const large = angForScore(sStart) - angForScore(sEnd) > 180 ? 1 : 0;
  return `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`;
}

function buildGauge(score, color) {
  const zones = [
    { a: 0, b: OFF_MAX, c: C.off },
    { a: OFF_MAX, b: NEUTRAL_MAX, c: C.neutral },
    { a: NEUTRAL_MAX, b: 100, c: C.on },
  ];
  const active = score < OFF_MAX ? 0 : score < NEUTRAL_MAX ? 1 : 2;
  let svg = `<svg viewBox="0 0 400 250" role="img" aria-label="Jauge du score ${score} sur 100">`;

  // segments de zone
  zones.forEach((zn, i) => {
    svg += `<path d="${arcPath(G.r, zn.a, zn.b)}" fill="none" stroke="${zn.c}" stroke-width="${G.th}" ` +
           `opacity="${i === active ? 1 : 0.28}" stroke-linecap="butt"/>`;
  });

  // graduations
  [0, OFF_MAX, NEUTRAL_MAX, 100].forEach((s) => {
    const o = polar(G.cx, G.cy, G.r - G.th / 2 - 4, angForScore(s));
    const o2 = polar(G.cx, G.cy, G.r - G.th / 2 - 13, angForScore(s));
    svg += `<line x1="${o.x.toFixed(1)}" y1="${o.y.toFixed(1)}" x2="${o2.x.toFixed(1)}" y2="${o2.y.toFixed(1)}" stroke="${C.bg}" stroke-width="2"/>`;
  });

  // libellés des extrémités
  svg += `<text x="${G.cx - G.r}" y="${G.cy + 24}" fill="${C.dim}" font-size="11" font-family="IBM Plex Mono, monospace" text-anchor="start" letter-spacing="1">RISK-OFF</text>`;
  svg += `<text x="${G.cx + G.r}" y="${G.cy + 24}" fill="${C.dim}" font-size="11" font-family="IBM Plex Mono, monospace" text-anchor="end" letter-spacing="1">RISK-ON</text>`;

  // aiguille + moyeu
  svg += `<line id="needle" x1="${G.cx}" y1="${G.cy}" x2="${G.cx}" y2="${G.cy - (G.r - 34)}" stroke="${color}" stroke-width="4" stroke-linecap="round"/>`;
  svg += `<circle cx="${G.cx}" cy="${G.cy}" r="9" fill="${C.panel}" stroke="${color}" stroke-width="3"/>`;

  // valeur + sous-texte
  svg += `<text id="gauge-score" x="${G.cx}" y="${G.cy - 36}" fill="${color}" font-size="62" font-weight="700" ` +
         `font-family="IBM Plex Mono, monospace" text-anchor="middle" style="font-variant-numeric:tabular-nums">0</text>`;
  svg += `<text x="${G.cx}" y="${G.cy - 12}" fill="${C.dim}" font-size="13" font-family="IBM Plex Mono, monospace" text-anchor="middle">sur 100</text>`;
  svg += `</svg>`;

  $("#gauge").innerHTML = svg;
  animateNeedle(score, color);
}

function animateNeedle(target, color) {
  const needle = document.getElementById("needle");
  const label = document.getElementById("gauge-score");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const setTo = (s) => {
    const p = polar(G.cx, G.cy, G.r - 34, angForScore(s));
    needle.setAttribute("x2", p.x.toFixed(2));
    needle.setAttribute("y2", p.y.toFixed(2));
    label.textContent = Math.round(s);
  };
  if (reduce) { setTo(target); return; }
  const dur = 1100, t0 = performance.now();
  const ease = (t) => 1 - Math.pow(1 - t, 3);
  (function frame(now) {
    const t = Math.min(1, (now - t0) / dur);
    setTo(target * ease(t));
    if (t < 1) requestAnimationFrame(frame);
    else setTo(target);
  })(t0);
}

// =========================================================================
//  CARTES D'INDICATEURS
// =========================================================================
function card(ind) {
  const el = document.createElement("article");
  el.className = "card" + (ind.available ? "" : " unavailable");
  const z = zoneFor(ind.subscore);
  const val = ind.subscore == null ? "—" : Math.round(ind.subscore);
  const tr = { up: ["↑", C.on], down: ["↓", C.off], flat: ["→", C.muted] }[ind.trend] || ["→", C.muted];

  el.innerHTML =
    `<div class="card-top">
       <div>
         <div class="card-name">${ind.name}</div>
         <div class="card-tickers">${ind.tickers.join(" · ")}</div>
       </div>
       <span class="tag" style="color:${z.color}">${z.label}</span>
     </div>
     <div class="card-sub">
       <span class="n" style="color:${z.color}">${val}</span>
       <span class="trend" style="color:${tr[1]}">${tr[0]}</span>
     </div>
     ${sparkline(ind.series, z.color)}
     <p class="card-meaning">${ind.meaning}</p>`;
  return el;
}

function sparkline(series, color) {
  if (!series || series.length < 2) return `<div class="spark"></div>`;
  const W = 120, H = 40, pad = 3;
  const n = series.length;
  const xs = (i) => (i / (n - 1)) * W;
  const ys = (v) => H - pad - (v / 100) * (H - 2 * pad);
  let pts = series.map((p, i) => `${xs(i).toFixed(1)},${ys(p.v).toFixed(1)}`).join(" ");
  const last = series[n - 1];
  const area = `${xs(0).toFixed(1)},${H} ${pts} ${xs(n - 1).toFixed(1)},${H}`;
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
            <polygon points="${area}" fill="${color}" opacity="0.10"/>
            <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round"/>
            <circle cx="${xs(n - 1).toFixed(1)}" cy="${ys(last.v).toFixed(1)}" r="2.4" fill="${color}"/>
          </svg>`;
}

// =========================================================================
//  HISTORIQUE (Chart.js)
// =========================================================================
function buildHistory(d) {
  // Enregistre le plugin d'annotations si le build CDN ne le fait pas tout seul.
  try {
    const ann = window["chartjs-plugin-annotation"];
    if (ann && window.Chart && Chart.registry && !Chart.registry.plugins.get("annotation")) {
      Chart.register(ann);
    }
  } catch (e) { /* sans annotation, le graphe reste lisible */ }

  const ctx = document.getElementById("history-chart").getContext("2d");
  const points = d.history.map((p) => ({ x: p.d, y: p.s }));

  // bandes de couleur par zone
  const band = (y0, y1, col) => ({
    type: "box", yMin: y0, yMax: y1, xMin: undefined, xMax: undefined,
    backgroundColor: col, borderWidth: 0, drawTime: "beforeDatasetsDraw",
  });
  const annotations = {
    zOff: band(0, OFF_MAX, "rgba(255,93,97,0.10)"),
    zNeu: band(OFF_MAX, NEUTRAL_MAX, "rgba(227,169,61,0.07)"),
    zOn: band(NEUTRAL_MAX, 100, "rgba(47,207,146,0.09)"),
  };
  const shortLabel = { covid: "Covid", rates: "2022 · taux", carry: "Carry yen" };
  (d.events || []).forEach((ev, i) => {
    annotations["ev" + i] = {
      type: "line", xMin: ev.date, xMax: ev.date,
      borderColor: "rgba(232,238,246,0.45)", borderWidth: 1, borderDash: [4, 4],
      label: {
        display: true, content: (shortLabel[ev.id] || ev.label) + " · " + ev.score,
        position: "start", backgroundColor: "rgba(20,27,41,0.92)", color: C.muted,
        font: { family: "IBM Plex Mono, monospace", size: 10 }, padding: 4, yAdjust: 2,
      },
    };
  });

  new Chart(ctx, {
    type: "line",
    data: {
      datasets: [{
        label: "Score",
        data: points,
        borderColor: "#cdd8ea",
        borderWidth: 1.4,
        pointRadius: 0,
        tension: 0.08,
        fill: { target: "origin", above: "rgba(90,162,255,0.05)" },
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 600 },
      interaction: { intersect: false, mode: "index" },
      scales: {
        x: {
          type: "time",
          time: { unit: "year", tooltipFormat: "dd MMM yyyy" },
          grid: { color: "rgba(33,43,59,0.6)" },
          ticks: { color: C.dim, font: { family: "IBM Plex Mono, monospace", size: 11 } },
        },
        y: {
          min: 0, max: 100,
          grid: { color: "rgba(33,43,59,0.6)" },
          ticks: { color: C.dim, stepSize: 20, font: { family: "IBM Plex Mono, monospace", size: 11 } },
        },
      },
      plugins: {
        legend: { display: false },
        annotation: { annotations },
        tooltip: {
          backgroundColor: "rgba(17,23,35,0.96)", borderColor: C.border, borderWidth: 1,
          titleColor: C.fg, bodyColor: C.fg, padding: 10,
          titleFont: { family: "IBM Plex Sans, sans-serif" },
          bodyFont: { family: "IBM Plex Mono, monospace" },
          callbacks: {
            label: (c) => {
              const v = c.parsed.y;
              return "Score " + v.toFixed(1) + " · " + zoneFor(v).label;
            },
          },
        },
      },
    },
  });
}

function buildEventChips(events) {
  const row = $("#events-row");
  if (!events || !events.length) { row.hidden = true; return; }
  row.innerHTML = events.map((ev) =>
    `<span class="event-chip">${ev.label} — plus bas <b>${ev.score}</b> le ${frDate(ev.date)}</span>`
  ).join("");
}
