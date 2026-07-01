---
name: coc7-campaign-manager
description: Manage CoC campaigns stored in the shared database. Use for creating, listing, selecting, archiving, saving, verifying, loading, or undoing campaigns and complete database snapshots, including campaign-scoped player-role notes synchronized with USER.md. Supports investigator library, rule set selection, and ChromaDB vector storage.
---

# CoC Campaign Manager

Use the deterministic JSON CLI. Do not compose SQL.

## Resolve the campaign first

1. Reuse the campaign ID already established in the current conversation.
2. Otherwise list active campaigns:

   ```powershell
   python -m <domain-cli> campaign list --status active
   ```

3. If exactly one active campaign exists, select it. If multiple exist, ask the
   user which campaign to use.

## Manage campaigns

Create only after the user asks to start a new campaign.

### 开团流程

**Step 1 — 确定规则版本。** 检查当前可用的规则集：

```
coc7_rules action=status
```

首次使用时规则集自动入库（lazy ingest）。

**Step 2 — 确定模组来源。** 先检查数据库中已有哪些模组：

```
coc7_module action=status
```

然后问用户：使用已有模组，还是导入新模组？

**Step 3 — 一键开团：**

```
coc7_campaign action=start name="战役名称" module_name="模组名称" \
  rule_set_id="coc7-7e-srd" \
  [source_path="<path>"]
```

自动完成：创建战役 + 绑定规则与扩展 + 初始存档 (slot 1) + 可选导入模组。

### 导入新模组

调查员可以提供本地路径或上传 PDF/Markdown 文件。

```
coc7_module action=import campaign_id=<id> source_path="<path>" module_name="<name>"
coc7_module action=index campaign_id=<id>
coc7_module action=status campaign_id=<id>
```

导入后报告 chapter/scene/chunk/embedding 数量。

### 分步操作（维护后备）

```powershell
python -m <domain-cli> campaign create --name "战役名称" --module "模组名称"
```

**创建战役后必须立即创建初始 Snapshot**：

```powershell
python -m <domain-cli> save create --campaign <campaign-id> --label "初始状态" --workspace "<workspace>"
```

## Investigator library

调查员绑定战役，NPC 在全局库中。

```
# Campaign Investigators
coc7_character action=list campaign_id=<id>

# Global NPC library
coc7_character action=list type=npc

# Create Investigator (bound to campaign)
coc7_character action=create type=investigator campaign_id=<id> name="调查员名" \
  player="玩家名" occupation="教授"

# Create NPC (global library)
coc7_character action=create type=npc name="NPC名"

# Get details
coc7_character action=get character_id=<id>
```

CLI fallback:

```powershell
python -m <domain-cli> character create --type investigator --campaign <id> --name "..." --player "..."
python -m <domain-cli> character list --campaign <id>
python -m <domain-cli> character show --character <id>
```

## Import module content

Always check if the module already exists first:

```powershell
python -m <domain-cli> module list --campaign <campaign-id>
```

Only import when missing or the user explicitly requests re-import.

```powershell
python -m <domain-cli> module import --campaign <campaign-id> --name "模组名称" --path "<path>"
python -m <domain-cli> module index --campaign <campaign-id>
```

PDF imports use the dedicated structured converter. Reject import when bookmark
coverage is below 95% or no headings can be recovered.

## Run module progress

At start of campaign turn call `coc7_module action=current`. If no current scene,
use `action=index` to select the first unlocked scene, expand it, then persist
with `action=set_scene`.

## Save a complete snapshot (with auto recap)

Prefer the native `coc7_save` tool:

```
coc7_save action=create campaign_id=<id> label="探索阿卡姆前"
coc7_save action=list campaign_id=<id>
coc7_save action=lineage campaign_id=<id>
coc7_save action=verify campaign_id=<id> slot=1
coc7_save action=restore campaign_id=<id> slot=1 [auto_save=true]
coc7_save action=delete campaign_id=<id> slot=3
coc7_save action=export campaign_id=<id> slot=1 output="save.json"
```

Each create now automatically generates a recap, triggers long-term memory.

### Campaign memory

```
coc7_memory action=search campaign_id=<id> query="我们调查过哪些线索？"
coc7_memory action=scope campaign_id=<id>
coc7_memory action=get campaign_id=<id>
coc7_memory action=status
coc7_memory action=reindex campaign_id=<id>
```

### List and verify saves

```powershell
python -m <domain-cli> save list --campaign <campaign-id>
python -m <domain-cli> save verify --campaign <campaign-id> --slot <slot>
```

### Load a save

```powershell
python -m <domain-cli> save load --campaign <campaign-id> --slot <slot> --workspace "<workspace>"
```

### Undo

```powershell
python -m <domain-cli> undo --campaign <campaign-id> --count 1 --workspace "<workspace>"
```

## USER.md player roles

Maintain this campaign-scoped block:

```markdown
<!-- coc7-campaign:<campaign-id>:players:start -->
## 战役玩家调查员

- 玩家甲：调查员甲
- 玩家乙：调查员乙
<!-- coc7-campaign:<campaign-id>:players:end -->
```
