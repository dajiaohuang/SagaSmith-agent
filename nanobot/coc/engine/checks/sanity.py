"""
CoC 7e 理智系统 (Sanity) — 理智损失、临时/不定期疯狂、狂乱发作。

核心规则:
    - SAN max = 99 - CthulhuMythos 技能值
    - 损失 ≥ 5 → 临时疯狂 (Temporary Insanity)
    - 当日累计 ≥ daily_limit → 不定期疯狂 (Indefinite Insanity)
    - 狂乱发作 (Bout of Madness): 投表决定具体症状
    - Pulp 规则: 可消耗 Luck 减半理智损失
"""

from enum import IntEnum
import random


class InsanityType(IntEnum):
    """疯狂类型"""
    NONE = 0
    TEMPORARY = 1      # 临时疯狂
    INDEFINITE = 2     # 不定期疯狂
    PERMANENT = 3      # 永久疯狂 (极端情况)


BOUT_TABLE_REAL = [
    ("失忆", "陷入失忆状态，不知道自己是谁。"),
    ("躯体症状", "出现身体症状如失明、失聪、颤抖。"),
    ("暴力倾向", "对周围人或物进行暴力攻击。"),
    ("偏执", "严重偏执，认为所有人都在迫害自己。"),
    ("重大人格", "人格发生重大改变。"),
    ("恐惧", "被强烈的恐惧支配。"),
    ("狂躁", "出现狂躁行为。"),
    ("幻觉", "出现强烈的幻觉。"),
    ("心理依赖", "对某人或某物产生心理依赖。"),
    ("昏厥", "直接昏厥。"),
]

BOUT_TABLE_SUMMARY = [
    ("失忆 / 神游", "茫然而行，无法记起自己的行为。"),
    ("躯体症状", "心脏狂跳、视力模糊、肌肉痉挛。"),
    ("退缩", "蜷缩哭泣，无法行动。"),
    ("暴力倾向", "对最近的人或物进行暴力攻击。"),
    ("偏执", "认为有人正在追杀自己，表现出极度的不信任。"),
    ("重大人格", "人格特质发生永久或半永久的改变。"),
    ("恐惧", "被强烈的恐惧支配，表现出回避行为。"),
    ("狂躁", "表现出难以自控的狂躁冲动。"),
    ("幻觉", "持续的幻觉影响正常判断。"),
    ("昏厥 / 假性死亡", "进入类似昏迷的状态。"),
]


def calculate_sanity_max(cthulhu_mythos_value: int = 0) -> int:
    """计算 SAN 上限 = 99 - CthulhuMythos"""
    return max(0, 99 - cthulhu_mythos_value)


def resolve_sanity_loss(
    current_san: int,
    san_max: int,
    loss_amount: int,
    daily_loss_accumulated: int = 0,
    daily_limit: int | None = None,
    cthulhu_mythos_value: int = 0,
    is_mythos_hardened: bool = False,
    pulp_rules: bool = False,
    investigator_name: str = "",
    source: str = "",
) -> dict:
    """
    理智损失完整结算。

    参数:
        current_san: 当前 SAN 值
        san_max: SAN 上限
        loss_amount: 理智损失量
        daily_loss_accumulated: 当日已累计损失
        daily_limit: 当日上限 (默认 = current_san // 5)
        cthulhu_mythos_value: Cthulhu Mythos 技能值 (影响上限)
        is_mythos_hardened: 是否已对 Mythos 产生免疫
        pulp_rules: 是否启用 Pulp 规则 (可 Luck 减半)
        investigator_name: 调查员名称
        source: 损失来源描述

    返回:
        {
            "new_san": int,
            "actual_loss": int,       # 实际损失量
            "indef_insanity_daily_limit": int,
            "temp_insanity": bool,     # 是否进入临时疯狂
            "indef_insanity": bool,    # 是否进入不定期疯狂
            "insanity_type": str,      # "none" / "temporary" / "indefinite"
            "bout_of_madness": bool,   # 是否需要狂乱发作
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    detail_lines = []
    actual_loss = loss_amount

    # 应用 hardness 减免
    if is_mythos_hardened:
        actual_loss = max(0, actual_loss // 2)
        detail_lines.append(f"  (Mythos Hardened: 损失减半为 {actual_loss})")

    # 新 SAN 值
    new_san = max(0, current_san - actual_loss)
    new_san = min(new_san, san_max)

    # 临时疯狂判定: 单次损失 ≥ 5
    temp_insanity = actual_loss >= 5

    # 不定期疯狂判定
    new_daily_loss = daily_loss_accumulated + actual_loss
    daily_limit = daily_limit if daily_limit is not None else max(1, current_san // 5)
    indef_insanity = temp_insanity and new_daily_loss >= daily_limit

    # 确定疯狂类型
    if indef_insanity:
        insanity_type = "indefinite"
    elif temp_insanity:
        insanity_type = "temporary"
    else:
        insanity_type = "none"

    bout_of_madness = temp_insanity

    detail_lines.append(
        f"【理智损失】{investigator_name}：{source or '未知来源'}"
    )
    detail_lines.append(f"  → SAN {current_san} - {actual_loss} = {new_san}（上限 {san_max}）")

    if temp_insanity:
        detail_lines.append(f"  ⚠️ 损失 ≥ 5 → 临时疯狂")
        if indef_insanity:
            detail_lines.append(f"  ⚠️⚠️ 当日累计 {new_daily_loss}/{daily_limit} → 不定期疯狂！")
        else:
            detail_lines.append(f"  当日累计 {new_daily_loss}/{daily_limit}")

    summary = (
        f"{investigator_name} SAN: {current_san} → {new_san}"
        f" (损失 {actual_loss})"
    )
    if insanity_type == "indefinite":
        summary += " ⚠️ 不定期疯狂"
    elif insanity_type == "temporary":
        summary += " ⚠️ 临时疯狂"

    return {
        "new_san": new_san,
        "actual_loss": actual_loss,
        "daily_loss_accumulated": new_daily_loss,
        "daily_limit": daily_limit,
        "indef_insanity_daily_limit": daily_limit,
        "temp_insanity": temp_insanity,
        "indef_insanity": indef_insanity,
        "insanity_type": insanity_type,
        "bout_of_madness": bout_of_madness,
        "detail_lines": detail_lines,
        "summary_line": summary,
    }


def roll_bout_of_madness(real_time: bool = True) -> dict:
    """
    狂乱发作表掷骰。

    参数:
        real_time: True = 实时发作 (战斗轮中), False = 总结型 (幕间)

    返回:
        {
            "type": str,         # 狂乱类型名称
            "description": str,  # 症状描述
            "roll": int,         # d10 结果
            "is_phobia": bool,   # 是否恐惧症
            "is_mania": bool,    # 是否狂躁症
        }
    """
    table = BOUT_TABLE_REAL if real_time else BOUT_TABLE_SUMMARY
    roll = random.randint(1, 10)
    name, desc = table[roll - 1]

    return {
        "type": name,
        "description": desc,
        "roll": roll,
        "is_phobia": name in ("恐惧", "偏执"),
        "is_mania": name in ("狂躁", "暴力倾向"),
    }


def is_temporary_insanity(san_loss: int) -> bool:
    """判断是否触发临时疯狂（损失 ≥ 5）"""
    return san_loss >= 5


def calculate_daily_limit(current_san: int) -> int:
    """计算每日理智损失上限"""
    return max(1, current_san // 5)
