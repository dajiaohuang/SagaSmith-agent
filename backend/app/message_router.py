from __future__ import annotations

from sqlalchemy.orm import Session

from app.campaign_control import campaign_status, command_result, execute_command
from app.commands import route_command
from app.config import settings
from app.db.models import Campaign
from app.services import resolve_chat
from app.tools.spell_catalog import direct_spell_lookup, format_spell
from app.campaign_memory import build_memory_package


def process_message(
    db: Session,
    campaign: Campaign,
    session_id: str | None,
    character_id: str | None,
    message: str,
    actor_id: str | None = None,
    is_dm: bool = False,
) -> dict:
    compact = " ".join(message.strip().split())
    lowered = compact.casefold()
    if lowered.startswith(("/记忆", "/memory")):
        query = compact.split(maxsplit=1)[1] if len(compact.split(maxsplit=1)) > 1 else compact
        package = build_memory_package(db, campaign.id, query, session_id)
        lines = [f"- [{item['type']}] {item['content']}" for item in package["memories"]]
        return command_result("memory", "\n".join(lines) or "当前还没有可用的结构化战役记忆。", data=package)
    if lowered in {"/剧情线", "/threads"}:
        package = build_memory_package(db, campaign.id, compact, session_id)
        lines = [f"- {item['title']}: {item['description']}" for item in package["threads"]]
        return command_result("threads", "\n".join(lines) or "当前没有开放的剧情线。", data=package)
    command = route_command(message)
    if command:
        return execute_command(db, command, campaign, session_id, actor_id, is_dm)
    spell_lookup = direct_spell_lookup(message, settings.data_dir, 5)
    if spell_lookup:
        spell_query, spells = spell_lookup
        if not spells:
            return command_result("spell_search", f"没有找到与“{spell_query}”匹配的法术。", ok=False)
        return {
            **command_result("spell_search", "\n\n".join(format_spell(spell) for spell in spells)),
            "data": {"query": spell_query, "spells": spells},
        }
    if campaign_status(campaign) == "paused":
        return command_result(
            "paused",
            "战役当前处于暂停状态。DM 可发送 /继续 恢复战役；其他命令可发送 /帮助 查看。",
            ok=False,
        )
    return resolve_chat(db, campaign.id, session_id, character_id, message)
