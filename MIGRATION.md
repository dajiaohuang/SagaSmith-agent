# D&D DM Agent — 多平台 Plugin 打包计划

将 dnd-dm-agent 的所有自定义内容打包为 OpenClaw、NanoBot、Hermes 三平台的
原生 plugin，遵循各平台 plugin 范式。

---

## 一、平台 Plugin 范式对比

| | OpenClaw | NanoBot | Hermes |
|---|----------|---------|--------|
| **Plugin 格式** | Bundle 目录（`.claude-plugin/` + `.mcp.json` + `SKILL.md`） | `skills/<name>/SKILL.md` + tools 自动发现 | `~/.hermes/plugins/<name>/` + `plugin.yaml` + `__init__.py` |
| **Skill 定义** | `SKILL.md`（YAML frontmatter） | `SKILL.md`（YAML frontmatter + `always: true/false`） | `SKILL.md`（YAML frontmatter + `version` + `platforms`） |
| **工具注册** | MCP Server（stdio/HTTP）→ `serverName__toolName` | Python Tool 类，package scan 自动注册 | `ctx.register_tool()` in `__init__.py` |
| **安装方式** | `openclaw plugins install <path>` | 复制到 `skills/` 和 `agent/tools/` | `pip install` + entry point 或手动复制 |
| **命名空间** | MCP server name 前缀 | 无（全局 tool name） | `plugin:skill` 前缀 |
| **发布** | GitHub repo / tarball | 复制目录 | PyPI pip 包 |

---

## 二、公共资源层（三平台共享）

无论哪个平台，以下内容是相同的，放在共享资源目录：

```
dnd-dm-resources/
├── SKILL.md.dnd-dm              # DM 人格 Skill
├── SKILL.md.dnd-campaign        # 战役管理 Skill
├── SKILL.md.dnd-module-gen      # 模组生成 Skill
├── SKILL.md.napcat-qq           # QQ 频道 Skill
├── SKILL.md                     # 合并版（可选）
│
├── references/                  # Skill 引用文件
│   ├── DM_RULES.md
│   ├── DM_TEMPLATES.md
│   ├── CHAR_CREATION.md
│   ├── MODULE_INDEX.md
│   └── MODULE_ARC.md
│
├── templates/                   # SOUL 模板
│   ├── SOUL.md                  # 明萨拉·班瑞 DM 人格
│   ├── IDENTITY.md
│   ├── AGENTS.md
│   └── memory/MEMORY.md
│
├── data/                        # 规则数据
│   ├── srd/                     # SRD 5.2.1 英文 (20 文件)
│   └── srd-zh/                  # SRD 中文
│
├── db_schema/                   # SQLite schema + 迁移
│   └── migrations/              # 6 个 Alembic 脚本
│
├── MCP/                         # MCP Server 实现（Python）
│   ├── dnd_campaign.py          # 战役 CRUD MCP tool
│   ├── dnd_save.py              # 存档 MCP tool
│   ├── dnd_module.py            # 模组 MCP tool
│   ├── dnd_rules.py             # 规则 MCP tool
│   ├── dnd_dice.py              # 骰子计算 MCP tool
│   └── dnd_db.py                # 数据库管理
│
└── napcat/                      # QQ 频道参考
    └── napcat.py
```

---

## 三、OpenClaw Plugin

### 目录结构

```
dnd-dm-openclaw/
├── .claude-plugin/
│   └── plugin.json              # 声明为 OpenClaw bundle
├── .mcp.json                    # MCP Server 配置
├── SKILL.md                     # 合并的 skill 指令（给 agent 的提示词）
├── references/                  # → dnd-dm-resources/references/
├── templates/                   # → dnd-dm-resources/templates/
├── data/                        # → dnd-dm-resources/data/
├── MCP/                         # → dnd-dm-resources/MCP/
└── tools/                       # NapCat QQ channel
    └── napcat.py
```

### `.claude-plugin/plugin.json`

```json
{
  "name": "dnd-dm",
  "version": "1.0.0",
  "description": "D&D 5e Dungeon Master agent — campaign DB, module import, dice engine, rule retrieval"
}
```

### `.mcp.json`

```json
{
  "mcpServers": {
    "dnd-campaign": {
      "command": "python",
      "args": ["-m", "dnd_dm_mcp.campaign"],
      "env": { "DND_DATABASE_URL": "sqlite:///${WORKSPACE}/dnd_dm.db" }
    },
    "dnd-save": {
      "command": "python",
      "args": ["-m", "dnd_dm_mcp.save"],
      "env": { "DND_DATABASE_URL": "sqlite:///${WORKSPACE}/dnd_dm.db" }
    },
    "dnd-module": {
      "command": "python",
      "args": ["-m", "dnd_dm_mcp.module"],
      "env": { "DND_DATABASE_URL": "sqlite:///${WORKSPACE}/dnd_dm.db" }
    },
    "dnd-rules": {
      "command": "python",
      "args": ["-m", "dnd_dm_mcp.rules"],
      "env": { "DND_DATABASE_URL": "sqlite:///${WORKSPACE}/dnd_dm.db" }
    },
    "dnd-dice": {
      "command": "python",
      "args": ["-m", "dnd_dm_mcp.dice"]
    }
  }
}
```

### 安装

```bash
openclaw plugins install ./dnd-dm-openclaw
openclaw gateway restart
# 首次：导入 SRD 数据
dnd-rules__ingest_srd --path ./data/srd/
```

### 工具名映射

```
dnd-campaign__campaign_start → 一键开团
dnd-campaign__campaign_list   → 列出战役
dnd-save__save_create         → 创建存档
dnd-module__module_import     → 导入模组
dnd-module__module_search     → 搜索模组
dnd-rules__rules_search       → 搜索规则
dnd-dice__roll_d20            → d20 检定
...
```

---

## 四、NanoBot Plugin

### 目录结构

```
dnd-dm-nanobot/
├── skills/
│   ├── dnd-dm/
│   │   ├── SKILL.md            # always: true（核心 DM 人格）
│   │   └── references/         # DM_RULES.md 等
│   ├── dnd-campaign-manager/
│   │   └── SKILL.md            # always: false（按需加载）
│   ├── dnd-module-gen/
│   │   └── SKILL.md            # always: false
│   └── napcat-qq/
│       └── SKILL.md            # always: false
│
├── tools/
│   ├── dnd_campaign.py         # DndCampaignTool
│   ├── dnd_module.py           # DndModuleTool
│   ├── dnd_rules.py            # DndRulesTool
│   ├── dnd_save.py             # DndSaveTool
│   └── dnd_dice.py             # DndDiceTool（新增）
│
├── templates/
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── AGENTS.md
│   ├── agent/
│   │   └── identity.md
│   └── memory/
│       └── MEMORY.md
│
├── domain/                     # D&D 业务层
│   ├── db/                     # database + models + migrations + services
│   ├── modules/                # chunking + pdf_parser + scene_utils + search
│   ├── rules/                  # embedding + parser + ingest + search
│   └── engine/                 # dice + checks + resolve + xp + templates
│
├── channels/
│   └── napcat.py
│
├── data/
│   ├── srd/
│   └── srd-zh/
│
├── scripts/
│   ├── install.sh              # 复制所有文件到 ~/.nanobot/
│   └── ingest-srd.sh           # 导入 SRD
│
└── README.md
```

### `install.sh`

```bash
#!/bin/bash
NANOBOT="$HOME/.nanobot"
cp -r skills/*    "$NANOBOT/skills/"
cp -r tools/*.py  "$NANOBOT/agent/tools/"
cp -r templates/* "$NANOBOT/templates/"
cp -r domain/*    "$NANOBOT/dnd/"
cp -r channels/*  "$NANOBOT/channels/"
cp -r data/*      "$NANOBOT/dnd/data/"
echo "D&D DM Agent installed. Restart nanobot gateway."
```

### Skill frontmatter 设置

```yaml
# dnd-dm/SKILL.md
---
name: dnd-dm
description: D&D 5e Dungeon Master — core adjudication loop, dice engine, campaign/snapshot workflow, rule/module retrieval.
always: true
---

# dnd-campaign-manager/SKILL.md
---
name: dnd-campaign-manager
description: Manage D&D campaigns — create, import modules, save/load snapshots, undo.
always: false
---
```

---

## 五、Hermes Plugin

### 目录结构

```
dnd-dm-hermes/
├── __init__.py                  # register(ctx) 入口
├── plugin.yaml                 # 插件声明
├── skills/                     # 4 个 SKILL.md
│   ├── dnd-dm/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── dnd-campaign/
│   │   └── SKILL.md
│   ├── dnd-module-gen/
│   │   └── SKILL.md
│   └── napcat-qq/
│       └── SKILL.md
├── tools/                      # MCP server 实现
│   └── mcp_servers.py
├── templates/                  # SOUL
│   └── SOUL.md
├── data/
│   └── srd/
├── mcp_config.yaml             # Hermes MCP 配置
└── db_schema/
    └── migrations/
```

### `plugin.yaml`

```yaml
name: dnd-dm
version: 1.0.0
description: D&D 5e Dungeon Master agent system
author: dm-agent
homepage: https://github.com/dajiaohuang/dnd-dm-agent
license: MIT
capabilities:
  tools: true
  mcp: true
  skills: true
platforms: [macos, linux, windows]
```

### `__init__.py`

```python
from pathlib import Path

def register(ctx):
    # Register bundled skills
    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(f"dnd-{child.name}", skill_md)
    
    # Register MCP servers from mcp_config.yaml
    import yaml
    mcp_cfg = yaml.safe_load((Path(__file__).parent / "mcp_config.yaml").read_text())
    for name, cfg in mcp_cfg.get("mcpServers", {}).items():
        ctx.register_mcp_server(name, cfg)
    
    # Expose a dnd-dice tool directly (no MCP needed)
    from .tools.mcp_servers import roll_d20_schema, roll_d20_handler
    ctx.register_tool("dnd_dice__roll_d20", roll_d20_schema, roll_d20_handler)
```

### 安装

```bash
# pip install (entry point)
pip install dnd-dm-hermes

# 或手动复制
cp -r dnd-dm-hermes ~/.hermes/plugins/dnd-dm
hermes gateway restart
```

### Skill 加载方式

```
skill_view("dnd-dnd-dm")           # → 加载 DM 人格
skill_view("dnd-dnd-campaign")     # → 加载战役管理
```

Hermes 的 `plugin:skill` 命名空间确保不会与内置 skill 冲突。

---

## 六、各平台适配差异

| 能力 | OpenClaw | NanoBot | Hermes |
|------|----------|---------|--------|
| DM 人格注入 | SKILL.md 全文注入 prompt | `always: true` → 每次注入 | `skill_view()` → 按需注入 |
| 骰子计算 | dnd-dice MCP tool | DndDiceTool Python 类 | `ctx.register_tool()` |
| 数据库 | MCP stdio server | Python 直接调用 SQLAlchemy | MCP stdio server |
| 模组 PDF 解析 | MCP tool | Python 直接调用 | MCP tool |
| QQ 频道 | NapCat channel（单独文件） | napcat.py channel | 不适用（Hermes 无 QQ channel） |
| 规则数据 | 随 plugin 打包 | 随 plugin 打包 | 随 plugin 打包 |

---

## 七、分阶段实施

### Phase 1: 公共资源层
- 创建 `dnd-dm-resources/` 目录
- 提取 SKILL.md、references、templates、data、db_schema

### Phase 2: MCP Server 实现
- 将 4 个 NanoBot Tool 改写为 5 个 MCP Server（stdio 协议）
- 新增 `dnd-dice` MCP Server（纯计算，无数据库依赖）
- 测试 MCP Server 独立运行

### Phase 3: OpenClaw Plugin
- 创建 `.claude-plugin/` + `.mcp.json` + `SKILL.md`
- 测试 `openclaw plugins install`

### Phase 4: NanoBot Plugin
- 所有组件放入标准 NanoBot 路径
- `install.sh` 一键部署
- Skill frontmatter 设置 `always: true/false`

### Phase 5: Hermes Plugin
- 创建 `plugin.yaml` + `__init__.py`
- 注册 skills + MCP servers + 内联 tools
- 测试 pip install entry point

### Phase 6: 文档
- 各平台 README
- 首次安装脚本（SRD 导入、数据库初始化）
- Docker Compose 一键部署
