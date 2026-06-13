from __future__ import annotations

from typing import Any


ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")
POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
SKILL_ABILITIES = {
    "athletics": "str",
    "acrobatics": "dex",
    "sleight_of_hand": "dex",
    "stealth": "dex",
    "arcana": "int",
    "history": "int",
    "investigation": "int",
    "nature": "int",
    "religion": "int",
    "animal_handling": "wis",
    "insight": "wis",
    "medicine": "wis",
    "perception": "wis",
    "survival": "wis",
    "deception": "cha",
    "intimidation": "cha",
    "performance": "cha",
    "persuasion": "cha",
}
CLASS_SAVING_THROWS = {
    "barbarian": ("str", "con"), "野蛮人": ("str", "con"),
    "bard": ("dex", "cha"), "吟游诗人": ("dex", "cha"),
    "cleric": ("wis", "cha"), "牧师": ("wis", "cha"),
    "druid": ("int", "wis"), "德鲁伊": ("int", "wis"),
    "fighter": ("str", "con"), "战士": ("str", "con"),
    "monk": ("str", "dex"), "武僧": ("str", "dex"),
    "paladin": ("wis", "cha"), "圣武士": ("wis", "cha"),
    "ranger": ("str", "dex"), "游侠": ("str", "dex"),
    "rogue": ("dex", "int"), "游荡者": ("dex", "int"),
    "sorcerer": ("con", "cha"), "术士": ("con", "cha"),
    "warlock": ("wis", "cha"), "邪术师": ("wis", "cha"),
    "wizard": ("int", "wis"), "法师": ("int", "wis"),
    "artificer": ("con", "int"), "奇械师": ("con", "int"),
}
CLASS_HIT_DICE = {
    "barbarian": 12, "野蛮人": 12,
    "fighter": 10, "战士": 10, "paladin": 10, "圣武士": 10, "ranger": 10, "游侠": 10,
    "bard": 8, "吟游诗人": 8, "cleric": 8, "牧师": 8, "druid": 8, "德鲁伊": 8,
    "monk": 8, "武僧": 8, "rogue": 8, "游荡者": 8, "warlock": 8, "邪术师": 8,
    "artificer": 8, "奇械师": 8,
    "sorcerer": 6, "术士": 6, "wizard": 6, "法师": 6,
}


def ability_modifier(score: int) -> int:
    return score // 2 - 5


def proficiency_bonus(level: int) -> int:
    return 2 + (max(1, level) - 1) // 4


def point_buy_cost(abilities: dict[str, int]) -> int | None:
    if set(abilities) != set(ABILITY_KEYS) or any(score not in POINT_BUY_COSTS for score in abilities.values()):
        return None
    return sum(POINT_BUY_COSTS[score] for score in abilities.values())


def skill_bonus(
    skill: str,
    abilities: dict[str, int],
    proficiency: int,
    proficient: bool = False,
    expertise: bool = False,
    misc: int = 0,
) -> int:
    ability = SKILL_ABILITIES[skill]
    multiplier = 2 if expertise else 1 if proficient else 0
    return ability_modifier(abilities[ability]) + proficiency * multiplier + misc


def saving_throw_bonus(
    ability: str,
    abilities: dict[str, int],
    proficiency: int,
    proficient: bool = False,
    misc: int = 0,
) -> int:
    return ability_modifier(abilities[ability]) + (proficiency if proficient else 0) + misc


def armor_class(
    abilities: dict[str, int],
    armor_type: str = "unarmored",
    armor_base: int = 10,
    shield_bonus: int = 0,
    misc: int = 0,
    dexterity_cap: int | None = None,
    class_name: str = "",
) -> int:
    dexterity = ability_modifier(abilities["dex"])
    if armor_type in {"heavy", "重型"}:
        dexterity = 0
    elif armor_type in {"medium", "中型"}:
        dexterity = min(dexterity, 2 if dexterity_cap is None else dexterity_cap)
    elif dexterity_cap is not None:
        dexterity = min(dexterity, dexterity_cap)
    if armor_type in {"unarmored", "无甲"}:
        key = class_name.strip().lower()
        if key in {"barbarian", "野蛮人"}:
            armor_base = 10 + ability_modifier(abilities["con"])
        elif key in {"monk", "武僧"}:
            armor_base = 10 + ability_modifier(abilities["wis"])
    return armor_base + dexterity + shield_bonus + misc


def derive_character_rules(raw: dict[str, Any]) -> dict[str, Any]:
    abilities = {key: int(raw.get("abilities", {}).get(key, 10)) for key in ABILITY_KEYS}
    class_name = str(raw.get("class_name", "")).strip()
    class_key = class_name.lower()
    level = int(raw.get("level", 1))
    proficiency = proficiency_bonus(level)
    hit_die = int(raw.get("hit_die") or CLASS_HIT_DICE.get(class_key) or CLASS_HIT_DICE.get(class_name) or 8)
    save_proficiencies = list(raw.get("saving_throw_proficiencies") or CLASS_SAVING_THROWS.get(class_key)
                              or CLASS_SAVING_THROWS.get(class_name) or [])
    skills = {
        name: {
            "proficient": name in raw.get("skill_proficiencies", []),
            "expertise": name in raw.get("skill_expertise", []),
            "bonus": skill_bonus(
                name, abilities, proficiency,
                name in raw.get("skill_proficiencies", []),
                name in raw.get("skill_expertise", []),
            ),
        }
        for name in SKILL_ABILITIES
    }
    spellcasting_ability = str(raw.get("spellcasting_ability", "")).lower()
    spell_modifier = ability_modifier(abilities.get(spellcasting_ability, 10)) if spellcasting_ability else None
    return {
        "ability_modifiers": {key: ability_modifier(value) for key, value in abilities.items()},
        "proficiency_bonus": proficiency,
        "point_buy_cost": point_buy_cost(abilities),
        "point_buy_remaining": None if point_buy_cost(abilities) is None else 27 - point_buy_cost(abilities),
        "hit_die": hit_die,
        "saving_throw_proficiencies": save_proficiencies,
        "saving_throws": {
            key: saving_throw_bonus(key, abilities, proficiency, key in save_proficiencies)
            for key in ABILITY_KEYS
        },
        "skills": skills,
        "initiative": ability_modifier(abilities["dex"]),
        "passive_perception": 10 + skills["perception"]["bonus"],
        "spell_save_dc": 8 + proficiency + spell_modifier if spell_modifier is not None else None,
        "spell_attack_bonus": proficiency + spell_modifier if spell_modifier is not None else None,
        "carrying_capacity": abilities["str"] * 15,
        "encumbered_at": abilities["str"] * 5,
        "heavily_encumbered_at": abilities["str"] * 10,
    }


def validate_character_rules(raw: dict[str, Any], derived: dict[str, Any]) -> list[str]:
    errors = []
    if derived["point_buy_cost"] is not None and derived["point_buy_cost"] > 27:
        errors.append(f"Point buy exceeds 27 points: {derived['point_buy_cost']}")
    if derived["point_buy_cost"] is None:
        errors.append("Point buy requires all six ability scores between 8 and 15.")
    if int(raw.get("level", 1)) > 1 and not raw.get("max_hp"):
        errors.append("Characters above level 1 must provide max_hp until level-up HP choices are implemented.")
    selected_skills = set(raw.get("skill_proficiencies", [])) | set(raw.get("skill_expertise", []))
    unknown_skills = sorted(selected_skills - set(SKILL_ABILITIES))
    if unknown_skills:
        errors.append(f"Unknown skills: {', '.join(unknown_skills)}")
    if int(raw.get("hit_die") or derived["hit_die"]) not in {6, 8, 10, 12}:
        errors.append("Hit die must be d6, d8, d10, or d12.")
    return errors
