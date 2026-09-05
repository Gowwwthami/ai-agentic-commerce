"""Payment router — verify, link, failed, and public key."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent.orchestrator import _payment_view
from config import RAZORPAY_KEY_ID
from deps import get_db
from schemas import PaymentActionRequest, PaymentVerifyRequest
from services.audit_service import write_audit_event
from services.order_service import (
    can_retry,
    get_active_order,
    mark_failed,
    mark_paid,
    order_to_dict,
    transition,
)
from services.razorpay_service import (
    RazorpayUnavailable,
    create_payment_link,
    verify_signature,
)
from services.session_service import get_or_create_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["Payment"])


@router.get("/key")
def get_payment_key():
    """Return only the Razorpay publishable key."""
    if not RAZORPAY_KEY_ID:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured on this server.",
        )

    return {"key_id": RAZORPAY_KEY_ID}


@router.post("/verify")
def verify_payment(
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Verify a Razorpay payment and mark the matching order PAID.

    The order ID supplied by the browser must match the Razorpay order
    stored against the current GlowCart order before signature verification
    can result in a PAID state.
    """

    session = get_or_create_session(db, payload.session_id)
    order = get_active_order(db, session.id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="No active order found.",
        )

    if not order.razorpay_order_id:
        raise HTTPException(
            status_code=409,
            detail="This order does not have a Razorpay order yet.",
        )

    if payload.razorpay_order_id != order.razorpay_order_id:
        write_audit_event(
            db,
            "payment_verification_failed",
            (
                "Razorpay order ID did not match the active GlowCart "
                "order. Order NOT marked paid."
            ),
            session_id=session.id,
            order_id=order.id,
            metadata={
                "expected_razorpay_order_id": order.razorpay_order_id,
                "received_razorpay_order_id": payload.razorpay_order_id,
            },
        )

        raise HTTPException(
            status_code=400,
            detail="Payment verification failed: order mismatch.",
        )

    if order.status != "PAYMENT_PENDING":
        if order.status == "PAID":
            return {
                "status": "PAID",
                "order": order_to_dict(order),
            }

        raise HTTPException(
            status_code=409,
            detail=(
                f"Payment cannot be verified while the order is "
                f"in {order.status} state."
            ),
        )

    ok = verify_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )

    if not ok:
        write_audit_event(
            db,
            "payment_verification_failed",
            (
                "Razorpay signature verification failed. "
                "Order NOT marked paid."
            ),
            session_id=session.id,
            order_id=order.id,
            metadata={
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
            },
        )

        raise HTTPException(
            status_code=400,
            detail="Payment verification failed.",
        )

    order = mark_paid(
        db,
        order,
        payload.razorpay_payment_id,
    )

    write_audit_event(
        db,
        "payment_verified",
        (
            f"Payment verified. Order {order.id} marked PAID. "
            f"payment_id={payload.razorpay_payment_id}"
        ),
        session_id=session.id,
        order_id=order.id,
        metadata={
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
        },
    )

    return {
        "status": "PAID",
        "order": order_to_dict(order),
    }


@router.post("/link")
def create_link(
    payload: PaymentActionRequest,
    db: Session = Depends(get_db),
):
    """Create a Razorpay Test Mode payment link as recovery."""

    session = get_or_create_session(db, payload.session_id)
    order = get_active_order(db, session.id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="No active order found.",
        )

    if not can_retry(order):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Retry limit reached ({order.max_attempts}). "
                "No further payment attempts will be made."
            ),
        )

    try:
        link = create_payment_link(
            float(order.total_amount),
            description=f"GlowCart demo order {order.id}",
            reference=f"gc{order.id}a{order.payment_attempts}",
        )
    except RazorpayUnavailable as exc:
        write_audit_event(
            db,
            "payment_link_failed",
            f"Could not create payment link: {exc}",
            session_id=session.id,
            order_id=order.id,
        )

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    url = link.get("short_url")

    if not url:
        write_audit_event(
            db,
            "payment_link_failed",
            "Razorpay returned no payment-link URL.",
            session_id=session.id,
            order_id=order.id,
        )

        raise HTTPException(
            status_code=502,
            detail="Razorpay did not return a payment-link URL.",
        )

    order.payment_link_url = url
    order.payment_attempts = (
        order.payment_attempts or 0
    ) + 1

    if order.status != "PAYMENT_PENDING":
        try:
            transition(order, "PAYMENT_PENDING")
        except HTTPException:
            order.status = "PAYMENT_PENDING"

    db.commit()
    db.refresh(order)

    write_audit_event(
        db,
        "payment_link_created",
        (
            "Created Razorpay Test Mode payment link "
            "as a recovery option."
        ),
        session_id=session.id,
        order_id=order.id,
        metadata={
            "payment_link_id": link.get("id"),
            "url": url,
        },
    )

    return {
        "order": order_to_dict(order),
        "payment_link_url": url,
        "payment": _payment_view(order),
    }


@router.post("/failed")
def payment_failed(
    payload: PaymentActionRequest,
    db: Session = Depends(get_db),
):
    """Mark a payment as failed and return bounded recovery options."""

    session = get_or_create_session(db, payload.session_id)
    order = get_active_order(db, session.id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="No active order found.",
        )

    if order.status == "PAID":
        raise HTTPException(
            status_code=409,
            detail="This order is already paid.",
        )

    if order.status not in {
        "PAYMENT_FAILED",
        "PAYMENT_RECOVERY",
    }:
        order = mark_failed(db, order)

    write_audit_event(
        db,
        "payment_failure",
        (
            "Payment reported failed from the frontend callback. "
            "No successful charge is being claimed."
        ),
        session_id=session.id,
        order_id=order.id,
    )

    remaining = max(
        0,
        order.max_attempts - order.payment_attempts,
    )

    if remaining > 0:
        try:
            transition(order, "PAYMENT_RECOVERY")
            db.commit()
        except HTTPException:
            db.rollback()

        db.refresh(order)

        write_audit_event(
            db,
            "recovery_attempt",
            "Recovery options offered after payment failure.",
            session_id=session.id,
            order_id=order.id,
        )

        return {
            "order": order_to_dict(order),
            "payment": _payment_view(order),
            "recovery_options": [
                "retry_payment",
                "payment_link",
            ],
        }

    return {
        "order": order_to_dict(order),
        "payment": _payment_view(order),
        "recovery_options": [],
    }