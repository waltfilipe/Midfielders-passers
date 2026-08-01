"""Transfermarkt market-value enrichment via transfermarkt-wrapper (offline prefetch only)."""

from __future__ import annotations

import asyncio
from typing import Any

from player_profiles import (
    _name_match_score,
    _normalize_name,
    _normalize_team,
    _team_match_score,
    read_cached_profile,
    update_player_profile_cache,
)

TRANSFERMARKT_FETCH_STATUS_KEY = "transfermarkt_fetch_status"
TRANSFERMARKT_ID_KEY = "transfermarkt_id"
TRANSFERMARKT_PHOTO_URL_KEY = "transfermarkt_photo_url"
MARKET_VALUE_EUR_KEY = "market_value_eur"
MARKET_VALUE_DISPLAY_KEY = "market_value_display"
MARKET_VALUE_UPDATED_KEY = "market_value_updated"
TMKT_MAX_RETRIES = 4
TMKT_RETRY_BACKOFF_SEC = 1.5


async def _tmkt_call_with_retry(coro_factory, *, label: str):
    last_error: Exception | None = None
    for attempt in range(TMKT_MAX_RETRIES):
        try:
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001 - retry transient Transfermarkt API failures
            last_error = exc
            if attempt >= TMKT_MAX_RETRIES - 1:
                break
            await asyncio.sleep(TMKT_RETRY_BACKOFF_SEC * (attempt + 1))
    raise RuntimeError(f"Transfermarkt request failed for {label}: {last_error}") from last_error


def _tmkt_row_name(row: dict) -> str:
    name_field = str(row.get("name") or "").strip()
    club = str(row.get("club") or "").strip()
    if club and name_field.endswith(club):
        return name_field[: -len(club)].strip()
    return name_field


def _pick_tmkt_search_result(
    results: list[dict],
    *,
    player_name: str,
    team: str,
) -> dict | None:
    if not results:
        return None
    target_name = _normalize_name(player_name)
    scored: list[tuple[float, dict]] = []
    for row in results:
        row_name = _normalize_name(_tmkt_row_name(row))
        name_score = _name_match_score(row_name, target_name)
        team_score = _team_match_score(row.get("club"), team)
        min_team = 0.55 if len(target_name.split()) == 1 else 0.2
        if team_score < min_team and name_score < 0.95:
            continue
        scored.append((name_score * 0.65 + team_score * 0.35, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return None
    best_score, best_row = scored[0]
    return best_row if best_score >= 0.45 else None


def _transfermarkt_fields_from_player_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    current = (data.get("marketValueDetails") or {}).get("current") or {}
    value_eur = current.get("value")
    compact = current.get("compact") or {}
    display = None
    if isinstance(compact, dict) and compact.get("content"):
        display = (
            f"{compact.get('prefix', '')}"
            f"{compact.get('content', '')}"
            f"{compact.get('suffix', '')}"
        )
    elif value_eur is not None:
        display = format_market_value_eur(int(value_eur))
    portrait = data.get("portraitUrl")
    return {
        MARKET_VALUE_EUR_KEY: int(value_eur) if value_eur is not None else None,
        MARKET_VALUE_DISPLAY_KEY: display,
        MARKET_VALUE_UPDATED_KEY: current.get("determined"),
        TRANSFERMARKT_PHOTO_URL_KEY: str(portrait) if portrait else None,
    }


def _market_value_from_player_payload(payload: dict[str, Any]) -> dict[str, Any]:
    fields = _transfermarkt_fields_from_player_payload(payload)
    return {
        MARKET_VALUE_EUR_KEY: fields.get(MARKET_VALUE_EUR_KEY),
        MARKET_VALUE_DISPLAY_KEY: fields.get(MARKET_VALUE_DISPLAY_KEY),
        MARKET_VALUE_UPDATED_KEY: fields.get(MARKET_VALUE_UPDATED_KEY),
    }


def format_market_value_eur(value_eur: int) -> str:
    if value_eur >= 1_000_000:
        amount = value_eur / 1_000_000
        text = f"{amount:.2f}".rstrip("0").rstrip(".")
        return f"€{text}M"
    if value_eur >= 1_000:
        amount = value_eur / 1_000
        text = f"{amount:.1f}".rstrip("0").rstrip(".")
        return f"€{text}K"
    return f"€{value_eur:,}"


def read_cached_market_value(player_id: str) -> str | None:
    """Cached Transfermarkt market value label (e.g. €55.00M) or None. No network."""
    profile = read_cached_profile(player_id)
    display = profile.get(MARKET_VALUE_DISPLAY_KEY)
    if display:
        return str(display)
    value_eur = profile.get(MARKET_VALUE_EUR_KEY)
    if value_eur is not None:
        try:
            return format_market_value_eur(int(value_eur))
        except (TypeError, ValueError):
            return None
    return None


def read_cached_market_value_eur(player_id: str) -> int | None:
    """Cached Transfermarkt market value in EUR or None. No network."""
    value_eur = read_cached_profile(player_id).get(MARKET_VALUE_EUR_KEY)
    if value_eur is None:
        return None
    try:
        return int(value_eur)
    except (TypeError, ValueError):
        return None


def transfermarkt_cache_is_fresh(player_id: str, *, force: bool = False) -> bool:
    if force:
        return False
    profile = read_cached_profile(player_id)
    if not profile:
        return False
    if profile.get(MARKET_VALUE_EUR_KEY) is not None or profile.get(MARKET_VALUE_DISPLAY_KEY):
        return True
    return profile.get(TRANSFERMARKT_FETCH_STATUS_KEY) == "not_found"


async def fetch_transfermarkt_market_value_async(
    player_name: str,
    team: str,
) -> dict[str, Any]:
    from tmkt import TMKT

    queries = [player_name]
    if team:
        queries.append(f"{player_name} {team}")

    best_row: dict | None = None
    best_score = 0.0
    seen_ids: set[str] = set()

    async with TMKT() as tmkt:
        for query in queries:
            results = await _tmkt_call_with_retry(
                lambda q=query: tmkt.player_search(q),
                label=f"search:{query}",
            )
            if not isinstance(results, list):
                continue
            for row in results:
                row_id = str(row.get("id") or "")
                if row_id and row_id in seen_ids:
                    continue
                if row_id:
                    seen_ids.add(row_id)
            picked = _pick_tmkt_search_result(results, player_name=player_name, team=team)
            if not picked:
                continue
            row_name = _normalize_name(_tmkt_row_name(picked))
            target_name = _normalize_name(player_name)
            score = _name_match_score(row_name, target_name) * 0.65 + _team_match_score(
                picked.get("club"),
                team,
            ) * 0.35
            if score > best_score:
                best_row = picked
                best_score = score

        if not best_row:
            return {TRANSFERMARKT_FETCH_STATUS_KEY: "not_found"}

        player_id = int(best_row["id"])
        payload = await _tmkt_call_with_retry(
            lambda pid=player_id: tmkt.get_player(pid),
            label=f"player:{player_id}",
        )
        fields = _transfermarkt_fields_from_player_payload(payload if isinstance(payload, dict) else {})
        status = "ok" if fields.get(MARKET_VALUE_EUR_KEY) is not None else "not_found"
        return {
            TRANSFERMARKT_ID_KEY: str(player_id),
            TRANSFERMARKT_FETCH_STATUS_KEY: status,
            **fields,
        }


def fetch_transfermarkt_market_value(player_name: str, team: str) -> dict[str, Any]:
    """Network fetch for offline prefetch scripts. Do not call from Streamlit hot path."""
    return asyncio.run(fetch_transfermarkt_market_value_async(player_name, team))


def prefetch_transfermarkt_for_player(
    player_id: str,
    player_name: str,
    team: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    pid = str(player_id or "").strip()
    if transfermarkt_cache_is_fresh(pid, force=force):
        return read_cached_profile(pid)
    fetched = fetch_transfermarkt_market_value(player_name, team)
    return update_player_profile_cache(pid, fetched)


async def fetch_transfermarkt_photo_by_id_async(transfermarkt_id: str) -> dict[str, Any]:
    from tmkt import TMKT

    async with TMKT() as tmkt:
        payload = await _tmkt_call_with_retry(
            lambda tid=int(transfermarkt_id): tmkt.get_player(tid),
            label=f"player-photo:{transfermarkt_id}",
        )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    portrait = data.get("portraitUrl")
    return {
        TRANSFERMARKT_PHOTO_URL_KEY: str(portrait) if portrait else None,
    }


def prefetch_transfermarkt_photo_for_player(
    player_id: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    pid = str(player_id or "").strip()
    profile = read_cached_profile(pid)
    if not force and profile.get(TRANSFERMARKT_PHOTO_URL_KEY):
        return profile
    transfermarkt_id = profile.get(TRANSFERMARKT_ID_KEY)
    if not transfermarkt_id:
        return profile
    fetched = asyncio.run(fetch_transfermarkt_photo_by_id_async(str(transfermarkt_id)))
    return update_player_profile_cache(pid, fetched)
