import random
import re

DICE_RE = re.compile(r"(?P<count>\d*)d(?P<sides>\d+)(?P<mod>[+-]\d+)?")


def roll_dice(formula: str) -> dict:
    match = DICE_RE.fullmatch(formula.replace(" ", "").lower())
    if not match:
        raise ValueError(f"Invalid dice formula: {formula}")
    count = int(match.group("count") or 1)
    sides = int(match.group("sides"))
    modifier = int(match.group("mod") or 0)
    if count < 1 or count > 100 or sides < 2 or sides > 1000:
        raise ValueError("Dice limits exceeded")
    rolls = [random.randint(1, sides) for _ in range(count)]
    return {"formula": formula, "rolls": rolls, "modifier": modifier, "total": sum(rolls) + modifier}


def roll_with_advantage(modifier: int = 0, disadvantage: bool = False) -> dict:
    rolls = [random.randint(1, 20), random.randint(1, 20)]
    chosen = min(rolls) if disadvantage else max(rolls)
    return {
        "formula": f"2d20k{'l' if disadvantage else 'h'}1{modifier:+d}",
        "rolls": rolls, "chosen": chosen, "modifier": modifier, "total": chosen + modifier,
    }

