"""Lobby mode tools — simple state management for the game-external mode.

The LLM fully controls the lobby flow. These tools give it direct
read/write access to ``campaign.config.lobby_state``.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Campaign


def _ok(narration: str, **kw: Any) -> dict:
    return {"ok": True, "kind": "lobby", "narration": narration, "data": kw or {}}


def _err(narration: str) -> dict:
    return {"ok": False, "kind": "lobby", "narration": narration}


def _get_state(db: Session, campaign: Campaign | None, session_id: str | None = None) -> dict:
    if campaign is None:
        from app.lobby_sessions import lobby_state
        return lobby_state(db, session_id)
    return (campaign.config or {}).get("lobby_state") or {}


def _set_state(
    db: Session, campaign: Campaign | None, state: dict,
    session_id: str | None = None, message_context: dict | None = None,
) -> None:
    if campaign is None:
        from app.lobby_sessions import set_lobby_state
        set_lobby_state(db, session_id, state, message_context=message_context)
        return
    cfg = copy.deepcopy(campaign.config or {})
    cfg["lobby_state"] = state
    campaign.config = cfg
    db.commit()


# ═══════════════════════════════════════════════════════════════════
#  LLM TOOL SCHEMAS
# ═══════════════════════════════════════════════════════════════════

LOBBY_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_lobby_state",
            "description": "读取大厅当前状态(DM确认/待选选项/生成的设定等)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_lobby_state",
            "description": "更新大厅状态。LLM自由控制流程: 设置待选选项/保存生成的设定/标记DM已确认等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "object",
                        "description": (
                            "要合并到大厅状态的键值对。支持的键:\n"
                            "- dm_confirmed: true/false\n"
                            "- pending_options: [{id,action,label}]\n"
                            "- generated_setting: {name,description}\n"
                            "- confirmed_campaign: 战役名(已确认要创建)\n"
                        ),
                    },
                },
                "required": ["state"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_lobby_option",
            "description": "执行用户选择的待选选项(用户回复数字时调用)",
            "parameters": {
                "type": "object",
                "properties": {
                    "option_number": {"type": "integer", "description": "选项编号(1开始)"},
                },
                "required": ["option_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_campaign_now",
            "description": "确认创建战役(用户同意后调用)。从lobby_state.generated_setting读取名称和设定。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ═══════════════════════════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════════════════════════

def handle_get_lobby_state(
    db: Session, campaign: Campaign | None, session_id: str | None = None, **_kw: Any,
) -> dict:
    state = _get_state(db, campaign, session_id)
    return _ok(json.dumps(state, ensure_ascii=False, indent=2), state=state)


def handle_set_lobby_state(
    db: Session, campaign: Campaign | None, state: dict | None = None,
    session_id: str | None = None, message_context: dict | None = None, **_kw: Any,
) -> dict:
    if not state:
        return _err("state is required")
    current = _get_state(db, campaign, session_id)
    current.update(state)
    _set_state(db, campaign, current, session_id, message_context)
    return _ok(f"大厅状态已更新。{len(current)} 个键。", state=current)


def handle_resolve_lobby_option(
    db: Session, campaign: Campaign | None,
    option_number: int = 0, session_id: str | None = None,
    message_context: dict | None = None, **_kw: Any,
) -> dict:
    state = _get_state(db, campaign, session_id)
    options = state.get("pending_options") or []
    if option_number < 1 or option_number > len(options):
        return _err(f"选项不存在。可选 1-{len(options)}。")
    opt = options[option_number - 1]
    action = opt.get("action", "")

    if action == "create_campaign":
        return _create_campaign_from_state(db, campaign, state)

    elif action == "regenerate":
        state.pop("generated_setting", None)
        state.pop("pending_options", None)
        _set_state(db, campaign, state, session_id, message_context)
        return _ok("已清除。请描述你想要的新战役。")

    elif action == "enter_dm":
        if campaign is None:
            return _err("当前没有活跃战役。请先创建战役。")
        cfg = copy.deepcopy(campaign.config or {})
        cfg["play_style"] = "campaign"
        cfg["lobby_state"] = state
        campaign.config = cfg; db.commit()
        return _ok(f"已进入 DM 模式。当前战役: {campaign.name}。")

    elif action == "enter_dice":
        if campaign is None:
            return _err("当前没有活跃战役。请先创建战役。")
        cfg = copy.deepcopy(campaign.config or {})
        cfg["play_style"] = "dice_assistant"
        cfg["lobby_state"] = state
        campaign.config = cfg; db.commit()
        return _ok(f"已进入骰娘模式。当前战役: {campaign.name}。")

    return _err(f"未知操作: {action}")


def handle_create_campaign_now(
    db: Session, campaign: Campaign | None, session_id: str | None = None, **_kw: Any,
) -> dict:
    state = _get_state(db, campaign, session_id)
    return _create_campaign_from_state(db, campaign, state)


def _create_campaign_from_state(
    db: Session, campaign: Campaign | None, state: dict,
) -> dict:
    gs = state.get("generated_setting") or {}
    name = gs.get("name", "新战役")
    desc = gs.get("description", "")
    state["dm_confirmed"] = True
    if campaign is None:
        from app.db.models import Campaign as _Campaign
        from app.qq_bindings import set_active_napcat_campaign
        from app.services import uid
        new_campaign = _Campaign(
            id=uid("camp"), name=name, description=desc,
            system_version="DND_5E_2014",
            config={"play_style": "lobby", "lobby_state": copy.deepcopy(state)},
        )
        db.add(new_campaign)
        db.commit()
        set_active_napcat_campaign(db, new_campaign)
        return _ok(f"已创建并切换到新战役“{name}”（{new_campaign.id}）。",
                   campaign_id=new_campaign.id)
    cfg = copy.deepcopy(campaign.config or {})
    cfg["pending_generated_campaign_name"] = name
    cfg["pending_generated_campaign_description"] = desc
    cfg["lobby_state"] = state
    campaign.config = cfg; db.commit()
    from app.campaign_control import execute_command
    from app.commands import Command
    return execute_command(
        db, Command("create_campaign_from_prompt"), campaign,
        None, None, True, None,
    )


LOBBY_HANDLERS = {
    "get_lobby_state": handle_get_lobby_state,
    "set_lobby_state": handle_set_lobby_state,
    "resolve_lobby_option": handle_resolve_lobby_option,
    "create_campaign_now": handle_create_campaign_now,
}
