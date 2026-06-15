from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Campaign, Character
from app.services import append_event, serialize, update_character
from app.tools.effect_engine import add_effect, collect_active_effects, remove_effect, resolve_effective_character
from app.tools.dice import roll_dice


ABILITY_TARGETS = {
    "力量": "abilities.str", "敏捷": "abilities.dex", "体质": "abilities.con",
    "體質": "abilities.con", "智力": "abilities.int", "感知": "abilities.wis", "魅力": "abilities.cha",
}
MECHANICAL_TARGETS = {
    "ac": "combat.armor_class", "护甲等级": "combat.armor_class", "護甲等級": "combat.armor_class",
    "先攻": "combat.initiative", "速度": "combat.speed", "移动速度": "combat.speed", "移動速度": "combat.speed",
    **ABILITY_TARGETS,
}
PRESETS = {
    "祝福术": {
        "definition_id": "bless", "name": "祝福术", "scope": "both",
        "duration": {"type": "rounds", "remaining": 10, "tick_on": "round_end"},
        "stacking": {"group": "bless", "mode": "non_stackable"},
        "concentration": {"required": True},
        "modifiers": [{
            "target": "roll.bonus_dice", "operation": "add_dice", "value": "1d4",
            "conditions": {"roll_types": ["attack_roll", "saving_throw"]},
        }],
        "tags": ["buff", "spell"],
    },
    "吟游诗人激励": {
        "definition_id": "bardic_inspiration", "name": "吟游诗人激励", "scope": "both",
        "duration": {"type": "minutes", "remaining": 10},
        "consumption": {
            "type": "on_roll", "remaining_uses": 1,
            "eligible_rolls": ["ability_check", "attack_roll", "saving_throw"],
        },
        "stacking": {"group": "bardic_inspiration", "mode": "replace"},
        "modifiers": [{
            "target": "roll.bonus_dice", "operation": "add_dice", "value": "1d6",
            "conditions": {"roll_types": ["ability_check", "attack_roll", "saving_throw"]},
        }],
        "tags": ["buff", "feature"],
    },
}


def _result(narration: str, command: str, data: dict | None = None) -> dict:
    return {
        "ok": True, "kind": "effect_action", "command": command, "narration": narration,
        "data": data or {}, "rolls": [], "state_changes": [], "events": [],
    }


def _target_character(db: Session, campaign: Campaign, bound: Character | None, message: str) -> Character | None:
    characters = db.scalars(select(Character).where(Character.campaign_id == campaign.id)).all()
    named = [item for item in characters if item.character_name.casefold() in message.casefold()]
    return named[0] if len(named) == 1 else bound


def _natural_effect(message: str, actor_id: str | None) -> dict | None:
    for name, preset in PRESETS.items():
        if name in message:
            effect = json.loads(json.dumps(preset, ensure_ascii=False))
            if effect.get("concentration", {}).get("required"):
                effect["concentration"]["owner_character_id"] = actor_id or ""
            return effect
    json_match = re.search(r"\{.*\}", message, re.S)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    lowered = message.casefold()
    target = next((path for name, path in MECHANICAL_TARGETS.items() if name.casefold() in lowered), None)
    amount = re.search(r"([+-]\s*\d+)", message)
    if not target or not amount:
        return None
    value = int(amount.group(1).replace(" ", ""))
    rounds = re.search(r"持续\s*(\d+)\s*回合|持續\s*(\d+)\s*回合", message)
    combat_only = any(term in message for term in ("仅战斗", "只在战斗", "戰鬥中"))
    name = re.sub(r"\s+", " ", message).strip()[:80]
    return {
        "name": name,
        "definition_id": f"custom_{target.replace('.', '_')}",
        "scope": "combat_only" if combat_only else "both",
        "duration": {
            "type": "rounds" if rounds else "permanent",
            "remaining": int(next(group for group in rounds.groups() if group)) if rounds else None,
            "tick_on": "round_end",
        },
        "stacking": {"group": "", "mode": "stack"},
        "modifiers": [{"target": target, "operation": "add", "value": value}],
        "tags": ["custom", "buff" if value >= 0 else "debuff"],
        "created_by": actor_id or "",
    }


def resolve_effect_action(
    db: Session,
    campaign: Campaign,
    bound_character: Character | None,
    message: str,
    actor_id: str | None = None,
    session_id: str | None = None,
) -> dict | None:
    lowered = message.casefold()
    target = _target_character(db, campaign, bound_character, message)
    query_terms = ("查看效果", "当前效果", "當前效果", "有什么效果", "有什麼效果", "active effects")
    if any(term in lowered for term in query_terms):
        if not target:
            return _result("当前没有可查询的绑定角色。", "list_effects")
        combat = bool(((campaign.config or {}).get("turn_state") or {}).get("combat"))
        effects = collect_active_effects(target.data, combat)
        snapshot = resolve_effective_character(target.data, combat)["effective"]
        lines = [
            f"- {item['name']}（{item.get('scope', 'both')}，{(item.get('duration') or {}).get('type', 'permanent')}）"
            for item in effects
        ]
        return _result(
            f"{target.character_name} 当前生效效果：\n" + ("\n".join(lines) if lines else "（无）")
            + f"\n有效 AC：{snapshot['combat'].get('armor_class', '?')}，先攻：{snapshot['combat'].get('initiative', '?')}",
            "list_effects", {"effects": effects, "effective": snapshot},
        )
    remove_match = re.search(r"(?:移除效果|解除效果|取消效果|remove effect)\s*[：:]?\s*(.+)", message, re.I)
    if remove_match:
        if not target:
            return _result("当前没有可修改的绑定角色。", "remove_effect")
        next_data, removed = remove_effect(target.data, remove_match.group(1).strip())
        if not removed:
            return _result("没有找到匹配的持续效果。", "remove_effect")
        change = update_character(db, target, {"active_effects": next_data["active_effects"]},
                                  f"removed effect: {remove_match.group(1)}", "effect_removed")
        return _result(f"已从 {target.character_name} 移除：{'、'.join(item['name'] for item in removed)}",
                       "remove_effect", {"removed": removed, "change": serialize(change)})
    add_trigger = any(term in lowered for term in ("添加效果", "增加效果", "获得效果", "獲得效果", "施加", "添加buff", "添加debuff"))
    if not add_trigger:
        return None
    if not target:
        return _result("当前没有可修改的绑定角色，也没有唯一匹配的角色名。", "add_effect")
    effect = _natural_effect(message, target.id)
    if not effect:
        return _result(
            "无法解析效果机械数据。可使用例如“添加效果：AC +2，持续 3 回合”，或直接附带效果 JSON。",
            "add_effect",
        )
    next_data, added, removed = add_effect(target.data, effect)
    change = update_character(db, target, {"active_effects": next_data["active_effects"]},
                              f"added effect: {added['name']}", "effect_added", [added["definition_id"]])
    event = append_event(
        db, campaign.id, session_id, "effect_added", f"{target.character_name} 获得效果 {added['name']}",
        [target.id], {"effect": added, "replaced_effect_ids": removed},
    )
    result = _result(f"已为 {target.character_name} 添加效果：{added['name']}。", "add_effect", {
        "effect": added, "replaced_effect_ids": removed, "change": serialize(change),
    })
    result["events"] = [serialize(event)]
    return result


def resolve_concentration_damage(
    db: Session,
    campaign: Campaign,
    damaged_character: Character,
    damage: int,
) -> dict | None:
    owned = []
    for target in db.scalars(select(Character).where(Character.campaign_id == campaign.id)).all():
        for effect in target.data.get("active_effects") or []:
            concentration = effect.get("concentration") or {}
            if concentration.get("required") and concentration.get("owner_character_id") == damaged_character.id:
                owned.append((target, effect))
    if not owned:
        return None
    effective = resolve_effective_character(damaged_character.data, True)["effective"]
    con_save = (effective.get("saving_throws") or {}).get("con", 0)
    modifier = int(con_save.get("bonus", 0) if isinstance(con_save, dict) else con_save)
    dc = max(10, damage // 2)
    roll = roll_dice(f"1d20{modifier:+d}")
    removed = []
    if roll["total"] < dc:
        for target, effect in owned:
            next_data, matched = remove_effect(target.data, effect["effect_id"])
            if matched:
                update_character(db, target, {"active_effects": next_data["active_effects"]},
                                 "concentration broken by damage", "concentration_broken", [effect["definition_id"]])
                removed.extend(matched)
    return {"roll": roll, "dc": dc, "success": roll["total"] >= dc, "removed": removed}
