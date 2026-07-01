"""
CoC 7e 技能成长引擎。

CoC 的"升级"系统:
    - 使用技能时获得成长标记（在技能检定中 roll 常规成功）
    - 幕间成长: d100 > 当前技能值 → +1D10
    - 掌握 (Mastery): 技能 ≥ 90 → 获得 2D6 SAN 恢复
    - 幸运成长: d100 > 当前幸运 → +2D10
"""

import random
from .dice.rolls import roll_dice_expression


def resolve_skill_development(
    current_value: int,
) -> dict:
    """
    技能成长判定。

    COC 规则:
        - 成长需要在技能检定中获得常规成功（标记成长）
        - 幕间: d100 > 当前值 → +1D10
        - 掌握 (≥ 90): 获得 2D6 SAN 恢复
        - 成长不可使技能 > 100

    参数:
        current_value: 当前技能值 (0-100)

    返回:
        {
            "improved": bool,           # 是否成功成长
            "gain": int,                # 成长值 (1-10)
            "new_value": int,           # 新技能值
            "mastered": bool,           # 是否达到掌握 (≥90)
            "san_recovery": int | None, # 掌握时的 SAN 恢复 (2D6)
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    # 确定成长量
    improvement_roll = random.randint(1, 100)
    improved = improvement_roll > current_value

    if not improved:
        return {
            "improved": False,
            "gain": 0,
            "new_value": current_value,
            "mastered": False,
            "san_recovery": None,
            "detail_lines": [
                f"【技能成长】当前 {current_value}%",
                f"  → d100 = {improvement_roll} ≤ {current_value}，未成长",
            ],
            "summary_line": f"技能成长失败（{improvement_roll} ≤ {current_value}）",
        }

    # 掷成长骰 1D10
    gain_roll = random.randint(1, 10)
    new_value = min(100, current_value + gain_roll)

    # 掌握判定
    mastered = new_value >= 90
    san_recovery = None
    if mastered:
        san_roll1 = random.randint(1, 6)
        san_roll2 = random.randint(1, 6)
        san_recovery = san_roll1 + san_roll2

    detail_lines = [
        f"【技能成长】当前 {current_value}%",
        f"  → d100 = {improvement_roll} > {current_value} ✅ 成长！",
        f"  → 1D10 = {gain_roll}，新值 = {new_value}",
    ]
    if mastered:
        detail_lines.append(f"  ⭐ 技能掌握！获得 {san_recovery} SAN 恢复")

    return {
        "improved": True,
        "gain": gain_roll,
        "new_value": new_value,
        "mastered": mastered,
        "san_recovery": san_recovery,
        "detail_lines": detail_lines,
        "summary_line": (
            f"技能成长: {current_value} → {new_value} (+{gain_roll})"
            + (f" ⭐ 掌握 +{san_recovery} SAN" if mastered else "")
        ),
    }


def resolve_luck_development(
    current_luck: int,
) -> dict:
    """
    幸运成长判定。

    COC 规则:
        - 幕间: d100 > 当前幸运 → +2D10

    参数:
        current_luck: 当前幸运值

    返回:
        {
            "improved": bool,
            "gain": int,
            "new_value": int,
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    improvement_roll = random.randint(1, 100)
    improved = improvement_roll > current_luck

    if not improved:
        return {
            "improved": False,
            "gain": 0,
            "new_value": current_luck,
            "detail_lines": [
                f"【幸运成长】当前 {current_luck}",
                f"  → d100 = {improvement_roll} ≤ {current_luck}，未成长",
            ],
            "summary_line": f"幸运未成长（{improvement_roll} ≤ {current_luck}）",
        }

    # 2D10
    r1 = random.randint(1, 10)
    r2 = random.randint(1, 10)
    gain = r1 + r2
    new_value = current_luck + gain

    return {
        "improved": True,
        "gain": gain,
        "new_value": new_value,
        "detail_lines": [
            f"【幸运成长】当前 {current_luck}",
            f"  → d100 = {improvement_roll} > {current_luck} ✅ 成长！",
            f"  → 2D10 = {r1} + {r2} = {gain}，新值 = {new_value}",
        ],
        "summary_line": f"幸运成长: {current_luck} → {new_value} (+{gain})",
    }


def mark_skill_for_development(success_level: int) -> bool:
    """
    判断技能检定是否可标记成长。

    COC 规则: 常规成功 (非大成功/困难/极难) 才标记
    但简化规则: 任何成功都可以标记
    """
    from .checks.skill import SuccessLevel
    return success_level >= SuccessLevel.REGULAR
