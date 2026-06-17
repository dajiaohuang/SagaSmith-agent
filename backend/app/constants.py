"""Shared constants used across dice assistant and DM narrative paths."""

import re

# Detects "make a DC X strength save" / "roll 1d20+5" patterns in LLM output
ROLL_REQUEST_RE = re.compile(
    r"(?:投掷|投|掷|roll|make\s+a|进行|需要)(?:一个)?"
    r"(?:(?:DC\s*(\d+)\s*)?(力量|敏捷|体质|智力|感知|魅力|"
    r"strength|dexterity|constitution|intelligence|wisdom|charisma|"
    r"str|dex|con|int|wis|cha)"
    r"\s*(?:检定|豁免|check|save|saving throw))|"
    r"(?:请\s*(?:投掷|投|roll)\s*(?:\d*d\d+(?:[+-]\d+)?))|"
    r"(?:please\s*roll\s*(?:\d*d\d+(?:[+-]\d+)?))",
    re.IGNORECASE,
)

ROLL_FORMULA_RE = re.compile(r"\b(\d*d\d+(?:[+-]\d+)?)\b", re.IGNORECASE)
