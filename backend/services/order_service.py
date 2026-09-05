import json
from datetime import datetime

from fastapi import HTTPException

from config import MAX_PAYMENT_ATTEMPTS
from models import Order
from services.cart_service import get_cart

ALLOWED_TRANSITIONS = {
    "CART": {"PENDING_CONFIRMATION", "CANCELLED"},
    "PENDING_CONFIRMATION": {
        "CART",
        "PAYMENT_PENDING",
        "CANCELLED",
        "PAYMENT_FAILED",
    },
    "PAYMENT_PENDING": {"PAID", "CANCELLED", "PAYMENT_FAILED"},
    "PAYMENT_FAILED": {
        "PAYMENT_RECOVERY",
        "CANCELLED",
        "PAYMENT_PENDING",
    },
    "PAYMENT_RECOVERY": {
        "PAYMENT_PENDING",
        "PAID",
        "CANCELLED",
        "PAYMENT_FAILED",
    },
    "PAID": set(),
    "CANCELLED": set(),
}


def order_to_dict(order: Order | None) -> dict | None:
    if not order:
        return None
    return {
        "id": order.id,
        "session_id": order.session_id,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "amount_paise": int(round(float(order.total_amount) * 100)),
        "currency": order.currency,
        "merchant": order.merchant,
        "items": json.loads(order.items_snapshot or "[]"),
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_id": order.razorpay_payment_id,
        "payment_link_url": order.payment_link_url,
        "payment_attempts": order.payment_attempts,
        "max_attempts": order.max_attempts,
        "attempts_remaining": max(
            0,
            order.max_attempts - order.payment_attempts,
        ),
        "created_at": order.created_at.isoformat() + "Z",
    }


def get_active_order(db, session_id: str) -> Order | None:
    return (
        db.query(Order)
        .filter(
            Order.session_id == session_id,
            Order.status.notin_(["PAID", "CANCELLED"]),
        )
        .order_by(Order.id.desc())
        .first()
    )


def transition(order: Order, new_status: str) -> Order:
    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed and new_status != order.status:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move order from {order.status} to {new_status}.",
        )
    order.status = new_status
    order.updated_at = datetime.utcnow()
    return order


def snapshot_cart_into_order(db, session_id: str) -> Order:
    cart = get_cart(db, session_id)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Your cart is empty.")

    order = get_active_order(db, session_id)
    if order and order.status in {"PAID"}:
        order = None

    payload = json.dumps(cart["items"])
    total = cart["total"]
    merchant = cart["merchant"]
    now = datetime.utcnow()

    if order and order.status in {
        "CART",
        "PAYMENT_RECOVERY",
        "PENDING_CONFIRMATION",
        "PAYMENT_FAILED",
    }:
        order.items_snapshot = payload
        order.total_amount = total
        order.merchant = merchant
        if order.status != "PENDING_CONFIRMATION":
            if order.status == "CART":
                transition(order, "PENDING_CONFIRMATION")
            elif order.status in {"PAYMENT_FAILED", "PAYMENT_RECOVERY"}:
                transition(order, "PENDING_CONFIRMATION")
            else:
                order.status = "PENDING_CONFIRMATION"
                order.updated_at = now
        else:
            order.updated_at = now
        db.commit()
        db.refresh(order)
        return order

    order = Order(
        session_id=session_id,
        status="PENDING_CONFIRMATION",
        total_amount=total,
        currency="INR",
        merchant=merchant,
        items_snapshot=payload,
        payment_attempts=0,
        max_attempts=MAX_PAYMENT_ATTEMPTS,
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def mark_paid(db, order: Order, payment_id: str) -> Order:
    if order.status != "PAID":
        transition(order, "PAID")
    order.razorpay_payment_id = payment_id
    db.commit()
    db.refresh(order)
    return order


def mark_failed(db, order: Order) -> Order:
    if order.status == "PAID":
        raise HTTPException(
            status_code=409,
            detail="This order is already paid.",
        )
    if order.status != "PAYMENT_FAILED":
        if "PAYMENT_FAILED" in ALLOWED_TRANSITIONS.get(order.status, set()):
            transition(order, "PAYMENT_FAILED")
        else:
            order.status = "PAYMENT_FAILED"
            order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


def can_retry(order: Order) -> bool:
    if order.status == "PAID":
        return False
    return order.payment_attempts < order.max_attempts
