"""Interactive quadrant heatmap: hover a quadrant to compare where its passes go."""

from __future__ import annotations

import json

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

# Mirrors CMAP_XP_GRAY_RED / CMAP_FREQ_GREEN from xp_study_maps so the interactive
# map and the static matplotlib maps in the same tab read identically.
XP_COLORSCALE: tuple[tuple[float, str], ...] = (
    (0.00, "#4b5563"),
    (0.25, "#9ca3af"),
    (0.55, "#f87171"),
    (0.80, "#ef4444"),
    (1.00, "#b91c1c"),
)
VOLUME_COLORSCALE: tuple[tuple[float, str], ...] = (
    (0.00, "#132033"),
    (0.35, "#166534"),
    (0.70, "#22c55e"),
    (1.00, "#bbf7d0"),
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
    padding: 0.24rem 0.85rem;
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
    grid-template-columns: minmax(300px, 1.5fr) minmax(255px, 1fr);
    gap: 0.75rem;
    align-items: start;
  }
  @media (max-width: 640px) {
    .qmap-body { grid-template-columns: 1fr; }
  }
  #qmap-plot { width: 100%; border-radius: 12px; overflow: hidden; }
  .qmap-panel {
    background: rgba(15,23,42,0.55);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
  }
  .qp-title { display: block; font-size: 0.95rem; font-weight: 800; color: #e2e8f0; margin: 0 0 0.15rem 0; }
  .qp-sub { display: block; color: #94a3b8; font-size: 0.75rem; line-height: 1.4; margin-bottom: 0.55rem; }
  .qp-section-label {
    display: block;
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #93a4bc;
    margin: 0 0 0.35rem 0;
  }
  .qp-dest {
    position: relative;
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 9px;
    padding: 0.34rem 0.5rem 0.38rem 0.5rem;
    margin-bottom: 0.32rem;
    overflow: hidden;
    background: rgba(2,6,23,0.35);
  }
  .qp-dest.is-same { border-color: rgba(56,189,248,0.35); }
  .qp-dest-bar {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    background: rgba(56,189,248,0.10);
    z-index: 0;
  }
  .qp-dest-inner { position: relative; z-index: 1; }
  .qp-dest-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.4rem;
  }
  .qp-dest-name { font-size: 0.79rem; font-weight: 700; color: #e2e8f0; }
  .qp-dest-share { font-size: 0.79rem; font-weight: 800; color: #38bdf8; }
  .qp-dest-meta { color: #94a3b8; font-size: 0.7rem; margin-bottom: 0.18rem; }
  .qp-cell {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.71rem;
    line-height: 1.5;
  }
  .qp-cell-tag {
    flex: 0 0 auto;
    width: 42px;
    color: #94a3b8;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.62rem;
    letter-spacing: 0.04em;
  }
  .qp-dot { flex: 0 0 auto; width: 8px; height: 8px; border-radius: 50%; border: 1px solid rgba(248,250,252,0.3); }
  .qp-dot.is-rare { border-radius: 2px; transform: rotate(45deg); }
  .qp-cell-name {
    flex: 1 1 auto;
    min-width: 0;
    color: #cbd5e1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .qp-cell-val { flex: 0 0 auto; color: #94a3b8; white-space: nowrap; }
  .qp-cell-val b { color: #e2e8f0; font-weight: 700; }
  .qp-hint { color: #94a3b8; font-size: 0.78rem; line-height: 1.5; margin: 0.3rem 0 0 0; }
  .qp-legend {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.5rem;
    padding-top: 0.45rem;
    border-top: 1px dashed rgba(148,163,184,0.18);
    color: #94a3b8;
    font-size: 0.66rem;
  }
  .qp-legend .qp-dot { width: 7px; height: 7px; background: #94a3b8; }
</style>
</head>
<body>
<div class="qmap-wrap">
  <div class="qmap-toolbar">
    <span class="qmap-toolbar-label">Cor do mapa</span>
    <button class="qmap-btn is-active" data-metric="xp">xP médio</button>
    <button class="qmap-btn" data-metric="volume">Volume (%)</button>
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
  var XP_SCALE = __XP_SCALE__;
  var VOL_SCALE = __VOL_SCALE__;
  var QUAD_ORDER = __QUAD_ORDER__;
  var PLOT_HEIGHT = __PLOT_HEIGHT__;

  var FIELD_X = DATA.field_x;
  var FIELD_Y = DATA.field_y;
  var COLS = DATA.dest_cols;
  var ROWS = DATA.dest_rows;
  var CELL_W = FIELD_X / COLS;
  var CELL_H = FIELD_Y / ROWS;
  var SPLIT_X = FIELD_X / 2;
  var SPLIT_Y = FIELD_Y / 2;

  var plotEl = document.getElementById('qmap-plot');
  var panelEl = document.getElementById('qmap-panel');
  var metric = 'xp';
  var activeQuad = null;

  function fmtInt(v) { return Number(v).toLocaleString('pt-BR'); }
  function fmtPct(v) { return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%'; }
  function fmtXp(v) { return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function currentState() {
    return activeQuad ? DATA.origins[activeQuad] : DATA.overall;
  }

  function volumeGrid(state) {
    var total = Math.max(state.passes, 1);
    return state.count_grid.map(function (row) {
      return row.map(function (v) { return v > 0 ? (v / total) * 100 : null; });
    });
  }

  // Fixed scales across hover states keep colours comparable between quadrants.
  function scaleMax(kind) {
    var states = [DATA.overall].concat(QUAD_ORDER.map(function (k) { return DATA.origins[k]; }));
    var best = 0;
    states.forEach(function (s) {
      if (!s || !s.passes) return;
      var grid = kind === 'xp' ? s.xp_grid : volumeGrid(s);
      grid.forEach(function (row) {
        row.forEach(function (v) { if (v !== null && v > best) best = v; });
      });
    });
    return best || 1;
  }
  var XP_MAX = scaleMax('xp');
  var VOL_MAX = scaleMax('volume');

  function stopsToScale(stops) { return stops.map(function (s) { return [s[0], s[1]]; }); }

  function colorAt(stops, t) {
    t = Math.max(0, Math.min(1, t));
    var lo = stops[0], hi = stops[stops.length - 1];
    for (var i = 0; i < stops.length - 1; i++) {
      if (t >= stops[i][0] && t <= stops[i + 1][0]) { lo = stops[i]; hi = stops[i + 1]; break; }
    }
    var span = (hi[0] - lo[0]) || 1;
    var k = (t - lo[0]) / span;
    function rgb(hex) {
      var h = hex.replace('#', '');
      return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
    }
    var a = rgb(lo[1]), b = rgb(hi[1]);
    return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * k) + ','
      + Math.round(a[1] + (b[1] - a[1]) * k) + ','
      + Math.round(a[2] + (b[2] - a[2]) * k) + ')';
  }

  function xpDot(value) { return colorAt(XP_SCALE, value / XP_MAX); }

  function cellCenters(n, size) {
    var out = [];
    for (var i = 0; i < n; i++) out.push((i + 0.5) * size);
    return out;
  }

  function quadrantAt(x, y) {
    if (x < SPLIT_X) return y < SPLIT_Y ? 'def_left' : 'def_right';
    return y < SPLIT_Y ? 'att_left' : 'att_right';
  }

  function pitchShapes() {
    var line = 'rgba(248,250,252,0.72)';
    var mk = function (x0, y0, x1, y1) {
      return { type: 'rect', x0: x0, y0: y0, x1: x1, y1: y1, line: { color: line, width: 1.1 }, layer: 'above' };
    };
    var shapes = [
      mk(0, 0, FIELD_X, FIELD_Y),
      mk(0, 18, 18, 62),
      mk(FIELD_X - 18, 18, FIELD_X, 62),
      mk(0, 30, 6, 50),
      mk(FIELD_X - 6, 30, FIELD_X, 50),
      { type: 'line', x0: SPLIT_X, y0: 0, x1: SPLIT_X, y1: FIELD_Y, line: { color: line, width: 1.1 }, layer: 'above' },
      { type: 'circle', x0: SPLIT_X - 10, y0: SPLIT_Y - 10, x1: SPLIT_X + 10, y1: SPLIT_Y + 10, line: { color: line, width: 1.1 }, layer: 'above' }
    ];

    // Outline the origin quadrant only: the other quadrants still carry the
    // destination data we want readable, so they must not be dimmed.
    if (activeQuad) {
      var ob = DATA.origins[activeQuad].bounds;
      shapes.push({
        type: 'rect', x0: ob[0], y0: ob[1], x1: ob[2], y1: ob[3],
        line: { color: 'rgba(56,189,248,0.95)', width: 2.4 },
        fillcolor: 'rgba(0,0,0,0)', layer: 'above'
      });
    }

    shapes.push({ type: 'line', x0: SPLIT_X, y0: 0, x1: SPLIT_X, y1: FIELD_Y, line: { color: 'rgba(203,213,225,0.55)', width: 1.5, dash: 'dot' }, layer: 'above' });
    shapes.push({ type: 'line', x0: 0, y0: SPLIT_Y, x1: FIELD_X, y1: SPLIT_Y, line: { color: 'rgba(203,213,225,0.55)', width: 1.5, dash: 'dot' }, layer: 'above' });
    return shapes;
  }

  function heatmapTrace(state) {
    var isXp = metric === 'xp';
    var grid = isXp ? state.xp_grid : volumeGrid(state);
    var counts = state.count_grid;
    var text = grid.map(function (row, r) {
      return row.map(function (v, c) {
        if (v === null) return 'Sem passes registrados';
        var x = (c + 0.5) * CELL_W, y = (r + 0.5) * CELL_H;
        return '<b>' + DATA.zone_labels[r][c] + '</b><br>'
          + fmtInt(counts[r][c]) + ' passes · ' + fmtPct((counts[r][c] / Math.max(state.passes, 1)) * 100) + '<br>'
          + 'xP médio ' + fmtXp(state.xp_grid[r][c] === null ? 0 : state.xp_grid[r][c]) + '<br>'
          + '<i>' + DATA.quadrant_labels[quadrantAt(x, y)] + '</i>';
      });
    });
    return {
      type: 'heatmap',
      x: cellCenters(COLS, CELL_W),
      y: cellCenters(ROWS, CELL_H),
      z: grid,
      text: text,
      hoverinfo: 'text',
      colorscale: stopsToScale(isXp ? XP_SCALE : VOL_SCALE),
      zmin: 0,
      zmax: isXp ? XP_MAX : VOL_MAX,
      xgap: 1,
      ygap: 1,
      showscale: true,
      colorbar: {
        title: { text: isXp ? 'xP médio' : '% dos passes', side: 'right', font: { size: 10, color: '#94a3b8' } },
        thickness: 10,
        len: 0.82,
        outlinewidth: 0,
        tickfont: { size: 9, color: '#94a3b8' },
        tickformat: isXp ? '.2f' : '.1f'
      },
      hoverongaps: false
    };
  }

  function extremeMarkersTrace(state) {
    var xs = [], ys = [], syms = [], cols = [], txt = [];
    QUAD_ORDER.forEach(function (dk) {
      var d = state.destinations[dk];
      if (!d || !d.passes) return;
      [['common', 'circle', 'mais comum'], ['rare', 'diamond', 'mais raro']].forEach(function (spec) {
        var cell = d[spec[0]];
        if (!cell) return;
        xs.push(cell.x); ys.push(cell.y); syms.push(spec[1]);
        cols.push(xpDot(cell.mean_xp));
        txt.push('<b>' + d.label + ' · ' + spec[2] + '</b><br>' + cell.label + '<br>'
          + fmtInt(cell.count) + ' passes · xP médio ' + fmtXp(cell.mean_xp));
      });
    });
    return {
      type: 'scatter',
      mode: 'markers',
      x: xs, y: ys,
      marker: { size: 11, symbol: syms, color: cols, line: { color: '#f8fafc', width: 1.4 } },
      hoverinfo: 'text',
      text: txt,
      showlegend: false
    };
  }

  function layout(state) {
    var annotations = QUAD_ORDER.map(function (key) {
      var b = DATA.origins[key].bounds;
      var pad = (b[3] - b[1]) * 0.075;
      return {
        x: (b[0] + b[2]) / 2,
        y: key.indexOf('left') >= 0 ? b[1] + pad : b[3] - pad,
        xref: 'x', yref: 'y',
        text: DATA.quadrant_labels[key].toUpperCase(),
        showarrow: false,
        font: { size: 9, color: activeQuad === key ? '#bae6fd' : '#cbd5e1' },
        bgcolor: 'rgba(15,23,42,0.72)',
        borderpad: 3,
        opacity: activeQuad && activeQuad !== key ? 0.5 : 1
      };
    });
    return {
      height: PLOT_HEIGHT,
      margin: { l: 6, r: 6, t: 6, b: 6 },
      paper_bgcolor: '#0f172a',
      plot_bgcolor: '#0d1526',
      shapes: pitchShapes(),
      annotations: annotations,
      hovermode: 'closest',
      hoverlabel: { bgcolor: '#111827', bordercolor: '#334155', font: { color: '#f8fafc', size: 11 } },
      dragmode: false,
      xaxis: { range: [-2, FIELD_X + 2], visible: false, fixedrange: true, constrain: 'domain' },
      // y reversed so the pitch matches the mplsoccer StatsBomb maps in the same tab.
      yaxis: { range: [FIELD_Y + 2, -2], visible: false, fixedrange: true, scaleanchor: 'x', scaleratio: 1, constrain: 'domain' }
    };
  }

  function traces(state) {
    var out = [heatmapTrace(state)];
    if (activeQuad) out.push(extremeMarkersTrace(state));
    return out;
  }

  function cellRow(tag, cell, isRare) {
    if (!cell) return '';
    return '<div class="qp-cell">'
      + '<span class="qp-cell-tag">' + tag + '</span>'
      + '<span class="qp-dot' + (isRare ? ' is-rare' : '') + '" style="background:' + xpDot(cell.mean_xp) + '"></span>'
      + '<span class="qp-cell-name" title="' + cell.label + '">' + cell.label + '</span>'
      + '<span class="qp-cell-val">' + fmtInt(cell.count) + ' · xP <b>' + fmtXp(cell.mean_xp) + '</b></span>'
      + '</div>';
  }

  function destBlocks(state) {
    var items = QUAD_ORDER.map(function (k) { return state.destinations[k]; })
      .filter(function (d) { return d && d.passes > 0; })
      .sort(function (a, b) { return b.share_pct - a.share_pct; });
    if (!items.length) return '<p class="qp-hint">Sem passes registrados.</p>';
    return items.map(function (d) {
      return '<div class="qp-dest' + (d.is_same ? ' is-same' : '') + '">'
        + '<div class="qp-dest-bar" style="width:' + Math.max(d.share_pct, 1.5) + '%"></div>'
        + '<div class="qp-dest-inner">'
        + '<div class="qp-dest-head"><span class="qp-dest-name">' + d.label
        + (d.is_same ? ' · mesmo quadrante' : '') + '</span>'
        + '<span class="qp-dest-share">' + fmtPct(d.share_pct) + '</span></div>'
        + '<div class="qp-dest-meta">' + fmtInt(d.passes) + ' passes · xP médio ' + fmtXp(d.mean_xp) + '</div>'
        + cellRow('comum', d.common, false)
        + cellRow('raro', d.rare, true)
        + '</div></div>';
    }).join('');
  }

  function renderPanel(state) {
    var head, sub, label;
    if (activeQuad) {
      head = state.label;
      sub = fmtInt(state.passes) + ' passes saindo daqui · ' + fmtPct(state.share_pct)
        + ' do total · xP médio ' + fmtXp(state.mean_xp);
      label = 'Para onde vão esses passes';
    } else {
      head = 'Visão geral';
      sub = fmtInt(state.passes) + ' passes de meio-campistas. Passe o mouse por um quadrante '
        + 'para comparar para onde saem os passes dele.';
      label = 'Destino de todos os passes';
    }
    panelEl.innerHTML = '<span class="qp-title">' + head + '</span>'
      + '<span class="qp-sub">' + sub + '</span>'
      + '<span class="qp-section-label">' + label + '</span>'
      + destBlocks(state)
      + '<div class="qp-legend"><span class="qp-dot"></span><span>comum (volume)</span>'
      + '<span class="qp-dot is-rare"></span><span>raro (xP alto)</span></div>';
  }

  function draw() {
    var state = currentState();
    Plotly.react(plotEl, traces(state), layout(state), { displayModeBar: false, responsive: true });
    renderPanel(state);
  }

  Plotly.newPlot(plotEl, traces(currentState()), layout(currentState()),
    { displayModeBar: false, responsive: true }).then(function () {
    renderPanel(currentState());
    plotEl.on('plotly_hover', function (ev) {
      var pt = ev.points && ev.points[0];
      if (!pt || typeof pt.x !== 'number' || typeof pt.y !== 'number') return;
      var key = quadrantAt(pt.x, pt.y);
      // Geometry never moves, so re-hovering the same quadrant cannot loop.
      if (key === activeQuad || !DATA.origins[key] || !DATA.origins[key].passes) return;
      activeQuad = key;
      draw();
    });
  });

  document.querySelectorAll('.qmap-btn[data-metric]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.qmap-btn[data-metric]').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      metric = btn.getAttribute('data-metric');
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


def build_quadrant_map_html(
    analysis: dict,
    *,
    quadrant_labels: dict[str, str],
    zone_labels: list[list[str]],
    plot_height: int = 470,
) -> str:
    """Self-contained Plotly page: hover a quadrant to compare where its passes go."""
    origins = analysis.get("origins") or {}
    payload = {
        "origins": origins,
        "overall": analysis.get("overall"),
        "total_passes": analysis.get("total_passes", 0),
        "dest_cols": analysis.get("dest_cols", 12),
        "dest_rows": analysis.get("dest_rows", 8),
        "field_x": analysis.get("field_x", 120.0),
        "field_y": analysis.get("field_y", 80.0),
        "xp_max": analysis.get("xp_max", 1.0),
        "quadrant_labels": quadrant_labels,
        "zone_labels": zone_labels,
    }
    return (
        _TEMPLATE
        .replace("__PLOTLY_CDN__", PLOTLY_CDN)
        .replace("__DATA__", json.dumps(payload))
        .replace("__XP_SCALE__", json.dumps([[s, c] for s, c in XP_COLORSCALE]))
        .replace("__VOL_SCALE__", json.dumps([[s, c] for s, c in VOLUME_COLORSCALE]))
        .replace("__QUAD_ORDER__", json.dumps(list(origins.keys())))
        .replace("__PLOT_HEIGHT__", str(int(plot_height)))
    )
