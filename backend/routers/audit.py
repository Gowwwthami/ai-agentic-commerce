"""Audit trail router."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from deps import get_db
from services.audit_service import list_audit_events

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/{session_id}")
def get_audit(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Return up to 50 audit events for a session, newest first."""
    return list_audit_events(db, session_id, limit=min(limit, 50))
