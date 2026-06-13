from app.tools.character_rules import (
    armor_class,
    derive_character_rules,
    point_buy_cost,
    proficiency_bonus,
)


def test_core_excel_formulas_are_available_as_code():
    abilities = {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10}
    assert point_buy_cost(abilities) == 27
    assert proficiency_bonus(1) == 2
    assert proficiency_bonus(17) == 6
    assert armor_class(abilities) == 12


def test_wizard_rules_are_derived_from_template_logic():
    derived = derive_character_rules({
        "class_name": "Wizard",
        "level": 1,
        "abilities": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        "skill_proficiencies": ["arcana", "history"],
        "spellcasting_ability": "int",
    })
    assert derived["hit_die"] == 6
    assert derived["saving_throw_proficiencies"] == ["int", "wis"]
    assert derived["skills"]["arcana"]["bonus"] == 4
    assert derived["passive_perception"] == 11
    assert derived["spell_save_dc"] == 12
    assert derived["spell_attack_bonus"] == 4
    assert derived["carrying_capacity"] == 120
