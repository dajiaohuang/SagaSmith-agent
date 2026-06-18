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
            "name": "show_lobby",
            "description": "查看大厅：列出全部战役，并标出当前选中的战役。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_campaign_simple",
            "description": "直接创建并选中一个新战役。只在用户明确要求创建战役时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "战役名称"},
                    "description": {"type": "string", "description": "一句话简介，可留空"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_random_proposal",
            "description": "保存 Agent 当场生成的一个随机战役或角色设定，等待用户确认。不会直接创建。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["campaign", "character", "npc"]},
                    "proposal": {
                        "type": "object",
                        "description": (
                            "战役需包含 name、description；角色需包含 name、class_name、"
                            "level、ancestry、background、abilities，可附加 backstory/appearance。"
                        ),
                    },
                },
                "required": ["kind", "proposal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_random_proposal",
            "description": "用户明确说要、确认、就用这个时，把当前待确认的随机设定正式创建为战役或角色。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discard_random_proposal",
            "description": "用户明确拒绝当前随机设定时清除它。用户要求换一个时不要调用，直接生成并保存新提案。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
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

def handle_show_lobby(
    db: Session, campaign: Campaign | None, **_kw: Any,
) -> dict:
    from sqlalchemy import select
    from app.qq_bindings import active_napcat_campaign

    campaigns = db.scalars(select(Campaign).order_by(Campaign.updated_at.desc())).all()
    active = active_napcat_campaign(db) or campaign
    if not campaigns:
        return _ok("大厅里还没有战役。告诉我一个名称，我可以直接创建。", campaign_ids=[])
    lines = ["战役大厅："]
    for item in campaigns:
        marker = "（当前）" if active and item.id == active.id else ""
        lines.append(f"- {item.name}{marker} [{item.id}]")
    lines.append("你可以创建新战役、切换战役，或进入当前战役。")
    return _ok(
        "\n".join(lines),
        campaign_ids=[item.id for item in campaigns],
        active_campaign_id=active.id if active else None,
        turn_consuming=False,
    )


def handle_create_campaign_simple(
    db: Session, campaign: Campaign | None, name: str = "",
    description: str = "", **_kw: Any,
) -> dict:
    from app.qq_bindings import set_active_napcat_campaign
    from app.services import uid

    name = name.strip()
    if not name:
        return _err("请先告诉我新战役的名称。")
    new_campaign = Campaign(
        id=uid("camp"),
        name=name,
        description=description.strip(),
        system_version="DND_5E_2014",
        config={"play_style": "lobby", "scene": "新场景"},
    )
    db.add(new_campaign)
    db.commit()
    set_active_napcat_campaign(db, new_campaign)
    return _ok(
        f"已创建并选中战役「{new_campaign.name}」。你可以继续建卡，或直接进入 DM。",
        campaign_id=new_campaign.id,
    )


def handle_save_random_proposal(
    db: Session, campaign: Campaign | None, kind: str = "",
    proposal: dict | None = None, session_id: str | None = None,
    message_context: dict | None = None, **_kw: Any,
) -> dict:
    proposal = copy.deepcopy(proposal or {})
    if kind not in {"campaign", "character", "npc"}:
        return _err("随机设定类型必须是 campaign、character 或 npc。")
    if kind in {"character", "npc"} and campaign is None:
        return _err("请先创建或选中一个战役，再随机生成角色或 NPC。")
    if not str(proposal.get("name") or "").strip():
        return _err("随机设定缺少名称，请重新生成。")
    if kind in {"character", "npc"} and not str(proposal.get("class_name") or "").strip():
        return _err("单卡设定缺少职业或生物类型，请重新生成。")

    state = copy.deepcopy(_get_state(db, campaign, session_id))
    state["pending_proposal"] = {"kind": kind, "proposal": proposal}
    _set_state(db, campaign, state, session_id, message_context)
    label = {"campaign": "战役", "character": "角色", "npc": "NPC"}[kind]
    return _ok(
        f"随机{label}设定：\n{json.dumps(proposal, ensure_ascii=False, indent=2)}\n"
        f"要用这个设定创建{label}吗？你也可以说“换一个”。",
        pending_proposal=state["pending_proposal"],
        turn_consuming=False,
    )


def handle_confirm_random_proposal(
    db: Session, campaign: Campaign | None, session_id: str | None = None,
    message_context: dict | None = None, user_id: str = "", **_kw: Any,
) -> dict:
    state = copy.deepcopy(_get_state(db, campaign, session_id))
    pending = state.get("pending_proposal") or {}
    kind = pending.get("kind")
    proposal = copy.deepcopy(pending.get("proposal") or {})
    if kind not in {"campaign", "character", "npc"} or not proposal:
        return _err("当前没有等待确认的随机设定。")

    if kind == "campaign":
        state.pop("pending_proposal", None)
        _set_state(db, campaign, state, session_id, message_context)
        return handle_create_campaign_simple(
            db=db,
            campaign=campaign,
            name=str(proposal.get("name") or ""),
            description=str(proposal.get("description") or proposal.get("summary") or ""),
        )
    if campaign is None:
        return _err("请先创建或选中一个战役，再创建角色。")

    from app.db.models import Character
    from app.qq_bindings import bind_qq
    from app.services import uid
    from app.blocking_card_subagent import rewrite_single_card_blocking

    actor_type = "npc" if kind == "npc" else "player"
    data = rewrite_single_card_blocking(
        proposal,
        actor_type=actor_type,
        player_name="DM" if actor_type == "npc" else (user_id or "Player"),
    )
    state.pop("pending_proposal", None)
    _set_state(db, campaign, state, session_id, message_context)
    character_name = str((data.get("basic") or {}).get("name") or "").strip()
    character = Character(
        id=uid("char"), campaign_id=campaign.id,
        player_name="DM" if actor_type == "npc" else (user_id or "Player"),
        character_name=character_name, data=data,
    )
    db.add(character)
    db.commit()
    if actor_type == "player" and user_id.isdigit():
        bind_qq(db, campaign.id, user_id, character, character.character_name)
    return _ok(
        f"单卡已通过规则与 XLSX 往返校验，并创建{(' NPC' if actor_type == 'npc' else '角色')}"
        f"「{character.character_name}」（{character.id}）。",
        character_id=character.id,
    )


def handle_discard_random_proposal(
    db: Session, campaign: Campaign | None, session_id: str | None = None,
    message_context: dict | None = None, **_kw: Any,
) -> dict:
    state = copy.deepcopy(_get_state(db, campaign, session_id))
    if not state.pop("pending_proposal", None):
        return _ok("当前没有等待确认的随机设定。", turn_consuming=False)
    _set_state(db, campaign, state, session_id, message_context)
    return _ok("已放弃当前随机设定。", turn_consuming=False)


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
    "show_lobby": handle_show_lobby,
    "create_campaign_simple": handle_create_campaign_simple,
    "save_random_proposal": handle_save_random_proposal,
    "confirm_random_proposal": handle_confirm_random_proposal,
    "discard_random_proposal": handle_discard_random_proposal,
    "get_lobby_state": handle_get_lobby_state,
    "set_lobby_state": handle_set_lobby_state,
    "resolve_lobby_option": handle_resolve_lobby_option,
    "create_campaign_now": handle_create_campaign_now,
}
