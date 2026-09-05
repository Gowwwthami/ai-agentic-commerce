import json
from datetime import datetime

from models import AuditEvent


def write_audit_event(
    db,
    event_type: str,
    description: str,
    session_id: str | None = None,
    order_id: int | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    safe_meta = dict(metadata or {})
    safe_meta.pop("key_secret", None)
    event = AuditEvent(
        session_id=session_id,
        order_id=order_id,
        event_type=event_type,
        description=description,
        metadata_json=json.dumps(safe_meta),
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_audit_events(db, session_id: str, limit: int = 50) -> list[dict]:
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.session_id == session_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": event.id,
            "session_id": event.session_id,
            "order_id": event.order_id,
            "event_type": event.event_type,
            "description": event.description,
            "metadata": json.loads(event.metadata_json or "{}"),
            "created_at": event.created_at.isoformat() + "Z",
        }
        for event in events
    ]
