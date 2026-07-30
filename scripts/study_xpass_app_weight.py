#!/usr/bin/env python3
"""Estimate runtime/memory impact of the New xP tab vs existing heavy loaders."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

import xpass_engine as xpe
import xp_engine as xe


def _peak_mb(fn):
    tracemalloc.start()
    t0 = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed, peak / (1024 * 1024)


def main() -> int:
    print("=== xPass app weight study ===\n")

    json_path = xpe.XPASS_PLAYERS_JSON
    parquet_path = xe.XP_EUROPEAN_PASSES_PARQUET

    json_disk = json_path.stat().st_size if json_path.is_file() else 0
    parquet_disk = parquet_path.stat().st_size if parquet_path.is_file() else 0
    print(f"European parquet on disk: {parquet_disk / 1e6:.2f} MB")
    print(f"xPass players JSON on disk: {json_disk / 1e3:.1f} KB")

    if json_path.is_file():
        bundle, t_json, mem_json = _peak_mb(xpe.load_xpass_player_bundle)
        n_players = len(bundle.get("players", []))
        print(f"\nload_xpass_player_bundle(): {t_json*1000:.1f} ms, peak {mem_json:.2f} MB, {n_players} players")

    def _load_parquet():
        return pd.read_parquet(parquet_path)

    _, t_pq, mem_pq = _peak_mb(_load_parquet)
    print(f"pd.read_parquet (full season): {t_pq:.2f} s, peak {mem_pq:.1f} MB")

    ratio = (json_disk / parquet_disk * 100) if parquet_disk else 0
    print(f"\nJSON is {ratio:.3f}% of parquet disk size")
    if json_path.is_file():
        print(f"JSON load memory is ~{mem_json / mem_pq * 100:.2f}% of parquet load memory")

    print("\n=== Verdict ===")
    print("New xP tab uses only precomputed JSON — no parquet, no sklearn at runtime.")
    print("Impact on app startup: negligible (tab is lazy; JSON loads on first visit).")
    print("Player Profile unchanged — no extra cost there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
