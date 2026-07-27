"""Interactive 12x8 cell heatmap: hover a cell to see where its passes end up."""

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
  .qmap-toolbar-sep { flex: 0 0 auto; width: 1px; height: 18px; background: rgba(148,163,184,0.22); margin: 0 0.3rem; }
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
    grid-template-columns: minmax(300px, 1.55fr) minmax(250px, 1fr);
    gap: 0.75rem;
    align-items: start;
  }
  @media (max-width: 640px) {
    .qmap-body { grid-template-columns: 1fr; }
  }
  #qmap-plot { width: 100%; border-radius: 12px; overflow: hidden; }
  /* Fixed height with inner scroll: the panel grows when a cell is selected and a
     reflow here would resize the plot underneath the pointer mid-hover. */
  .qmap-panel {
    background: rgba(15,23,42,0.55);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
    height: __PLOT_HEIGHT__px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(148,163,184,0.35) transparent;
  }
  .qmap-panel::-webkit-scrollbar { width: 6px; }
  .qmap-panel::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.35); border-radius: 3px; }
  .qp-title { display: block; font-size: 0.95rem; font-weight: 800; color: #e2e8f0; margin: 0 0 0.15rem 0; }
  .qp-sub { display: block; color: #94a3b8; font-size: 0.75rem; line-height: 1.4; margin-bottom: 0.55rem; }
  .qp-pin {
    display: inline-block;
    margin-left: 0.35rem;
    padding: 0.05rem 0.4rem;
    border-radius: 999px;
    background: rgba(56,189,248,0.18);
    border: 1px solid rgba(56,189,248,0.45);
    color: #bae6fd;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    vertical-align: middle;
  }
  .qp-warn {
    display: block;
    margin-bottom: 0.5rem;
    padding: 0.3rem 0.45rem;
    border-radius: 7px;
    background: rgba(245,158,11,0.12);
    border: 1px solid rgba(245,158,11,0.35);
    color: #fcd34d;
    font-size: 0.7rem;
    line-height: 1.35;
  }
  .qp-section-label {
    display: block;
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #93a4bc;
    margin: 0.55rem 0 0.35rem 0;
  }
  .qp-section-label:first-of-type { margin-top: 0; }
  .qp-row {
    position: relative;
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 8px;
    padding: 0.26rem 0.45rem 0.28rem 0.45rem;
    margin-bottom: 0.26rem;
    overflow: hidden;
    background: rgba(2,6,23,0.35);
  }
  .qp-row.is-self { border-color: rgba(56,189,248,0.35); }
  .qp-row-bar {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    background: rgba(56,189,248,0.10);
    z-index: 0;
  }
  .qp-row.is-rare .qp-row-bar { background: rgba(239,68,68,0.12); }
  .qp-row-inner {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  .qp-dot { flex: 0 0 auto; width: 8px; height: 8px; border-radius: 50%; border: 1px solid rgba(248,250,252,0.3); }
  .qp-dot.is-rare { border-radius: 2px; transform: rotate(45deg); }
  .qp-row-name {
    flex: 1 1 auto;
    min-width: 0;
    font-size: 0.74rem;
    font-weight: 700;
    color: #e2e8f0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .qp-row-val { flex: 0 0 auto; font-size: 0.71rem; color: #94a3b8; white-space: nowrap; }
  .qp-row-val b { color: #e2e8f0; font-weight: 800; }
  .qp-quads { display: flex; gap: 0.25rem; margin-top: 0.1rem; }
  .qp-quad {
    flex: 1 1 0;
    min-width: 0;
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 7px;
    padding: 0.24rem 0.3rem;
    background: rgba(2,6,23,0.35);
    text-align: center;
  }
  .qp-quad-name {
    display: block;
    font-size: 0.58rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #93a4bc;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .qp-quad-val { display: block; font-size: 0.82rem; font-weight: 800; color: #38bdf8; }
  .qp-hint { color: #94a3b8; font-size: 0.76rem; line-height: 1.5; margin: 0.3rem 0 0 0; }
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
    <span class="qmap-toolbar-label">Cor</span>
    <button class="qmap-btn is-active" data-metric="xp">xP médio</button>
    <button class="qmap-btn" data-metric="volume">Volume (%)</button>
    <span class="qmap-toolbar-sep"></span>
    <span class="qmap-toolbar-label">Escala</span>
    <button class="qmap-btn is-active" data-scale="fixed">Fixa</button>
    <button class="qmap-btn" data-scale="relative">Relativa</button>
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
  var PLOT_HEIGHT = __PLOT_HEIGHT__;

  var FIELD_X = DATA.field_x;
  var FIELD_Y = DATA.field_y;
  var COLS = DATA.cols;
  var ROWS = DATA.rows;
  var NCELLS = COLS * ROWS;
  var CELL_W = FIELD_X / COLS;
  var CELL_H = FIELD_Y / ROWS;
  var SPLIT_X = FIELD_X / 2;
  var SPLIT_Y = FIELD_Y / 2;
  var TOP_LIST = 5;

  var plotEl = document.getElementById('qmap-plot');
  var panelEl = document.getElementById('qmap-panel');
  var metric = 'xp';
  var scaleMode = 'fixed';
  var activeCell = null;
  var pinnedCell = null;
  var pendingFrame = null;

  function fmtInt(v) { return Number(v).toLocaleString('pt-BR'); }
  function fmtPct(v) { return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%'; }
  function fmtXp(v) { return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function currentState() {
    if (activeCell !== null && DATA.origins[activeCell]) return DATA.origins[activeCell];
    return DATA.overall;
  }

  function volumeValues(state) {
    var total = Math.max(state.passes, 1);
    return state.counts.map(function (v) { return v > 0 ? (v / total) * 100 : null; });
  }

  function stateValues(state) {
    return metric === 'xp' ? state.xp : volumeValues(state);
  }

  function toGrid(flat) {
    var out = [];
    for (var r = 0; r < ROWS; r++) out.push(flat.slice(r * COLS, (r + 1) * COLS));
    return out;
  }

  // Fixed scales come from the aggregation (99th/98th percentile) so hovering
  // different cells keeps colours comparable; relative rescales per cell.
  function scaleMax(state) {
    if (scaleMode === 'fixed') {
      return metric === 'xp' ? DATA.xp_scale_max : DATA.volume_scale_max;
    }
    var best = 0;
    stateValues(state).forEach(function (v) { if (v !== null && v > best) best = v; });
    return best || 1;
  }

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

  function xpDot(value) { return colorAt(XP_SCALE, value / DATA.xp_scale_max); }

  function cellCenters(n, size) {
    var out = [];
    for (var i = 0; i < n; i++) out.push((i + 0.5) * size);
    return out;
  }

  function cellIndexAt(x, y) {
    var c = Math.max(0, Math.min(COLS - 1, Math.floor(x / CELL_W)));
    var r = Math.max(0, Math.min(ROWS - 1, Math.floor(y / CELL_H)));
    return r * COLS + c;
  }

  function cellBounds(idx) {
    var c = idx % COLS, r = Math.floor(idx / COLS);
    return [c * CELL_W, r * CELL_H, (c + 1) * CELL_W, (r + 1) * CELL_H];
  }

  function cellCenter(idx) {
    var c = idx % COLS, r = Math.floor(idx / COLS);
    return [(c + 0.5) * CELL_W, (r + 0.5) * CELL_H];
  }

  function quadrantKeyAt(idx) {
    var p = cellCenter(idx);
    if (p[0] < SPLIT_X) return p[1] < SPLIT_Y ? 'def_left' : 'def_right';
    return p[1] < SPLIT_Y ? 'att_left' : 'att_right';
  }

  // Rare cells need a sample floor, but a single origin cell has far fewer
  // passes than the whole pitch, so the floor scales with the state.
  function rareMinCount(state) {
    return Math.max(3, Math.min(DATA.min_cell_passes, Math.round(state.passes / 40)));
  }

  function topDestinations(state) {
    var total = Math.max(state.passes, 1);
    var items = [];
    for (var i = 0; i < NCELLS; i++) {
      if (!state.counts[i]) continue;
      items.push({
        index: i,
        count: state.counts[i],
        share: (state.counts[i] / total) * 100,
        xp: state.xp[i] === null ? 0 : state.xp[i]
      });
    }
    var common = items.slice().sort(function (a, b) { return b.count - a.count; }).slice(0, TOP_LIST);
    var floor = rareMinCount(state);
    var eligible = items.filter(function (d) { return d.count >= floor; });
    if (!eligible.length) eligible = items;
    var rare = eligible.slice().sort(function (a, b) { return b.xp - a.xp; }).slice(0, TOP_LIST);
    return { common: common, rare: rare, floor: floor };
  }

  function quadrantSplit(state) {
    var total = Math.max(state.passes, 1);
    var acc = { def_left: 0, def_right: 0, att_left: 0, att_right: 0 };
    for (var i = 0; i < NCELLS; i++) {
      if (!state.counts[i]) continue;
      acc[quadrantKeyAt(i)] += state.counts[i];
    }
    return ['def_left', 'def_right', 'att_left', 'att_right'].map(function (k) {
      return { key: k, label: DATA.quadrant_labels[k], share: (acc[k] / total) * 100, passes: acc[k] };
    });
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

    // Outline the origin cell only: every other cell still carries destination
    // data we want readable, so nothing gets dimmed.
    if (activeCell !== null) {
      var b = cellBounds(activeCell);
      shapes.push({
        type: 'rect', x0: b[0], y0: b[1], x1: b[2], y1: b[3],
        line: { color: 'rgba(56,189,248,0.95)', width: 2.6 },
        fillcolor: 'rgba(0,0,0,0)', layer: 'above'
      });
    }
    return shapes;
  }

  function hoverText(state) {
    var total = Math.max(state.passes, 1);
    var values = stateValues(state);
    var out = [];
    for (var r = 0; r < ROWS; r++) {
      var row = [];
      for (var c = 0; c < COLS; c++) {
        var i = r * COLS + c;
        var origin = DATA.origins[i];
        var originLine;
        if (i === activeCell) {
          originLine = '<i>origem atual · ' + fmtInt(state.passes) + ' passes saem daqui</i>';
        } else if (origin) {
          originLine = '<i>' + fmtInt(origin.passes) + ' passes saem daqui — passe o mouse</i>';
        } else {
          originLine = '<i>amostra insuficiente como origem</i>';
        }
        if (values[i] === null) {
          row.push('<b>' + DATA.cell_labels[i] + '</b><br>Sem passes chegando aqui<br>' + originLine);
          continue;
        }
        row.push('<b>' + DATA.cell_labels[i] + '</b><br>'
          + fmtInt(state.counts[i]) + ' passes · ' + fmtPct((state.counts[i] / total) * 100) + '<br>'
          + 'xP médio ' + fmtXp(state.xp[i] === null ? 0 : state.xp[i]) + '<br>'
          + originLine);
      }
      out.push(row);
    }
    return out;
  }

  function heatmapTrace(state) {
    var isXp = metric === 'xp';
    var zmax = scaleMax(state);
    return {
      type: 'heatmap',
      x: cellCenters(COLS, CELL_W),
      y: cellCenters(ROWS, CELL_H),
      z: toGrid(stateValues(state)),
      text: hoverText(state),
      hoverinfo: 'text',
      colorscale: stopsToScale(isXp ? XP_SCALE : VOL_SCALE),
      zmin: 0,
      zmax: zmax,
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
    var tops = topDestinations(state);
    var xs = [], ys = [], syms = [], cols = [], txt = [];
    var seen = {};
    tops.common.slice(0, 3).forEach(function (d) {
      var p = cellCenter(d.index);
      seen[d.index] = true;
      xs.push(p[0]); ys.push(p[1]); syms.push('circle'); cols.push(xpDot(d.xp));
      txt.push('<b>Destino mais comum</b><br>' + DATA.cell_labels[d.index] + '<br>'
        + fmtInt(d.count) + ' passes · ' + fmtPct(d.share) + ' · xP ' + fmtXp(d.xp));
    });
    tops.rare.slice(0, 3).forEach(function (d) {
      if (seen[d.index]) return;
      var p = cellCenter(d.index);
      xs.push(p[0]); ys.push(p[1]); syms.push('diamond'); cols.push(xpDot(d.xp));
      txt.push('<b>Destino mais raro (xP alto)</b><br>' + DATA.cell_labels[d.index] + '<br>'
        + fmtInt(d.count) + ' passes · ' + fmtPct(d.share) + ' · xP ' + fmtXp(d.xp));
    });
    // Purely decorative: hover must always resolve to the heatmap cell under the
    // pointer, so the markers never intercept it.
    return {
      type: 'scatter',
      mode: 'markers',
      x: xs, y: ys,
      marker: { size: 10, symbol: syms, color: cols, line: { color: '#f8fafc', width: 1.4 } },
      hoverinfo: 'skip',
      text: txt,
      showlegend: false
    };
  }

  function layout() {
    return {
      height: PLOT_HEIGHT,
      margin: { l: 6, r: 6, t: 6, b: 6 },
      paper_bgcolor: '#0f172a',
      plot_bgcolor: '#0d1526',
      shapes: pitchShapes(),
      hovermode: 'closest',
      hoverlabel: { bgcolor: '#111827', bordercolor: '#334155', font: { color: '#f8fafc', size: 11 } },
      dragmode: false,
      xaxis: { range: [-2, FIELD_X + 2], visible: false, fixedrange: true, constrain: 'domain' },
      // y reversed so the pitch matches the mplsoccer StatsBomb maps in the same tab.
      yaxis: { range: [FIELD_Y + 2, -2], visible: false, fixedrange: true, scaleanchor: 'x', scaleratio: 1, constrain: 'domain' }
    };
  }

  function traces(state) {
    return [heatmapTrace(state), extremeMarkersTrace(state)];
  }

  function destRow(d, isRare, state) {
    var isSelf = activeCell !== null && d.index === activeCell;
    return '<div class="qp-row' + (isRare ? ' is-rare' : '') + (isSelf ? ' is-self' : '') + '">'
      + '<div class="qp-row-bar" style="width:' + Math.max(Math.min(d.share, 100), 1.5) + '%"></div>'
      + '<div class="qp-row-inner">'
      + '<span class="qp-dot' + (isRare ? ' is-rare' : '') + '" style="background:' + xpDot(d.xp) + '"></span>'
      + '<span class="qp-row-name" title="' + DATA.cell_labels[d.index] + '">' + DATA.cell_labels[d.index]
      + (isSelf ? ' · mesma célula' : '') + '</span>'
      + '<span class="qp-row-val">' + fmtPct(d.share) + ' · ' + fmtInt(d.count)
      + ' · xP <b>' + fmtXp(d.xp) + '</b></span>'
      + '</div></div>';
  }

  function quadBlocks(state) {
    return '<div class="qp-quads">' + quadrantSplit(state).map(function (q) {
      return '<div class="qp-quad">'
        + '<span class="qp-quad-name" title="' + q.label + '">' + q.label.replace(' · ', '<br>') + '</span>'
        + '<span class="qp-quad-val">' + fmtPct(q.share) + '</span>'
        + '</div>';
    }).join('') + '</div>';
  }

  function renderPanel(state) {
    var tops = topDestinations(state);
    var head, sub, warn = '';
    if (activeCell !== null) {
      head = state.label;
      sub = fmtInt(state.passes) + ' passes saindo daqui · ' + fmtPct(state.share_pct)
        + ' do total · xP médio ' + fmtXp(state.mean_xp);
      if (pinnedCell !== null) head += '<span class="qp-pin">fixado</span>';
      if (state.passes < 150) {
        warn = '<span class="qp-warn">Amostra pequena para esta célula — leia os destinos com cautela.</span>';
      }
    } else {
      head = 'Visão geral';
      sub = fmtInt(state.passes) + ' passes de meio-campistas. Passe o mouse por qualquer célula '
        + 'do grid ' + COLS + '×' + ROWS + ' para ver para onde vão os passes que saem dela. '
        + 'Clique para fixar.';
    }
    panelEl.innerHTML = '<span class="qp-title">' + head + '</span>'
      + '<span class="qp-sub">' + sub + '</span>'
      + warn
      + '<span class="qp-section-label">Distribuição por quadrante</span>'
      + quadBlocks(state)
      + '<span class="qp-section-label">Destinos mais comuns</span>'
      + (tops.common.length
        ? tops.common.map(function (d) { return destRow(d, false, state); }).join('')
        : '<p class="qp-hint">Sem passes registrados.</p>')
      + '<span class="qp-section-label">Destinos mais raros (xP alto)</span>'
      + (tops.rare.length
        ? tops.rare.map(function (d) { return destRow(d, true, state); }).join('')
        : '<p class="qp-hint">Amostra insuficiente.</p>')
      + '<div class="qp-legend"><span class="qp-dot"></span><span>comum (volume)</span>'
      + '<span class="qp-dot is-rare"></span><span>raro (xP alto, mín. '
      + fmtInt(tops.floor) + ' passes) · os 3 primeiros de cada lista aparecem no mapa</span></div>';
  }

  function draw() {
    var state = currentState();
    Plotly.react(plotEl, traces(state), layout(), { displayModeBar: false, responsive: true });
    renderPanel(state);
  }

  // Hover fires for every cell crossed by the pointer; coalescing into one frame
  // keeps the 96-cell grid responsive instead of queueing a redraw per event.
  function scheduleDraw() {
    if (pendingFrame) return;
    pendingFrame = requestAnimationFrame(function () {
      pendingFrame = null;
      draw();
    });
  }

  function setActive(idx) {
    if (idx === activeCell) return;
    if (idx !== null && !DATA.origins[idx]) return;
    activeCell = idx;
    scheduleDraw();
  }

  Plotly.newPlot(plotEl, traces(currentState()), layout(),
    { displayModeBar: false, responsive: true }).then(function () {
    renderPanel(currentState());
    plotEl.on('plotly_hover', function (ev) {
      if (pinnedCell !== null) return;
      var pt = ev.points && ev.points[0];
      if (!pt || typeof pt.x !== 'number' || typeof pt.y !== 'number') return;
      setActive(cellIndexAt(pt.x, pt.y));
    });
    plotEl.on('plotly_click', function (ev) {
      var pt = ev.points && ev.points[0];
      if (!pt || typeof pt.x !== 'number' || typeof pt.y !== 'number') return;
      var idx = cellIndexAt(pt.x, pt.y);
      if (!DATA.origins[idx]) return;
      pinnedCell = pinnedCell === idx ? null : idx;
      activeCell = idx;
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

  document.querySelectorAll('.qmap-btn[data-scale]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.qmap-btn[data-scale]').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      scaleMode = btn.getAttribute('data-scale');
      draw();
    });
  });

  document.getElementById('qmap-reset').addEventListener('click', function () {
    activeCell = null;
    pinnedCell = null;
    draw();
  });
})();
</script>
</body>
</html>
"""


def build_cell_map_html(
    analysis: dict,
    *,
    plot_height: int = 500,
) -> str:
    """Self-contained Plotly page: hover a 12x8 cell to see where its passes go."""
    payload = {
        "origins": analysis.get("origins") or {},
        "overall": analysis.get("overall"),
        "total_passes": analysis.get("total_passes", 0),
        "cols": analysis.get("cols", 12),
        "rows": analysis.get("rows", 8),
        "field_x": analysis.get("field_x", 120.0),
        "field_y": analysis.get("field_y", 80.0),
        "min_cell_passes": analysis.get("min_cell_passes", 20),
        "min_origin_passes": analysis.get("min_origin_passes", 25),
        "xp_scale_max": analysis.get("xp_scale_max", 1.0),
        "volume_scale_max": analysis.get("volume_scale_max", 1.0),
        "cell_labels": analysis.get("cell_labels") or [],
        "quadrant_labels": analysis.get("quadrant_labels") or {},
    }
    return (
        _TEMPLATE
        .replace("__PLOTLY_CDN__", PLOTLY_CDN)
        .replace("__DATA__", json.dumps(payload))
        .replace("__XP_SCALE__", json.dumps([[s, c] for s, c in XP_COLORSCALE]))
        .replace("__VOL_SCALE__", json.dumps([[s, c] for s, c in VOLUME_COLORSCALE]))
        .replace("__PLOT_HEIGHT__", str(int(plot_height)))
    )


# Backward-compatible alias for older imports / hot-reload caches.
build_quadrant_map_html = build_cell_map_html
