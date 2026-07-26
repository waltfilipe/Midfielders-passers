"""Interactive quadrant pass map: hover a quadrant to reveal its common and rare routes."""

from __future__ import annotations

import json

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

# Matches CMAP_XP_GRAY_RED from xp_study_maps so both views read the same way.
XP_COLOR_STOPS: tuple[tuple[float, str], ...] = (
    (0.00, "#6b7280"),
    (0.25, "#9ca3af"),
    (0.55, "#f87171"),
    (0.80, "#ef4444"),
    (1.00, "#b91c1c"),
)

_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<script src="__PLOTLY_CDN__"></script>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: #0f172a;
    color: #e2e8f0;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .qmap-wrap {
    border: 1px solid rgba(148,163,184,0.18);
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(30,41,59,0.55) 0%, rgba(15,23,42,0.35) 100%);
    padding: 0.75rem 0.9rem 0.85rem 0.9rem;
  }
  .qmap-toolbar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
  }
  .qmap-toolbar-label {
    color: #93a4bc;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-right: 0.25rem;
  }
  .qmap-btn {
    background: rgba(15,23,42,0.7);
    border: 1px solid rgba(148,163,184,0.28);
    color: #cbd5e1;
    border-radius: 999px;
    padding: 0.24rem 0.8rem;
    font-size: 0.79rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .qmap-btn:hover { border-color: rgba(56,189,248,0.5); color: #e2e8f0; }
  .qmap-btn.is-active {
    background: rgba(56,189,248,0.16);
    border-color: rgba(56,189,248,0.6);
    color: #bae6fd;
  }
  .qmap-body {
    display: grid;
    grid-template-columns: minmax(290px, 1.55fr) minmax(215px, 0.95fr);
    gap: 0.75rem;
    align-items: start;
  }
  @media (max-width: 620px) {
    .qmap-body { grid-template-columns: 1fr; }
  }
  #qmap-plot {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
  }
  .qmap-panel {
    background: rgba(15,23,42,0.55);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
    min-height: 320px;
  }
  .qp-title {
    display: block;
    font-size: 0.95rem;
    font-weight: 800;
    color: #e2e8f0;
    margin: 0 0 0.15rem 0;
  }
  .qp-sub {
    display: block;
    color: #94a3b8;
    font-size: 0.76rem;
    line-height: 1.4;
    margin-bottom: 0.6rem;
  }
  .qp-hint {
    color: #94a3b8;
    font-size: 0.8rem;
    line-height: 1.5;
  }
  .qp-section { margin-top: 0.65rem; }
  .qp-section h4 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0 0 0.35rem 0;
    font-size: 0.74rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #93a4bc;
  }
  .qp-list { list-style: none; margin: 0; padding: 0; }
  .qp-item {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
    padding: 0.22rem 0;
    border-bottom: 1px dashed rgba(148,163,184,0.14);
    font-size: 0.78rem;
  }
  .qp-item:last-child { border-bottom: none; }
  .qp-dot {
    flex: 0 0 auto;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    border: 1px solid rgba(248,250,252,0.35);
  }
  .qp-route {
    flex: 1 1 auto;
    min-width: 0;
    color: #e2e8f0;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .qp-meta { flex: 0 0 auto; color: #94a3b8; font-size: 0.72rem; white-space: nowrap; }
  .qp-legend {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.7rem;
    padding-top: 0.55rem;
    border-top: 1px dashed rgba(148,163,184,0.18);
    color: #94a3b8;
    font-size: 0.7rem;
  }
  .qp-bar {
    flex: 1 1 auto;
    height: 7px;
    border-radius: 999px;
    background: linear-gradient(90deg, #6b7280 0%, #9ca3af 25%, #f87171 55%, #ef4444 80%, #b91c1c 100%);
  }
</style>
</head>
<body>
<div class="qmap-wrap">
  <div class="qmap-toolbar">
    <span class="qmap-toolbar-label">Rotas</span>
    <button class="qmap-btn is-active" data-mode="common">Mais comuns</button>
    <button class="qmap-btn" data-mode="rare">Mais raros</button>
    <button class="qmap-btn" data-mode="both">Ambos</button>
    <button class="qmap-btn" id="qmap-reset" style="margin-left:auto">Ver todos</button>
  </div>
  <div class="qmap-body">
    <div id="qmap-plot"></div>
    <aside class="qmap-panel" id="qmap-panel"></aside>
  </div>
</div>

<script>
(function () {
  var DATA = __DATA__;
  var STOPS = __STOPS__;
  var FIELD_X = DATA.field_x || 120;
  var FIELD_Y = DATA.field_y || 80;
  var XP_MAX = DATA.xp_max || 1.0;
  var QUAD_ORDER = __QUAD_ORDER__;
  var PLOT_HEIGHT = __PLOT_HEIGHT__;

  var plotEl = document.getElementById('qmap-plot');
  var panelEl = document.getElementById('qmap-panel');
  var mode = 'common';
  var activeQuad = null;

  function fmtInt(v) { return Number(v).toLocaleString('pt-BR'); }
  function fmtPct(v) { return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%'; }
  function fmtXp(v) { return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function hexToRgb(hex) {
    var h = hex.replace('#', '');
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }

  function xpColor(value, alpha) {
    var t = Math.max(0, Math.min(1, Number(value) / XP_MAX));
    var lo = STOPS[0], hi = STOPS[STOPS.length - 1];
    for (var i = 0; i < STOPS.length - 1; i++) {
      if (t >= STOPS[i][0] && t <= STOPS[i + 1][0]) { lo = STOPS[i]; hi = STOPS[i + 1]; break; }
    }
    var span = (hi[0] - lo[0]) || 1;
    var k = (t - lo[0]) / span;
    var c0 = hexToRgb(lo[1]), c1 = hexToRgb(hi[1]);
    var r = Math.round(c0[0] + (c1[0] - c0[0]) * k);
    var g = Math.round(c0[1] + (c1[1] - c0[1]) * k);
    var b = Math.round(c0[2] + (c1[2] - c0[2]) * k);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + (alpha === undefined ? 1 : alpha) + ')';
  }

  function pitchShapes() {
    var line = 'rgba(226,232,240,0.55)';
    var rect = function (x0, y0, x1, y1, extra) {
      var s = { type: 'rect', x0: x0, y0: y0, x1: x1, y1: y1, line: { color: line, width: 1.2 }, layer: 'above' };
      return Object.assign(s, extra || {});
    };
    var shapes = [
      rect(0, 0, FIELD_X, FIELD_Y),
      rect(0, 18, 18, 62),
      rect(FIELD_X - 18, 18, FIELD_X, 62),
      rect(0, 30, 6, 50),
      rect(FIELD_X - 6, 30, FIELD_X, 50),
      { type: 'line', x0: FIELD_X / 2, y0: 0, x1: FIELD_X / 2, y1: FIELD_Y, line: { color: line, width: 1.2 }, layer: 'above' },
      { type: 'circle', x0: FIELD_X / 2 - 10, y0: FIELD_Y / 2 - 10, x1: FIELD_X / 2 + 10, y1: FIELD_Y / 2 + 10, line: { color: line, width: 1.2 }, layer: 'above' }
    ];
    // Quadrant guides.
    shapes.push({ type: 'line', x0: FIELD_X / 2, y0: 0, x1: FIELD_X / 2, y1: FIELD_Y, line: { color: 'rgba(203,213,225,0.5)', width: 1.6, dash: 'dot' }, layer: 'above' });
    shapes.push({ type: 'line', x0: 0, y0: FIELD_Y / 2, x1: FIELD_X, y1: FIELD_Y / 2, line: { color: 'rgba(203,213,225,0.5)', width: 1.6, dash: 'dot' }, layer: 'above' });
    return shapes;
  }

  function quadrantTraces() {
    return QUAD_ORDER.map(function (key) {
      var q = DATA.quadrants[key];
      var b = q.bounds;
      var isActive = activeQuad === key;
      var baseAlpha = activeQuad === null ? 0.30 : (isActive ? 0.34 : 0.07);
      return {
        type: 'scatter',
        mode: 'lines',
        x: [b[0], b[2], b[2], b[0], b[0]],
        y: [b[1], b[1], b[3], b[3], b[1]],
        fill: 'toself',
        fillcolor: xpColor(q.mean_xp, baseAlpha),
        line: { color: isActive ? 'rgba(56,189,248,0.9)' : 'rgba(148,163,184,0.25)', width: isActive ? 2.2 : 1 },
        hoveron: 'fills',
        hoverinfo: 'text',
        text: '<b>' + q.label + '</b><br>' + fmtInt(q.passes) + ' passes · ' + fmtPct(q.share_pct)
              + '<br>xP médio ' + fmtXp(q.mean_xp) + '<br><i>passe o mouse para ver as rotas</i>',
        showlegend: false,
        customdata: [key],
        name: q.label
      };
    });
  }

  function routesForMode(q) {
    if (mode === 'common') return q.common.map(function (r) { return Object.assign({ kind: 'common' }, r); });
    if (mode === 'rare') return q.rare.map(function (r) { return Object.assign({ kind: 'rare' }, r); });
    return q.common.map(function (r) { return Object.assign({ kind: 'common' }, r); })
      .concat(q.rare.map(function (r) { return Object.assign({ kind: 'rare' }, r); }));
  }

  function routeAnnotations(routes) {
    if (!routes.length) return [];
    var counts = routes.filter(function (r) { return !r.is_self; }).map(function (r) { return r.count; });
    var maxC = counts.length ? Math.max.apply(null, counts) : 1;
    var minC = counts.length ? Math.min.apply(null, counts) : 1;
    var span = Math.max(maxC - minC, 1);
    return routes.filter(function (r) { return !r.is_self; }).map(function (r) {
      var w = 1.6 + 4.4 * ((r.count - minC) / span);
      return {
        x: r.x1, y: r.y1, ax: r.x0, ay: r.y0,
        xref: 'x', yref: 'y', axref: 'x', ayref: 'y',
        showarrow: true,
        arrowhead: 3,
        arrowsize: 0.9,
        arrowwidth: w,
        arrowcolor: xpColor(r.mean_xp, r.kind === 'rare' ? 0.98 : 0.85),
        standoff: 2,
        text: ''
      };
    });
  }

  function routeMarkerTrace(routes) {
    var pts = routes.filter(function (r) { return !r.is_self; });
    return {
      type: 'scatter',
      mode: 'markers',
      x: pts.map(function (r) { return r.x1; }),
      y: pts.map(function (r) { return r.y1; }),
      marker: {
        size: 9,
        color: pts.map(function (r) { return xpColor(r.mean_xp, 0.95); }),
        line: { color: '#f8fafc', width: 1 },
        symbol: pts.map(function (r) { return r.kind === 'rare' ? 'diamond' : 'circle'; })
      },
      hoverinfo: 'text',
      text: pts.map(function (r) {
        return '<b>' + r.origin_label + ' → ' + r.dest_label + '</b><br>'
          + fmtInt(r.count) + ' passes · ' + fmtPct(r.share_pct) + ' do quadrante<br>'
          + 'xP médio ' + fmtXp(r.mean_xp) + ' · ' + r.distance_m + ' m<br>'
          + (r.kind === 'rare' ? '<i>rota rara</i>' : '<i>rota comum</i>');
      }),
      showlegend: false,
      name: 'rotas'
    };
  }

  function selfRouteTrace(routes) {
    var pts = routes.filter(function (r) { return r.is_self; });
    return {
      type: 'scatter',
      mode: 'markers',
      x: pts.map(function (r) { return r.x0; }),
      y: pts.map(function (r) { return r.y0; }),
      marker: {
        size: 20,
        color: pts.map(function (r) { return xpColor(r.mean_xp, 0.5); }),
        line: { color: 'rgba(248,250,252,0.75)', width: 1.4 },
        symbol: 'circle-open-dot'
      },
      hoverinfo: 'text',
      text: pts.map(function (r) {
        return '<b>Passe curto na mesma zona</b><br>' + r.origin_label + '<br>'
          + fmtInt(r.count) + ' passes · ' + fmtPct(r.share_pct) + ' do quadrante<br>'
          + 'xP médio ' + fmtXp(r.mean_xp);
      }),
      showlegend: false,
      name: 'curtos'
    };
  }

  function layout() {
    var shapes = pitchShapes();
    var annotations = [];
    if (activeQuad) {
      annotations = routeAnnotations(routesForMode(DATA.quadrants[activeQuad]));
    }
    QUAD_ORDER.forEach(function (key) {
      var q = DATA.quadrants[key];
      var b = q.bounds;
      // Keep labels hugging the touchlines so they stay clear of the route arrows.
      var pad = (b[3] - b[1]) * 0.09;
      annotations.push({
        x: (b[0] + b[2]) / 2,
        y: key.indexOf('left') >= 0 ? b[1] + pad : b[3] - pad,
        xref: 'x', yref: 'y',
        text: q.label.toUpperCase(),
        showarrow: false,
        font: { size: 9.5, color: activeQuad === key ? '#bae6fd' : '#94a3b8', family: 'inherit' },
        bgcolor: 'rgba(15,23,42,0.66)',
        borderpad: 3,
        opacity: activeQuad && activeQuad !== key ? 0.45 : 1
      });
    });
    return {
      height: PLOT_HEIGHT,
      margin: { l: 6, r: 6, t: 6, b: 6 },
      paper_bgcolor: '#0f172a',
      plot_bgcolor: '#111c33',
      shapes: shapes,
      annotations: annotations,
      hovermode: 'closest',
      hoverlabel: { bgcolor: '#111827', bordercolor: '#334155', font: { color: '#f8fafc', size: 12 } },
      dragmode: false,
      xaxis: { range: [-2, FIELD_X + 2], visible: false, fixedrange: true, constrain: 'domain' },
      // y reversed so the pitch matches the mplsoccer StatsBomb maps in the same tab.
      yaxis: { range: [FIELD_Y + 2, -2], visible: false, fixedrange: true, scaleanchor: 'x', scaleratio: 1, constrain: 'domain' }
    };
  }

  function traces() {
    var out = quadrantTraces();
    if (activeQuad) {
      var routes = routesForMode(DATA.quadrants[activeQuad]);
      out.push(selfRouteTrace(routes));
      out.push(routeMarkerTrace(routes));
    }
    return out;
  }

  function routeListHtml(routes, emptyMsg) {
    if (!routes.length) return '<p class="qp-hint">' + emptyMsg + '</p>';
    return '<ul class="qp-list">' + routes.slice(0, 5).map(function (r) {
      var arrow = r.is_self ? (r.origin_label + ' (curto)') : (r.origin_label + ' → ' + r.dest_label);
      return '<li class="qp-item">'
        + '<span class="qp-dot" style="background:' + xpColor(r.mean_xp, 1) + '"></span>'
        + '<span class="qp-route" title="' + arrow + '">' + arrow + '</span>'
        + '<span class="qp-meta">' + fmtInt(r.count) + ' · xP ' + fmtXp(r.mean_xp) + '</span>'
        + '</li>';
    }).join('') + '</ul>';
  }

  function renderPanel() {
    if (!activeQuad) {
      var rows = QUAD_ORDER.map(function (key) {
        var q = DATA.quadrants[key];
        return '<li class="qp-item">'
          + '<span class="qp-dot" style="background:' + xpColor(q.mean_xp, 1) + '"></span>'
          + '<span class="qp-route">' + q.label + '</span>'
          + '<span class="qp-meta">' + fmtPct(q.share_pct) + ' · xP ' + fmtXp(q.mean_xp) + '</span>'
          + '</li>';
      }).join('');
      panelEl.innerHTML = '<span class="qp-title">Visão geral</span>'
        + '<span class="qp-sub">' + fmtInt(DATA.total_passes) + ' passes de meio-campistas. '
        + 'Passe o mouse por um quadrante do campo para ver as rotas mais comuns e as mais raras que saem dele.</span>'
        + '<ul class="qp-list">' + rows + '</ul>'
        + '<div class="qp-legend"><span>comum</span><span class="qp-bar"></span><span>raro</span></div>';
      return;
    }
    var q = DATA.quadrants[activeQuad];
    var commonHtml = (mode === 'rare') ? '' :
      '<div class="qp-section"><h4>Mais comuns (volume)</h4>' + routeListHtml(q.common, 'Sem rotas.') + '</div>';
    var rareHtml = (mode === 'common') ? '' :
      '<div class="qp-section"><h4>Mais raros (xP alto)</h4>' + routeListHtml(q.rare, 'Sem rotas com amostra suficiente.') + '</div>';
    panelEl.innerHTML = '<span class="qp-title">' + q.label + '</span>'
      + '<span class="qp-sub">' + fmtInt(q.passes) + ' passes saindo daqui · ' + fmtPct(q.share_pct)
      + ' do total · xP médio ' + fmtXp(q.mean_xp) + '</span>'
      + commonHtml + rareHtml
      + '<div class="qp-legend"><span>comum</span><span class="qp-bar"></span><span>raro</span></div>';
  }

  function draw() {
    Plotly.react(plotEl, traces(), layout(), { displayModeBar: false, responsive: true });
    renderPanel();
  }

  Plotly.newPlot(plotEl, traces(), layout(), { displayModeBar: false, responsive: true }).then(function () {
    renderPanel();
    plotEl.on('plotly_hover', function (ev) {
      var pt = ev.points && ev.points[0];
      if (!pt || !pt.data || !pt.data.customdata) return;
      var key = pt.data.customdata[0];
      if (typeof key !== 'string' || !DATA.quadrants[key] || key === activeQuad) return;
      activeQuad = key;
      draw();
    });
  });

  document.querySelectorAll('.qmap-btn[data-mode]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.qmap-btn[data-mode]').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      mode = btn.getAttribute('data-mode');
      draw();
    });
  });

  document.getElementById('qmap-reset').addEventListener('click', function () {
    activeQuad = null;
    draw();
  });
})();
</script>
</body>
</html>
"""


def build_quadrant_map_html(analysis: dict, *, plot_height: int = 470) -> str:
    """Self-contained Plotly page: hover a quadrant to reveal its common and rare routes."""
    quad_order = [key for key in analysis.get("quadrants", {})]
    payload = {
        "quadrants": analysis.get("quadrants", {}),
        "total_passes": analysis.get("total_passes", 0),
        "field_x": analysis.get("field_x", 120.0),
        "field_y": analysis.get("field_y", 80.0),
        "xp_max": analysis.get("xp_max", 1.0),
    }
    return (
        _TEMPLATE
        .replace("__PLOTLY_CDN__", PLOTLY_CDN)
        .replace("__DATA__", json.dumps(payload))
        .replace("__STOPS__", json.dumps([[stop, color] for stop, color in XP_COLOR_STOPS]))
        .replace("__QUAD_ORDER__", json.dumps(quad_order))
        .replace("__PLOT_HEIGHT__", str(int(plot_height)))
    )
