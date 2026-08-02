#!/usr/bin/env python3
"""Offline similarity with style/rate metrics + pass-origin heatmap."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import passes_engine as pe
import xp_engine as xe
import midfield_origin as mo
import transfermarkt_profiles as tm
import similarity_engine as sim
from european_similarity_engine import (
    ALT_KEYS,
    ALT_METRICS,
    attach_derived_rates,
    heatmap_similarity,
    knn_similarity,
    metric_snapshot,
)
from passes_engine import compute_pass_ratings

REPORT_PATH = ROOT / "docs" / "player_similarity_alt_metrics.md"
JSON_PATH = ROOT / "docs" / "player_similarity_alt_metrics.json"

SEVEN_PILLAR_KEYS: tuple[str, ...] = (
    "pass_volume_display",
    "pass_efficiency_display",
    "pass_buildup_display",
    "pass_chance_creation_display",
    "xp_activity_display",
    "xp_efficiency_display",
    "xp_edge_display",
)

EXAMPLES: tuple[str, ...] = (
    "Joshua Kimmich",
    "Bruno Fernandes",
    "João Neves",
)


def _load_pool() -> tuple[list[dict], dict[str, pd.DataFrame]]:
    players = pe.build_european_league_midfielders()
    passes_by_player = pe.load_european_league_passes_grouped()
    players = mo.apply_midfield_position_groups(players, passes_by_player, {})
    _, players_by_id, _ = compute_pass_ratings(players)
    _, xp_players = xe.build_european_league_xp_analytics()
    xp_by_id = {str(p["player_id"]): p for p in xp_players}

    merged: list[dict] = []
    for player in players:
        pid = str(player["player_id"])
        xp = xp_by_id.get(pid, {})
        if not xp:
            continue
        row = {**player, **xp}
        row["pass_rating"] = players_by_id.get(pid, {}).get("pass_rating")
        row["market_value_eur"] = tm.read_cached_market_value_eur(pid)
        row["market_value_display"] = tm.read_cached_market_value(pid)
        attach_derived_rates(row)
        merged.append(row)

    eligible = [
        p
        for p in merged
        if p.get("xp_profile_bars_eligible")
        and all(p.get(k) is not None for k in ALT_KEYS)
    ]
    return eligible, passes_by_player


def _knn_similarity(
    target: dict,
    pool: list[dict],
    keys: tuple[str, ...],
    *,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    return knn_similarity(target, pool, keys, top_k=top_k)


def _heatmap_similarity(
    target: dict,
    pool: list[dict],
    passes_by_id: dict[str, pd.DataFrame],
    *,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    return heatmap_similarity(target, pool, passes_by_id, top_k=top_k)


def _hybrid_similarity(
    target: dict,
    pool: list[dict],
    passes_by_id: dict[str, pd.DataFrame],
    *,
    metric_weight: float = 0.65,
    heatmap_weight: float = 0.35,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    metric_rows = {
        r["player_name"]: r
        for r in _knn_similarity(target, pool, ALT_KEYS, top_k=len(pool))
    }
    heat_rows = {
        r["player_name"]: r
        for r in _heatmap_similarity(target, pool, passes_by_id, top_k=len(pool))
    }
    names = set(metric_rows) & set(heat_rows)
    combined: list[dict[str, Any]] = []
    for name in names:
        m = metric_rows[name]
        h = heat_rows[name]
        score = metric_weight * m["similarity_pct"] + heatmap_weight * h["similarity_pct"]
        combined.append(
            {
                **m,
                "heatmap_similarity_pct": h["similarity_pct"],
                "origin_dominant": h.get("origin_dominant"),
                "similarity_pct": round(score, 1),
            }
        )
    combined.sort(key=lambda r: (-r["similarity_pct"], str(r["player_name"])))
    return combined[:top_k]


def _player_by_name(pool: list[dict], name: str) -> dict | None:
    key = name.strip().lower()
    for p in pool:
        if str(p.get("player_name", "")).strip().lower() == key:
            return p
    return None


def _metric_snapshot(player: dict) -> dict[str, float]:
    return metric_snapshot(player)


def build_report(pool: list[dict], passes_by_id: dict[str, pd.DataFrame]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "n_pool": len(pool),
        "alt_metrics": [{"key": k, "label": l} for k, l in ALT_METRICS],
        "examples": {},
    }
    for name in EXAMPLES:
        target = _player_by_name(pool, name)
        if target is None:
            payload["examples"][name] = {"error": "not in pool"}
            continue
        seven = _knn_similarity(target, pool, SEVEN_PILLAR_KEYS, top_k=8)
        alt = _knn_similarity(target, pool, ALT_KEYS, top_k=8)
        heat = _heatmap_similarity(target, pool, passes_by_id, top_k=8)
        hybrid = _hybrid_similarity(target, pool, passes_by_id, top_k=8)
        payload["examples"][name] = {
            "team": target.get("team"),
            "market_value_display": target.get("market_value_display"),
            "metrics": _metric_snapshot(target),
            "seven_pillars_similar": seven,
            "alt_metrics_similar": alt,
            "heatmap_similar": heat,
            "hybrid_similar": hybrid,
        }
    return payload


def _render_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Player similarity — alt metrics + heatmap",
        "",
        f"Pool: **{payload['n_pool']}** eligible midfielders.",
        "",
        "## Métricas alternativas (k-NN em z-scores)",
        "",
        "| Key | Label |",
        "|---|---|",
    ]
    for item in payload["alt_metrics"]:
        lines.append(f"| `{item['key']}` | {item['label']} |")
    lines.extend(
        [
            "",
            "**Heatmap:** cosseno entre grelhas 8×6 de origem dos passes.",
            "",
            "**Híbrido:** 65% métricas alternativas + 35% heatmap.",
            "",
        ]
    )
    for name, block in payload["examples"].items():
        if block.get("error"):
            lines.append(f"## {name}\n\nNot in pool.\n")
            continue
        lines.append(f"## {name} ({block['team']}) · {block['market_value_display']}")
        m = block["metrics"]
        lines.append(
            "- "
            + " · ".join(f"{k} {v:.2f}" if k != "COE" and "COE" not in k else f"{k} {v:+.1f}pp" for k, v in m.items())
        )
        lines.append("")

        def table(title: str, rows: list[dict], extra: str = "") -> None:
            lines.append(f"### {title}")
            lines.append("")
            if extra:
                lines.append(extra)
                lines.append("")
            lines.append("| Sim % | Player | Team | MV | xP pass |")
            lines.append("|---:|---|---|---:|---:|")
            for r in rows:
                lines.append(
                    f"| {r['similarity_pct']} | {r['player_name']} | {r['team']} | "
                    f"{r['market_value_display']} | {r.get('xp_pass_rating', '—')} |"
                )
            lines.append("")

        table("7 pilares (referência anterior)", block["seven_pillars_similar"])
        table("Métricas alternativas", block["alt_metrics_similar"])
        table("Heatmap (origem dos passes)", block["heatmap_similar"])
        table(
            "Híbrido (65% métricas + 35% heatmap)",
            block["hybrid_similar"],
            extra="Inclui jogadores que combinam estilo de taxas **e** zona de ação.",
        )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    pool, passes_by_id = _load_pool()
    payload = build_report(pool, passes_by_id)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_md(payload), encoding="utf-8")
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Pool size: {len(pool)}")


if __name__ == "__main__":
    main()
