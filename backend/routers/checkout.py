"""Checkout flow router — start and confirm checkout."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from deps import get_db
from schemas import CheckoutConfirmRequest, SessionRequest
from agent.orchestrator import _do_confirm_checkout, _do_start_checkout
from services.session_service import get_or_create_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checkout", tags=["Checkout"])


@router.post("/start")
def start_checkout(payload: SessionRequest, db: Session = Depends(get_db)):
    """Snapshot the cart into an order and wait for explicit confirmation."""
    session = get_or_create_session(db, payload.session_id)
    return _do_start_checkout(db, session)


@router.post("/confirm")
def confirm_checkout(
    payload: CheckoutConfirmRequest, db: Session = Depends(get_db)
):
    """Confirm checkout — creates a Razorpay Test Mode order."""
    session = get_or_create_session(db, payload.session_id)
    return _do_confirm_checkout(db, session)
