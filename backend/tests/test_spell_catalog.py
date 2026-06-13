from pathlib import Path

from app.tools.spell_catalog import build_spell_catalog, direct_spell_lookup, search_spells


DATA_DIR = Path(__file__).parents[2] / "data"


def test_two_excel_spell_lists_merge_and_search():
    spells = build_spell_catalog(DATA_DIR / "raw")
    assert len(spells) > 700
    fireball = search_spells("火球术", DATA_DIR, 1)[0]
    assert fireball["english_name"] == "Fireball"
    assert len(fireball["sources"]) >= 2
    assert "法师" not in fireball["classes"]
    assert "wizard" in fireball["classes"]


def test_direct_spell_lookup_requires_explicit_query_or_question():
    explicit = direct_spell_lookup("/法术 火球术", DATA_DIR)
    assert explicit and explicit[1][0]["english_name"] == "Fireball"
    question = direct_spell_lookup("火球术是什么效果", DATA_DIR)
    assert question and question[1][0]["english_name"] == "Fireball"
    assert direct_spell_lookup("我施放火球术", DATA_DIR) is None
