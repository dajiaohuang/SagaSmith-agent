from app.tools.character_rules import (
    armor_class,
    derive_character_rules,
    point_buy_cost,
    proficiency_bonus,
)
from app.tools.item_schema import normalize_inventory
from app.tools.effect_engine import add_effect, advance_effect_durations, resolve_effective_character, roll_effects_for


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


def test_inventory_normalizes_standard_and_custom_items():
    inventory = normalize_inventory([
        {"instance_id": "bag_1", "name": "Explorer's Pack", "item_type": "container"},
        {
            "instance_id": "blade_1",
            "name": "Moonlit Letter Opener",
            "type": "custom",
            "weight": 0.2,
            "value": 7,
            "equipped": True,
            "equipped_slot": "main_hand",
            "container_instance_id": "bag_1",
            "custom_data": {"moon_phase": "waxing", "homebrew_rule": {"glows": True}},
            "creator_note": "Any unknown field is preserved.",
        },
    ])
    custom = inventory[1]
    assert custom["item_type"] == "custom"
    assert custom["weight_each"] == 0.2
    assert custom["value_each"] == {"amount": 7.0, "currency": "gp"}
    assert custom["custom_data"]["homebrew_rule"]["glows"]
    assert custom["creator_note"] == "Any unknown field is preserved."

    legacy = normalize_inventory([{"item_id": "longsword", "name": "Longsword"}])[0]
    assert legacy["item_type"] == "weapon"
    assert legacy["weapon"]["damage_dice"] == "1d8"


def test_effect_engine_combines_persistent_combat_and_equipped_effects():
    data = {
        "abilities": {"str": 16, "dex": 14, "con": 12, "int": 10, "wis": 10, "cha": 10},
        "combat": {"armor_class": 12, "initiative": 2, "speed": 30, "proficiency_bonus": 2},
        "skills": {"athletics": {"proficient": True, "bonus": 5}},
        "saving_throws": {"str": 5, "dex": 2, "con": 1, "int": 0, "wis": 0, "cha": 0},
        "inventory": normalize_inventory([{
            "name": "Guardian Ring", "equipped": True, "attuned": True,
            "effects": [{"name": "Ring Guard", "modifiers": [
                {"target": "combat.armor_class", "operation": "add", "value": 1},
            ]}],
        }]),
        "active_effects": [{
            "name": "Battle Focus", "scope": "combat_only",
            "duration": {"type": "rounds", "remaining": 2, "tick_on": "round_end"},
            "modifiers": [
                {"target": "abilities.str", "operation": "add", "value": 2},
                {"target": "combat.armor_class", "operation": "add", "value": 2},
            ],
        }],
    }
    outside = resolve_effective_character(data, combat=False)["effective"]
    inside = resolve_effective_character(data, combat=True)["effective"]
    assert outside["combat"]["armor_class"] == 13
    assert inside["combat"]["armor_class"] == 15
    assert inside["ability_modifiers"]["str"] == 4
    assert inside["skills"]["athletics"]["bonus"] == 6
    advanced, expired = advance_effect_durations(data, "round_end")
    assert advanced["active_effects"][0]["duration"]["remaining"] == 1
    advanced, expired = advance_effect_durations(advanced, "round_end")
    assert expired[0]["name"] == "Battle Focus"


def test_effect_engine_replaces_concentration_and_exposes_roll_effects():
    data, first, removed = add_effect({}, {
        "name": "First concentration",
        "concentration": {"required": True, "owner_character_id": "caster"},
        "modifiers": [{"target": "roll.advantage", "operation": "advantage", "value": True,
                       "conditions": {"roll_types": ["ability_check"]}}],
    })
    data, second, removed = add_effect(data, {
        "name": "Bless",
        "concentration": {"required": True, "owner_character_id": "caster"},
        "modifiers": [{"target": "roll.bonus_dice", "operation": "add_dice", "value": "1d4",
                       "conditions": {"roll_types": ["saving_throw"]}}],
    })
    assert removed == [first["effect_id"]]
    context = roll_effects_for(resolve_effective_character(data), "saving_throw")
    assert context["bonus_dice"] == ["1d4"]
