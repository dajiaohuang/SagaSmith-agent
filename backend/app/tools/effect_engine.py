from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.tools.character_rules import ABILITY_KEYS, SKILL_ABILITIES, ability_modifier


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class EffectSource(FlexibleModel):
    type: str = "custom"
    source_id: str = ""
    actor_id: str = ""
    item_id: str = ""


class EffectDuration(FlexibleModel):
    type: str = "permanent"
    remaining: int | None = None
    tick_on: str = "round_end"
    expires_at: str | None = None
    expire_trigger: str | None = None


class EffectConsumption(FlexibleModel):
    type: str = "none"
    remaining_uses: int | None = None
    eligible_rolls: list[str] = Field(default_factory=list)


class EffectStacking(FlexibleModel):
    group: str = ""
    mode: str = "stack"
    priority: int = 0


class EffectModifier(FlexibleModel):
    target: str
    operation: str = "add"
    value: Any = 0
    conditions: dict[str, Any] = Field(default_factory=dict)


class ActiveEffect(FlexibleModel):
    effect_id: str = ""
    definition_id: str = ""
    name: str = "自定义效果"
    source: EffectSource = Field(default_factory=EffectSource)
    target: dict[str, Any] = Field(default_factory=dict)
    scope: str = "both"
    status: str = "active"
    duration: EffectDuration = Field(default_factory=EffectDuration)
    consumption: EffectConsumption = Field(default_factory=EffectConsumption)
    concentration: dict[str, Any] = Field(default_factory=dict)
    stacking: EffectStacking = Field(default_factory=EffectStacking)
    modifiers: list[EffectModifier] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str | None = None
    created_by: str = ""


def normalize_effect(raw: dict[str, Any], *, source: dict[str, Any] | None = None) -> dict[str, Any]:
    value = copy.deepcopy(raw)
    if not value.get("effect_id"):
        value["effect_id"] = f"effect_{uuid4().hex[:12]}"
    if not value.get("definition_id"):
        value["definition_id"] = value.get("effect_type") or value["effect_id"]
    if not value.get("name"):
        value["name"] = value.get("description") or value["definition_id"]
    if "modifiers" not in value:
        value["modifiers"] = copy.deepcopy((value.get("data") or {}).get("modifiers") or [])
    if source:
        value["source"] = {**source, **(value.get("source") or {})}
    return ActiveEffect.model_validate(value).model_dump(mode="json")


def normalize_effects(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [normalize_effect(item) for item in (raw or [])]


def _item_effects(data: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in data.get("inventory") or []:
        if not item.get("equipped") or not item.get("quantity", 1):
            continue
        if item.get("attunement_required") and not item.get("attuned"):
            continue
        for raw in item.get("effects") or []:
            activation = raw.get("activation") or (raw.get("data") or {}).get("activation") or {}
            if activation.get("requires_attunement") and not item.get("attuned"):
                continue
            result.append(normalize_effect(raw, source={
                "type": "item",
                "source_id": item.get("instance_id") or item.get("item_id", ""),
                "item_id": item.get("instance_id") or item.get("item_id", ""),
            }))
    return result


def _scope_active(scope: str, combat: bool) -> bool:
    return scope in {"both", "campaign", "scene"} or scope == "combat_only" and combat or scope == "non_combat_only" and not combat


def collect_active_effects(data: dict[str, Any], combat: bool = False) -> list[dict[str, Any]]:
    candidates = [*normalize_effects(data.get("active_effects")), *_item_effects(data)]
    candidates = [
        item for item in candidates
        if item.get("status") == "active"
        and _scope_active(item.get("scope", "both"), combat)
        and ((item.get("consumption") or {}).get("remaining_uses") is None
             or int((item.get("consumption") or {}).get("remaining_uses")) > 0)
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    independent = []
    for item in candidates:
        stacking = item.get("stacking") or {}
        group = stacking.get("group") or ""
        if not group or stacking.get("mode", "stack") == "stack":
            independent.append(item)
        else:
            grouped.setdefault(group, []).append(item)
    for items in grouped.values():
        mode = (items[-1].get("stacking") or {}).get("mode", "non_stackable")
        if mode in {"replace", "unique"}:
            independent.append(items[-1])
        elif mode in {"highest", "lowest"}:
            def effect_value(item: dict[str, Any]) -> float:
                values = [
                    abs(float(modifier.get("value", 0)))
                    for modifier in item.get("modifiers") or []
                    if isinstance(modifier.get("value"), (int, float))
                ]
                return max(values, default=0)
            independent.append((max if mode == "highest" else min)(items, key=effect_value))
        else:
            independent.append(max(items, key=lambda item: int((item.get("stacking") or {}).get("priority", 0))))
    return independent


def _apply_numeric(current: int | float, operation: str, value: Any) -> int | float:
    number = float(value)
    if operation == "add":
        return current + number
    if operation == "subtract":
        return current - number
    if operation == "set":
        return number
    if operation == "minimum":
        return max(current, number)
    if operation == "maximum":
        return min(current, number)
    if operation == "multiply":
        return current * number
    return current


def _numeric_modifiers(effects: list[dict[str, Any]], target: str, base: int | float) -> int | float:
    result = base
    for effect in effects:
        for modifier in effect.get("modifiers") or []:
            if modifier.get("target") == target and modifier.get("operation") in {
                "add", "subtract", "set", "minimum", "maximum", "multiply",
            }:
                result = _apply_numeric(result, modifier.get("operation", "add"), modifier.get("value", 0))
    return int(result) if float(result).is_integer() else result


def resolve_effective_character(data: dict[str, Any], combat: bool = False) -> dict[str, Any]:
    base = copy.deepcopy(data or {})
    effects = collect_active_effects(base, combat)
    abilities = {
        key: int(_numeric_modifiers(effects, f"abilities.{key}", int((base.get("abilities") or {}).get(key, 10))))
        for key in ABILITY_KEYS
    }
    original_abilities = {key: int((base.get("abilities") or {}).get(key, 10)) for key in ABILITY_KEYS}
    modifiers = {key: ability_modifier(value) for key, value in abilities.items()}
    original_modifiers = {key: ability_modifier(value) for key, value in original_abilities.items()}
    combat_data = copy.deepcopy(base.get("combat") or {})
    derived = copy.deepcopy(base.get("derived") or {})
    for key in ("armor_class", "speed", "initiative", "proficiency_bonus", "passive_perception", "max_hp"):
        fallback = derived.get(key, 0)
        combat_data[key] = _numeric_modifiers(effects, f"combat.{key}", combat_data.get(key, fallback))
    skills = copy.deepcopy(base.get("skills") or derived.get("skills") or {})
    for name, ability in SKILL_ABILITIES.items():
        entry = skills.get(name, {})
        raw_bonus = entry.get("bonus", 0) if isinstance(entry, dict) else entry
        bonus = int(raw_bonus) + modifiers[ability] - original_modifiers[ability]
        bonus = _numeric_modifiers(effects, f"skills.{name}", bonus)
        skills[name] = {**entry, "bonus": bonus} if isinstance(entry, dict) else bonus
    saves = copy.deepcopy(base.get("saving_throws") or derived.get("saving_throws") or {})
    for ability in ABILITY_KEYS:
        entry = saves.get(ability, original_modifiers[ability])
        raw_bonus = entry.get("bonus", 0) if isinstance(entry, dict) else entry
        bonus = int(raw_bonus) + modifiers[ability] - original_modifiers[ability]
        bonus = _numeric_modifiers(effects, f"saving_throws.{ability}", bonus)
        saves[ability] = {**entry, "bonus": bonus} if isinstance(entry, dict) else bonus
    spellcasting = copy.deepcopy(base.get("spellcasting") or {})
    for key in ("save_dc", "attack_bonus"):
        spellcasting[key] = _numeric_modifiers(effects, f"spellcasting.{key}", spellcasting.get(key, 0) or 0)
    roll_effects = []
    for effect in effects:
        for modifier in effect.get("modifiers") or []:
            if str(modifier.get("target", "")).startswith("roll.") or modifier.get("operation") in {"advantage", "disadvantage", "add_dice"}:
                roll_effects.append({**copy.deepcopy(modifier), "effect_id": effect["effect_id"], "effect_name": effect["name"]})
    effective = {
        "abilities": abilities,
        "ability_modifiers": modifiers,
        "combat": combat_data,
        "saving_throws": saves,
        "skills": skills,
        "spellcasting": spellcasting,
        "roll_effects": roll_effects,
        "active_effects": effects,
    }
    snapshot = copy.deepcopy(base)
    snapshot["effective"] = effective
    return snapshot


def roll_effects_for(snapshot: dict[str, Any], roll_type: str) -> dict[str, Any]:
    advantage = 0
    bonus_dice = []
    consumable_effect_ids = []
    for modifier in ((snapshot.get("effective") or {}).get("roll_effects") or []):
        eligible = (modifier.get("conditions") or {}).get("roll_types") or []
        if eligible and roll_type not in eligible:
            continue
        operation = modifier.get("operation")
        if operation == "advantage":
            advantage += 1
        elif operation == "disadvantage":
            advantage -= 1
        elif operation == "add_dice":
            bonus_dice.append(str(modifier.get("value")))
        consumable_effect_ids.append(modifier.get("effect_id"))
    return {
        "advantage": "advantage" if advantage > 0 else "disadvantage" if advantage < 0 else "normal",
        "bonus_dice": bonus_dice,
        "effect_ids": list(dict.fromkeys(item for item in consumable_effect_ids if item)),
    }


def add_effect(data: dict[str, Any], raw_effect: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    result = copy.deepcopy(data)
    effect = normalize_effect(raw_effect)
    effects = normalize_effects(result.get("active_effects"))
    removed = []
    concentration = effect.get("concentration") or {}
    owner = concentration.get("owner_character_id")
    if concentration.get("required") and owner:
        kept = []
        for current in effects:
            current_concentration = current.get("concentration") or {}
            if current_concentration.get("required") and current_concentration.get("owner_character_id") == owner:
                removed.append(current["effect_id"])
            else:
                kept.append(current)
        effects = kept
    stacking = effect.get("stacking") or {}
    if stacking.get("mode") in {"replace", "unique"} and stacking.get("group"):
        kept = []
        for current in effects:
            if (current.get("stacking") or {}).get("group") == stacking["group"]:
                removed.append(current["effect_id"])
            else:
                kept.append(current)
        effects = kept
    effects.append(effect)
    result["active_effects"] = effects
    return result, effect, removed


def remove_effect(data: dict[str, Any], query: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(data)
    lowered = query.casefold()
    removed = [
        item for item in normalize_effects(result.get("active_effects"))
        if lowered in item.get("effect_id", "").casefold()
        or lowered in item.get("definition_id", "").casefold()
        or lowered in item.get("name", "").casefold()
    ]
    removed_ids = {item["effect_id"] for item in removed}
    result["active_effects"] = [
        item for item in normalize_effects(result.get("active_effects")) if item["effect_id"] not in removed_ids
    ]
    return result, removed


def advance_effect_durations(data: dict[str, Any], trigger: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(data)
    kept, expired = [], []
    for effect in normalize_effects(result.get("active_effects")):
        duration = effect.get("duration") or {}
        if trigger == "combat_end" and effect.get("scope") == "combat_only":
            expired.append(effect)
            continue
        if duration.get("expire_trigger") == trigger:
            expired.append(effect)
            continue
        if duration.get("type") in {"rounds", "turns"} and duration.get("tick_on", "round_end") == trigger:
            remaining = int(duration.get("remaining") or 0) - 1
            effect["duration"]["remaining"] = remaining
            if remaining <= 0:
                expired.append(effect)
                continue
        kept.append(effect)
    result["active_effects"] = kept
    return result, expired


def consume_roll_effects(data: dict[str, Any], effect_ids: list[str], roll_type: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(data)
    consumed = []
    effects = normalize_effects(result.get("active_effects"))
    for effect in effects:
        if effect["effect_id"] not in effect_ids:
            continue
        consumption = effect.get("consumption") or {}
        eligible = consumption.get("eligible_rolls") or []
        if consumption.get("type") != "on_roll" or eligible and roll_type not in eligible:
            continue
        remaining = int(consumption.get("remaining_uses") or 0) - 1
        effect["consumption"]["remaining_uses"] = remaining
        consumed.append(effect)
        if remaining <= 0:
            effect["status"] = "consumed"
    result["active_effects"] = effects
    return result, consumed
