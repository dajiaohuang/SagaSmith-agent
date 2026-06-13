from pathlib import Path
from collections import Counter

from app.config import settings
from app.tools.spell_catalog import level_number, save_spell_catalog


def main() -> None:
    target = settings.data_dir / "generated" / "spells" / "spell_catalog.json"
    spells = save_spell_catalog(settings.data_dir / "raw", target)
    source_counts = Counter(source for spell in spells for source in spell["sources"])
    level_counts = Counter(level_number(spell.get("level")) for spell in spells)
    class_counts = Counter(class_name for spell in spells for class_name in spell["classes"])
    report = [
        "# 合并法术目录报告",
        "",
        f"- 合并后去重条目：`{len(spells)}`",
        f"- 同时具有中英文名：`{sum(bool(spell['name'] and spell['english_name']) for spell in spells)}`",
        "",
        "## 来源覆盖",
        "",
        *[f"- `{source}`：{count}" for source, count in source_counts.most_common()],
        "",
        "## 环阶分布",
        "",
        *[f"- `{level}` 环：{count}" for level, count in sorted(level_counts.items())],
        "",
        "## 职业覆盖",
        "",
        *[f"- `{class_name}`：{count}" for class_name, count in class_counts.most_common()],
    ]
    (target.parent / "spell_catalog_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Built {len(spells)} merged spells at {target}")


if __name__ == "__main__":
    main()
