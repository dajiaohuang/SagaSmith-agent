"""Blocking single-card normalization and validation.

This deliberately does not enqueue work. The caller waits for one LLM rewrite,
then validates rules and verifies that the resulting JSON survives the official
character-sheet XLSX export/import path before it may be persisted.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from app.config import PROJECT_ROOT, settings
from app.llm import chat_completion
from app.tools.character_builder import (
    build_character_data,
    export_character_sheet,
    parse_character_sheet_xlsx,
)
from app.tools.character_rules import ABILITY_KEYS, CLASS_HIT_DICE, derive_character_rules


SUBMIT_CARD_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_single_card",
        "description": "Submit exactly one rules-valid D&D 5E 2014 character-sheet record.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "character_name": {"type": "string"},
                "class_name": {"type": "string"},
                "level": {"type": "integer", "minimum": 1, "maximum": 20},
                "ancestry": {"type": "string"},
                "subrace": {"type": "string"},
                "background": {"type": "string"},
                "alignment": {"type": "string"},
                "gender": {"type": "string"},
                "age": {"type": "string"},
                "faith": {"type": "string"},
                "appearance": {"type": "string"},
                "traits": {"type": "string"},
                "ideals": {"type": "string"},
                "bonds": {"type": "string"},
                "flaws": {"type": "string"},
                "backstory": {"type": "string"},
                "abilities": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {key: {"type": "integer"} for key in ABILITY_KEYS},
                    "required": list(ABILITY_KEYS),
                },
                "max_hp": {"type": "integer", "minimum": 1},
                "armor_class": {"type": "integer", "minimum": 1},
                "speed": {"type": "integer", "minimum": 0},
                "spellcasting_ability": {
                    "type": "string", "enum": ["", "int", "wis", "cha"],
                },
            },
            "required": [
                "character_name", "class_name", "level", "ancestry", "background",
                "abilities", "max_hp", "armor_class", "speed",
            ],
        },
    },
}


def _extract_tool_arguments(response: Any) -> dict[str, Any]:
    for call in list(getattr(response, "tool_calls", None) or []):
        if getattr(call.function, "name", "") == "submit_single_card":
            value = json.loads(call.function.arguments or "{}")
            if isinstance(value, dict):
                return value
    raise ValueError("单卡 Subagent 未返回 submit_single_card 结构化结果。")


def _validate_raw(raw: dict[str, Any], actor_type: str) -> None:
    allowed = set(SUBMIT_CARD_TOOL["function"]["parameters"]["properties"]) | {
        "actor_type", "player_name",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError("单卡包含模板契约之外的字段：" + "、".join(unknown))
    missing = [
        key for key in ("character_name", "class_name", "ancestry", "background")
        if not str(raw.get(key) or "").strip()
    ]
    if missing:
        raise ValueError("单卡缺少必填字段：" + "、".join(missing))
    level = int(raw.get("level") or 0)
    if not 1 <= level <= 20:
        raise ValueError("角色等级必须在 1-20。")
    abilities = raw.get("abilities") or {}
    if set(abilities) != set(ABILITY_KEYS):
        raise ValueError("单卡必须包含六项且仅包含六项属性。")
    scores = {key: int(abilities[key]) for key in ABILITY_KEYS}
    if actor_type == "player":
        if any(not 8 <= score <= 15 for score in scores.values()):
            raise ValueError("玩家角色使用 27 点购点时，基础属性必须在 8-15。")
        from app.tools.character_rules import point_buy_cost
        cost = point_buy_cost(scores)
        if cost is None or cost > 27:
            raise ValueError("玩家角色属性不符合 D&D 5E 27 点购点规则。")
        class_name = str(raw.get("class_name") or "").strip()
        if class_name not in CLASS_HIT_DICE and class_name.lower() not in CLASS_HIT_DICE:
            raise ValueError(f"未知的 D&D 5E 职业：{class_name}")
    elif any(not 1 <= score <= 30 for score in scores.values()):
        raise ValueError("NPC 属性必须在 D&D 5E 有效范围 1-30。")
    derived = derive_character_rules(raw)
    if level == 1:
        expected_hp = max(1, int(derived["hit_die"]) + int(derived["ability_modifiers"]["con"]))
        if int(raw.get("max_hp") or 0) != expected_hp:
            raise ValueError(f"1 级最大生命值应为 {expected_hp}。")


def _template_path() -> Path:
    candidates = list((settings.data_dir / "raw").glob("*人物卡模板.xlsx"))
    if not candidates:
        candidates = list((PROJECT_ROOT / "data" / "raw").glob("*人物卡模板.xlsx"))
    if not candidates:
        raise ValueError("未找到 D&D 5E 人物卡模板 XLSX。")
    return candidates[0]


def _verify_xlsx_roundtrip(data: dict[str, Any], player_name: str) -> None:
    with TemporaryDirectory(prefix="dm-single-card-") as temp_dir:
        target = Path(temp_dir) / "card.xlsx"
        export_character_sheet(data, player_name, _template_path(), target)
        parsed = parse_character_sheet_xlsx(target)
    if not parsed:
        raise ValueError("结构化角色卡无法由模板 XLSX 反向解析。")
    basic = data["basic"]
    primary_class = basic["classes"][0]
    expected = {
        "character_name": basic["name"],
        "class_name": primary_class["name"],
        "level": int(primary_class["level"]),
        "ancestry": basic["ancestry"],
        "background": basic["background"],
        "alignment": basic["alignment"],
        "gender": basic["gender"],
        "age": basic["age"],
        "appearance": basic["appearance"],
        "traits": data["personality"]["traits"],
        "ideals": data["personality"]["ideals"],
        "bonds": data["personality"]["bonds"],
        "flaws": data["personality"]["flaws"],
        "backstory": data["personality"]["backstory"],
        "abilities": data["abilities"],
        "max_hp": int(data["combat"]["max_hp"]),
        "armor_class": int(data["combat"]["armor_class"]),
        "speed": int(data["combat"]["speed"]),
        "spellcasting_ability": data["spellcasting"]["ability"],
    }
    actual = {
        "character_name": parsed.get("character_name"),
        "class_name": parsed.get("class_name"),
        "level": int(parsed.get("level") or 0),
        "ancestry": parsed.get("ancestry"),
        "background": parsed.get("background"),
        "alignment": parsed.get("alignment"),
        "gender": parsed.get("gender"),
        "age": parsed.get("age"),
        "appearance": parsed.get("appearance"),
        "traits": parsed.get("traits"),
        "ideals": parsed.get("ideals"),
        "bonds": parsed.get("bonds"),
        "flaws": parsed.get("flaws"),
        "backstory": parsed.get("backstory"),
        "abilities": parsed.get("abilities"),
        "max_hp": int(parsed.get("max_hp") or 0),
        "armor_class": int(parsed.get("armor_class") or 0),
        "speed": int(parsed.get("speed") or 0),
        "spellcasting_ability": parsed.get("spellcasting_ability"),
    }
    if actual != expected:
        mismatches = [key for key in expected if expected[key] != actual.get(key)]
        raise ValueError("角色卡未通过 XLSX 往返一致性校验：" + "、".join(mismatches))


def rewrite_single_card_blocking(
    proposal: dict[str, Any], *, actor_type: str, player_name: str = "",
) -> dict[str, Any]:
    """Synchronously rewrite and validate exactly one card; never persists it."""
    if actor_type not in {"player", "npc"}:
        raise ValueError("actor_type must be player or npc")
    messages = [
        {
            "role": "system",
            "content": (
                "You are a blocking single-card normalization subagent. Rewrite exactly one "
                "D&D 5E 2014 player character or NPC concept into the supplied tool schema. "
                "Only normalize the provided concept and derive required mechanics; do not expand "
                "the story or invent homebrew mechanics. For a player, use legal 27-point-buy "
                "base scores (8-15), a PHB class, and rules-consistent HP/AC/speed. For an NPC, "
                "keep ability scores in 1-30. The schema is the exact XLSX-compatible contract. "
                "Call submit_single_card exactly once."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {"actor_type": actor_type, "proposal": proposal},
                ensure_ascii=False,
            ),
        },
    ]
    last_error = "单卡 Subagent 未产生有效结果。"
    for _attempt in range(3):
        response = chat_completion(
            messages,
            temperature=0.1,
            tools=[SUBMIT_CARD_TOOL],
            tool_choice="required",
            timeout=120,
        )
        try:
            if response is None or isinstance(response, str):
                raise ValueError("单卡 Subagent 不可用或未返回结构化工具调用。")
            raw = _extract_tool_arguments(response)
            raw["actor_type"] = actor_type
            raw["player_name"] = player_name or ("DM" if actor_type == "npc" else "Player")
            _validate_raw(raw, actor_type)
            data = build_character_data(raw)
            errors = list(data.get("validation_errors") or [])
            if actor_type == "npc":
                errors = [error for error in errors if not error.startswith("Point buy")]
            if errors:
                raise ValueError("角色卡规则校验失败：" + "；".join(errors))
            _verify_xlsx_roundtrip(data, raw["player_name"])
            return data
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            messages.append({
                "role": "user",
                "content": f"Validation failed: {last_error} Fix only this one card and resubmit.",
            })
    raise ValueError(f"单卡 Subagent 连续三次未通过校验：{last_error}")
