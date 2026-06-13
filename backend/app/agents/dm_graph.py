from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class DMState(TypedDict, total=False):
    user_message: str
    dm_context: str
    intent: dict[str, Any]
    ruling: dict[str, Any]
    proposed_actions: list[dict[str, Any]]
    memory_context: dict[str, Any]
    retrieved_memory: dict[str, Any]
    memory_write_plan: dict[str, Any]
    errors: list[str]


def retrieve_memory(state: DMState) -> DMState:
    package = state.get("memory_context") or {"memories": [], "entities": [], "threads": []}
    return {"retrieved_memory": package}


def parse_intent(state: DMState) -> DMState:
    text = state["user_message"].lower()
    if any(x in text for x in ["药水", "藥水", "potion"]):
        kind = "inventory_action"
    elif any(x in text for x in ["施放", "施法", "法术", "法術", "cast", "spell"]):
        kind = "spell_action"
    elif any(x in text for x in ["说服", "說服", "persuad"]):
        kind = "social_action"
    elif any(x in text for x in ["休", "rest"]):
        kind = "rest"
    elif any(x in text for x in ["攻击", "攻擊", "attack"]):
        kind = "combat_action"
    else:
        kind = "character_action"
    return {"intent": {"intent_type": kind, "confidence": 0.8, "entities": {}}}


def arbitrate_rules(state: DMState) -> DMState:
    kind = state["intent"]["intent_type"]
    rulings = {
        "social_action": {"requires_roll": True, "roll_type": "persuasion", "dc": 13},
        "inventory_action": {"requires_roll": False, "rule_refs": ["potion_healing"]},
        "rest": {"requires_roll": False, "rule_refs": ["rest"]},
    }
    return {"ruling": rulings.get(kind, {"requires_roll": False})}


def plan_actions(state: DMState) -> DMState:
    actions = []
    if state["ruling"].get("requires_roll"):
        actions.append({"tool": "roll_dice", "args": {"formula": "1d20"}})
    actions.append({"tool": "append_campaign_event", "args": {}})
    return {
        "proposed_actions": actions,
        "memory_write_plan": {
            "extract_after_event": True,
            "intent_type": state["intent"]["intent_type"],
            "skip": False,
        },
    }


builder = StateGraph(DMState)
builder.add_node("memory_retriever", retrieve_memory)
builder.add_node("intent_parser", parse_intent)
builder.add_node("rules_arbiter", arbitrate_rules)
builder.add_node("action_planner", plan_actions)
builder.add_edge(START, "memory_retriever")
builder.add_edge("memory_retriever", "intent_parser")
builder.add_edge("intent_parser", "rules_arbiter")
builder.add_edge("rules_arbiter", "action_planner")
builder.add_edge("action_planner", END)
dm_graph = builder.compile()
