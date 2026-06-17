from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.campaign_editor import serialize as editor_serialize
from app.db.database import SessionLocal
from app.db.models import Campaign, CampaignSettingDraft, Character, TaskSession
from app.llm import chat_completion


EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dm-subagent")


def enqueue_subagent_task(task_id: str) -> None:
    EXECUTOR.submit(run_subagent_task, task_id)


def run_subagent_task(task_id: str) -> None:
    with SessionLocal() as db:
        task = db.get(TaskSession, task_id)
        if not task or task.task_type != "subagent_proposal":
            return
        if task.status not in {"queued", "ready_to_review", "ready_to_commit"}:
            return
        task.status = "running"
        db.commit()
        try:
            campaign = db.get(Campaign, task.campaign_id)
            if not campaign:
                raise ValueError("campaign not found")
            proposal_data = copy.deepcopy(task.proposal_data or {})
            role = str(proposal_data.get("agent_role") or "")
            if role == "campaign_setting_reviewer":
                result = review_campaign_setting_drafts(db, campaign, proposal_data)
            elif role == "character_sheet_reviewer":
                result = review_character_sheet(db, campaign, proposal_data)
            elif role == "campaign_compressor":
                result = compress_campaign_events(db, campaign, proposal_data)
            else:
                result = generic_review(campaign, proposal_data)
            proposal_data["result"] = result
            proposal_data["completed_at"] = datetime.now(UTC).isoformat()
            parent = db.get(TaskSession, task.parent_task_id) if task.parent_task_id else None
            current_version = ((parent.draft_data or {}).get("_meta") or {}).get("version", 0) if parent else 0
            source_version = proposal_data.get("source_parent_version", 0)
            proposal_data["current_parent_version"] = current_version
            proposal_data["stale"] = bool(parent and current_version != source_version)
            task.proposal_data = proposal_data
            task.status = "ready_to_review"
            task.next_prompt = "子任务已完成，请审核结果。"
            db.commit()
        except Exception as exc:
            task = db.get(TaskSession, task_id)
            if task:
                data = copy.deepcopy(task.proposal_data or {})
                data["error"] = str(exc)
                data["completed_at"] = datetime.now(UTC).isoformat()
                task.proposal_data = data
                task.status = "failed"
                task.next_prompt = "子任务执行失败，请查看 error。"
                db.commit()


def review_campaign_setting_drafts(db, campaign: Campaign, proposal_data: dict[str, Any]) -> dict[str, Any]:
    proposal = proposal_data.get("proposal") or {}
    draft_ids = [str(item) for item in proposal.get("draft_ids") or []]
    drafts = [
        item for item in db.scalars(select(CampaignSettingDraft).where(
            CampaignSettingDraft.campaign_id == campaign.id,
            CampaignSettingDraft.id.in_(draft_ids),
        )).all()
    ]
    draft_payload = [editor_serialize(item) for item in drafts]
    llm_review = chat_completion([
        {
            "role": "system",
            "content": (
                "You are a background campaign setting reviewer. "
                "Review drafts for consistency, missing details, useful NPC hooks, and publication risks. "
                "Return concise Chinese notes."
            ),
        },
        {"role": "user", "content": f"Campaign: {campaign.name}\nDrafts: {draft_payload}"},
    ], temperature=0.2)
    fallback_notes = [
        f"草稿 {item.name or item.target_setting_id or item.id}：检查名称、可见性、关系引用与摘要是否足够发布。"
        for item in drafts
    ]
    return {
        "kind": "campaign_setting_review",
        "draft_ids": draft_ids,
        "summary": llm_review or "已完成设定草稿后台审核。",
        "recommendations": fallback_notes,
        "blocking_issues": [],
    }


def review_character_sheet(db, campaign: Campaign, proposal_data: dict[str, Any]) -> dict[str, Any]:
    character_id = str((proposal_data.get("proposal") or {}).get("character_id") or "")
    character = db.get(Character, character_id) if character_id else None
    if not character or character.campaign_id != campaign.id:
        raise ValueError("character not found")
    data = character.data or {}
    llm_review = chat_completion([
        {
            "role": "system",
            "content": (
                "You are a background DND character sheet reviewer. "
                "Check required mechanical fields, inventory structure, class/ability consistency, and missing play notes. "
                "Return concise Chinese notes."
            ),
        },
        {"role": "user", "content": f"Campaign: {campaign.name}\nCharacter: {character.character_name}\nSheet: {data}"},
    ], temperature=0.2)
    combat = data.get("combat") or {}
    abilities = data.get("abilities") or {}
    issues = []
    for field in ("armor_class", "max_hp", "current_hp", "proficiency_bonus"):
        if combat.get(field) is None:
            issues.append(f"combat.{field} 未填写。")
    for ability in ("str", "dex", "con", "int", "wis", "cha"):
        if abilities.get(ability) is None:
            issues.append(f"abilities.{ability} 未填写。")
    return {
        "kind": "character_sheet_review",
        "character_id": character.id,
        "summary": llm_review or f"已完成 {character.character_name} 的角色卡后台审核。",
        "recommendations": [
            "确认 AC、HP、熟练加值、属性调整值、物品结构和法术列表是否符合当前等级。",
            "如用于战斗，请确认 active_effects 与 inventory.effects 可被效果引擎读取。",
        ],
        "blocking_issues": issues,
    }


def compress_campaign_events(db, campaign: Campaign, proposal_data: dict[str, Any]) -> dict[str, Any]:
    """Background subagent: compress old events into a summary and archive memories."""
    from app.memory_compressor import COMPRESS_EVERY, get_uncompressed_events, mark_compressed, archive_old_memories, compress_with_llm

    events = get_uncompressed_events(db, campaign.id, COMPRESS_EVERY)
    if not events:
        return {"kind": "campaign_compression", "summary": "无可压缩事件。", "compressed": 0}
    summary = compress_with_llm(events, campaign.name or "")
    mark_compressed(db, events)
    archived = archive_old_memories(db, campaign.id)
    return {
        "kind": "campaign_compression",
        "summary": summary,
        "compressed_events": len(events),
        "archived_memories": archived,
    }


def generic_review(campaign: Campaign, proposal_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "generic_subagent_review",
        "summary": f"已接收战役“{campaign.name}”的后台子任务。",
        "recommendations": [str(proposal_data.get("goal") or "请审核该子任务输出。")],
        "blocking_issues": [],
    }
