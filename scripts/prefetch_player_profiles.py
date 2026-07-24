"""One-off: pre-populate the player profile cache (age, height, foot) for European midfielders.

Run offline so the app reads ages from cache without any network calls in the hot path.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import passes_engine as pe
import player_profiles as pp


def main() -> None:
    players = pe.build_european_league_midfielders()
    total = len(players)
    print(f"Prefetching profiles for {total} midfielders…", flush=True)
    resolved_age = 0
    for i, player in enumerate(players, start=1):
        profile = pp.get_player_profile(
            str(player.get("player_id", "")),
            str(player.get("player_name", "")),
            str(player.get("team", "")),
        )
        if profile.get("age") is not None:
            resolved_age += 1
        if i % 25 == 0 or i == total:
            print(f"  {i}/{total} · ages resolved: {resolved_age}", flush=True)
        time.sleep(0.15)
    print(f"Done. Ages resolved for {resolved_age}/{total} players.", flush=True)


if __name__ == "__main__":
    main()
