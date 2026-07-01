# 调查员创建指南

## Step 1: 掷属性 (Characteristics)

| 属性 | 公式 | 范围 |
|------|------|------|
| STR (力量) | 3D6 × 5 | 15-90 |
| CON (体质) | 3D6 × 5 | 15-90 |
| SIZ (体型) | (2D6+6) × 5 | 40-90 |
| DEX (敏捷) | 3D6 × 5 | 15-90 |
| APP (外貌) | 3D6 × 5 | 15-90 |
| INT (智力) | (2D6+6) × 5 | 40-90 |
| POW (意志) | 3D6 × 5 | 15-90 |
| EDU (教育) | (2D6+6) × 5 | 40-90 |

使用 `make_characteristics()` 创建模板，或逐属性 `roll_stat()`。

## Step 2: 计算衍生属性

| 属性 | 公式 |
|------|------|
| HP | (SIZ + CON) / 10 |
| MP | POW / 5 |
| SAN | POW (初始上限 99) |
| Luck | 3D6 × 5 (初始) |
| MOV | 根据 DEX/SIZ/STR 确定 (通常 8) |
| DB | 根据 STR+SIZ 查表 |
| Build | 根据 STR+SIZ 查表 |

## Step 3: 选择职业

通过 `coc7_character` 的 `occupation` 字段指定。

职业决定：
- 职业技能点 = 某属性 × 乘数
- 信用评级范围
- 职业技能列表

## Step 4: 分配技能点

- 职业技能点 = 职业指定的属性 × 乘数 (通常 EDU × 2 或 INT × 2)
- 个人兴趣点 = INT × 2
- 将点数分配到技能的 adjustment 字段中

## Step 5: 决定装备和资金

- 信用评级决定初始资金
- 守秘人确认装备

## Step 6: 填写背景

- 传记、个人描述、理念、重要之人、关键地点、珍爱之物
- 通过 `coc7_character update character_id=<id> fields={...}` 更新

## Step 7:（可选）Pulp 原型

Pulp 规则下选择原型，获得额外属性和技能点。
通过 `archetype` 字段指定。
