from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import LobbySessionState


MAX_LOBBY_MESSAGES = 16


def get_lobby_session(
    db: Session,
    session_id: str | None,
    *,
    create: bool = False,
    message_context: dict[str, Any] | None = None,
) -> LobbySessionState | None:
    if not session_id:
        return None
    row = db.get(LobbySessionState, session_id)
    if row or not create:
        return row
    context = message_context or {}
    row = LobbySessionState(
        id=session_id,
        platform=str(context.get("platform") or "web"),
        chat_id=str(context.get("group_id") or "") or None,
        user_id=str(context.get("sender_id") or "") or None,
        state={},
        messages=[],
    )
    db.add(row)
    db.commit()
    return row


def lobby_state(db: Session, session_id: str | None) -> dict:
    row = get_lobby_session(db, session_id)
    return copy.deepcopy(row.state or {}) if row else {}


def set_lobby_state(
    db: Session,
    session_id: str | None,
    state: dict,
    *,
    message_context: dict[str, Any] | None = None,
) -> None:
    row = get_lobby_session(db, session_id, create=True, message_context=message_context)
    if row is None:
        raise ValueError("lobby session_id is required when no campaign is active")
    row.state = copy.deepcopy(state)
    db.commit()


def append_lobby_exchange(
    db: Session,
    session_id: str | None,
    user_message: str,
    assistant_message: str,
    *,
    message_context: dict[str, Any] | None = None,
) -> None:
    row = get_lobby_session(db, session_id, create=True, message_context=message_context)
    if row is None:
        return
    messages = list(row.messages or [])
    messages.extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message},
    ])
    row.messages = messages[-MAX_LOBBY_MESSAGES:]
    db.commit()
