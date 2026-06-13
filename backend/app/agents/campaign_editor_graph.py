from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class EditorState(TypedDict, total=False):
    user_message: str
    setting_context: list[dict[str, Any]]
    intent: str
    related_settings: list[dict[str, Any]]
    proposal: dict[str, Any]
    validation: dict[str, Any]


def classify_intent(state: EditorState) -> EditorState:
    text = state["user_message"].strip()
    lowered = text.casefold()
    if any(word in lowered for word in ["删除", "归档", "archive", "delete"]):
        intent = "archive_setting"
    elif any(word in lowered for word in ["修改", "更新", "改成", "update", "change"]):
        intent = "update_setting"
    elif any(word in lowered for word in ["检查", "冲突", "validate", "check"]):
        intent = "validate_setting"
    elif any(word in lowered for word in ["查看", "查询", "inspect", "show"]):
        intent = "inspect_setting"
    elif any(word in lowered for word in ["创建", "新增", "设定", "create", "add"]):
        intent = "create_setting"
    else:
        intent = "brainstorm"
    return {"intent": intent}


def retrieve_related(state: EditorState) -> EditorState:
    text = state["user_message"].casefold()
    settings = state.get("setting_context", [])
    ranked = sorted(settings, key=lambda item: int(item.get("name", "").casefold() in text), reverse=True)
    return {"related_settings": ranked[:5]}


def build_proposal(state: EditorState) -> EditorState:
    message = state["user_message"].strip()
    related = state.get("related_settings") or []
    target = related[0] if related and related[0].get("name", "").casefold() in message.casefold() else None
    return {"proposal": {
        "operation": state["intent"].replace("_setting", ""),
        "target_setting_id": target.get("id") if target else None,
        "raw_request": message,
    }}


def validate_proposal(state: EditorState) -> EditorState:
    return {"validation": {"valid": True, "warnings": []}}


builder = StateGraph(EditorState)
builder.add_node("classify_editor_intent", classify_intent)
builder.add_node("retrieve_related_settings", retrieve_related)
builder.add_node("generate_proposal", build_proposal)
builder.add_node("validate_proposal", validate_proposal)
builder.add_edge(START, "classify_editor_intent")
builder.add_edge("classify_editor_intent", "retrieve_related_settings")
builder.add_edge("retrieve_related_settings", "generate_proposal")
builder.add_edge("generate_proposal", "validate_proposal")
builder.add_edge("validate_proposal", END)
campaign_editor_graph = builder.compile()
