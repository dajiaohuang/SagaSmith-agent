[English](COMBAT_SYSTEM.md) | [简体中文]

# 战斗系统

本文档说明 **DM 模式** 与 **骰娘模式** 下的战斗行为，包括回合流程、动作配额追踪、LLM Agent 战斗工具、自然语言行动解析和追问机制。

## 共享战斗核心

DM 模式与骰娘模式使用同一套确定性战斗管线。差异只影响叙述权限和 NPC 控制方式：

| | DM 模式 | 骰娘模式 |
|---|---------|---------|
| 输出 | 机械数据 → LLM 叙事包装 | 纯机械数据 |
| 扮演 | ✅ NPC 台词、环境描写 | ❌ 禁止 |
| 建议 | ✅ 战术建议 (默认) | ❌ 禁止 (默认) |
| 系统路径 | `resolve_chat(mode="dm")` | `resolve_chat(mode="dice")` |

共同规则：

- 战斗只读取 HotSnapshot 热数据。AC、HP、调整值、豁免、先攻、施法数值、物品和持续效果来自 `get_hot_character()`。
- 所有投骰通过 `checked_roll()` 执行（`random.randint` + `DiceAuditLog` 审计）。
- 没有实体角色卡的角色不能加入先攻。
- 系统为所有参战角色投掷先攻并进入回合制模式。

## 回合动作配额

v3.0 起，回合内动作由系统追踪配额，而非每步自动推进回合。

```
回合开始 → 恢复配额:
  main_action: 1        主动作 (攻击、施法、疾走、撤退、闪避等)
  bonus_action: 1       附赠动作 (双武器副手、灵巧施法等)
  reaction: 1           反应 (借机攻击、护盾术等，回合外也可用)
  movement: speed       移动距离 (尺)
  extra_actions: 0      动作如潮等特性增加

每次 combat_attack/combat_cast_spell  → 扣 main_action (或 extra_actions)
combat_attack(bonus_action=True)       → 扣 bonus_action
combat_dash/disengage/dodge            → 扣 main_action
use_feature("action_surge")            → extra_actions += 1
move(distance)                         → movement -= distance
end_turn()                             → 推进回合
```

回合不会自动推进。玩家必须说"结束回合"或调用 `end_turn` 才推进。

## 战斗工具

### 行动工具

| 工具 | 消耗 | 自动结算 |
|------|------|---------|
| `combat_attack` | main_action 或 bonus_action 或 extra_actions | d20+加值 → 攻击骰；伤害骰 |
| `combat_cast_spell` | main_action 或 bonus_action 或 extra_actions | 法术DC/攻击骰 |
| `combat_ability_check` | main_action | d20+调整值 (推撞/擒抱等) |
| `combat_dash` | main_action | 速度翻倍 |
| `combat_disengage` | main_action | 免借机攻击 |
| `combat_dodge` | main_action | 攻击劣势，敏捷豁免优势 |
| `use_feature` | 特性决定 | 动作如潮、回气、至圣斩等 |
| `move` | movement | 移动到指定位置 |
| `end_turn` | — | 结束回合，推进到下一个行动者 |

### 查询/追问工具

| 工具 | 消耗 | 说明 |
|------|------|------|
| `ask_clarification` | 无 | 信息不足时追问，不消耗动作 |
| `turn_status` | 无 | 查询当前回合剩余动作配额 |

### 检定工具

| 工具 | 说明 |
|------|------|
| `ability_check` | 属性/技能检定，读热数据 |
| `saving_throw` | 豁免检定，读热数据 |
| `apply_damage` | 造成伤害，更新 HP |
| `apply_healing` | 治疗，更新 HP |
| `apply_condition` | 添加状态 |
| `remove_condition` | 移除状态 |

## 自然语言行动流程

```
轮到卡利恩 (Fighter Lv5)
  → 系统: 剩余: 主动作1, 附赠1, 反应1, 移动30

用户: "我用长剑攻击地精"
  → combat_attack(target="地精", weapon="长剑")
  → main_action: 1→0
  → "命中，8点。剩余: 附赠1, 移动30"

用户: "动作如潮"
  → use_feature("action_surge")
  → extra_actions: 0→1
  → "动作如潮发动。剩余: 主动作1, 附赠1, 移动30"

用户: "再打兽人"
  → combat_attack(target="兽人")
  → extra_actions: 1→0
  → "命中，12点。剩余: 附赠1, 移动30"

用户: "用附赠动作副手攻击地精"
  → combat_attack(target="地精", weapon="短剑", use_bonus_action=True)
  → bonus_action: 1→0
  → "副手命中，4点"

用户: "结束回合"
  → end_turn → advance_turn
  → "轮到地精了"
```

### 追问示例

```
用户: "我用法术打他"
  → LLM: ask_clarification("用哪个法术？准备有魔法飞弹(1环)、火球术(3环)")
用户: "火球术"
  → LLM: ask_clarification("几环？还有1个3环和2个4环")
用户: "3环"
  → LLM: ask_clarification("目标是谁？")
用户: "兽人和地精"
  → combat_cast_spell(spell="火球术", level=3, targets=["兽人","地精"], save_type="dex")
  → main_action: 1→0, spell_slots[3]: 1→0
  → "火球术 DC15。请 DM 投目标豁免。伤害 8d6=32"
```

## 热数据注入

每个战斗回合的 LLM system prompt 中包含：
- 当前行动角色 HotSnapshot (含 buff/debuff 后的实时属性)
- 全体参战者 HotSnapshot 列表
- 先攻顺序 + 当前轮次
- 回合动作配额

## 共享规则（DM 与骰娘一致）

- 先攻、回合推进、反应窗口：共用 `campaign_turns.py` 和 `combat_reactions.py`
- 投骰审计：共用 `checked_roll()` + `DiceAuditLog`
- 热数据：共用 `get_hot_character()`
- 战斗工具：共用 `tools/combat_tools.py` 和 `tools/check_tools.py`

## DM 模式战斗

可以：描写环境、扮演 NPC、表现剧情、给战术建议。
必须：从 HotSnapshot 读取机械数值，不虚构。

## 骰娘模式战斗

可以：结算攻击、施法、检定、伤害、治疗、状态、反应。
不得：描写场景、扮演 NPC、给战术建议（`/combatadviceon` 可开启）。
