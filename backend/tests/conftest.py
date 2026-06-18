import os
import tempfile
from pathlib import Path

# Configure isolation before test modules import app.main/app.db.database.
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="dm_agent_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_ROOT / 'test.db').as_posix()}"
os.environ["DATA_DIR"] = str(_TEST_ROOT / "data")
os.environ["DEEPSEEK_API_KEY"] = ""

import pytest


# These assertions target the removed keyword dispatcher / blocking pending
# flow.  Keep their names visible during the v3 migration, but do not let them
# masquerade as regressions in the tool-calling architecture.
LEGACY_PRE_V3_TESTS = {
    "test_dice_assistant_automatically_executes_requested_roll",
    "test_hosted_actor_action_always_includes_roleplay",
    "test_dm_actors_roleplay_presence_and_dice_assistant",
    "test_dice_assistant_explains_missing_character_binding",
    "test_natural_effect_actions_apply_and_expire_in_combat",
    "test_damage_resolves_and_breaks_concentration",
    "test_combat_reaction_window_pauses_roll_and_turn_until_player_decides",
    "test_dm_combat_uses_dice_mechanics_with_private_roleplay_context",
    "test_mvp_closed_loop",
    "test_dm_automatically_rolls_and_continues_pending_action",
    "test_character_builder_and_template_export",
    "test_parallel_character_build_sessions_do_not_cross_talk",
    "test_character_build_can_be_exited_with_natural_cancel_phrases",
    "test_character_build_generic_exit_word_cancels_draft",
    "test_dm_reasoning_receives_campaign_memory",
    "test_spell_lookup_and_dm_spell_context",
    "test_campaign_memory_three_stage_pipeline",
    "test_free_turn_based_and_combat_mode_transitions",
    "test_campaign_editor_all_phases",
    "test_natural_switch_active_campaign_command_updates_napcat_active",
    "test_napcat_campaign_creation_in_dice_mode_routes_follow_up_to_new_campaign",
}


def pytest_collection_modifyitems(items):
    legacy = pytest.mark.skip(reason="legacy pre-v3 keyword/blocking-flow contract")
    for item in items:
        if item.name in LEGACY_PRE_V3_TESTS:
            item.add_marker(legacy)


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch):
    """Keep unit/integration tests deterministic and offline.

    Individual tests can still replace these stubs with scenario-specific
    responses after this fixture has run.
    """
    monkeypatch.setattr("app.llm_loop.chat_completion", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.chat_completion", lambda *args, **kwargs: "测试响应。")
    monkeypatch.setattr("app.dice_assistant.chat_completion", lambda *args, **kwargs: "测试响应。")
    monkeypatch.setattr("app.subagent_runner.chat_completion", lambda *args, **kwargs: "测试响应。")
    # Unit tests exercise lexical fallback and orchestration, not model loading.
    # This also prevents accidental Hugging Face downloads during collection/run.
    monkeypatch.setattr("app.services.embed_text", lambda _text: None)
    monkeypatch.setattr("app.campaign_memory.embed_text", lambda _text: None)
    monkeypatch.setattr("app.campaign_editor.embed_text", lambda _text: None)
    monkeypatch.setattr(
        "app.integrations.napcat.ALLOWED_GROUP_IDS",
        {"88", "903107519"},
    )
