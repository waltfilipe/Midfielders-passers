"""Nationality region presets for player pool filters."""

from __future__ import annotations

NATIONALITY_REGION_WORLD = "World"
NATIONALITY_REGION_WESTERN_EUROPE = "Western Europe"
NATIONALITY_REGION_EASTERN_EUROPE = "Eastern Europe"
NATIONALITY_REGION_LATIN_AMERICA = "Latin America"
NATIONALITY_REGION_AFRICA = "Africa"

NATIONALITY_REGION_OPTIONS: tuple[str, ...] = (
    NATIONALITY_REGION_WORLD,
    NATIONALITY_REGION_WESTERN_EUROPE,
    NATIONALITY_REGION_EASTERN_EUROPE,
    NATIONALITY_REGION_LATIN_AMERICA,
    NATIONALITY_REGION_AFRICA,
)

# Canonical nationality labels as stored in player_profiles_cache.json.
NATIONALITY_ALIASES: dict[str, str] = {
    "kingdom of denmark": "Denmark",
    "kingdom of the netherlands": "The Netherlands",
    "ivory coast": "Ivory Coast",
    "macedonia": "North Macedonia",
    "united kingdom": "United Kingdom",
}

NATIONALITY_REGION_COUNTRIES: dict[str, frozenset[str]] = {
    NATIONALITY_REGION_WESTERN_EUROPE: frozenset({
        "Albania",
        "Austria",
        "Belgium",
        "Denmark",
        "England",
        "France",
        "Germany",
        "Iceland",
        "Ireland",
        "Italy",
        "Kingdom of Denmark",
        "Kingdom of the Netherlands",
        "Norway",
        "Portugal",
        "Scotland",
        "Spain",
        "Sweden",
        "Switzerland",
        "The Netherlands",
        "United Kingdom",
        "Wales",
    }),
    NATIONALITY_REGION_EASTERN_EUROPE: frozenset({
        "Armenia",
        "Bosnia and Herzegovina",
        "Bulgaria",
        "Croatia",
        "Czechia",
        "Hungary",
        "Kosovo",
        "Lithuania",
        "Macedonia",
        "Montenegro",
        "Poland",
        "Romania",
        "Serbia",
        "Slovakia",
        "Ukraine",
    }),
    NATIONALITY_REGION_LATIN_AMERICA: frozenset({
        "Argentina",
        "Brazil",
        "Chile",
        "Colombia",
        "Ecuador",
        "Guadeloupe",
        "Honduras",
        "Mexico",
        "Paraguay",
        "Uruguay",
        "Venezuela",
    }),
    NATIONALITY_REGION_AFRICA: frozenset({
        "Algeria",
        "Cameroon",
        "Central African Republic",
        "DR Congo",
        "Equatorial Guinea",
        "Ghana",
        "Guinea",
        "Ivory Coast",
        "Libya",
        "Mali",
        "Mauritania",
        "Morocco",
        "Nigeria",
        "Senegal",
        "Tunisia",
        "Zambia",
        "Zimbabwe",
    }),
}


def normalize_nationality(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    return NATIONALITY_ALIASES.get(text.lower(), text)


def countries_for_regions(regions: list[str] | tuple[str, ...] | None) -> set[str]:
    selected: set[str] = set()
    for region in regions or []:
        if region == NATIONALITY_REGION_WORLD:
            continue
        selected.update(NATIONALITY_REGION_COUNTRIES.get(region, ()))
    return selected


def resolve_nationality_filter(
    regions: list[str] | tuple[str, ...] | None,
    countries: list[str] | tuple[str, ...] | None,
) -> set[str] | None:
    """Return allowed nationalities, or None when no nationality filter should apply."""
    region_list = list(regions or [])
    country_list = list(countries or [])
    non_world_regions = [region for region in region_list if region != NATIONALITY_REGION_WORLD]
    if not non_world_regions and not country_list:
        return None
    allowed = countries_for_regions(non_world_regions)
    allowed.update(country_list)
    return allowed


def nationality_matches_filter(
    nationality: str | None,
    *,
    allowed: set[str] | None,
) -> bool:
    if not allowed:
        return True
    normalized = normalize_nationality(nationality)
    if not normalized:
        return False
    if normalized in allowed:
        return True
    # Allow alias overlap between region sets and cache labels.
    for candidate in allowed:
        if candidate.lower() == normalized.lower():
            return True
    return False
