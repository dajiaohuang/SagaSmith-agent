"""
CoC 7e 技能检定引擎 — d100 vs 阈值，五级成功判定。

核心概念:
    - 阈值 (threshold): 技能的百分值，如 50%、75%
    - 难度 (difficulty): regular / hard / extreme / critical
    - 成功等级: 大失败 / 失败 / 常规成功 / 困难成功 / 极难成功 / 大成功
    - 奖励骰 / 惩罚骰: 影响最终掷骰结果
    - Luck: 可消耗降低掷骰结果
    - 推掷 (Push): 可重新掷骰一次，但失败代价更大
"""

from enum import IntEnum


class SuccessLevel(IntEnum):
    """成功等级"""
    FUMBLE = -99
    FAILURE = 0
    REGULAR = 1
    HARD = 2
    EXTREME = 3
    CRITICAL = 4


class Difficulty(IntEnum):
    """难度等级"""
    UNKNOWN = -1
    REGULAR = 1
    HARD = 2
    EXTREME = 3
    CRITICAL = 4
    IMPOSSIBLE = 9


DIFFICULTY_LABELS = {
    Difficulty.REGULAR: "常规",
    Difficulty.HARD: "困难",
    Difficulty.EXTREME: "极难",
    Difficulty.CRITICAL: "大成功",
    Difficulty.UNKNOWN: "未知",
    Difficulty.IMPOSSIBLE: "不可能",
}

SUCCESS_LABELS = {
    SuccessLevel.FUMBLE: "大失败",
    SuccessLevel.FAILURE: "失败",
    SuccessLevel.REGULAR: "常规成功",
    SuccessLevel.HARD: "困难成功",
    SuccessLevel.EXTREME: "极难成功",
    SuccessLevel.CRITICAL: "大成功",
}


def threshold_ranges(threshold: int, flat_threshold_modifier: int = 0) -> dict:
    """
    计算给定阈值下的各成功等级数值范围。

    COC 7e 规则:
        - 大成功 (Critical): 01
        - 极难成功 (Extreme): ≤ 阈值/5
        - 困难成功 (Hard): ≤ 阈值/2
        - 常规成功 (Regular): ≤ 阈值
        - 失败: 常规+1 到 大失败-1
        - 大失败 (Fumble): 96-100 (阈值<50) 或 100 (阈值≥50)

    参数:
        threshold: 基础阈值 (百分比)
        flat_threshold_modifier: 阈值修正值

    返回:
        {成功等级: [下限, 上限], ...}
    """
    effective_threshold = threshold + flat_threshold_modifier

    extreme = max(1, effective_threshold // 5)
    hard = max(1, effective_threshold // 2)
    regular = max(1, effective_threshold)

    # 大失败下限
    if effective_threshold < 50:
        fumble_min = 96
    else:
        fumble_min = 100

    result = {}

    # 大成功
    result[SuccessLevel.CRITICAL] = [1, 1]

    # 极难成功 (01 ~ floor(threshold/5))
    if extreme > 1:
        result[SuccessLevel.EXTREME] = [2, extreme]
    else:
        result[SuccessLevel.EXTREME] = [1, 1]

    # 困难成功 (extreme+1 ~ floor(threshold/2))
    result[SuccessLevel.HARD] = [extreme + 1, hard]

    # 常规成功 (hard+1 ~ threshold)
    result[SuccessLevel.REGULAR] = [hard + 1, regular]

    # 失败 (regular+1 ~ fumble_min-1)
    if regular + 1 <= fumble_min - 1:
        result[SuccessLevel.FAILURE] = [regular + 1, fumble_min - 1]

    # 大失败 (fumble_min ~ 100)
    result[SuccessLevel.FUMBLE] = [fumble_min, 100]

    return result


def resolve_skill_check(
    d100_total: int,
    threshold: int,
    difficulty: str | Difficulty = "regular",
    bonus_dice: int = 0,
    penalty_dice: int = 0,
    flat_dice_modifier: int = 0,
    flat_threshold_modifier: int = 0,
    luck_spent: int = 0,
    skill_name: str = "",
    investigator_name: str = "",
) -> dict:
    """
    完整技能检定结算。

    参数:
        d100_total: d100 掷骰结果 (1-100)
        threshold: 技能阈值 (百分比)
        difficulty: 难度等级
        bonus_dice: 奖励骰数量
        penalty_dice: 惩罚骰数量
        flat_dice_modifier: 掷骰结果修正 (加/减)
        flat_threshold_modifier: 阈值修正
        luck_spent: 消耗的幸运值
        skill_name: 技能名称
        investigator_name: 调查员名称

    返回:
        {
            "d100": int,
            "modified_total": int,
            "threshold": int,
            "difficulty": str,
            "effective_threshold": int,
            "success": bool,
            "success_level": str,
            "is_critical": bool,
            "is_fumble": bool,
            "luck_required_regular": int,
            "luck_required_hard": int,
            "luck_required_extreme": int,
            "luck_required_critical": int,
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    # 规范化参数
    if isinstance(difficulty, str):
        try:
            difficulty = Difficulty[difficulty.upper()]
        except KeyError:
            difficulty = Difficulty.REGULAR

    # 计算修正后总值
    modified_total = d100_total + flat_dice_modifier - luck_spent
    modified_total = max(1, min(100, modified_total))

    # 计算阈值范围
    ranges = threshold_ranges(threshold, flat_threshold_modifier)

    # 确定成功等级
    success_level = None
    for level in sorted(ranges.keys(), reverse=True):
        lo, hi = ranges[level]
        if lo <= modified_total <= hi:
            success_level = level
            break

    if success_level is None:
        success_level = SuccessLevel.FAILURE

    # 按难度判定是否算"成功"
    is_success = success_level >= difficulty

    # 计算晋升各级成功所需的 luck 值
    luck_required_regular = _luck_required(modified_total, ranges.get(SuccessLevel.REGULAR))
    luck_required_hard = _luck_required(modified_total, ranges.get(SuccessLevel.HARD))
    luck_required_extreme = _luck_required(modified_total, ranges.get(SuccessLevel.EXTREME))
    luck_required_critical = _luck_required(modified_total, ranges.get(SuccessLevel.CRITICAL))

    # 构建展示文本
    detail_lines = []
    skill_label = skill_name or "技能"
    name_label = investigator_name or "调查员"

    diff_label = DIFFICULTY_LABELS.get(difficulty, "常规")
    action_line = f"【{skill_label}检定·{diff_label}】{name_label}：阈值 {threshold}"
    if flat_threshold_modifier:
        action_line += f" ({threshold:+d}修正)"
    detail_lines.append(action_line)

    dice_str = f"  → d100 = {d100_total}"
    if bonus_dice or penalty_dice:
        modifiers = []
        if bonus_dice:
            modifiers.append(f"奖励骰{bonus_dice}")
        if penalty_dice:
            modifiers.append(f"惩罚骰{penalty_dice}")
        dice_str += f" ({'/'.join(modifiers)})"
    if flat_dice_modifier:
        dice_str += f" {'+' if flat_dice_modifier > 0 else ''}{flat_dice_modifier}"
    if luck_spent:
        dice_str += f" -{luck_spent}(幸运)"
    dice_str += f" = {modified_total}"
    detail_lines.append(dice_str)

    success_label = SUCCESS_LABELS.get(success_level, "未知")
    result_str = (
        f"  → {success_label}"
        f"（{modified_total} / 阈值 {threshold}）"
    )
    if success_level == SuccessLevel.CRITICAL:
        result_str += " ⚡"
    elif success_level == SuccessLevel.FUMBLE:
        result_str += " 💀"
    elif is_success:
        result_str += " ✅"
    else:
        result_str += " ❌"
    detail_lines.append(result_str)

    summary_line = (
        f"{name_label}（{skill_label} {threshold}%）："
        f"d100={d100_total}"
    )
    if luck_spent:
        summary_line += f" -{luck_spent}幸"
    summary_line += f" = {modified_total} → {success_label}"
    if is_success:
        summary_line += " ✅"
    else:
        summary_line += " ❌"

    return {
        "d100": d100_total,
        "modified_total": modified_total,
        "threshold": threshold,
        "difficulty": difficulty.name.lower() if hasattr(difficulty, 'name') else str(difficulty),
        "effective_threshold": threshold + flat_threshold_modifier,
        "success": is_success,
        "success_level": success_level,
        "success_label": success_label,
        "is_critical": success_level == SuccessLevel.CRITICAL,
        "is_fumble": success_level == SuccessLevel.FUMBLE,
        "luck_required_regular": luck_required_regular,
        "luck_required_hard": luck_required_hard,
        "luck_required_extreme": luck_required_extreme,
        "luck_required_critical": luck_required_critical,
        "detail_lines": detail_lines,
        "summary_line": summary_line,
    }


def _luck_required(current: int, target_range: list[int] | None) -> int:
    """计算从 current 降到 target_range 所需幸运值"""
    if target_range is None:
        return 0
    lo, hi = target_range
    if current <= hi:
        return 0
    return current - hi


def get_success_label(level: int) -> str:
    """获取成功等级的中文标签"""
    return SUCCESS_LABELS.get(level, f"等级{level}")
