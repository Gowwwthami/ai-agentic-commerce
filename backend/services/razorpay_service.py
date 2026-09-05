import logging

from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

logger = logging.getLogger(__name__)


class RazorpayUnavailable(Exception):
    """Raised when Razorpay Test Mode cannot complete a request."""


def _client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RazorpayUnavailable(
            "Razorpay Test Mode is not configured. "
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
        )
    try:
        import razorpay
    except ImportError as exc:
        raise RazorpayUnavailable("Razorpay SDK is not installed.") from exc
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def public_key_id() -> str | None:
    return RAZORPAY_KEY_ID


def amount_to_paise(amount_inr: float) -> int:
    return int(round(float(amount_inr) * 100))


def create_order(
    amount_inr: float,
    receipt: str,
    notes: dict | None = None,
) -> dict:
    paise = amount_to_paise(amount_inr)
    if paise < 100:
        raise ValueError("Amount must be at least ₹1.00 for Razorpay.")

    client = _client()
    payload = {
        "amount": paise,
        "currency": "INR",
        "receipt": receipt[:40],
        "payment_capture": 1,
        "notes": notes or {},
    }
    try:
        created = client.order.create(data=payload)
    except Exception as exc:
        logger.exception("Razorpay order create failed")
        raise RazorpayUnavailable(
            f"Razorpay could not create an order: {exc}"
        ) from exc

    return {
        "id": created.get("id"),
        "amount": created.get("amount", paise),
        "currency": created.get("currency", "INR"),
        "status": created.get("status"),
        "receipt": created.get("receipt", receipt),
    }


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    client = _client()
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
        return True
    except Exception:
        logger.exception("Razorpay signature verification failed")
        return False


def create_payment_link(
    amount_inr: float,
    description: str,
    reference: str,
) -> dict:
    paise = amount_to_paise(amount_inr)
    client = _client()
    payload = {
        "amount": paise,
        "currency": "INR",
        "accept_partial": False,
        "description": description[:200],
        "reference_id": reference[:40],
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "notes": {
            "demo": "true",
            "source": "glowcart-agent",
        },
    }
    try:
        created = client.payment_link.create(payload)
    except Exception as exc:
        logger.exception("Razorpay payment link create failed")
        raise RazorpayUnavailable(
            "Razorpay could not create a payment link. "
            "Test Mode may not support this request."
        ) from exc

    return {
        "id": created.get("id"),
        "short_url": created.get("short_url"),
        "status": created.get("status"),
        "amount": created.get("amount", paise),
    }
