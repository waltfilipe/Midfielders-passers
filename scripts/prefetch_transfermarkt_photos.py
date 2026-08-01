"""Backfill Transfermarkt portrait URLs for cached players.

Uses the stored transfermarkt_id to fetch portraitUrl without re-running search.
Run offline; the app reads transfermarkt_photo_url as a fallback when photo_url
from TheSportsDB is missing.

Examples:
    python scripts/prefetch_transfermarkt_photos.py --only-missing
    python scripts/prefetch_transfermarkt_photos.py --only-missing --missing-primary-photo
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
from player_profiles import read_cached_profile


def _needs_fetch(
    player: dict,
    *,
    only_missing: bool,
    missing_primary_photo: bool,
    force: bool,
) -> bool:
    if force:
        return True
    pid = str(player.get("player_id", ""))
    profile = read_cached_profile(pid)
    if not profile.get("transfermarkt_id"):
        return False
    if missing_primary_photo and profile.get("photo_url"):
        return False
    if not only_missing:
        return True
    return not profile.get("transfermarkt_photo_url")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prefetch Transfermarkt portrait URLs.")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Fetch only players without transfermarkt_photo_url in cache.",
    )
    parser.add_argument(
        "--missing-primary-photo",
        action="store_true",
        help="Restrict to players whose TheSportsDB photo_url is empty.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch portrait URLs even when already cached.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.25,
        help="Delay between network requests in seconds (default: 0.25).",
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
        if _needs_fetch(
            player,
            only_missing=args.only_missing,
            missing_primary_photo=args.missing_primary_photo,
            force=args.force,
        )
    ]
    if args.limit > 0:
        targets = targets[: args.limit]

    total = len(targets)
    print(
        f"Prefetching Transfermarkt photos for {total}/{len(players)} midfielders "
        f"(only_missing={args.only_missing}, missing_primary_photo={args.missing_primary_photo}, "
        f"force={args.force})…",
        flush=True,
    )

    resolved = 0
    errors = 0
    for i, player in enumerate(targets, start=1):
        pid = str(player.get("player_id", ""))
        name = str(player.get("player_name", ""))
        try:
            profile = tm.prefetch_transfermarkt_photo_for_player(pid, force=args.force)
        except Exception as exc:  # noqa: BLE001 - keep batch prefetch running
            errors += 1
            print(f"  ERROR {i}/{total} · {name}: {exc}", flush=True)
            if args.sleep > 0:
                time.sleep(args.sleep)
            continue
        if profile.get("transfermarkt_photo_url"):
            resolved += 1
        if i % 20 == 0 or i == total:
            print(f"  {i}/{total} · photos: {resolved} · errors: {errors}", flush=True)
        if args.sleep > 0:
            time.sleep(args.sleep)

    fallback_ready = 0
    for player in players:
        pid = str(player["player_id"])
        profile = read_cached_profile(pid)
        if profile.get("photo_url") or profile.get("transfermarkt_photo_url"):
            fallback_ready += 1
    print(
        f"Done. Players with a primary or fallback photo in cache: {fallback_ready}/{len(players)}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
