#!/usr/bin/env python3
"""Train xPass model and export European midfielder metrics (offline only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import xpass_engine as xpe


def main() -> None:
    print(f"Building xPass model ({xpe.XPASS_MODEL_VERSION})...")
    meta = xpe.build_and_save_european_xpass(refit=True)
    print("CV (match-fold):", meta.get("cv_match_metrics"))
    print("Full sample:", meta.get("full_sample_metrics"))
    print(f"Players exported: {meta.get('n_players')}")
    print("Done:", xpe.XPASS_PLAYERS_JSON)


if __name__ == "__main__":
    main()
