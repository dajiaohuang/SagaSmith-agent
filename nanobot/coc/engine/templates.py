"""
CoC 7e 数据模板工厂 — 调查员、战斗参与者、事件模板。

对等 DND 的 `engine/save/templates.py` 中的 make_character_template() 等。
"""


def make_characteristics(**overrides) -> dict:
    """八维属性模板

    COC 标准属性公式:
        - STR/CON/DEX/APP/POW: 3D6×5
        - SIZ/INT: (2D6+6)×5
        - EDU: (2D6+6)×5

    返回:
        {str: {formula, value}, con: {...}, ...}
    """
    default = {
        "str": {"formula": "3D6*5", "value": None},
        "con": {"formula": "3D6*5", "value": None},
        "siz": {"formula": "(2D6+6)*5", "value": None},
        "dex": {"formula": "3D6*5", "value": None},
        "app": {"formula": "3D6*5", "value": None},
        "int": {"formula": "(2D6+6)*5", "value": None},
        "pow": {"formula": "3D6*5", "value": None},
        "edu": {"formula": "(2D6+6)*5", "value": None},
    }
    default.update(overrides)
    return default


def make_attribs(**overrides) -> dict:
    """衍生属性模板"""
    default = {
        "hp": {"value": None, "max": None},
        "mp": {"value": None, "max": None},
        "lck": {"value": 50},
        "san": {"value": 99, "max": 99},
        "mov": {"value": 8},
        "db": {"value": "0"},
        "build": {"value": 0},
        "armor": {"value": ""},
    }
    default.update(overrides)
    return default


def make_conditions(**overrides) -> dict:
    """状态条件模板"""
    default = {
        "critical_wounds": False,
        "unconscious": False,
        "dying": False,
        "dead": False,
        "prone": False,
        "tempo_insane": False,
        "indef_insane": False,
    }
    default.update(overrides)
    return default


def make_investigator_template(name="新调查员", **overrides) -> dict:
    """
    调查员数据模板 -> 对应数据库中调查员角色的 sheet_json。

    对等 DND 的 make_character_template()。
    """
    template = {
        "name": name,
        "characteristics": make_characteristics(),
        "attribs": make_attribs(),
        "conditions": make_conditions(),
        "infos": {
            "occupation": "",
            "archetype": "",
            "age": "",
            "sex": "",
            "residence": "",
            "birthplace": "",
            "organization": "",
        },
        "monetary": {
            "credit_rating": 10,
            "spending_level": 10,
            "cash": "",
            "assets": "",
        },
        "skills": [],
        "weapons": [],
        "spells": [],
        "talents": [],
        "books": [],
        "development": {
            "personal": 0,
            "occupation": 0,
            "archetype": 0,
            "experience_package": 0,
        },
        "sanity_loss_events": [],
        "biography": [],
        "backstory": "",
        "notes": "",
    }
    template.update(overrides)
    return template


def make_skill_entry(
    name: str,
    specialization: str = "",
    base: str = "0",
    adjustments: dict | None = None,
    properties: dict | None = None,
) -> dict:
    """
    技能条目模板。

    参数:
        name: 技能名称 (如 "侦查", "格斗")
        specialization: 专精 (如 "斗殴", "剑")
        base: 基础值公式 (如 "DEX*2", "25")
        adjustments: 调整值 {base, personal, occupation, archetype, experience, experience_package}
        properties: 属性 {fighting, firearm, ranged, special, push, ...}
    """
    return {
        "name": name,
        "specialization": specialization,
        "base": base,
        "adjustments": adjustments or {
            "base": 0,
            "personal": 0,
            "occupation": 0,
            "archetype": 0,
            "experience": 0,
            "experience_package": 0,
        },
        "properties": properties or {
            "noxpgain": False,
            "special": bool(specialization),
            "rarity": False,
            "push": True,
            "fighting": False,
            "firearm": False,
            "ranged": False,
            "requiresname": False,
            "picknameonly": False,
            "own": False,
            "keepbasevalue": False,
        },
    }


def make_weapon_entry(
    name: str = "",
    skill_name: str = "",
    damage: str = "1D4",
    range_normal: str = "",
    range_long: str = "",
    range_extreme: str = "",
    uses_per_round: str = "1",
    malfunction: int | None = None,
    ammo: int = 0,
    properties: dict | None = None,
) -> dict:
    """
    武器条目模板。
    """
    return {
        "name": name,
        "skill": {"name": skill_name},
        "damage": damage,
        "range": {
            "normal": {"value": range_normal},
            "long": {"value": range_long},
            "extreme": {"value": range_extreme},
        },
        "uses_per_round": uses_per_round,
        "malfunction": malfunction,
        "ammo": ammo,
        "properties": properties or {
            "rngd": False,
            "mnvr": False,
            "thrown": False,
            "shotgun": False,
            "dbrl": False,
            "impl": False,
            "brst": False,
            "auto": False,
            "ahdb": False,
            "addb": False,
            "slnt": False,
            "spcl": False,
            "mont": False,
            "blst": False,
            "stun": False,
            "rare": False,
            "burn": False,
        },
    }


def make_combatant_template(
    name="",
    hp=10,
    max_hp=10,
    mov=8,
    build=0,
    db="0",
    armor="",
    skills: dict | None = None,
    weapons: list | None = None,
    **extra,
) -> dict:
    """
    战斗参与者模板。

    对等 DND 的 make_combatant_template()。
    COC 无 AC 和先攻值（使用 DEX / 技能对抗）。
    """
    entry = {
        "name": name,
        "hp": hp,
        "max_hp": max_hp,
        "mov": mov,
        "build": build,
        "db": db,
        "armor": armor,
        "skills": skills or {},
        "weapons": weapons or [],
        "status": "active",  # active / unconscious / dying / dead
    }
    entry.update(extra)
    return entry


def make_event_template(
    event_id="",
    title="",
    description="",
    event_type="scene",  # scene / combat / discovery / social / sanity
    **extra,
) -> dict:
    """
    事件数据模板。

    对等 DND 的 make_quest_template()。
    """
    entry = {
        "id": event_id,
        "title": title,
        "description": description,
        "type": event_type,
    }
    entry.update(extra)
    return entry
