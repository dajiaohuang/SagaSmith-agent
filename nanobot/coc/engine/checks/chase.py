"""
CoC 7e 追逐系统引擎。

追逐规则:
    - 参与者按 MOV 排序
    - 每轮行动次数 = MOV - 偏移 + 1
    - 速度检定: 成功 → MOV+1 / 失败 → MOV-1
    - 可以进行射击、施法等追逐行动
"""

from .skill import resolve_skill_check, SuccessLevel


def resolve_chase_speed_check(
    d100_result: int,
    current_mov: int,
    difficulty: str = "regular",
    participant_name: str = "",
) -> dict:
    """
    追逐速度检定。

    CoC 追逐规则:
        - 大成功/极难成功: MOV + 2
        - 困难成功: MOV + 1
        - 常规成功: MOV 不变
        - 失败: MOV - 1
        - 大失败: MOV - 1 且绊倒/物品掉落

    参数:
        d100_result: 速度检定 d100 结果
        current_mov: 当前 MOV 值
        difficulty: 难度
        participant_name: 参与者名称

    返回:
        {
            "new_mov": int,
            "mov_change": int,         # MOV 变化量
            "success_level": int,
            "tripped": bool,           # 是否绊倒
            "actions": int,            # 当前可行动作次数
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    # MOV 作为"阈值"进行检定 (MOV 越高越好)
    threshold = max(1, current_mov * 10)  # MOV 1-20 → 阈值 10%-200%

    # 但 COC 追逐中实际上是 d100 vs 某个固定难度
    # 此处简化: 使用 MOV 值作为百分比
    skill_value = current_mov * 5  # MOV 8 → 40%

    result = resolve_skill_check(
        d100_total=d100_result,
        threshold=skill_value,
        difficulty=difficulty,
        skill_name="速度检定",
        investigator_name=participant_name,
    )

    success_level = result["success_level"]
    tripped = False
    mov_change = 0

    if success_level >= SuccessLevel.EXTREME:
        mov_change = 2
    elif success_level >= SuccessLevel.HARD:
        mov_change = 1
    elif success_level >= SuccessLevel.REGULAR:
        mov_change = 0
    else:
        mov_change = -1
        if success_level == SuccessLevel.FUMBLE:
            tripped = True

    new_mov = max(1, current_mov + mov_change)
    actions = calc_chase_actions(new_mov)

    detail_lines = [
        f"【追逐速度检定】{participant_name}：当前 MOV {current_mov}",
        f"  → MOV {current_mov} {'+' if mov_change >= 0 else ''}{mov_change} = {new_mov}",
        f"  → 可行动作: {actions}",
    ]
    if tripped:
        detail_lines.append("  💀 绊倒/物品掉落！")

    summary = f"{participant_name} MOV {current_mov} → {new_mov}"
    if tripped:
        summary += " (绊倒)"
    summary += f" | 动作 {actions}"

    return {
        "new_mov": new_mov,
        "mov_change": mov_change,
        "success_level": success_level,
        "tripped": tripped,
        "actions": actions,
        "detail_lines": detail_lines,
        "summary_line": summary,
    }


def calc_chase_actions(mov: int, offset: int = 0) -> int:
    """
    计算追逐中的可行动作次数。

    公式: actions = MOV - offset + 1
    offset 通常为 0，但在复杂地形中可能 > 0

    参数:
        mov: 当前 MOV 值
        offset: 追逐偏移值 (通常 0)

    返回:
        int: 可行动作次数
    """
    return max(1, mov - offset + 1)


def can_assist(participant_mov: int, target_mov: int) -> bool:
    """
    判断一个参与者是否能协助另一个。
    条件: 两者同阵营，且速度接近 (MOV 差 ≤ 3)
    """
    return abs(participant_mov - target_mov) <= 3


def resolve_chase_action(
    action_type: str,
    skill_value: int,
    d100_result: int,
    distance: int = 0,
    modifier: int = 0,
    actor_name: str = "",
) -> dict:
    """
    追逐中的具体行动检定。

    行动类型:
        - "catch_up": 缩短距离
        - "escape": 逃脱
        - "shoot": 射击
        - "cast_spell": 施法
        - "obstacle": 越过障碍

    参数:
        action_type: 行动类型
        skill_value: 对应技能值
        d100_result: 检定结果
        distance: 当前距离
        modifier: 修正值
        actor_name: 行动者名称

    返回:
        dict: 行动结果
    """
    action_labels = {
        "catch_up": "缩短距离",
        "escape": "逃脱",
        "shoot": "射击",
        "cast_spell": "施法",
        "obstacle": "越过障碍",
    }

    result = resolve_skill_check(
        d100_total=d100_result,
        threshold=skill_value,
        flat_threshold_modifier=modifier,
        skill_name=action_labels.get(action_type, action_type),
        investigator_name=actor_name,
    )

    distance_change = 0
    if action_type == "catch_up":
        if result["success"]:
            distance_change = -1
        else:
            distance_change = 1
    elif action_type == "escape":
        if result["success"]:
            distance_change = 1

    return {
        "action_type": action_type,
        "success": result["success"],
        "success_level": result["success_level"],
        "distance_change": distance_change,
        "new_distance": max(0, distance + distance_change),
        "detail_lines": result["detail_lines"],
        "summary_line": result["summary_line"],
    }
