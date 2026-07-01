"""
CoC 7e 战斗解析引擎 — 近战攻击、远程攻击、伤害结算。

COC 战斗核心机制:
    - 无 AC: 使用技能对抗（攻击者 vs 防御者闪避/格斗）
    - 近战: 格斗(Fighting)技能 vs 闪避(Dodge) 或 格斗
    - 远程: 枪械/弓箭 vs 闪避 (一般不能格挡子弹)
    - 伤害: 武器伤害 + 伤害加值(DB)
    - 重击: 伤害取最大值（非翻倍）
    - 大失败: 近战武器脱手 / 远程武器卡壳
"""

from .skill import (
    Difficulty, SuccessLevel, resolve_skill_check, threshold_ranges
)
from ..dice.rolls import roll_dice_expression


def resolve_melee_attack(
    d100_result: int,
    skill_value: int,
    damage_bonus: str | None = None,
    weapon_damage: str | None = None,
    target_dodge: int | None = None,
    target_fighting: int | None = None,
    bonus_dice: int = 0,
    penalty_dice: int = 0,
    attacker_name: str = "",
    weapon_name: str = "",
) -> dict:
    """
    近战攻击结算。

    COC 近战规则:
        - 攻击者 vs 防御者: 比较成功等级
        - 攻击者成功且成功等级 > 防御者 → 命中
        - 防御者无技能 (dodge=0) → 自动失败
        - 防御者选择闪避则用 Dodge，选择格挡则用 Fighting

    参数:
        d100_result: 攻击者的 d100 结果
        skill_value: 格斗技能值
        damage_bonus: 伤害加值，如 "1D4"
        weapon_damage: 武器伤害公式，如 "1D8+2"
        target_dodge: 目标的闪避值 (默认优先)
        target_fighting: 目标的格斗值 (当不闪避时)
        bonus_dice: 攻击奖励骰
        penalty_dice: 攻击惩罚骰
        attacker_name: 攻击者名称
        weapon_name: 武器名称

    返回:
        {
            "hit": bool,
            "success_level": int,
            "target_success_level": int | None,
            "damage": dict | None,
            "is_critical": bool,
            "is_fumble": bool,
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    detail_lines = [
        f"【近战攻击】{attacker_name}（{weapon_name or '徒手'}）：技能 {skill_value}%"
    ]

    # 攻击者技能检定
    attack_result = resolve_skill_check(
        d100_total=d100_result,
        threshold=skill_value,
        bonus_dice=bonus_dice,
        penalty_dice=penalty_dice,
        skill_name=weapon_name or "格斗",
        investigator_name=attacker_name,
    )
    detail_lines.extend(attack_result["detail_lines"])

    # 如果大失败，直接失手
    if attack_result["is_fumble"]:
        detail_lines.append("  💀 大失败！武器脱手/失衡！")
        return {
            "hit": False,
            "success_level": SuccessLevel.FUMBLE,
            "target_success_level": None,
            "damage": None,
            "is_critical": False,
            "is_fumble": True,
            "detail_lines": detail_lines,
            "summary_line": f"{attacker_name} 大失败！攻击失手！",
        }

    # 目标防御检定（默认用闪避）
    target_skill = target_dodge or target_fighting
    target_skill_name = "闪避" if target_dodge and (target_fighting is None or target_dodge >= target_fighting) else "格斗"
    target_skill_value = target_dodge if target_skill_name == "闪避" else (target_fighting or 0)

    if target_skill_value is None or target_skill_value <= 0:
        # 目标无防御技能，自动失败
        target_level = SuccessLevel.FAILURE
        detail_lines.append(f"  → 目标无{target_skill_name}技能，自动失败")
    else:
        # 目标进行防御检定（d100 由引擎外提供）
        target_level = SuccessLevel.FAILURE  # 占位，实际需传入
        detail_lines.append(f"  → 目标{target_skill_name} {target_skill_value}% (待同步)")

    # 比较成功等级
    attack_level = attack_result["success_level"]

    if target_level < SuccessLevel.FAILURE:
        target_level = SuccessLevel.FAILURE

    if attack_level > target_level:
        # 命中
        damage = _calc_weapon_damage(
            weapon_damage, damage_bonus, critical=attack_result["is_critical"]
        )
        detail_lines.append(f"  → 命中！伤害: {damage['detail']}")
        summary = f"{attacker_name} 命中！{damage['total']} 点伤害"
        if attack_result["is_critical"]:
            summary += " (重击！)"
    else:
        damage = None
        if attack_level == target_level:
            detail_lines.append("  → 均势 — 攻击被格挡/闪避")
        else:
            detail_lines.append("  → 未命中 — 目标成功防御")
        summary = f"{attacker_name} 未命中"

    return {
        "hit": damage is not None,
        "success_level": attack_level,
        "target_success_level": target_level,
        "damage": damage,
        "is_critical": attack_result["is_critical"],
        "is_fumble": False,
        "detail_lines": detail_lines,
        "summary_line": summary,
    }


def resolve_ranged_attack(
    d100_result: int,
    skill_value: int,
    weapon_damage: str,
    range_band: str = "normal",
    range_data: dict | None = None,
    damage_bonus_half: bool = False,
    damage_bonus_full: bool = False,
    damage_bonus: str | None = None,
    bonus_dice: int = 0,
    penalty_dice: int = 0,
    malfunction: int | None = None,
    attacker_name: str = "",
    weapon_name: str = "",
) -> dict:
    """
    远程攻击结算。

    参数:
        d100_result: 射击 d100 结果
        skill_value: 枪械/弓技能值
        weapon_damage: 武器伤害公式
        range_band: 射程波段 - normal / long / extreme
        range_data: {normal: {value, damage}, long: {value, damage}, extreme: {value, damage}}
        damage_bonus_half: 是否加一半 DB
        damage_bonus_full: 是否加满 DB
        damage_bonus: DB 字符串
        bonus_dice: 奖励骰
        penalty_dice: 惩罚骰
        malfunction: 卡壳阈值 (通常 99-100)
        attacker_name: 攻击者
        weapon_name: 武器名称

    返回:
        {hit, success_level, damage, is_malfunction, ...}
    """
    detail_lines = [
        f"【远程攻击】{attacker_name}（{weapon_name or '武器'}）：技能 {skill_value}%，"
        f"射程 {range_band}"
    ]

    # 射程修正
    range_penalty = 0
    if range_band == "long":
        range_penalty = 1
    elif range_band == "extreme":
        range_penalty = 2

    attack_result = resolve_skill_check(
        d100_total=d100_result,
        threshold=skill_value,
        bonus_dice=bonus_dice,
        penalty_dice=penalty_dice + range_penalty,
        skill_name=weapon_name or "射击",
        investigator_name=attacker_name,
    )
    detail_lines.extend(attack_result["detail_lines"])

    # 卡壳判定
    is_malfunction = False
    if malfunction and d100_result >= malfunction:
        is_malfunction = True
        detail_lines.append(f"  ⚠️ 卡壳/故障！（d100 ≥ {malfunction}）")
        return {
            "hit": False,
            "success_level": attack_result["success_level"],
            "damage": None,
            "is_malfunction": True,
            "is_fumble": attack_result["is_fumble"],
            "detail_lines": detail_lines,
            "summary_line": f"{attacker_name} 武器卡壳！",
        }

    if attack_result["is_fumble"]:
        detail_lines.append("  💀 大失败！武器走火/卡壳！")
        return {
            "hit": False,
            "success_level": SuccessLevel.FUMBLE,
            "damage": None,
            "is_malfunction": True,
            "is_fumble": True,
            "detail_lines": detail_lines,
            "summary_line": f"{attacker_name} 大失败！",
        }

    if not attack_result["success"]:
        detail_lines.append("  → 未命中")
        return {
            "hit": False,
            "success_level": attack_result["success_level"],
            "damage": None,
            "is_malfunction": False,
            "is_fumble": False,
            "detail_lines": detail_lines,
            "summary_line": f"{attacker_name} 未命中",
        }

    # 命中 — 计算伤害
    effective_db = damage_bonus if damage_bonus_full else (
        damage_bonus if damage_bonus_half else None
    )

    damage = _calc_weapon_damage(
        weapon_damage,
        db=effective_db,
        critical=attack_result["is_critical"],
    )
    detail_lines.append(f"  → 命中！伤害: {damage['detail']}")

    return {
        "hit": True,
        "success_level": attack_result["success_level"],
        "damage": damage,
        "is_malfunction": False,
        "is_fumble": False,
        "detail_lines": detail_lines,
        "summary_line": (
            f"{attacker_name} 命中！{damage['total']} 点伤害"
            + (" (重击！)" if attack_result["is_critical"] else "")
        ),
    }


def _calc_weapon_damage(
    damage_formula: str | None,
    db: str | None = None,
    critical: bool = False,
) -> dict:
    """
    武器伤害结算。

    COC 规则:
        - 普通: 掷武器伤害 + DB
        - 重击 (大成功): 伤害取满值 (非翻倍!)
            即 damage_dice.max() + db.max()
        - DB 格式: "1D4", "-1D4" 等

    参数:
        damage_formula: 武器伤害公式
        db: 伤害加值公式
        critical: 是否重击

    返回:
        {
            "total": int,
            "weapon_rolls": list[int],
            "db_rolls": list[int] | None,
            "weapon_total": int,
            "db_total": int,
            "detail": str,
        }
    """
    weapon_total = 0
    db_total = 0
    all_weapon_rolls = []
    all_db_rolls = []

    if critical:
        # 重击 — 取满值
        weapon_total = _max_damage(damage_formula) if damage_formula else 0
        if db:
            db_total = _max_damage(db) if '-' not in db else _min_damage(db)
        detail = f"⚡ 重击满伤!"
    else:
        if damage_formula:
            wd = roll_dice_expression(damage_formula)
            all_weapon_rolls = wd["rolls"]
            weapon_total = wd["total"]
        if db:
            dd = roll_dice_expression(db)
            all_db_rolls = dd["rolls"]
            db_total = dd["total"]

        parts = []
        if damage_formula:
            parts.append(f"武器: {weapon_total}")
        if db:
            parts.append(f"DB: {db_total}")
        detail = " + ".join(parts)

    total = weapon_total + db_total

    return {
        "total": total,
        "weapon_rolls": all_weapon_rolls,
        "db_rolls": all_db_rolls,
        "weapon_total": weapon_total,
        "db_total": db_total,
        "detail": f"{detail} = {total}" if not critical else f"{detail}{weapon_total}+{db_total}={total}",
    }


def _max_damage(formula: str) -> int:
    """计算伤害公式的满值"""
    import re
    total = 0
    parts = re.split(r'([+-])', formula)
    current_op = '+'
    for part in parts:
        part = part.strip()
        if part == '+':
            current_op = '+'
        elif part == '-':
            current_op = '-'
        elif 'D' in part.upper():
            match = re.match(r'(\d+)D(\d+)', part.upper())
            if match:
                count = int(match.group(1))
                sides = int(match.group(2))
                value = count * sides
                total = total + value if current_op == '+' else total - value
        elif part:
            value = int(part)
            total = total + value if current_op == '+' else total - value
    return total


def _min_damage(formula: str) -> int:
    """计算伤害公式的最小值（用于负DB）"""
    import re
    total = 0
    parts = re.split(r'([+-])', formula)
    current_op = '+'
    for part in parts:
        part = part.strip()
        if part == '+':
            current_op = '+'
        elif part == '-':
            current_op = '-'
        elif 'D' in part.upper():
            match = re.match(r'(\d+)D(\d+)', part.upper())
            if match:
                count = int(match.group(1))
                sides = int(match.group(2))
                value = count * 1  # 最小值
                total = total + value if current_op == '+' else total - value
        elif part:
            value = int(part)
            total = total + value if current_op == '+' else total - value
    return total
