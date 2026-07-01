# CoC 7e 守秘人输出格式模板

## 检定结果输出

### 技能检定
```
【技能名称检定·难度】调查员名：阈值 X%
  → d100 = YY (奖励骰/惩罚骰)
  → 结果 = YY (阈值 X%) → 常规成功 ✅
```

### 战斗攻击
```
【近战攻击】攻击者（武器名）：技能 X%
  → d100 = YY = 结果
  → 命中！伤害: D+DB = N 点
```

### 理智损失
```
【理智损失】调查员名：来源
  → SAN XX - N = YY（上限 ZZ）
  ⚠️ 损失 ≥ 5 → 临时疯狂
```

## 叙事输出

### 场景描述
```
地点：
时间：
氛围：[感官细节描述]

[场景主要描述]
```

### NPC 介绍
```
[NPC 名] — [简要印象]
[外貌和举止描述]
```

### 线索呈现
```
[线索描述]

隐藏信息：（仅守秘人可见）
[DC 或检定类型]
```

## Snapshot 存档格式

```json
{
  "snapshot": {
    "campaign_id": "...",
    "schema_version": 1,
    "captured_at": "2026-06-30T...",
    "payload": {
      "world_state": {...},
      "party": {...},
      "characters": [...],
      "combats": [...],
      "plot_summaries": [...],
      "events": [...],
      "scene_states": [...],
      "channel_bindings": [...],
      "rule_profile": {...}
    }
  }
}
```
