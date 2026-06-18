import json
from types import SimpleNamespace

from app.blocking_card_subagent import rewrite_single_card_blocking


def test_blocking_single_card_rewrite_validates_rules_and_xlsx_roundtrip(monkeypatch):
    raw = {
        "character_name": "伊澜",
        "class_name": "游侠",
        "level": 1,
        "ancestry": "木精灵",
        "subrace": "",
        "background": "侍僧",
        "alignment": "中立善良",
        "gender": "女",
        "age": "86",
        "faith": "",
        "appearance": "银发，披旧旅行斗篷。",
        "traits": "谨慎",
        "ideals": "守护",
        "bonds": "寻找失踪导师",
        "flaws": "过度多疑",
        "backstory": "曾在边境观测星象。",
        "abilities": {"str": 10, "dex": 15, "con": 13, "int": 12, "wis": 14, "cha": 8},
        "max_hp": 11,
        "armor_class": 15,
        "speed": 30,
        "spellcasting_ability": "wis",
    }
    response = SimpleNamespace(tool_calls=[SimpleNamespace(function=SimpleNamespace(
        name="submit_single_card", arguments=json.dumps(raw, ensure_ascii=False),
    ))])
    monkeypatch.setattr(
        "app.blocking_card_subagent.chat_completion",
        lambda *_args, **_kwargs: response,
    )

    data = rewrite_single_card_blocking(
        {"name": "伊澜", "concept": "边境游侠"},
        actor_type="player",
        player_name="2480933622",
    )

    assert data["basic"]["name"] == "伊澜"
    assert data["basic"]["classes"][0]["name"] == "游侠"
    assert data["validation_errors"] == []
