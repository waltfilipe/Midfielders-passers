#!/usr/bin/env python3
"""Offline k-NN player similarity on seven scout pillars (Option 1).

Pillars: Volume, Efficiency, Build-up, Chance creation, Productivity,
Precision, Lethality — mapped to pass/xP display scores (1–10 within position).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import passes_engine as pe
import xp_engine as xe
import midfield_origin as mo
import transfermarkt_profiles as tm
from passes_engine import compute_pass_ratings

REPORT_PATH = ROOT / "docs" / "player_similarity_seven_pillars.md"
JSON_PATH = ROOT / "docs" / "player_similarity_seven_pillars.json"

SIMILARITY_PILLARS: tuple[tuple[str, str], ...] = (
    ("pass_volume_display", "Volume"),
    ("pass_efficiency_display", "Efficiency"),
    ("pass_buildup_display", "Build-up"),
    ("pass_chance_creation_display", "Chance creation"),
    ("xp_activity_display", "Productivity"),
    ("xp_efficiency_display", "Precision"),
    ("xp_edge_display", "Lethality"),
)

PILLAR_KEYS: tuple[str, ...] = tuple(key for key, _ in SIMILARITY_PILLARS)

EXAMPLE_TARGETS: tuple[str, ...] = (
    "Joshua Kimmich",
    "Vitinha",
    "Bruno Fernandes",
    "Rodri",
    "João Neves",
    "Manuel Locatelli",
)


def _load_players() -> list[dict]:
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
        merged.append(row)
    return merged


def _eligible_pool(players: list[dict]) -> list[dict]:
    return [
        p
        for p in players
        if p.get("xp_profile_bars_eligible")
        and all(p.get(key) is not None for key in PILLAR_KEYS)
    ]


def _pillar_vector(player: dict) -> np.ndarray:
    return np.array([float(player[key]) for key in PILLAR_KEYS], dtype=float)


def _zscore_matrix(players: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    mat = np.vstack([_pillar_vector(p) for p in players])
    mean = mat.mean(axis=0)
    std = mat.std(axis=0)
    std[std == 0] = 1.0
    return (mat - mean) / std, mean


def _similarity_pct(distance: float, scale: float) -> float:
    if scale <= 0:
        return 100.0 if distance == 0 else 0.0
    return float(np.clip(100.0 * (1.0 - distance / scale), 0.0, 100.0))


def find_similar(
    target: dict,
    pool: list[dict],
    *,
    top_k: int = 10,
    exclude_same_player: bool = True,
    max_market_value_eur: float | None = None,
) -> list[dict[str, Any]]:
    candidates = [
        p
        for p in pool
        if (not exclude_same_player or str(p["player_id"]) != str(target["player_id"]))
        and (
            max_market_value_eur is None
            or p.get("market_value_eur") is None
            or float(p["market_value_eur"]) <= max_market_value_eur
        )
    ]
    if not candidates:
        return []

    z_pool, _ = _zscore_matrix(candidates)
    z_target = (_pillar_vector(target) - z_pool.mean(axis=0)) / np.where(
        z_pool.std(axis=0) == 0, 1.0, z_pool.std(axis=0)
    )
    # Recompute target z using full candidate moments for consistency
    raw = np.vstack([_pillar_vector(p) for p in candidates])
    mean = raw.mean(axis=0)
    std = raw.std(axis=0)
    std[std == 0] = 1.0
    z_target = (_pillar_vector(target) - mean) / std

    diffs = z_pool - z_target
    dists = np.sqrt((diffs ** 2).sum(axis=1))
    scale = float(dists.max()) if len(dists) else 1.0
    if scale <= 0:
        scale = 1.0

    rows: list[dict[str, Any]] = []
    for dist, cand in zip(dists, candidates):
        pillar_delta = {
            label: round(float(cand[key]) - float(target[key]), 1)
            for key, label in SIMILARITY_PILLARS
        }
        rows.append(
            {
                "player_id": cand["player_id"],
                "player_name": cand.get("player_name"),
                "team": cand.get("team"),
                "similarity_pct": round(_similarity_pct(float(dist), scale), 1),
                "distance": round(float(dist), 3),
                "market_value_display": cand.get("market_value_display") or "—",
                "market_value_eur": cand.get("market_value_eur"),
                "xp_pass_rating": cand.get("xp_pass_rating"),
                "xp_profile_archetype_label": cand.get("xp_profile_archetype_label"),
                "pillars": {label: round(float(cand[key]), 1) for key, label in SIMILARITY_PILLARS},
                "pillar_delta": pillar_delta,
            }
        )
    rows.sort(key=lambda r: (-r["similarity_pct"], r["distance"]))
    return rows[:top_k]


def _player_by_name(pool: list[dict], name: str) -> dict | None:
    name_l = name.strip().lower()
    for p in pool:
        if str(p.get("player_name", "")).strip().lower() == name_l:
            return p
    return None


def _format_target_pillars(target: dict) -> str:
    parts = [f"{label} {float(target[key]):.1f}" for key, label in SIMILARITY_PILLARS]
    return " · ".join(parts)


def _render_examples(pool: list[dict]) -> dict[str, Any]:
    out: dict[str, Any] = {"n_pool": len(pool), "examples": {}}
    for name in EXAMPLE_TARGETS:
        target = _player_by_name(pool, name)
        if target is None:
            out["examples"][name] = {"error": "not in eligible pool"}
            continue
        similar = find_similar(target, pool, top_k=8)
        target_mv = target.get("market_value_eur")
        cheaper: list[dict[str, Any]] = []
        if target_mv is not None and float(target_mv) > 0:
            cap = float(target_mv) * 0.35
            cheaper = find_similar(target, pool, top_k=5, max_market_value_eur=cap)
        out["examples"][name] = {
            "team": target.get("team"),
            "market_value_display": target.get("market_value_display"),
            "pillars": {label: round(float(target[key]), 1) for key, label in SIMILARITY_PILLARS},
            "top_similar": similar,
            "cheaper_similar_max_35pct_mv": cheaper,
        }
    return out


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Player similarity — seven pillars (offline k-NN)",
        "",
        f"Pool: **{payload['n_pool']}** eligible European midfielders.",
        "",
        "Distance: Euclidean on z-scores of display scores (1–10 within position).",
        "",
        "| Pillar | Metric key |",
        "|---|---|",
    ]
    for key, label in SIMILARITY_PILLARS:
        lines.append(f"| {label} | `{key}` |")
    lines.append("")

    for name, block in payload["examples"].items():
        if block.get("error"):
            lines.append(f"## {name}\n\nNot found in pool.\n")
            continue
        lines.append(f"## {name} ({block.get('team', '—')})")
        lines.append(f"- Market value: **{block.get('market_value_display', '—')}**")
        pillar_str = " · ".join(f"{k} {v}" for k, v in block["pillars"].items())
        lines.append(f"- Pillars: {pillar_str}")
        lines.append("")
        lines.append("### Most similar")
        lines.append("")
        lines.append("| Similarity | Player | Team | MV | xP pass | Top deltas |")
        lines.append("|---:|---|---|---:|---:|---|")
        for row in block["top_similar"]:
            deltas = row["pillar_delta"]
            top = sorted(deltas.items(), key=lambda x: -abs(x[1]))[:3]
            delta_str = ", ".join(f"{k} {v:+.1f}" for k, v in top)
            lines.append(
                f"| {row['similarity_pct']}% | {row['player_name']} | {row['team']} | "
                f"{row['market_value_display']} | {row.get('xp_pass_rating', '—')} | {delta_str} |"
            )
        if block.get("cheaper_similar_max_35pct_mv"):
            lines.append("")
            lines.append("### Similar · ≤35% of target market value")
            lines.append("")
            lines.append("| Similarity | Player | Team | MV | xP pass |")
            lines.append("|---:|---|---|---:|---:|")
            for row in block["cheaper_similar_max_35pct_mv"]:
                lines.append(
                    f"| {row['similarity_pct']}% | {row['player_name']} | {row['team']} | "
                    f"{row['market_value_display']} | {row.get('xp_pass_rating', '—')} |"
                )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    players = _load_players()
    pool = _eligible_pool(players)
    payload = _render_examples(pool)
    payload["pillar_keys"] = list(PILLAR_KEYS)
    payload["pillar_labels"] = [label for _, label in SIMILARITY_PILLARS]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {JSON_PATH}")
    print(f"Eligible pool: {len(pool)}")


if __name__ == "__main__":
    main()
