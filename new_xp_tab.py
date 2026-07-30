"""Streamlit UI for the New xP preview tab (xPV vs completion xP)."""

from __future__ import annotations

import html

import streamlit as st

import xpass_engine as xpass

XPASS_DATA_CACHE_VERSION = 1

_NEW_XP_LEADERBOARDS: tuple[tuple[str, str, str, str], ...] = (
    (
        "xpass_coe_pct",
        "Completion Over Expected (COE)",
        "Melhor execução vs. dificuldade média dos passes tentados (% acerto − % esperado).",
        "fa-bullseye",
    ),
    (
        "xpass_residual_p90",
        "Residual de execução /90",
        "Soma de (acerto − probabilidade) por passe, normalizada por 90 min.",
        "fa-arrow-trend-up",
    ),
    (
        "xpass_hard_coe_pct",
        "COE em passes difíceis",
        "Overperformance em tentativas com xP < 65% (passes de alto risco geométrico).",
        "fa-fire",
    ),
    (
        "xpv_per_pass",
        "xPV por passe (valor)",
        "Valor médio do destino (raridade OD) — a métrica clássica do app, renomeada xPV.",
        "fa-gem",
    ),
)


@st.cache_data(show_spinner=False)
def load_new_xp_player_bundle(_cache: int = XPASS_DATA_CACHE_VERSION) -> dict:
    return xpass.load_xpass_player_bundle()


def _new_xp_player_card_html(player: dict, metric: str, rank: int) -> str:
    name = html.escape(str(player.get("player_name", "—")))
    team = html.escape(str(player.get("team", "—")))
    league = html.escape(str(player.get("league", "—")))
    val = player.get(metric)
    val_txt = f"{float(val):+.2f}" if str(metric).endswith("_pct") else f"{float(val):.3f}"
    if metric == "xpv_per_pass":
        val_txt = f"{float(val):.4f}"
    acerto = float(player.get("pass_completion_pct") or 0)
    esperado = float(player.get("xpass_expected_pct") or 0)
    mins = int(player.get("minutes") or 0)
    attempts = int(player.get("pass_attempts") or 0)
    return (
        f'<div class="nxp-card">'
        f'<div class="nxp-rank">#{rank}</div>'
        f'<div class="nxp-body">'
        f'<div class="nxp-name">{name}</div>'
        f'<div class="nxp-meta">{team} · {league}</div>'
        f'<div class="nxp-val">{val_txt}</div>'
        f'<div class="nxp-sub">'
        f"{acerto:.1f}% acerto · {esperado:.1f}% xP esperado · "
        f"{attempts:,} tentativas · {mins:,} min"
        f"</div></div></div>"
    )


def _new_xp_leaderboard_html(
    players: list[dict],
    metric: str,
    title: str,
    blurb: str,
    icon: str,
) -> str:
    eligible = [p for p in players if p.get(metric) is not None]
    eligible.sort(key=lambda p: float(p[metric]), reverse=True)
    top = eligible[:8]
    cards = "".join(_new_xp_player_card_html(p, metric, i) for i, p in enumerate(top, start=1))
    return (
        f'<section class="nxp-board">'
        f'<div class="nxp-board-head">'
        f'<span class="nxp-board-ic"><i class="fa-solid {icon}"></i></span>'
        f'<div><div class="nxp-board-title">{html.escape(title)}</div>'
        f'<div class="nxp-board-blurb">{html.escape(blurb)}</div></div></div>'
        f'<div class="nxp-card-grid">{cards}</div></section>'
    )


def render_new_xp_tab() -> None:
    st.markdown(
        """
<style>
.nxp-shell{max-width:1180px;margin:0 auto 1.5rem;}
.nxp-hero{background:linear-gradient(135deg,#0f172a 0%,#1e293b 55%,#0f2744 100%);
  border:1px solid #334155;border-radius:14px;padding:1.25rem 1.4rem;margin-bottom:1.1rem;}
.nxp-hero h3{margin:0 0 .45rem;color:#f8fafc;font-size:1.15rem;}
.nxp-hero p{margin:.35rem 0;color:#94a3b8;font-size:.9rem;line-height:1.55;}
.nxp-pillrow{display:flex;flex-wrap:wrap;gap:.55rem;margin-top:.75rem;}
.nxp-pill{background:#1e293b;border:1px solid #475569;border-radius:999px;padding:.28rem .7rem;
  font-size:.78rem;color:#e2e8f0;}
.nxp-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.65rem;margin:.9rem 0 1.1rem;}
.nxp-metric{background:#111827;border:1px solid #374151;border-radius:10px;padding:.65rem .75rem;}
.nxp-metric-k{font-size:.72rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em;}
.nxp-metric-v{font-size:1.05rem;color:#f9fafb;font-weight:600;margin-top:.15rem;}
.nxp-board{background:#0b1220;border:1px solid #1f2937;border-radius:12px;padding:1rem;margin-bottom:1rem;}
.nxp-board-head{display:flex;gap:.75rem;align-items:flex-start;margin-bottom:.85rem;}
.nxp-board-ic{width:34px;height:34px;border-radius:8px;background:#172554;color:#93c5fd;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.nxp-board-title{color:#f1f5f9;font-weight:600;font-size:.98rem;}
.nxp-board-blurb{color:#94a3b8;font-size:.82rem;line-height:1.45;margin-top:.15rem;}
.nxp-card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.55rem;}
.nxp-card{display:flex;gap:.65rem;background:#111827;border:1px solid #253041;border-radius:10px;padding:.65rem .7rem;}
.nxp-rank{font-size:.78rem;color:#64748b;font-weight:700;min-width:1.6rem;padding-top:.15rem;}
.nxp-name{color:#f8fafc;font-weight:600;font-size:.9rem;}
.nxp-meta{color:#64748b;font-size:.75rem;margin-top:.1rem;}
.nxp-val{color:#34d399;font-weight:700;font-size:1rem;margin-top:.25rem;}
.nxp-sub{color:#94a3b8;font-size:.72rem;margin-top:.2rem;line-height:1.35;}
</style>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("New xP — valor (xPV) vs. conclusão (xP)")
    bundle = load_new_xp_player_bundle()
    meta = bundle.get("meta") or {}
    players = bundle.get("players") or []
    if not players:
        st.warning(
            "Métricas xP ainda não foram geradas. Rode offline: "
            "`python scripts/build_xpass_european.py`"
        )
        return

    cv = meta.get("cv_match_metrics") or {}
    full = meta.get("full_sample_metrics") or {}
    st.markdown(
        '<div class="nxp-shell"><div class="nxp-hero">'
        "<h3>Duas métricas complementares</h3>"
        "<p><strong>xPV</strong> (Expected Pass <em>Value</em>) — o que o app já media: "
        "<em>quanto vale chegar naquele destino</em> (raridade OD × progresso × acessibilidade). "
        "Só passes completos.</p>"
        "<p><strong>xP</strong> (Expected Pass <em>completion</em>) — análogo ao xG: "
        "<em>probabilidade de completar</em> o passe dado origem, destino, distância e geometria. "
        "Treinado em passes certos e errados.</p>"
        '<div class="nxp-pillrow">'
        '<span class="nxp-pill">Logística L2 · grid 12×8 O/D</span>'
        '<span class="nxp-pill">CV por partida (5 folds)</span>'
        f'<span class="nxp-pill">{len(players)} meio-campistas elegíveis</span>'
        f'<span class="nxp-pill">v {html.escape(str(meta.get("version", "—")))}</span>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="nxp-metrics">'
        f'<div class="nxp-metric"><div class="nxp-metric-k">Brier (CV)</div>'
        f'<div class="nxp-metric-v">{float(cv.get("brier_score", 0)):.3f}</div></div>'
        f'<div class="nxp-metric"><div class="nxp-metric-k">ROC-AUC (CV)</div>'
        f'<div class="nxp-metric-v">{float(cv.get("roc_auc", 0)):.3f}</div></div>'
        f'<div class="nxp-metric"><div class="nxp-metric-k">% acerto real</div>'
        f'<div class="nxp-metric-v">{float(full.get("completion_rate", 0))*100:.1f}%</div></div>'
        f'<div class="nxp-metric"><div class="nxp-metric-k">% xP médio</div>'
        f'<div class="nxp-metric-v">{float(full.get("mean_predicted", 0))*100:.1f}%</div></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Calibração: média prevista ≈ taxa real de acerto. "
        "COE = Completion Over Expected (% acerto − % esperado para os mesmos passes). "
        "Player Profile permanece com a métrica xPV atual — esta aba é um preview isolado."
    )

    boards_html = "".join(
        _new_xp_leaderboard_html(players, metric, title, blurb, icon)
        for metric, title, blurb, icon in _NEW_XP_LEADERBOARDS
    )
    st.markdown(f'<div class="nxp-shell">{boards_html}</div>', unsafe_allow_html=True)

    with st.expander("Como interpretar — exemplos reais do modelo"):
        st.markdown(
            "- **Locatelli / Modrić** aparecem no topo de COE e xPV: escolhem destinos valiosos "
            "e ainda completam acima do esperado geometricamente.\n"
            "- **Kimmich / Vitinha** lideram residual/90: volume alto com execução consistentemente "
            "acima da curva em passes difíceis.\n"
            "- **de Jong / Pavlović** destacam em COE de passes difíceis (xP < 72%).\n"
            "- Um jogador pode ter **xPV alto** (destinos raros) com **COE neutro** — arrisca bem, "
            "mas executa na média; ou **COE alto** com xPV médio — finalizador seguro de passes difíceis."
        )
        st.markdown("**Métricas exportadas por jogador:**")
        st.markdown(
            "| Métrica | Significado |\n"
            "|---|---|\n"
            "| `xpass_expected_pct` | % de acerto esperado para o mix de passes tentados |\n"
            "| `xpass_coe_pct` | Over/under-performance vs. esperado (p.p.) |\n"
            "| `xpass_residual_total` | Σ (acerto − xP) — unidades de passe |\n"
            "| `xpass_residual_p90` | Residual total por 90 min |\n"
            "| `xpass_difficulty_mean` | Média de (1 − xP) — dificuldade do mix |\n"
            "| `xpass_hard_coe_pct` | COE só em passes com xP < 72% |\n"
            "| `xpv_per_pass` | Valor médio do destino (métrica clássica) |"
        )
