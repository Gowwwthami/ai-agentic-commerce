import json
import uuid
from datetime import datetime

from models import ShoppingSession


def get_or_create_session(db, session_id: str | None) -> ShoppingSession:
    sid = (session_id or "").strip() or str(uuid.uuid4())
    session = db.get(ShoppingSession, sid)
    if session:
        return session

    now = datetime.utcnow()
    session = ShoppingSession(
        id=sid,
        created_at=now,
        updated_at=now,
        conversation="[]",
        last_product_ids="[]",
        recommended_product_id=None,
        active_order_id=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def conversation(session: ShoppingSession) -> list[dict]:
    try:
        return json.loads(session.conversation or "[]")
    except json.JSONDecodeError:
        return []


def last_product_ids(session: ShoppingSession) -> list[int]:
    try:
        raw = json.loads(session.last_product_ids or "[]")
        return [int(item) for item in raw]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def append_message(db, session: ShoppingSession, role: str, content: str) -> None:
    history = conversation(session)
    history.append({"role": role, "content": content})
    session.conversation = json.dumps(history[-24:])
    session.updated_at = datetime.utcnow()
    db.commit()


def set_last_products(
    db,
    session: ShoppingSession,
    product_ids: list[int],
    recommended_id: int | None = None,
) -> None:
    session.last_product_ids = json.dumps(product_ids)
    if recommended_id is not None:
        session.recommended_product_id = recommended_id
    session.updated_at = datetime.utcnow()
    db.commit()


def set_last_comparison(
    db,
    session: ShoppingSession,
    comparison: dict | None,
) -> None:
    """Persist the last comparison so GET /session can return it."""
    session.last_comparison_json = json.dumps(comparison) if comparison else None
    session.updated_at = datetime.utcnow()
    db.commit()


def last_comparison(session: ShoppingSession) -> dict | None:
    """Return the last persisted comparison dict, or None."""
    try:
        raw = session.last_comparison_json
        if not raw:
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
