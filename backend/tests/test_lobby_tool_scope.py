from types import SimpleNamespace

import pytest

from app.db.models import Campaign, Character
from app.db.database import SessionLocal
from app.lobby_sessions import get_lobby_session
from app.main import app
from app.qq_bindings import active_napcat_campaign
from app.services import resolve_chat
from app import llm_loop
from app.tools.command_tools import handle_exit_to_lobby, tools_for_scope
from app.tools.lobby_tools import (
    handle_create_campaign_now,
    handle_create_campaign_simple,
    handle_confirm_random_proposal,
    handle_save_random_proposal,
    handle_set_lobby_state,
    handle_show_lobby,
)
from fastapi.testclient import TestClient


def _tool_names(campaign: Campaign | None) -> set[str]:
    return {tool["function"]["name"] for tool in tools_for_scope(campaign, False, "")}


def test_lobby_exposes_only_simple_campaign_and_character_tools():
    campaign = Campaign(
        id="camp_lobby_test",
        name="Lobby test",
        system_version="DND_5E_2014",
        config={"play_style": "lobby"},
    )

    names = _tool_names(campaign)

    assert names == {
        "show_lobby",
        "create_campaign_simple",
        "save_random_proposal",
        "confirm_random_proposal",
        "discard_random_proposal",
        "switch_campaign",
        "status",
        "enter_campaign_mode",
        "create_character_quick",
        "bind_character",
        "show_bindings",
        "export_character_sheet",
    }
    assert {
        "get_lobby_state",
        "set_lobby_state",
        "resolve_lobby_option",
        "complete_character_sheet",
        "generate_npc_set",
        "generate_setting",
        "generate_content",
        "execute_plan",
        "combat_attack",
        "apply_damage",
        "end_turn",
    }.isdisjoint(names)


def test_campaignless_lobby_only_exposes_campaign_selection():
    assert _tool_names(None) == {
        "show_lobby", "create_campaign_simple", "switch_campaign",
        "save_random_proposal", "confirm_random_proposal",
        "discard_random_proposal",
    }


def test_simple_lobby_create_and_overview():
    with TestClient(app), SessionLocal() as db:
        result = handle_create_campaign_simple(
            db=db, campaign=None, name="雾港残灯", description="港城调查短团",
        )
        assert result["ok"] is True

        overview = handle_show_lobby(db=db, campaign=None)
        assert overview["ok"] is True
        assert "雾港残灯（当前）" in overview["narration"]


def test_random_proposals_require_confirmation_before_creation(monkeypatch):
    session_id = "test_random_proposal_session"
    with TestClient(app), SessionLocal() as db:
        before_campaigns = len(db.query(Campaign).all())
        saved_campaign = handle_save_random_proposal(
            db=db, campaign=None, session_id=session_id, kind="campaign",
            proposal={"name": "群星墓园", "description": "漂浮墓园中的寻钥冒险"},
        )
        assert saved_campaign["ok"] is True
        assert len(db.query(Campaign).all()) == before_campaigns

        created_campaign = handle_confirm_random_proposal(
            db=db, campaign=None, session_id=session_id,
        )
        campaign = db.get(Campaign, created_campaign["data"]["campaign_id"])
        assert campaign.name == "群星墓园"

        before_characters = len(db.query(Character).all())
        saved_character = handle_save_random_proposal(
            db=db, campaign=campaign, kind="character",
            proposal={
                "name": "伊澜", "class_name": "游侠", "level": 2,
                "ancestry": "木精灵", "background": "失踪的观星员",
                "abilities": {"str": 10, "dex": 16, "con": 13, "int": 12, "wis": 15, "cha": 8},
            },
        )
        assert saved_character["ok"] is True
        assert len(db.query(Character).all()) == before_characters

        from app.tools.character_builder import build_character_data
        normalized = build_character_data({
            "character_name": "伊澜", "class_name": "游侠", "level": 1,
            "ancestry": "木精灵", "background": "失踪的观星员",
            "abilities": {"str": 10, "dex": 15, "con": 13, "int": 12, "wis": 14, "cha": 8},
            "max_hp": 11, "armor_class": 15, "speed": 30, "actor_type": "player",
        })
        monkeypatch.setattr(
            "app.blocking_card_subagent.rewrite_single_card_blocking",
            lambda *_args, **_kwargs: normalized,
        )

        created_character = handle_confirm_random_proposal(
            db=db, campaign=campaign, user_id="2480933622",
        )
        character = db.get(Character, created_character["data"]["character_id"])
        assert character.character_name == "伊澜"
        assert character.data["basic"]["classes"][0]["name"] == "游侠"


def test_failed_blocking_card_validation_keeps_proposal_and_writes_nothing(monkeypatch):
    with TestClient(app), SessionLocal() as db:
        campaign = Campaign(
            id="camp_blocking_card_failure",
            name="单卡失败测试",
            system_version="DND_5E_2014",
            config={"play_style": "lobby"},
        )
        db.add(campaign)
        db.commit()
        handle_save_random_proposal(
            db=db, campaign=campaign, kind="npc",
            proposal={"name": "灰牙", "class_name": "斥候"},
        )
        monkeypatch.setattr(
            "app.blocking_card_subagent.rewrite_single_card_blocking",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("rules invalid")),
        )
        before = len(db.query(Character).all())

        with pytest.raises(ValueError, match="rules invalid"):
            handle_confirm_random_proposal(db=db, campaign=campaign)

        db.refresh(campaign)
        assert len(db.query(Character).all()) == before
        assert campaign.config["lobby_state"]["pending_proposal"]["proposal"]["name"] == "灰牙"


def test_tool_loop_preserves_schema_arguments(monkeypatch):
    captured = {}

    def handler(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "narration": "done"}

    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(
            name="test_lobby_arguments",
            arguments='{"state":{"dm_confirmed":true},"option_number":2,"campaign_name":"新战役"}',
        ),
    )
    responses = iter([
        SimpleNamespace(content=None, tool_calls=[tool_call]),
        SimpleNamespace(content="完成", tool_calls=[]),
    ])

    monkeypatch.setitem(llm_loop.TOOL_HANDLERS, "test_lobby_arguments", handler)
    monkeypatch.setattr(llm_loop, "tools_for_scope", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(llm_loop, "chat_completion", lambda *_args, **_kwargs: next(responses))

    result = llm_loop.execute_llm_with_tools(
        db=object(), campaign=None, messages=[], message_context={"sender_id": "123"},
    )

    assert result["narration"] == "完成"
    assert captured["state"] == {"dm_confirmed": True}
    assert captured["option_number"] == 2
    assert captured["campaign_name"] == "新战役"


def test_campaignless_lobby_persists_state_and_history(monkeypatch):
    session_id = "napcat_group_903107519_2480933622"
    captured_messages = []

    def fake_chat(messages, **_kwargs):
        captured_messages.extend(messages)
        return "已读取上一轮设定，可以继续保存。"

    with TestClient(app), SessionLocal() as db:
        state = {
            "generated_setting": {
                "name": "黯影潮汐",
                "description": "黯影裂隙再次扩张。",
            },
            "pending_options": [
                {"id": 1, "action": "create_campaign", "label": "传统英雄团"},
            ],
        }
        result = handle_set_lobby_state(
            db=db, campaign=None, session_id=session_id, state=state,
            message_context={"platform": "napcat", "group_id": "903107519", "sender_id": "2480933622"},
        )
        assert result["ok"] is True

        monkeypatch.setattr(llm_loop, "chat_completion", fake_chat)
        reply = resolve_chat(
            db, None, session_id, None, "先保存", mode="lobby",
            message_context={"platform": "napcat", "group_id": "903107519", "sender_id": "2480933622"},
        )

        assert reply["narration"] == "已读取上一轮设定，可以继续保存。"
        assert any("黯影潮汐" in str(message.get("content")) for message in captured_messages)
        stored = get_lobby_session(db, session_id)
        assert stored.state["generated_setting"]["name"] == "黯影潮汐"
        assert stored.messages[-2]["content"] == "先保存"

        created = handle_create_campaign_now(db=db, campaign=None, session_id=session_id)
        assert created["ok"] is True
        assert active_napcat_campaign(db).name == "黯影潮汐"


def test_campaign_creation_is_revealed_only_after_exit_to_lobby():
    with TestClient(app), SessionLocal() as db:
        campaign = Campaign(
            id="camp_cross_mode_test",
            name="北境之门",
            system_version="DND_5E_2014",
            config={"play_style": "dice_assistant", "dice_dm_qq_user_id": "2480933622"},
        )
        db.add(campaign)
        db.commit()

        before = _tool_names(campaign)
        assert "exit_to_lobby" in before
        assert "create_campaign_from_prompt" not in before
        assert "create_campaign_now" not in before

        result = handle_exit_to_lobby(db=db, campaign=campaign)
        assert result["ok"] is True

        after = _tool_names(campaign)
        assert "create_campaign_simple" in after
        assert "create_campaign_from_prompt" not in after
        assert "create_campaign_now" not in after
        assert campaign.config["lobby_state"]["dm_confirmed"] is True
