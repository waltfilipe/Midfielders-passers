"""European outfield position families for on-demand app loading."""

from __future__ import annotations

from heuristic_scoring import rating_position_group

DEFAULT_POSITION_FAMILY = "midfielders"

EUROPEAN_POSITION_FAMILIES: tuple[tuple[str, str], ...] = (
    ("centerbacks", "Zagueiros"),
    ("fullbacks", "Laterais"),
    ("midfielders", "Meio-campistas"),
    ("wingers", "Extremos"),
)

EUROPEAN_POSITION_FAMILY_KEYS: tuple[str, ...] = tuple(
    key for key, _label in EUROPEAN_POSITION_FAMILIES
)

EUROPEAN_POSITION_FAMILY_LABELS: dict[str, str] = dict(EUROPEAN_POSITION_FAMILIES)

POSITION_CODES_BY_FAMILY: dict[str, frozenset[str]] = {
    "centerbacks": frozenset({"CB", "RCB", "LCB"}),
    "fullbacks": frozenset({"RB", "RWB", "LB", "LWB"}),
    "midfielders": frozenset({
        "CM", "CDM", "DM", "RCM", "LCM", "RDM", "LDM", "CAM",
    }),
    "wingers": frozenset({"RW", "RM", "LW", "LM"}),
}

RATING_GROUPS_BY_FAMILY: dict[str, frozenset[str]] = {
    "centerbacks": frozenset({"centerbacks"}),
    "fullbacks": frozenset({"fullbacks"}),
    "midfielders": frozenset({
        "midfielders",
        "central_midfielders",
        "attacking_midfielders",
    }),
    "wingers": frozenset({"wingers"}),
}


def normalize_position_family(position_family: str | None) -> str:
    key = str(position_family or DEFAULT_POSITION_FAMILY).strip().lower()
    if key not in EUROPEAN_POSITION_FAMILY_LABELS:
        raise ValueError(f"Unknown position family: {position_family!r}")
    return key


def position_family_label(position_family: str | None) -> str:
    return EUROPEAN_POSITION_FAMILY_LABELS.get(
        normalize_position_family(position_family),
        str(position_family or "—"),
    )


def position_codes_for_family(position_family: str | None) -> frozenset[str]:
    return POSITION_CODES_BY_FAMILY[normalize_position_family(position_family)]


def rating_groups_for_family(position_family: str | None) -> frozenset[str]:
    return RATING_GROUPS_BY_FAMILY[normalize_position_family(position_family)]


def is_position_code_in_family(position: str | None, position_family: str | None) -> bool:
    if not position:
        return False
    return str(position).strip().upper() in position_codes_for_family(position_family)


def is_rating_group_in_family(
    position_group: str | None,
    position_family: str | None,
) -> bool:
    if not position_group:
        return False
    return str(position_group).strip().lower() in rating_groups_for_family(position_family)


def player_belongs_to_family(player: dict, position_family: str | None) -> bool:
    group = str(player.get("position_group") or "").strip().lower()
    if group and is_rating_group_in_family(group, position_family):
        return True
    return is_position_code_in_family(player.get("position"), position_family)


def family_for_position_code(position: str | None) -> str | None:
    if not position:
        return None
    pos = str(position).strip().upper()
    for family, codes in POSITION_CODES_BY_FAMILY.items():
        if pos in codes:
            return family
    group = rating_position_group(pos)
    if group is None:
        return None
    for family, groups in RATING_GROUPS_BY_FAMILY.items():
        if group in groups:
            return family
    return None


def family_for_rating_group(position_group: str | None) -> str | None:
    if not position_group:
        return None
    group = str(position_group).strip().lower()
    for family, groups in RATING_GROUPS_BY_FAMILY.items():
        if group in groups:
            return family
    return None
