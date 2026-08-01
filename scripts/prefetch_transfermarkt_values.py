"""Prefetch Transfermarkt market values for European midfielders.

Run offline so the Streamlit app reads values from player_profiles_cache.json
without hitting Transfermarkt on every page load.

Examples:
    python scripts/prefetch_transfermarkt_values.py --only-missing --limit 10
    python scripts/prefetch_transfermarkt_values.py --force
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import passes_engine as pe
import transfermarkt_profiles as tm


def _needs_fetch(player: dict, *, only_missing: bool, force: bool) -> bool:
    if force:
        return True
    if not only_missing:
        return True
    pid = str(player.get("player_id", ""))
    return not tm.transfermarkt_cache_is_fresh(pid, force=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prefetch Transfermarkt market values.")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Fetch only players without a cached market value.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch every player, even when the cache already has a value.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.35,
        help="Delay between network requests in seconds (default: 0.35).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on number of players to fetch (0 = all targets).",
    )
    args = parser.parse_args()

    players = pe.build_european_league_midfielders()
    targets = [
        player
        for player in players
        if _needs_fetch(player, only_missing=args.only_missing, force=args.force)
    ]
    if args.limit > 0:
        targets = targets[: args.limit]

    total = len(targets)
    print(
        f"Prefetching Transfermarkt values for {total}/{len(players)} midfielders "
        f"(only_missing={args.only_missing}, force={args.force})…",
        flush=True,
    )

    resolved = 0
    not_found = 0
    errors = 0
    for i, player in enumerate(targets, start=1):
        pid = str(player.get("player_id", ""))
        name = str(player.get("player_name", ""))
        team = str(player.get("team", ""))
        try:
            profile = tm.prefetch_transfermarkt_for_player(
                pid,
                name,
                team,
                force=args.force,
            )
        except Exception as exc:  # noqa: BLE001 - keep batch prefetch running
            errors += 1
            print(f"  ERROR {i}/{total} · {name} ({team}): {exc}", flush=True)
            if args.sleep > 0:
                time.sleep(args.sleep)
            continue
        if profile.get("market_value_eur") is not None or profile.get("market_value_display"):
            resolved += 1
        elif profile.get("transfermarkt_fetch_status") == "not_found":
            not_found += 1
        if i % 10 == 0 or i == total:
            print(
                f"  {i}/{total} · values: {resolved} · not found: {not_found} · errors: {errors}",
                flush=True,
            )
        if args.sleep > 0:
            time.sleep(args.sleep)

    all_with_value = sum(
        1
        for player in players
        if tm.read_cached_market_value(str(player["player_id"])) is not None
    )
    print(
        f"Done. Market values cached for {all_with_value}/{len(players)} players.",
        flush=True,
    )


if __name__ == "__main__":
    main()
