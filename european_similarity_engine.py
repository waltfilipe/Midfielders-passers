"""European midfielder similarity — alt metrics k-NN and pass-origin heatmap."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import similarity_engine as sim

ALT_METRICS: tuple[tuple[str, str], ...] = (
    ("long_pass_share_pct", "% passes longos"),
    ("progressive_pass_rate", "% passes progressivos / passe"),
    ("impact_v2_per_pass", "Impact v2 / passe"),
    ("xpv_per_pass", "xPV / passe"),
    ("xpv_per_game", "xPV / jogo"),
    ("xpass_coe_pct", "COE"),
    ("xpass_long_coe_pct", "COE long passes"),
)

ALT_KEYS: tuple[str, ...] = tuple(key for key, _ in ALT_METRICS)


def attach_derived_rates(row: dict) -> None:
    passes_total = float(row.get("passes_total") or 0.0)
    passes_completed = float(row.get("passes_completed") or 0.0)
    progressive = float(row.get("progressive_passes") or 0.0)
    ti_v2 = float(row.get("test_impact_v2_count") or 0.0)
    minutes = float(row.get("minutes") or 0.0)

    row["progressive_pass_rate"] = (
        round(100.0 * progressive / passes_total, 2) if passes_total > 0 else None
    )
    row["impact_v2_per_pass"] = (
        round(100.0 * ti_v2 / passes_completed, 2) if passes_completed > 0 else None
    )
    xpv_total = row.get("xpv_total")
    if xpv_total is not None and minutes > 0:
        row["xpv_per_game"] = round(float(xpv_total) * 90.0 / minutes, 3)
    elif row.get("xpv_per_pass_p90") is not None:
        row["xpv_per_game"] = float(row["xpv_per_pass_p90"])
    elif row.get("xp_per_90") is not None:
        row["xpv_per_game"] = float(row["xp_per_90"])
    else:
        row["xpv_per_game"] = None


def build_similarity_pool(
    players: list[dict],
    xp_by_id: dict[str, dict],
    *,
    pass_by_id: dict[str, dict] | None = None,
) -> list[dict]:
    merged: list[dict] = []
    for player in players:
        pid = str(player["player_id"])
        xp = xp_by_id.get(pid)
        if not xp:
            continue
        row = {**player, **xp}
        if pass_by_id:
            row.update(pass_by_id.get(pid, {}))
        attach_derived_rates(row)
        merged.append(row)

    return [
        row
        for row in merged
        if row.get("xp_profile_bars_eligible")
        and all(row.get(key) is not None for key in ALT_KEYS)
    ]


def _vector(player: dict, keys: tuple[str, ...]) -> np.ndarray:
    return np.array([float(player[key]) for key in keys], dtype=float)


def knn_similarity(
    target: dict,
    pool: list[dict],
    keys: tuple[str, ...],
    *,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    return _knn_similarity(target, pool, keys, top_k=top_k)


def knn_alt_metrics_similarity(
    target: dict,
    pool: list[dict],
    *,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    return _knn_similarity(target, pool, ALT_KEYS, top_k=top_k)


def heatmap_similarity(
    target: dict,
    pool: list[dict],
    passes_by_id: dict[str, pd.DataFrame],
    *,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    pid = str(target["player_id"])
    target_profile = sim.pass_origin_profile(passes_by_id.get(pid))
    if target_profile is None:
        return []

    rows: list[dict[str, Any]] = []
    for candidate in pool:
        cand_id = str(candidate["player_id"])
        if cand_id == pid:
            continue
        profile = sim.pass_origin_profile(passes_by_id.get(cand_id))
        if profile is None:
            continue
        sim_pct = sim._cosine_similarity_pct(target_profile, profile)
        rows.append(_similarity_row(candidate, sim_pct, origin_dominant=sim.describe_dominant_origin_zone(profile)))

    rows.sort(key=lambda row: (-row["similarity_pct"], str(row["player_name"])))
    return rows[:top_k]


def metric_snapshot(player: dict) -> dict[str, float]:
    return {label: float(player[key]) for key, label in ALT_METRICS}


def _knn_similarity(
    target: dict,
    pool: list[dict],
    keys: tuple[str, ...],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    candidates = [player for player in pool if str(player["player_id"]) != str(target["player_id"])]
    if not candidates:
        return []

    raw = np.vstack([_vector(player, keys) for player in candidates])
    mean = raw.mean(axis=0)
    std = raw.std(axis=0)
    std[std == 0] = 1.0
    z_pool = (raw - mean) / std
    z_target = (_vector(target, keys) - mean) / std
    dists = np.sqrt(((z_pool - z_target) ** 2).sum(axis=1))
    scale = float(dists.max()) if len(dists) else 1.0
    if scale <= 0:
        scale = 1.0

    rows: list[dict[str, Any]] = []
    for dist, candidate in zip(dists, candidates):
        sim_pct = round(float(np.clip(100.0 * (1.0 - dist / scale), 0, 100)), 1)
        rows.append(_similarity_row(candidate, sim_pct, distance=round(float(dist), 3)))

    rows.sort(key=lambda row: (-row["similarity_pct"], row.get("distance", 0.0)))
    return rows[:top_k]


def _similarity_row(
    player: dict,
    similarity_pct: float,
    *,
    distance: float | None = None,
    origin_dominant: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "player_id": str(player.get("player_id", "")),
        "player_name": player.get("player_name"),
        "team": player.get("team"),
        "similarity_pct": round(float(similarity_pct), 1),
        "market_value_display": player.get("market_value") or player.get("market_value_display") or "—",
        "xp_pass_rating": player.get("xp_pass_rating"),
    }
    if distance is not None:
        row["distance"] = distance
    if origin_dominant is not None:
        row["origin_dominant"] = origin_dominant
    return row
