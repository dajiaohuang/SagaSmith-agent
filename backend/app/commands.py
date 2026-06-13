from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str


EXPLICIT_COMMANDS = {
    "/帮助": "help",
    "/help": "help",
    "/状态": "status",
    "/status": "status",
    "/保存": "save",
    "/save": "save",
    "/暂停": "pause",
    "/pause": "pause",
    "/继续": "resume",
    "/resume": "resume",
}

NATURAL_COMMANDS = {
    "帮助": "help",
    "查看帮助": "help",
    "战役状态": "status",
    "查看战役状态": "status",
    "保存战役": "save",
    "保存当前进度": "save",
    "保存一下": "save",
    "暂停战役": "pause",
    "先暂停一下": "pause",
    "继续战役": "resume",
    "恢复战役": "resume",
}


def route_command(message: str) -> Command | None:
    text = " ".join(message.strip().split())
    lowered = text.lower()
    if lowered in EXPLICIT_COMMANDS:
        return Command(EXPLICIT_COMMANDS[lowered])
    if text in NATURAL_COMMANDS:
        return Command(NATURAL_COMMANDS[text])
    return None
