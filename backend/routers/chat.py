from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from agent.orchestrator import handle_chat
from deps import get_db
from schemas import ChatRequest
from services.session_service import get_or_create_session

router = APIRouter(tags=["Agent"])


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        return handle_chat(db, payload.session_id, payload.message.strip())
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The shopping agent hit an unexpected error. No payment was taken.",
        )


@router.get("/session/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    from services.audit_service import list_audit_events
    from services.cart_service import get_cart
    from services.order_service import get_active_order, order_to_dict
    from agent.orchestrator import _payment_view
    from services.session_service import last_product_ids, last_comparison

    session = get_or_create_session(db, session_id)
    order = get_active_order(db, session.id)
    return {
        "session_id": session.id,
        "last_product_ids": last_product_ids(session),
        "recommended_product_id": session.recommended_product_id,
        "cart": get_cart(db, session.id),
        "order": order_to_dict(order),
        "payment": _payment_view(order),
        "audit": list_audit_events(db, session.id, limit=25),
        "comparison": last_comparison(session),
    }
