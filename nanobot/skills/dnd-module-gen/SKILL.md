---
name: dnd-module-gen
description: Generate D&D 5e adventure modules. Supports one-shot, short (3 chapters), medium (5 chapters), long (8 chapters), and sandbox. Use when the user asks to create, generate, or make a new adventure, module, or campaign setting.
---

# D&D Module Generator

Generate playable D&D 5e modules as Markdown text, then import them into the campaign database.

## Step 1: Determine Type

| Type | Chapters | Sessions | When to Use |
|------|----------|----------|-------------|
| **one-shot** | 1 | 1 (3-6h) | tonight's game |
| **short** | 3 | 3-8 | mini-campaign |
| **medium** | 5 | 2-4 months | full story arc |
| **long** | 8 | 6+ months | epic campaign |
| **sandbox** | 4-6 regions | open | player-driven |

Default: short. Ask the user or infer from their request.

## Step 2: Choose Paradigm

Each type has a default paradigm; user can override.

| Type | Default Paradigms | Alternatives |
|------|-------------------|--------------|
| one-shot | Five-Room Dungeon, Mystery, Heist | Beat Charts, Reverse Dungeon |
| short | Three-Act, Kishōtenketsu | Race Against Time, Island Design, Seven-Point |
| medium | Hero's Journey, Plot Point | Fish Tank Intrigue, Pointcrawl, Faction Turn |
| long | Double Triangle, Conspyramid | Megadungeon, Technoir Transmission |
| sandbox | Hexcrawl, Node-Based | Decision-Based, Blorb, Faction Turn |

### Paradigm Reference

**Space-driven (location as structure):**
- **Five-Room Dungeon**: entrance guardian → puzzle/RP → trick/setback → climax → reward/revelation. 5 scenes.
- **Node-Based / Pointcrawl**: nodes (places, NPCs, events) connected by clues/geography/time. Non-linear.
- **Hexcrawl**: hex grid map, each hex has encounters/locations. Random encounter tables.
- **Megadungeon**: multi-level dungeon, looping routes, factions within, unguarded treasure.
- **Island Design**: independent modular elements, explored in any order.

**Story-driven (narrative beats as structure):**
- **Three-Act**: establish → confront → resolve. Midpoint twist.
- **Hero's Journey**: ordinary world → cross threshold → trials → abyss → return.
- **Double Triangle**: rise (false victory) → fall → redemption. Ch.4 twist: players helped the villain.
- **Kishōtenketsu** (起承转合): introduce → develop → twist (non-conflict) → harmony. No required antagonist.
- **Beat Charts**: Hook → alternating Developments & Cliffhangers → Resolution.
- **Hamlet's Hit Points**: alternating hope/fear beats. Procedural beats (goals) + dramatic beats (emotions).
- **Seven-Point Story**: Hook → Plot Turn 1 → Pinch 1 → Midpoint → Pinch 2 → Plot Turn 2 → Resolution.

**Play-driven (mechanics as structure):**
- **Heist**: intel gathering → planning → execution → complication → escape. Player-designed plan.
- **Mystery**: Hook → 3 cool locations → 3 clues per node (Three Clue Rule) → reveal → ending.
- **Conspyramid**: 6-layer conspiracy (neighborhood→city→province→national→supranational→core) + 6-layer response (reflex→contain→deflect→embrace→entrap→destroy).
- **Faction Turn**: each faction has independent goal timeline, advances even without player intervention. Passive/reactive/active relationships.
- **Race Against Time**: clock: X rounds to complete Y, or disaster. Ticking clock each round.
- **Survival**: resource management focus (food, water, light, ammo). Resource drain per area.

**Character-driven (people as structure):**
- **Plot Point Campaign**: main Plot Point Episodes + optional Savage Tales (character personal arcs).
- **Fish Tank Intrigue**: events + factions (passive/reactive/active). Players are the variable dropped into the tank.
- **Technoir Transmission**: 36-node master table. 2d6 pick 3 seed nodes as triangle, define relationships, add instigation event.
- **Decision-Based**: clear choices → modular world → adaptation to player decisions.
- **Blorb Principles**: prep entities (places, characters, items) not plots. Three tiers of truth: prep > rules > improv.

**Hybrid/Experimental:**
- **Iceberg Diagram**: surface hook → hidden depths. Backstory → clues → dynamic challenges.
- **Reverse Dungeon**: players defend a location, monsters attack in waves.

## Step 3: Collect Parameters

Ask the user, or randomize. Tell them what was picked.

| Parameter | Description | Default |
|-----------|-------------|---------|
| type | one-shot / short / medium / long / sandbox | short |
| paradigm | see table above | type default |
| theme | undead, dragon, fey, political, planar, cult... | random |
| setting | forest, desert, city, underdark, coastal, mountain, swamp... | random |
| villain_type | necromancer, dragon, demon, bandit lord, corrupt noble, lich, crime syndicate... | random |
| level_range | e.g. 1-3, 3-5, 5-7, 7-10, 10-15 | 1-3 |
| tone | dark, heroic, mystery, political, horror, whimsical | dark |
| twist_count | number of plot twists (short:1, medium:2-3, long:4-6) | type default |
| npc_depth | simple / moderate / complex | moderate |
| ending_branches | number of ending variants | 2 |
| seed | random seed for reproducibility | random |

## Step 4: Generate by Type

### One-shot Template

```markdown
# <模组名>

## 冒险概要
<2-3 sentences: hook, core conflict, possible outcomes>

## 冒险背景
<3-5 sentences: world context, current situation>

# <scene1>: <title>
<social/narrative: NPC intro, mission briefing, clue>

# <scene2>: <title>
<exploration/dungeon: 3-5 rooms with #### headings>

# <scene3>: <title>
<boss/climax: enemies, tactics, resolution>

# <scene4>: <title>
<optional epilogue/twist>

# 附录
## 主要 NPC
- **<name>** (<race> <class>): <2-3 sentences>

## 怪物
- **<name>**: see SRD. Custom: <1 sentence>

## 魔法物品
- **<name>** (<rarity>): <1-2 sentences>
```

### Short Template (3 chapters, Three-Act)

```markdown
# <模组名>

## 冒险概要
<who, what, why, stakes>
## 冒险背景
<world context, key factions>
## 运作本模组
<level range, pacing, key choices>

# 第一章：<title>
<!-- ch.1, current -->
## <scene1>
<establish world, introduce key NPC, first minor conflict>
## <scene2>
<first real challenge, clue points to Ch.2>
## <scene3>
<transition: journey or investigation leading to next chapter>

# 第二章：<title>
<!-- ch.2, locked -->
## <scene1>
<escalation: midpoint twist, stakes raised>
## <scene2>
<core dungeon/challenge, 4-8 rooms>
## <scene3>
<revelation: truth revealed, player choice point>

# 第三章：<title>
<!-- ch.3, locked -->
## <scene1>
<climax preparation or final approach>
## <scene2>
<boss fight: enemies, tactics, phases>
## <scene3>
<resolution: 2-3 ending branches based on player choices>

# 附录
## 主要 NPC
每人 2-4 sentences, include: want, fear, secret
## 伏笔-回收表
| 伏笔 (Ch) | 回收 (Ch) | 内容 |
## 怪物
## 魔法物品
```

### Medium Template (5 chapters, Hero's Journey)

```markdown
# <模组名>

## 冒险概要
## 冒险背景
## 运作本模组
## 势力关系网
| 势力 | 目标 | 盟友 | 敌对 |
|------|------|------|------|

# 第一章：平凡世界与召唤
<!-- ch.1, current -->
<3-5 scenes: normal life disrupted, call to adventure, 1-2 side quest hooks>

# 第二章：跨越门槛
<!-- ch.2, locked -->
<4-6 scenes: enter unfamiliar world, first major battle, 1-2 recruitable allies>

# 第三章：试炼与盟友
<!-- ch.3, locked -->
<6-10 scenes: longest chapter, main + 1-2 side quests, mid-campaign crisis>

# 第四章：深渊
<!-- ch.4, locked -->
<4-6 scenes: lowest point, sacrifice moment, inner demon confrontation>

# 第五章：归来与新生
<!-- ch.5, locked -->
<4-6 scenes: climax boss, 2 ending variants, world changes proof>

# 附录
## 主要 NPC（含 want/fear/secret）
## 盟友系统（招募条件、忠诚度、个人任务）
## 伏笔-回收表
## 支线事件线
| 支线 | 触发章节 | 关联主线 | 奖励 |
## 势力关系变化（章节推进对照表）
## 怪物
## 魔法物品
```

### Long Template (8 chapters, Double Triangle)

```markdown
# <模组名>

## 冒险概要
## 冒险背景
## 运作本模组
## 势力关系网
## 反派时间线（玩家不干预时的进展）

# 第一弧：崛起 (Ch.1-4)
# 第一章：<title>
# 第二章：<title>
# 第三章：<title>
# 第四章：虚假胜利
<!-- players think they won, actually helped the villain -->

# 第二弧：陨落与重生 (Ch.5-8)
# 第五章：陨落
<!-- consequences, losses, party may separate -->
# 第六章：挣扎与启蒙
<!-- revelation: discover villain's true weakness, personal quest -->
# 第七章：集结力量
<!-- gather allies, obtain ultimate weapon, final quiet moment -->
# 第八章：最终决战
<!-- multi-phase boss, each PC spotlight moment, multiple endings -->

# 附录
## 主要 NPC（含 arc）
## 角色个人线（每 PC 2-3 场景）
## 伏笔-回收表（跨 8 章完整线索链）
## 势力关系变化
## 反派时间线
## 怪物（含 Boss 多阶段数据）
## 魔法物品
## Epilogue（各 NPC/地点结局）
```

### Sandbox Template (same as before, unchanged)

## Scene Requirements (All Types)

- Every scene starts with `# ` (H1) or `## ` (H2, if inside a chapter)
- Room/location sub-headings use `#### ` (H4 → type: "room")
- DC values for skill checks (DC 10-15 for low level, 15-20 for mid, 20+ for high)
- XP/gold rewards per encounter
- NPC list format: `- **<name>** (<race> <class>, <alignment>): <personality>.<role>.<secret>.`

## Import

```
dnd_module action=import campaign_id=<id> module_name="<name>" content="<generated markdown>"
dnd_module action=index campaign_id=<id>
```

Report chapter/scene/chunk counts. If generating a large module (medium+), consider writing to file first.
