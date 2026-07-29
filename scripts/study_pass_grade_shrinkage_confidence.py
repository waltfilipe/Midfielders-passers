"""Offline study: how much shrinkage and confidence pull grades toward 6.0.

Run:
    python3 scripts/study_pass_grade_shrinkage_confidence.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import passes_engine as pe  # noqa: E402
import xp_engine as xe  # noqa: E402
import xp_stats_engine as xs  # noqa: E402

MID = pe.RATING_DISPLAY_MID


def _composite_z_from_shrunk(rows: list[dict], shrunk: dict[str, list[float]]) -> list[float]:
    z_frame = pd.DataFrame(shrunk).apply(xs._zscore)
    weights = pd.Series(xs.XP_PASS_RATING_FEATURE_WEIGHTS)
    return (
        z_frame.mul(weights, axis=1).sum(axis=1) / weights.sum()
    ).astype(float).tolist()


def _rank_percentile_scores(rows: list[dict], composite_z: list[float]) -> list[float]:
    pool_size = len(rows)
    order = sorted(range(pool_size), key=lambda i: composite_z[i], reverse=True)
    scores = [0.0] * pool_size
    for rank, i in enumerate(order, start=1):
        scores[i] = xs.xp_pass_rating_blended_display(rank, pool_size, float(z_list[i]))
    return scores


def analyze_pool(rows: list[dict]) -> list[dict]:
    pool_size = len(rows)
    if pool_size == 0:
        return []

    passes = [float(p.get("passes_completed") or 0.0) for p in rows]
    p25_passes = float(np.percentile(passes, 25)) if passes else float(pe.RATING_CONFIDENCE_PASSES)
    p25_passes = max(p25_passes, 1.0)

    shrunk: dict[str, list[float]] = {}
    raw: dict[str, list[float]] = {}
    for key in xs.XP_PASS_RATING_FEATURES:
        pool_values = [float(p.get(key) or 0.0) for p in rows]
        raw[key] = pool_values
        shrunk[key] = [
            xs._xp_pass_rating_shrink_value(key, player, pool_values) for player in rows
        ]

    z_no_shrink = _composite_z_from_shrunk(rows, raw)
    z_shrunk = _composite_z_from_shrunk(rows, shrunk)
    pct_from_shrunk_z = _rank_percentile_scores(rows, z_shrunk)

    out: list[dict] = []
    for i, player in enumerate(rows):
        minutes = float(player.get("minutes") or 0.0)
        passes_n = float(player.get("passes_completed") or 0.0)
        conf = xs._xp_pass_rating_confidence({**player, "position_p25_passes": p25_passes})
        pct = pct_from_shrunk_z[i]
        final_grade, _unc = xs._apply_xp_pass_rating_confidence(pct, conf)

        w_xp = minutes / (minutes + pe.SHRINKAGE_MINUTES_K) if minutes > 0 else 0.0
        w_pass = passes_n / (passes_n + pe.SHRINKAGE_PASS_K) if passes_n > 0 else 0.0
        efetivo = 1.0 - xs.XP_PASS_RATING_CONFIDENCE_WEIGHT * (1.0 - conf)

        out.append(
            {
                "player": player.get("player_name"),
                "team": player.get("team"),
                "pool_key": xs._metric_rank_pool_key(player),
                "minutes": minutes,
                "passes": passes_n,
                "shrink_w_xp_per_90": round(w_xp, 3),
                "shrink_w_xp_m4_per_pass": round(w_pass, 3),
                "confidence": round(conf, 3),
                "efetivo": round(efetivo, 3),
                "z_no_shrink": round(z_no_shrink[i], 3),
                "z_shrunk": round(z_shrunk[i], 3),
                "z_delta": round(z_shrunk[i] - z_no_shrink[i], 3),
                "pct_before_conf": round(pct, 2),
                "grade_final": round(final_grade, 2),
                "pull_conf_to_6": round(final_grade - pct, 3),
                "pull_total_to_6": round(final_grade - MID, 3),
                "dist_from_6_final": round(abs(final_grade - MID), 3),
            }
        )
    return out


def summarize(df: pd.DataFrame, title: str) -> None:
    print(f"\n=== {title} ===")
    print(f"Players: {len(df)}")
    if df.empty:
        return

    def q(col: str, ps=(0.1, 0.25, 0.5, 0.75, 0.9)):
        vals = df[col].quantile(ps)
        return ", ".join(f"p{int(p*100)}={vals[p]:+.3f}" for p in ps)

    print(f"z delta (shrunk - raw): mean={df.z_delta.mean():+.3f}, {q('z_delta')}")
    print(f"confidence: mean={df.confidence.mean():.3f}, {q('confidence', (0.1,0.25,0.5,0.75,0.9))}")
    print(f"efetivo: mean={df.efetivo.mean():.3f}, {q('efetivo', (0.1,0.25,0.5,0.75,0.9))}")
    print(
        "pull conf (grade - pct_before_conf): "
        f"mean={df.pull_conf_to_6.mean():+.3f}, {q('pull_conf_to_6')}"
    )
    print(
        f"|grade-6| final: mean={df.dist_from_6_final.mean():.3f}, "
        f"median={df.dist_from_6_final.median():.3f}"
    )

    # Buckets by confidence
    bins = [0, 0.5, 0.7, 0.85, 1.01]
    labels = ["<0.50", "0.50-0.70", "0.70-0.85", ">=0.85"]
    df = df.copy()
    df["conf_bucket"] = pd.cut(df.confidence, bins=bins, labels=labels, right=False)
    bucket = (
        df.groupby("conf_bucket", observed=True)
        .agg(
            n=("player", "count"),
            conf_mean=("confidence", "mean"),
            pull_mean=("pull_conf_to_6", "mean"),
            pull_p90=("pull_conf_to_6", lambda s: s.quantile(0.1)),
            grade_mean=("grade_final", "mean"),
            pct_mean=("pct_before_conf", "mean"),
        )
        .round(3)
    )
    print("\nBy confidence bucket:")
    print(bucket.to_string())

    # What if confidence pull were removed?
    no_conf = df.pct_before_conf
    print(
        f"\nIf confidence pull removed: mean grade {no_conf.mean():.2f} "
        f"(now {df.grade_final.mean():.2f}); "
        f"mean |grade-6| {abs(no_conf - MID).mean():.2f} "
        f"(now {df.dist_from_6_final.mean():.2f})"
    )


def main() -> int:
    _, players = xe.build_european_league_xp_analytics()
    if not players:
        print("no players")
        return 1

    pools: dict[str, list[dict]] = {}
    for player in players:
        pools.setdefault(xs._metric_rank_pool_key(player), []).append(player)

    records: list[dict] = []
    for rows in pools.values():
        records.extend(analyze_pool(rows))

    df = pd.DataFrame(records)
    summarize(df, "ALL POOLS")

    # High vs low sample
    low = df[df.confidence < 0.7]
    high = df[df.confidence >= 0.85]
    summarize(low, "LOW CONFIDENCE (<0.70)")
    summarize(high, "HIGH CONFIDENCE (>=0.85)")

    # Top rated: how much conf pull hurts them
    top = df.nlargest(20, "pct_before_conf")
    print("\n=== TOP 20 BY PCT BEFORE CONFIDENCE ===")
    cols = [
        "player",
        "team",
        "minutes",
        "passes",
        "confidence",
        "pct_before_conf",
        "grade_final",
        "pull_conf_to_6",
    ]
    print(top[cols].to_string(index=False))

    # Biggest victims of confidence pull among good players
    good = df[df.pct_before_conf >= 7.5].copy()
    good["abs_pull"] = good.pull_conf_to_6.abs()
    victims = good.nsmallest(15, "pull_conf_to_6")
    print("\n=== GOOD PLAYERS (pct>=7.5) MOST PULLED TOWARD 6 ===")
    print(victims[cols].to_string(index=False))

    # Shrinkage-only effect on z for extreme minutes
    print("\n=== SHRINKAGE WEIGHT vs MINUTES (xp_per_90) ===")
    for m in (200, 450, 900, 1350, 1800, 2700):
        w = m / (m + pe.SHRINKAGE_MINUTES_K)
        print(f"  {m:4d} min -> weight={w:.3f} (pull toward pool mean)")

    print("\n=== SHRINKAGE WEIGHT vs PASSES (xp_m4_per_pass) ===")
    for p in (100, 300, 600, 900, 1200, 1800):
        w = p / (p + pe.SHRINKAGE_PASS_K)
        print(f"  {p:4d} passes -> weight={w:.3f}")

    print("\n=== CONFIDENCE FORMULA EXAMPLES ===")
    for minutes, passes, p25 in (
        (300, 200, 400),
        (600, 400, 400),
        (900, 600, 500),
        (1350, 900, 500),
        (1800, 1200, 600),
        (2700, 1800, 700),
    ):
        conf_passes = min(1.0, passes / max(p25, 1.0))
        conf_minutes = min(1.0, minutes / pe.RATING_CONFIDENCE_MINUTES)
        conf = 0.5 * conf_passes + 0.5 * conf_minutes
        efetivo = 1.0 - xs.XP_PASS_RATING_CONFIDENCE_WEIGHT * (1.0 - conf)
        pull_at_8 = (1.0 - efetivo) * (MID - 8.0)
        pull_at_7 = (1.0 - efetivo) * (MID - 7.0)
        print(
            f"  min={minutes:4d} pass={passes:4d} p25={p25:.0f} -> "
            f"conf={conf:.2f} efetivo={efetivo:.2f} | "
            f"pull@8.0={pull_at_8:+.2f} pull@7.0={pull_at_7:+.2f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
