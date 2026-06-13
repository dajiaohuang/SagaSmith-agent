from __future__ import annotations

import copy
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commands import Command
from app.db.models import Campaign, CampaignCheckpoint, CampaignEvent, Character
from app.services import append_event, create_summary, serialize, uid
from app.campaign_turns import (
    advance_turn, end_combat, enter_turn_mode, exit_turn_mode, format_turn_state,
    start_combat, turn_notification,
)


DM_ONLY_COMMANDS = {"save", "pause", "resume", "start_combat", "end_combat", "next_turn"}


def campaign_status(campaign: Campaign) -> str:
    return str((campaign.config or {}).get("status") or "active")


def set_campaign_status(campaign: Campaign, status: str, session_id: str | None = None) -> None:
    config = copy.deepcopy(campaign.config or {})
    config["status"] = status
    if session_id:
        config["active_session_id"] = session_id
    campaign.config = config


def create_checkpoint(
    db: Session,
    campaign: Campaign,
    session_id: str | None,
    created_by: str | None,
    label: str,
) -> CampaignCheckpoint:
    summary = create_summary(db, campaign.id, session_id)
    characters = db.scalars(select(Character).where(Character.campaign_id == campaign.id)).all()
    latest_event = db.scalar(
        select(CampaignEvent)
        .where(CampaignEvent.campaign_id == campaign.id)
        .order_by(CampaignEvent.created_at.desc())
        .limit(1)
    )
    checkpoint = CampaignCheckpoint(
        id=uid("checkpoint"),
        campaign_id=campaign.id,
        session_id=session_id,
        label=label,
        created_by=created_by,
        campaign_snapshot=json.loads(json.dumps(serialize(campaign), default=str)),
        character_snapshots=json.loads(json.dumps([serialize(character) for character in characters], default=str)),
        latest_event_id=latest_event.id if latest_event else None,
        summary_id=summary.id,
    )
    db.add(checkpoint)
    config = copy.deepcopy(campaign.config or {})
    config["last_checkpoint_id"] = checkpoint.id
    campaign.config = config
    db.commit()
    return checkpoint


def execute_command(
    db: Session,
    command: Command,
    campaign: Campaign,
    session_id: str | None,
    actor_id: str | None,
    is_dm: bool,
) -> dict:
    if command.name in DM_ONLY_COMMANDS and not is_dm:
        return command_result(command.name, "该命令仅限 DM 使用。", ok=False)

    if command.name == "help":
        return command_result("help", (
            "可用命令：\n"
            "/帮助 - 查看命令\n"
            "/状态 - 查看战役状态\n"
            "/保存 - 创建战役检查点（DM）\n"
            "/暂停 - 保存并暂停战役（DM）\n"
            "/继续 - 继续已暂停战役（DM）\n"
            "/回合模式 - 进入非战斗回合制\n"
            "/退出回合模式 - 退出非战斗回合制\n"
            "/进入战斗 - 投掷全体先攻并进入战斗（DM）\n"
            "/结束战斗 - 结束战斗并返回自由模式（DM）\n"
            "/下一回合 - 跳过当前行动者（DM）\n"
            "/法术 法术名 - 直接查询合并法术表"
        ))

    if command.name == "status":
        config = campaign.config or {}
        checkpoint = config.get("last_checkpoint_id") or "无"
        return command_result("status", (
            f"战役：{campaign.name}\n"
            f"状态：{campaign_status(campaign)}\n"
            f"当前会话：{config.get('active_session_id') or session_id or '无'}\n"
            f"最近检查点：{checkpoint}\n"
            f"{format_turn_state(campaign)}"
        ), data={"status": campaign_status(campaign), "last_checkpoint_id": config.get("last_checkpoint_id")})

    if command.name == "enter_turn_mode":
        state = enter_turn_mode(db, campaign)
        notification = turn_notification(db, campaign)
        append_event(db, campaign.id, session_id, "turn_mode_entered", "进入回合模式", [], {"turn_state": state})
        return command_result(
            "enter_turn_mode",
            f"已进入回合制模式。\n{format_turn_state(campaign)}",
            data={"turn_state": state, "turn_notification": notification},
        )

    if command.name == "exit_turn_mode":
        if not exit_turn_mode(db, campaign):
            return command_result(
                "exit_turn_mode",
                "战斗进行中，不能退出回合模式。请由 DM 使用 /结束战斗。",
                ok=False,
            )
        append_event(db, campaign.id, session_id, "turn_mode_exited", "退出回合模式", [], {})
        return command_result("exit_turn_mode", "已退出回合制模式，返回自由扮演模式。")

    if command.name == "start_combat":
        state = start_combat(db, campaign)
        if not state["participants"]:
            return command_result("start_combat", "战役中没有可加入战斗的角色。", ok=False)
        notification = turn_notification(db, campaign)
        order = "\n".join(
            f"{index + 1}. {item['name']}（{item['actor_type']}）：{item['initiative']['total']}"
            for index, item in enumerate(state["participants"])
        )
        append_event(db, campaign.id, session_id, "combat_started", "进入战斗", [], {
            "initiative_order": state["participants"],
        })
        return command_result(
            "start_combat",
            f"战斗开始，系统已为所有玩家角色与 NPC 投掷先攻：\n{order}\n\n{format_turn_state(campaign)}",
            data={"turn_state": state, "turn_notification": notification},
        )

    if command.name == "end_combat":
        end_combat(db, campaign)
        append_event(db, campaign.id, session_id, "combat_ended", "结束战斗", [], {})
        return command_result("end_combat", "战斗结束，已自动退出回合制模式并返回自由扮演模式。")

    if command.name == "next_turn":
        next_actor = advance_turn(db, campaign)
        notification = turn_notification(db, campaign)
        append_event(db, campaign.id, session_id, "turn_advanced", "下一回合", [], {
            "next_actor": next_actor,
        })
        return command_result(
            "next_turn",
            f"已推进回合。\n{format_turn_state(campaign)}",
            data={"turn_notification": notification},
        )

    if command.name == "save":
        checkpoint = create_checkpoint(db, campaign, session_id, actor_id, "manual_save")
        append_event(db, campaign.id, session_id, "campaign_saved", "保存战役", [], {
            "checkpoint_id": checkpoint.id, "created_by": actor_id,
        })
        return command_result("save", f"战役已保存。检查点：{checkpoint.id}", data=serialize(checkpoint))

    if command.name == "pause":
        if campaign_status(campaign) == "paused":
            return command_result("pause", "战役已经处于暂停状态。")
        checkpoint = create_checkpoint(db, campaign, session_id, actor_id, "pause")
        set_campaign_status(campaign, "paused", session_id)
        db.commit()
        append_event(db, campaign.id, session_id, "campaign_paused", "暂停战役", [], {
            "checkpoint_id": checkpoint.id, "created_by": actor_id,
        })
        return command_result("pause", f"战役已暂停并保存。检查点：{checkpoint.id}", data=serialize(checkpoint))

    if command.name == "resume":
        if campaign_status(campaign) == "active":
            return command_result("resume", "战役已经处于进行状态。")
        set_campaign_status(campaign, "active", session_id)
        db.commit()
        append_event(db, campaign.id, session_id, "campaign_resumed", "继续战役", [], {
            "created_by": actor_id,
        })
        return command_result("resume", f"战役“{campaign.name}”已继续。")

    return command_result(command.name, "未知命令。", ok=False)


def command_result(name: str, narration: str, ok: bool = True, data: dict | None = None) -> dict:
    return {
        "ok": ok,
        "kind": "command",
        "command": name,
        "narration": narration,
        "data": data or {},
        "rolls": [],
        "state_changes": [],
        "events": [],
    }
