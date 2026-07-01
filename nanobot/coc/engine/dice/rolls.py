"""
CoC 7e d100 骰子引擎
"""
import random
import re


def roll_d100(bonus_dice: int = 0, penalty_dice: int = 0) -> dict:
    """
    d100 掷骰，支持奖励/惩罚骰。

    奖励骰: 多掷一个十位骰，取最低结果（对玩家有利）。
    惩罚骰: 多掷一个十位骰，取最高结果（对玩家不利）。
    最大奖励/惩罚: 各 2 个。

    参数:
        bonus_dice: 奖励骰数量 (0-2)
        penalty_dice: 惩罚骰数量 (0-2)

    返回:
        {
            "total": int,           # 最终结果 (1-100)
            "tens_die": int,        # 十位骰结果 (1-10, 10=0)
            "unit_die": int,        # 个位骰结果 (1-10, 10=0)
            "all_tens": list[int],  # 所有十位骰结果 (含基础和奖励/惩罚)
            "bonus_dice_used": int,
            "penalty_dice_used": int,
            "detail": str,          # 人类可读描述
        }
    """
    bonus_dice = max(0, min(2, bonus_dice))
    penalty_dice = max(0, min(2, penalty_dice))

    # 基础十位骰和个位骰
    base_tens = random.randint(1, 10)
    unit = random.randint(1, 10)

    # 奖励/惩罚骰（额外十位骰）
    extra_tens = [random.randint(1, 10) for _ in range(bonus_dice + penalty_dice)]

    # 在 COC 中，十位骰的 10 = 0（十位为 0）
    def to_decader(val):
        return 0 if val == 10 else val

    all_tens = [base_tens] + extra_tens
    decaders = [to_decader(t) for t in all_tens]

    # 计算所有可能的 d100 结果
    def calc_total(dec):
        u = 0 if unit == 10 else unit
        if dec == 0 and u == 0:
            return 100
        return dec * 10 + u

    possible_totals = [calc_total(d) for d in decaders]

    if penalty_dice > 0 and bonus_dice == 0:
        # 惩罚: 取最高
        total = max(possible_totals)
        mode = "惩罚"
    elif bonus_dice > 0 and penalty_dice == 0:
        # 奖励: 取最低
        total = min(possible_totals)
        mode = "奖励"
    elif bonus_dice > 0 and penalty_dice > 0:
        # 同时有奖励和惩罚时，按"有效修正"处理
        net = bonus_dice - penalty_dice
        if net > 0:
            total = min(possible_totals)
            mode = "奖励"
        elif net < 0:
            total = max(possible_totals)
            mode = "惩罚"
        else:
            total = possible_totals[0]
            mode = "普通"
    else:
        total = possible_totals[0]
        mode = "普通"

    return {
        "total": total,
        "tens_die": base_tens,
        "unit_die": unit,
        "all_tens": all_tens,
        "bonus_dice_used": bonus_dice,
        "penalty_dice_used": penalty_dice,
        "detail": _format_d100_detail(total, base_tens, unit, extra_tens, bonus_dice, penalty_dice, mode),
    }


def _format_d100_detail(total, base_tens, unit, extra_tens, bonus, penalty, mode):
    """生成人类可读的掷骰描述"""
    u_str = unit if unit != 10 else "0"
    t_str = base_tens if base_tens != 10 else "0"
    parts = [f"d100: 十位={t_str} 个位={u_str} → {total}"]

    if extra_tens:
        extra_strs = [str(e) for e in extra_tens]
        label = "奖励骰" if bonus > 0 else "惩罚骰"
        parts.append(f"  {label}({'/'.join(extra_strs)})")

    if mode != "普通":
        parts.append(f"  [{mode}骰适用]")

    return " ".join(parts)


def roll_dice_expression(expr: str) -> dict:
    """
    通用骰子表达式求值。

    支持:
        - "3d6" → 3个六面骰
        - "1d8+2" → 1个八面骰 + 2
        - "1D4+1D6" → 混合骰子
        - "2d6+1D4+3" → 混合 + 固定加值

    参数:
        expr: 骰子表达式字符串

    返回:
        {
            "total": int,
            "rolls": list[int],
            "detail": str,
        }
    """
    expr = expr.strip().upper()
    pattern = r'(\d+)?D(\d+)'
    parts = re.split(pattern, expr)

    total = 0
    all_rolls = []
    detail_parts = []

    i = 0
    while i < len(parts):
        if re.match(r'^\d+$', parts[i]) and i + 2 < len(parts) and parts[i + 1] and parts[i + 2].isdigit():
            count = int(parts[i])
            sides = int(parts[i + 2])
            rolls = [random.randint(1, sides) for _ in range(count)]
            all_rolls.extend(rolls)
            sum_rolls = sum(rolls)
            total += sum_rolls
            detail_parts.append(f"{count}d{sides}: {'+'.join(map(str, rolls))}={sum_rolls}")
            i += 3
        elif re.match(r'^[+-]\d+$', parts[i]):
            total += int(parts[i])
            detail_parts.append(parts[i])
            i += 1
        elif parts[i] and re.match(r'^\d+$', parts[i]):
            # 裸数字作为固定加值
            total += int(parts[i])
            detail_parts.append(parts[i])
            i += 1
        else:
            i += 1

    return {
        "total": total,
        "rolls": all_rolls,
        "detail": " + ".join(detail_parts) + f" = {total}" if detail_parts else str(total),
    }


def roll_stat(formula: str = "3D6*5") -> int:
    """
    投掷角色属性值。

    标准 COC 公式:
        - STR/CON/DEX/APP/POW: 3D6×5 (15-90)
        - SIZ/INT: 2D6+6×5 (40-90)
        - EDU: (2D6+6)×5 或 (2D6+6)×5 + 年龄修正

    参数:
        formula: 属性公式

    返回:
        int: 属性百分值
    """
    # 处理 "3D6*5" 格式
    match = re.match(r'(\d+)D(\d+)(?:\s*\*\s*(\d+))?$', formula.upper())
    if match:
        count = int(match.group(1))
        sides = int(match.group(2))
        multiplier = int(match.group(3)) if match.group(3) else 1
        rolls = [random.randint(1, sides) for _ in range(count)]
        if "2D6+6" in formula.upper():
            # 处理 "2D6+6" 格式
            return (sum(rolls) + 6) * multiplier
        return sum(rolls) * multiplier

    # 处理 "(2D6+6)*5" 格式
    match = re.match(r'\((\d+)D(\d+)\s*\+\s*(\d+)\)\s*\*\s*(\d+)$', formula.upper())
    if match:
        count = int(match.group(1))
        sides = int(match.group(2))
        add = int(match.group(3))
        multiplier = int(match.group(4))
        rolls = [random.randint(1, sides) for _ in range(count)]
        return (sum(rolls) + add) * multiplier

    raise ValueError(f"无法解析属性公式: {formula}")
