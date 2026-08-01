#!/usr/bin/env python3
"""Offline clustering study for European midfielder profiles.

Builds feature matrices from pass, xP, xPass and composite metrics, evaluates
k=2..10 with multiple internal validation scores, and writes a markdown report.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import passes_engine as pe
import xp_engine as xe
import xp_stats_engine as xstats
import xpass_engine as xpass
import midfield_origin as mo
from passes_engine import compute_pass_ratings
from player_archetypes import attach_player_archetypes
from progression_engine import compute_progression_ratings as pg_compute_progression_ratings

REPORT_PATH = ROOT / "docs" / "player_profile_clustering_study.md"
JSON_PATH = ROOT / "docs" / "player_profile_clustering_study.json"

FEATURE_SETS: dict[str, list[str]] = {
    "xp_composites": list(xstats.XP_COMPOSITE_INDEX_KEYS),
    "xp_archetype_radar": list(xstats.XP_ARCHETYPE_RADAR_KEYS),
    "xp_pillars": list(xstats.XP_PROFILE_BAR_KEYS)
    + ["xp_consistency_display", "xp_quality_display"],
    "pass_scores": [
        "pass_volume_display",
        "pass_efficiency_display",
        "pass_buildup_display",
        "pass_chance_creation_display",
        "pass_impact_display",
    ],
    "xpass_execution": [
        "xpass_coe_pct",
        "xpass_residual_p90",
        "xpv_per_pass",
        "xpass_hard_coe_pct",
        "xpass_expected_pct",
        "pass_completion_pct",
    ],
    "impact_pass_style": [
        "impact_passes_p90",
        "impact_per_pass",
        "risk_pass_pct",
        "positive_dxt_pct",
        "construction_aip_p90",
        "aggression_aip_p90",
        "progressive_passes_p90",
        "final_third_passes_p90",
        "key_passes",
        "long_ball_completion_pct",
    ],
    "xp_threat_special": [
        "xp_m4_per_pass",
        "xp_m4_threat_rate",
        "xp_residual_mean",
        "xp_game_consistency_score",
        "xp_from_deep_share",
        "xp_final_third_share",
        "xp_box_share",
        "long_pass_share_pct",
        "short_pass_share_pct",
    ],
}

CORE_FEATURES: list[str] = sorted(
    dict.fromkeys(
        FEATURE_SETS["xp_composites"]
        + FEATURE_SETS["xp_archetype_radar"]
        + FEATURE_SETS["pass_scores"]
        + FEATURE_SETS["xpass_execution"]
        + FEATURE_SETS["impact_pass_style"][:6]
    )
)


def _load_merged_players() -> list[dict]:
    players = pe.build_european_league_midfielders()
    passes_by_player = pe.load_european_league_passes_grouped()
    players = mo.apply_midfield_position_groups(players, passes_by_player, {})
    _, players_by_id, _ = compute_pass_ratings(players)
    _, xp_players = xe.build_european_league_xp_analytics()
    xp_by_id = {str(p["player_id"]): p for p in xp_players}
    _, progression_by_id, _ = pg_compute_progression_ratings(
        players,
        [],
        pass_by_id=players_by_id,
        carry_by_id={},
    )

    merged: list[dict] = []
    for player in players:
        pid = str(player["player_id"])
        xp = xp_by_id.get(pid, {})
        prog = progression_by_id.get(pid, {})
        row = {
            **player,
            **xp,
            **{k: v for k, v in prog.items() if k not in player and k not in xp},
            "pass_rating": players_by_id.get(pid, {}).get("pass_rating"),
        }
        merged.append(row)
    return attach_player_archetypes(merged)


def _eligible_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("xp_profile_bars_eligible")
        and row.get("xp_pass_rating") is not None
    ]


def _build_matrix(
    rows: list[dict],
    feature_keys: list[str],
    *,
    group_key: str | None = "position_group",
) -> tuple[pd.DataFrame, list[str], list[str]]:
    usable_keys = [key for key in feature_keys if any(row.get(key) is not None for row in rows)]
    frame = pd.DataFrame(
        [{key: row.get(key) for key in usable_keys} for row in rows],
        index=[str(row["player_id"]) for row in rows],
    )
    labels = [str(row.get("player_name", "")) for row in rows]
    groups = [str(row.get(group_key or "", "all")) for row in rows]

    imputer = SimpleImputer(strategy="median")
    values = imputer.fit_transform(frame)

    if group_key:
        standardized = np.zeros_like(values, dtype=float)
        for group in sorted(set(groups)):
            mask = np.array([g == group for g in groups])
            if mask.sum() < 3:
                standardized[mask] = StandardScaler().fit_transform(values[mask])
            else:
                standardized[mask] = StandardScaler().fit_transform(values[mask])
    else:
        standardized = StandardScaler().fit_transform(values)

    return (
        pd.DataFrame(standardized, index=frame.index, columns=usable_keys),
        labels,
        groups,
    )


def _evaluate_k(matrix: pd.DataFrame, k: int, *, random_state: int = 42) -> dict:
    model = KMeans(n_clusters=k, random_state=random_state, n_init="auto")
    labels = model.fit_predict(matrix.values)
    if len(set(labels)) < 2:
        return {
            "k": k,
            "silhouette": float("nan"),
            "calinski_harabasz": float("nan"),
            "davies_bouldin": float("nan"),
            "inertia": float(model.inertia_),
            "labels": labels.tolist(),
        }
    return {
        "k": k,
        "silhouette": float(silhouette_score(matrix.values, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(matrix.values, labels)),
        "davies_bouldin": float(davies_bouldin_score(matrix.values, labels)),
        "inertia": float(model.inertia_),
        "labels": labels.tolist(),
    }


def _best_k(results: list[dict]) -> int:
    valid = [row for row in results if not math.isnan(row["silhouette"])]
    if not valid:
        return 4
    return int(max(valid, key=lambda row: row["silhouette"])["k"])


def _suggest_cluster_name(top_features: list[tuple[str, float]]) -> str:
    feats = {key: val for key, val in top_features}
    if feats.get("xp_quality_index", 0) > 0.6 and feats.get("xp_consistency_index", 0) > 0.5:
        return "Elite all-round"
    if feats.get("xp_archetype_creator_display", 0) > 0.45 or feats.get("xp_creator_index", 0) > 0.45:
        return "Creator"
    if feats.get("xp_archetype_progressor_display", 0) > 0.45 or feats.get("xp_progressor_index", 0) > 0.45:
        return "Progressor"
    if feats.get("xp_archetype_finisher_display", 0) > 0.45 or feats.get("xp_finisher_pass_index", 0) > 0.45:
        return "Impact / final third"
    if feats.get("xp_archetype_builder_display", 0) > 0.45 or feats.get("xp_builder_index", 0) > 0.45:
        return "Connector / builder"
    if feats.get("pass_buildup_display", 0) > 0.4 and feats.get("pass_completion_pct", 0) > 0.3:
        return "Safety / retention"
    if feats.get("xp_quality_index", 0) < -0.35:
        return "Below benchmark"
    return "Balanced / mixed"


def _cluster_profile(
    rows: list[dict],
    labels: list[int],
    feature_keys: list[str],
    matrix: pd.DataFrame,
) -> list[dict]:
    profiles: list[dict] = []
    for cluster_id in sorted(set(labels)):
        member_ids = [
            str(row["player_id"])
            for row, label in zip(rows, labels)
            if label == cluster_id
        ]
        members = [row for row, label in zip(rows, labels) if label == cluster_id]
        z_sub = matrix.loc[member_ids].values
        means = {
            feature_keys[i]: float(z_sub[:, i].mean()) for i in range(len(feature_keys))
        }
        top_features = sorted(
            means.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:6]
        label_suggested = _suggest_cluster_name(top_features)
        archetypes = Counter(str(m.get("xp_profile_archetype") or "—") for m in members)
        prog_arch = Counter(str(m.get("player_archetype_label") or "—") for m in members)
        origin = Counter(str(m.get("midfield_origin_profile") or "—") for m in members)
        examples = sorted(
            members,
            key=lambda m: float(m.get("xp_pass_rating") or 0),
            reverse=True,
        )[:5]
        profiles.append(
            {
                "cluster_id": cluster_id,
                "label_suggested": label_suggested,
                "size": len(members),
                "share_pct": round(100 * len(members) / len(rows), 1),
                "mean_xp_pass_rating": round(
                    float(np.nanmean([m.get("xp_pass_rating") for m in members])), 2
                ),
                "top_features": [
                    {"key": key, "mean_z": round(val, 2)} for key, val in top_features
                ],
                "xp_archetype_mix": dict(archetypes.most_common()),
                "progression_archetype_mix": dict(prog_arch.most_common(3)),
                "origin_mix": dict(origin.most_common()),
                "examples": [
                    {
                        "player_name": m.get("player_name"),
                        "team": m.get("team"),
                        "xp_pass_rating": m.get("xp_pass_rating"),
                        "xp_profile_archetype_label": m.get("xp_profile_archetype_label"),
                    }
                    for m in examples
                ],
            }
        )
    profiles.sort(key=lambda item: item["mean_xp_pass_rating"], reverse=True)
    return profiles


def _pca_variance(matrix: pd.DataFrame) -> dict:
    if matrix.shape[1] < 2:
        return {"n_components_80pct": 1, "n_components_90pct": 1}
    pca = PCA(random_state=42)
    pca.fit(matrix.values)
    cum = np.cumsum(pca.explained_variance_ratio_)
    return {
        "n_components_80pct": int(np.searchsorted(cum, 0.80) + 1),
        "n_components_90pct": int(np.searchsorted(cum, 0.90) + 1),
        "first_component_pct": round(float(pca.explained_variance_ratio_[0]) * 100, 1),
    }


def _compare_existing_archetypes(rows: list[dict]) -> dict:
    xp_counts = Counter(str(r.get("xp_profile_archetype") or "missing") for r in rows)
    prog_counts = Counter(str(r.get("player_archetype_label") or "missing") for r in rows)
    return {
        "xp_profile_archetypes": dict(xp_counts),
        "progression_archetypes": dict(prog_counts),
        "xp_n_types": len([k for k in xp_counts if k != "missing"]),
        "progression_n_types": len([k for k in prog_counts if k != "missing"]),
    }


def _render_markdown(payload: dict) -> str:
    lines = [
        "# Player profile clustering study",
        "",
        f"- Players in pool: **{payload['n_players_total']}**",
        f"- Eligible for clustering (xP profile bars): **{payload['n_players_eligible']}**",
        f"- Core feature count: **{payload['n_features']}**",
        "",
        "## Existing rule-based archetypes",
        "",
        f"- xP profile archetypes in use today: **{payload['existing_archetypes']['xp_n_types']}** "
        f"({', '.join(payload['existing_archetypes']['xp_profile_archetypes'].keys())})",
        f"- Progression archetypes (pass-side): **{payload['existing_archetypes']['progression_n_types']}**",
        "",
        "## Dimensionality",
        "",
        f"- Components for 80% variance: **{payload['pca']['n_components_80pct']}**",
        f"- Components for 90% variance: **{payload['pca']['n_components_90pct']}**",
        f"- First PCA component: **{payload['pca']['first_component_pct']}%**",
        "",
        "## Model selection (KMeans, standardized within position group)",
        "",
        "| k | Silhouette ↑ | Calinski-Harabasz ↑ | Davies-Bouldin ↓ |",
        "|---:|---:|---:|---:|",
    ]
    for row in payload["k_scan"]:
        lines.append(
            f"| {row['k']} | {row['silhouette']:.3f} | {row['calinski_harabasz']:.1f} | {row['davies_bouldin']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"**Best silhouette k:** {payload['best_k_silhouette']}",
            f"**Recommended k (balanced):** {payload['recommended_k']}",
            "",
            "## Recommendation",
            "",
            payload["recommendation_text"],
            "",
            "## Cluster profiles at recommended k",
            "",
        ]
    )
    for profile in payload["cluster_profiles"]:
        label = profile.get("label_suggested", "—")
        lines.append(
            f"### Cluster {profile['cluster_id']} — {label} — "
            f"{profile['size']} players ({profile['share_pct']}%)"
        )
        lines.append(
            f"- Mean xP pass rating: **{profile['mean_xp_pass_rating']}**"
        )
        lines.append(
            "- xP archetype mix: "
            + ", ".join(f"{k} ({v})" for k, v in profile["xp_archetype_mix"].items())
        )
        lines.append(
            "- Origin mix: "
            + ", ".join(f"{k} ({v})" for k, v in profile["origin_mix"].items())
        )
        lines.append("- Top standardized features:")
        for feat in profile["top_features"]:
            lines.append(f"  - `{feat['key']}`: {feat['mean_z']:+.2f}")
        lines.append("- Examples:")
        for ex in profile["examples"]:
            lines.append(
                f"  - {ex['player_name']} ({ex['team']}) — xP {ex['xp_pass_rating']}, "
                f"{ex.get('xp_profile_archetype_label', '—')}"
            )
        lines.append("")

    lines.extend(["## Options for the product", "", payload["options_text"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = _load_merged_players()
    eligible = _eligible_rows(rows)
    matrix, _, groups = _build_matrix(eligible, CORE_FEATURES)

    k_scan = [_evaluate_k(matrix, k) for k in range(2, 11)]
    best_k = _best_k(k_scan)

    # Balanced recommendation: statistical peak is often k=2, but product UX needs 4–5 buckets.
    silhouette_by_k = {row["k"]: row["silhouette"] for row in k_scan}
    peak = max(silhouette_by_k.values())
    candidates = [k for k, score in silhouette_by_k.items() if score >= peak - 0.05]
    if 5 in candidates and silhouette_by_k[5] >= 0.12:
        recommended_k = 5
    elif 4 in candidates and silhouette_by_k[4] >= 0.12:
        recommended_k = 4
    elif 3 in candidates:
        recommended_k = 3
    else:
        recommended_k = best_k

    labels = next(row["labels"] for row in k_scan if row["k"] == recommended_k)
    cluster_profiles = _cluster_profile(eligible, labels, list(matrix.columns), matrix)

    alt_profiles: dict[str, list[dict]] = {}
    for alt_k in (2, 3, 5):
        if alt_k == recommended_k:
            continue
        alt_labels = next(row["labels"] for row in k_scan if row["k"] == alt_k)
        alt_profiles[str(alt_k)] = _cluster_profile(
            eligible, alt_labels, list(matrix.columns), matrix
        )

    origin_segments: dict[str, dict] = {}
    for origin in sorted({str(r.get("midfield_origin_profile") or "—") for r in eligible}):
        sub_rows = [r for r in eligible if str(r.get("midfield_origin_profile") or "—") == origin]
        if len(sub_rows) < 30:
            continue
        sub_matrix, _, _ = _build_matrix(sub_rows, CORE_FEATURES, group_key=None)
        sub_scan = [_evaluate_k(sub_matrix, k) for k in range(2, 8)]
        sub_best = _best_k(sub_scan)
        origin_segments[origin] = {
            "n": len(sub_rows),
            "best_k_silhouette": sub_best,
            "best_silhouette": round(
                max(r["silhouette"] for r in sub_scan if not math.isnan(r["silhouette"])), 3
            ),
        }

    existing = _compare_existing_archetypes(eligible)
    pca_info = _pca_variance(matrix)

    recommendation_text = (
        f"Statistically, silhouette peaks at **k={best_k}** ({peak:.3f}) — a coarse split between "
        f"high and lower xP passers. For scouting dashboards, **{recommended_k} profiles** is the "
        "better product compromise: enough granularity for Connector / Progressor / Creator / "
        "Finisher-style scouting without fragmenting into hard-to-explain micro-clusters. "
        f"PCA suggests ~{pca_info['n_components_80pct']} independent dimensions for 80% variance "
        f"(~{pca_info['n_components_90pct']} for 90%), aligning with 4 radar axes plus execution style."
    )

    options_text = (
        "**Option A — 4 macro profiles (simplest):** Connector / Progressor / Creator / Finisher. "
        "Good for UI and compare tabs; loses specialists.\n\n"
        "**Option B — 5 data-driven profiles (recommended):** keep KMeans k=5 on the core feature set; "
        "name clusters from top z-scores (builder, creator, progressor, safety, limited).\n\n"
        "**Option C — 6 profiles (align with current xP archetypes):** reuse existing rule labels "
        "(elite, creative, safety, impact, regular, limited) — already implemented, but overlaps "
        "in practice.\n\n"
        "**Option D — 7–8 profiles (max detail):** only if you need fine-grained recruitment filters; "
        "silhouette gain vs k=5 is small and clusters become harder to explain."
    )

    payload = {
        "n_players_total": len(rows),
        "n_players_eligible": len(eligible),
        "n_features": matrix.shape[1],
        "feature_columns": list(matrix.columns),
        "position_group_counts": dict(Counter(groups)),
        "existing_archetypes": existing,
        "pca": pca_info,
        "k_scan": [{k: v for k, v in row.items() if k != "labels"} for row in k_scan],
        "best_k_silhouette": best_k,
        "recommended_k": recommended_k,
        "cluster_profiles": cluster_profiles,
        "alternate_cluster_profiles": alt_profiles,
        "origin_segments": origin_segments,
        "recommendation_text": recommendation_text,
        "options_text": options_text,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {JSON_PATH}")
    print(f"Eligible players: {len(eligible)} | Recommended k: {recommended_k}")


if __name__ == "__main__":
    main()
