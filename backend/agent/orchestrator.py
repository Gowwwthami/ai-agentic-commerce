import json
import logging

from fastapi import HTTPException

from agent.gemini_client import generate_json, generate_text, gemini_available
from agent.intent import (
    ParsedIntent,
    parse_fast_intent,
    parse_search_intent,
    to_dict,
)
from models import Product
from services.audit_service import list_audit_events, write_audit_event
from services.cart_service import add_to_cart, get_cart, remove_from_cart
from services.catalog_service import search_catalog
from services.order_service import (
    can_retry,
    get_active_order,
    mark_failed,
    order_to_dict,
    snapshot_cart_into_order,
    transition,
)
from services.recommend_service import compare_all_products, compare_payloads, rank_products
from services.razorpay_service import (
    RazorpayUnavailable,
    create_order,
    create_payment_link,
    public_key_id,
)
from services.session_service import (
    append_message,
    get_or_create_session,
    last_product_ids,
    set_last_comparison,
    set_last_products,
)

logger = logging.getLogger(__name__)


def handle_chat(db, session_id: str, message: str) -> dict:
    session = get_or_create_session(db, session_id)
    append_message(db, session, "user", message)
    write_audit_event(
        db,
        "user_shopping_request",
        f"User said: {message}",
        session_id=session.id,
    )

    try:
        intent = parse_fast_intent(message)
        if intent is None:
            intent = _gemini_intent(message) or parse_search_intent(message)
            if intent.source != "gemini":
                intent.source = intent.source or "rules"
        result = _dispatch(db, session, intent, message)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        result = _error_payload(db, session.id, detail or "That action could not be completed.")
    except Exception:
        logger.exception("Chat dispatch failed")
        result = _error_payload(
            db,
            session.id,
            "Something went wrong while handling that request. No payment was taken.",
        )

    assistant_text = result.get("message") or ""
    append_message(db, session, "assistant", assistant_text)
    result["session_id"] = session.id
    result.setdefault("actions", [])
    return result


def _error_payload(db, session_id: str, message: str) -> dict:
    order = get_active_order(db, session_id)
    return {
        "message": message,
        "products": [],
        "cart": get_cart(db, session_id),
        "order": order_to_dict(order),
        "payment": _payment_view(order),
        "comparison": None,
        "audit": list_audit_events(db, session_id, limit=25),
        "needs_confirmation": False,
        "actions": [],
    }


def _dispatch(db, session, intent: ParsedIntent, raw_message: str) -> dict:
    name = intent.name
    if name == "search":
        return _do_search(db, session, intent)
    if name == "compare":
        indexes = [0, 1]
        if intent.product_index is not None:
            indexes = [intent.product_index, intent.product_index + 1]
        return _do_compare(db, session, indexes, all_products=False)
    if name == "compare_all":
        return _do_compare(db, session, indexes=None, all_products=True)
    if name == "compare_best":
        return _do_compare_best(db, session, raw_message)
    if name == "add_to_cart":
        return _do_add(db, session, intent)
    if name == "buy_it":
        added = _do_add(
            db,
            session,
            ParsedIntent(
                name="add_to_cart",
                use_recommended=True,
                product_index=intent.product_index,
            ),
        )
        if "Tell me what" in (added.get("message") or ""):
            return added
        checkout = _do_start_checkout(db, session)
        checkout["message"] = (
            (added.get("message") or "") + " " + (checkout.get("message") or "")
        ).strip()
        checkout["actions"] = ["add_to_cart", "start_checkout"]
        return checkout
    if name == "get_cart":
        return _do_cart(
            db,
            session,
            "Here is your cart. Totals are calculated by the application, not the model.",
        )
    if name == "remove_from_cart":
        return _do_remove(db, session, intent)
    if name == "start_checkout":
        return _do_start_checkout(db, session)
    if name == "confirm_checkout":
        return _do_confirm_checkout(db, session)
    if name == "payment_failed":
        return _do_payment_failed(db, session)
    if name == "retry_payment":
        return _do_retry(db, session)
    if name == "payment_link":
        return _do_payment_link(db, session)
    if name == "show_audit":
        return _do_audit(db, session)
    return _do_search(db, session, parse_search_intent(raw_message))


def _gemini_intent(message: str) -> ParsedIntent | None:
    if not gemini_available():
        return None
    prompt = (
        "\nExtract shopping intent as JSON for a beauty/cosmetics shopping assistant.\n"
        "The catalog contains beauty products. Extract the user's actual search terms.\n"
        "Allowed intent names: search, compare, compare_all, compare_best, add_to_cart, get_cart,\n"
        "remove_from_cart, start_checkout, confirm_checkout, payment_failed,\n"
        "retry_payment, payment_link, show_audit.\n\n"
        "Schema:\n"
        "{\n"
        '  "name": "search",\n'
        '  "query": "the user\'s actual search terms (e.g. foundation, mascara, lipstick)",\n'
        '  "max_price": null,\n'
        '  "min_rating": null,\n'
        '  "brand": null,\n'
        '  "product_index": null,\n'
        '  "use_recommended": false\n'
        "}\n\n"
        "Rules:\n"
        "- query must reflect what the user actually asked for. Never replace with 'lipstick'.\n"
        "- max_price is a number or null.\n"
        "- product_index is 0 for first, 1 for second, 2 for third, else null.\n"
        "- Do not invent products.\n\n"
        f"User message: {message}\n"
    )
    data = generate_json(prompt)
    if not data:
        return None
    return ParsedIntent(
        name=str(data.get("name") or "search"),
        query=data.get("query"),
        max_price=(
            float(data["max_price"])
            if data.get("max_price") is not None
            else None
        ),
        min_rating=(
            float(data["min_rating"])
            if data.get("min_rating") is not None
            else None
        ),
        brand=data.get("brand"),
        product_index=(
            int(data["product_index"])
            if data.get("product_index") is not None
            else None
        ),
        use_recommended=bool(data.get("use_recommended")),
        source="gemini",
    )


def _products_from_ids(db, ids: list[int], constraints: dict | None = None) -> list[dict]:
    products = []
    for pid in ids:
        product = db.get(Product, pid)
        if product:
            products.append(product)
    if not products:
        return []
    return rank_products(
        db,
        products,
        constraints=constraints or {},
        with_evidence=True,
        limit=len(products),
    )


def _do_search(db, session, intent: ParsedIntent) -> dict:
    # Use the query from intent. Do NOT fall back to "lipstick" — if the
    # intent has no specific query, search across the full available catalog
    # so the ranking + constraints filter it.
    query = intent.query
    result = search_catalog(
        db,
        query=query,
        max_price=intent.max_price,
        min_rating=intent.min_rating,
        brand=intent.brand,
        limit=6,
        ranked=True,
    )
    products = result["products"]
    write_audit_event(
        db,
        "product_search",
        (
            f"Searched catalog for '{query}' with max_price="
            f"{intent.max_price}, min_rating={intent.min_rating}."
        ),
        session_id=session.id,
        metadata=to_dict(intent),
    )
    if not products:
        # If the query returned nothing because the catalog only contains
        # beauty products, do a fallback search across all available items.
        fallback = search_catalog(
            db,
            query=None,
            max_price=intent.max_price,
            min_rating=intent.min_rating,
            brand=intent.brand,
            limit=6,
            ranked=True,
        )
        if fallback["products"]:
            products = fallback["products"]
            result = fallback
        else:
            return _wrap(
                db,
                session,
                "I searched the GlowCart catalog and did not find a match "
                "for those constraints. Try a different search or adjust the budget.",
                actions=["search"],
            )

    set_last_products(
        db,
        session,
        [item["id"] for item in products],
        recommended_id=products[0]["id"],
    )
    write_audit_event(
        db,
        "recommendation_generated",
        f"Ranked {len(products)} products. Top pick: {products[0]['name']}",
        session_id=session.id,
        metadata={
            "product_ids": [item["id"] for item in products],
            "constraints": result.get("constraints"),
        },
    )
    message = _explain_recommendations(
        products,
        result.get("constraints") or {},
    )
    return _wrap(
        db,
        session,
        message,
        products=products,
        actions=["recommend", "search"],
    )


def _explain_recommendations(products: list[dict], constraints: dict) -> str:
    fallback_lines = [
        f"I searched the live catalog (not the model) and ranked {len(products)} option(s) "
        "using rating, review volume, price fit, stock, and sampled stored reviews.",
        "Prices are DEMO/SYNTHETIC merchant INR amounts. Review quotes come from "
        "the stored Amazon All Beauty review set, not live web reviews.",
    ]
    for index, product in enumerate(products, start=1):
        line = (
            f"{index}. {product['name']} — ₹{product['price']:.0f}, "
            f"rating {product.get('rating')}, "
            f"{product.get('review_count')} reviews. {product.get('why')}"
        )
        if product.get("pros"):
            line += "   Pros from stored reviews: " + ", ".join(product["pros"])
        if product.get("cons"):
            line += "   Cons from stored reviews: " + ", ".join(product["cons"])
        fallback_lines.append(line)
    fallback = "\n".join(fallback_lines)

    if not gemini_available():
        return fallback

    compact = []
    for product in products:
        evidence = product.get("review_evidence") or {}
        compact.append(
            {
                "name": product["name"],
                "brand": product.get("brand"),
                "price": product["price"],
                "rating": product.get("rating"),
                "review_count": product.get("review_count"),
                "why": product.get("why"),
                "pros": product.get("pros"),
                "cons": product.get("cons"),
                "excerpts": [
                    sample.get("text")
                    for sample in (evidence.get("samples") or [])[:2]
                ],
            }
        )
    prompt = (
        "\nYou are GlowCart, a careful shopping agent. Write a concise recommendation "
        "for the user.\nUse ONLY the JSON evidence. Do not invent products, prices, "
        "ratings, or review claims.\nMention that prices are synthetic demo INR pricing "
        "and reviews are stored dataset evidence.\nRecommend only from the products listed. "
        "150-250 words. No markdown headings.\n\n"
        f"Constraints: {json.dumps(constraints)}\n"
        f"Products: {json.dumps(compact)}\n"
    )
    text = generate_text(prompt)
    return text or fallback


def _do_compare(db, session, indexes: list[int] | None, all_products: bool = False) -> dict:
    """
    Compare products from the session's last result set.

    If all_products=True or indexes is None: compare the entire result set.
    If a specific index is given: compare that product against the full result set
    (not just pairwise) — the selected product becomes the focus product but all
    others are included for context.
    """
    ids = last_product_ids(session)
    if len(ids) < 2:
        return _wrap(
            db,
            session,
            "I need at least two products to compare. Search for products first.",
            actions=["compare_blocked"],
        )

    # Always load the full result set for comparison context
    all_payloads = _products_from_ids(db, ids)
    if len(all_payloads) < 2:
        return _wrap(
            db,
            session,
            "I could not load enough products for comparison.",
            actions=["compare_blocked"],
        )

    # Determine which product is the focus (for "compare the first one")
    focus_id: int | None = None
    if not all_products and indexes and len(indexes) > 0:
        focus_idx = indexes[0]
        if 0 <= focus_idx < len(ids):
            focus_id = ids[focus_idx]

    comparison = compare_all_products(all_payloads)

    # If a focus product was specified, make it the recommended_id tie-breaker
    # only if the intent specifically called it out — keep the score-based winner
    # as the actual recommendation.

    set_last_products(
        db,
        session,
        [p["id"] for p in all_payloads],
        recommended_id=comparison["recommended_id"],
    )
    set_last_comparison(db, session, comparison)

    product_names = ", ".join(p["name"].split(",")[0] for p in all_payloads[:3])
    if len(all_payloads) > 3:
        product_names += f" and {len(all_payloads) - 3} more"

    write_audit_event(
        db,
        "product_compared",
        (
            f"Compared {len(all_payloads)} products: {product_names}. "
            f"Recommended: {comparison['recommended_name']}."
        ),
        session_id=session.id,
        metadata={
            "ids": [p["id"] for p in all_payloads],
            "recommended_id": comparison["recommended_id"],
            "product_count": len(all_payloads),
            "focus_id": focus_id,
        },
    )
    message = _explain_comparison(comparison)
    return _wrap(
        db,
        session,
        message,
        products=all_payloads,
        comparison=comparison,
        actions=["compare"],
    )


def _explain_comparison(comparison: dict) -> str:
    products = comparison.get("products") or [
        comparison.get("left"), comparison.get("right")
    ]
    products = [p for p in products if p]
    winner_id = comparison.get("recommended_id")
    winner = next((p for p in products if p.get("id") == winner_id), products[0] if products else None)
    winner_name = comparison.get("recommended_name") or (winner["name"] if winner else "")

    # Deterministic fallback that never uses the LLM
    fallback_parts = [
        f"After comparing {len(products)} option(s), I recommend {winner_name}.",
    ]
    for r in (comparison.get("reasons") or [])[:3]:
        fallback_parts.append(r)
    bv_id = comparison.get("best_value_id")
    hr_id = comparison.get("highest_rated_id")
    bv = next((p for p in products if p.get("id") == bv_id), None)
    hr = next((p for p in products if p.get("id") == hr_id), None)
    if bv and bv["id"] != winner_id:
        fallback_parts.append(
            f"Best value: {bv['name'].split(',')[0]} at ₹{bv['price']:.0f}."
        )
    if hr and hr["id"] != winner_id and hr["id"] != (bv["id"] if bv else None):
        fallback_parts.append(
            f"Highest rated: {hr['name'].split(',')[0]} ({hr.get('rating')}★)."
        )
    fallback_parts.append(
        "Prices are DEMO/SYNTHETIC INR. Scores use rating, review volume, "
        "price fit, and stored review evidence."
    )
    fallback = " ".join(fallback_parts)

    if not gemini_available():
        return fallback

    compact = []
    for p in products:
        compact.append({
            "name": p["name"],
            "price": p.get("price"),
            "rating": p.get("rating"),
            "review_count": p.get("review_count"),
            "score": p.get("score"),
            "pros": (p.get("pros") or [])[:3],
            "cons": (p.get("cons") or [])[:2],
            "available": p.get("available"),
        })

    prompt = (
        f"\nYou are GlowCart. Compare these {len(products)} products using ONLY the JSON below.\n"
        "Do not invent any scores, ratings, reviews, or claims not in the data.\n"
        "Identify: (1) overall best pick, (2) best value, (3) highest rated, "
        "if different.\nMention synthetic INR pricing. 150-220 words. No markdown headings.\n\n"
        f"Products: {json.dumps(compact)}\n"
        f"Recommended ID: {winner_id}\n"
        f"Reasons: {json.dumps(comparison.get('reasons', []))}\n"
    )
    return generate_text(prompt) or fallback


def _do_compare_best(db, session, raw_message: str) -> dict:
    ids = last_product_ids(session)
    if len(ids) < 2:
        return _do_search(db, session, parse_search_intent(raw_message))

    payloads = _products_from_ids(db, ids)
    if not payloads:
        return _do_search(db, session, parse_search_intent(raw_message))

    lowered = raw_message.lower()
    if "long" in lowered:
        def lasting_key(item):
            pros = item.get("pros") or []
            return (
                1 if "long-lasting" in pros else 0,
                item.get("score") or 0,
            )
        payloads_sorted = sorted(payloads, key=lasting_key, reverse=True)
        winner = payloads_sorted[0]
        note = (
            f"Among the current picks, {winner['name']} has the strongest "
            "long-wear evidence in the sampled stored reviews."
            if "long-lasting" in (winner.get("pros") or [])
            else
            f"None of the current picks had strong long-wear keywords. "
            f"By overall score I would still pick {winner['name']}."
        )
        comparison = compare_all_products(payloads)
        set_last_products(db, session, [p["id"] for p in payloads], winner["id"])
        set_last_comparison(db, session, comparison)
        return _wrap(db, session, note, products=payloads, comparison=comparison, actions=["compare_best"])

    # Default: full multi-product comparison
    return _do_compare(db, session, indexes=None, all_products=True)


def _resolve_product_id(session, intent: ParsedIntent) -> int | None:
    ids = last_product_ids(session)
    if intent.use_recommended and session.recommended_product_id:
        return session.recommended_product_id
    if intent.product_index is not None and 0 <= intent.product_index < len(ids):
        return ids[intent.product_index]
    if intent.use_recommended and ids:
        return ids[0]
    if intent.product_index is None and len(ids) == 1:
        return ids[0]
    if intent.product_index is None and session.recommended_product_id:
        return session.recommended_product_id
    return None


def _do_add(db, session, intent: ParsedIntent) -> dict:
    product_id = _resolve_product_id(session, intent)
    if not product_id:
        return _wrap(
            db,
            session,
            "Tell me what you want first, then I can add a specific pick to your cart.",
            actions=["add_to_cart"],
        )
    cart = add_to_cart(db, session.id, product_id, intent.quantity or 1)
    added = cart.get("added_product") or {}
    write_audit_event(
        db,
        "cart_changed",
        f"Added {added.get('name', 'product')} to cart.",
        session_id=session.id,
        metadata={"product_id": product_id, "quantity": intent.quantity or 1},
    )
    write_audit_event(
        db,
        "product_selected",
        f"Selected product {added.get('name', product_id)}.",
        session_id=session.id,
        metadata={"product_id": product_id},
    )
    message = (
        f"Added {added.get('name', 'the product')} to your cart. "
        f"Subtotal is ₹{cart['total']:.2f} "
        "(application-calculated, synthetic INR pricing)."
    )
    return _wrap(db, session, message, cart=cart, actions=["add_to_cart"])


def _do_remove(db, session, intent: ParsedIntent) -> dict:
    cart = get_cart(db, session.id)
    if not cart["items"]:
        return _wrap(
            db,
            session,
            "Your cart is already empty.",
            cart=cart,
            actions=["remove_from_cart"],
        )
    index = intent.product_index if intent.product_index is not None else 0
    if index < 0 or index >= len(cart["items"]):
        index = 0
    item = cart["items"][index]
    cart = remove_from_cart(db, session.id, item["id"])
    write_audit_event(
        db,
        "cart_changed",
        f"Removed {item['name']} from cart.",
        session_id=session.id,
        metadata={"cart_item_id": item["id"]},
    )
    return _wrap(
        db,
        session,
        f"Removed {item['name']} from your cart.",
        cart=cart,
        actions=["remove_from_cart"],
    )


def _do_cart(db, session, message: str) -> dict:
    return _wrap(db, session, message, actions=["get_cart"])


def _do_start_checkout(db, session) -> dict:
    cart = get_cart(db, session.id)
    if not cart["items"]:
        return _wrap(
            db,
            session,
            "Your cart is empty, so I cannot start checkout.",
            cart=cart,
            actions=["start_checkout"],
        )
    order = snapshot_cart_into_order(db, session.id)
    session.active_order_id = order.id
    db.commit()
    write_audit_event(
        db,
        "checkout_started",
        f"Checkout started for ₹{float(order.total_amount):.2f}. "
        "Waiting for explicit confirmation.",
        session_id=session.id,
        order_id=order.id,
    )
    names = ", ".join(
        f"{item['name']} x{item['quantity']}" for item in cart["items"]
    )
    message = (
        f"You're about to place an order for {names} totaling "
        f"₹{float(order.total_amount):.2f} with {order.merchant}. "
        "This is DEMO/SYNTHETIC pricing. I will not charge anything until you "
        "explicitly confirm. Reply yes / confirm to proceed."
    )
    return _wrap(
        db,
        session,
        message,
        cart=cart,
        order=order_to_dict(order),
        needs_confirmation=True,
        actions=["start_checkout"],
    )


def _do_confirm_checkout(db, session) -> dict:
    order = get_active_order(db, session.id)
    if not order or order.status != "PENDING_CONFIRMATION":
        cart = get_cart(db, session.id)
        if cart["items"] and (not order or order.status == "CART"):
            return _do_start_checkout(db, session)
        return _wrap(
            db,
            session,
            "There is nothing waiting for confirmation. "
            "Add a product and say proceed to checkout first.",
            actions=["confirm_checkout"],
        )
    write_audit_event(
        db,
        "confirmation_received",
        "User explicitly confirmed checkout.",
        session_id=session.id,
        order_id=order.id,
    )
    return _create_razorpay_order(db, session, order)


def _create_razorpay_order(db, session, order) -> dict:
    if not can_retry(order):
        return _wrap(
            db,
            session,
            (
                f"Payment attempts are exhausted ({order.payment_attempts}/"
                f"{order.max_attempts}). No further charges will be attempted."
            ),
            order=order_to_dict(order),
            actions=["retry_blocked"],
        )
    try:
        created = create_order(
            float(order.total_amount),
            receipt=f"gc-{session.id[:8]}-{order.id}",
            notes={"session_id": session.id, "order_id": str(order.id)},
        )
    except (RazorpayUnavailable, ValueError) as exc:
        write_audit_event(
            db,
            "razorpay_error",
            f"I could not create a Razorpay Test Mode order, so nothing was charged. {exc}",
            session_id=session.id,
            order_id=order.id,
        )
        return _wrap(
            db,
            session,
            (
                "I could not create a Razorpay Test Mode order, so nothing was charged. "
                f"{exc} You can retry or ask for a payment link if Test Mode supports it."
            ),
            order=order_to_dict(order),
            actions=["razorpay_unavailable"],
            recovery_options=["retry_payment", "payment_link"],
        )

    order.razorpay_order_id = created.get("id")
    order.payment_attempts = (order.payment_attempts or 0) + 1
    transition(order, "PAYMENT_PENDING")
    db.commit()
    db.refresh(order)

    write_audit_event(
        db,
        "razorpay_order_created",
        (
            f"Created Razorpay order {order.razorpay_order_id} for "
            f"₹{float(order.total_amount):.2f}. Attempt {order.payment_attempts}."
        ),
        session_id=session.id,
        order_id=order.id,
        metadata={
            "razorpay_order_id": order.razorpay_order_id,
            "amount_paise": int(round(float(order.total_amount) * 100)),
            "amount": float(order.total_amount),
        },
    )
    write_audit_event(
        db,
        "payment_attempt",
        (
            f"Payment attempt {order.payment_attempts} started. "
            "Success is not claimed until Razorpay verification."
        ),
        session_id=session.id,
        order_id=order.id,
    )
    message = (
        f"Razorpay Test Mode order {order.razorpay_order_id} is ready for "
        f"₹{float(order.total_amount):.2f}. Open the checkout widget to pay. "
        "I will not mark this paid until verification succeeds. If payment fails, "
        "I can retry (bounded) or create a payment link."
    )
    return _wrap(
        db,
        session,
        message,
        order=order_to_dict(order),
        payment=_payment_view(order),
        open_checkout=True,
        actions=["create_payment"],
    )


def _do_payment_failed(db, session) -> dict:
    order = get_active_order(db, session.id)
    if not order:
        return _wrap(
            db,
            session,
            "There is no open payment to fail.",
            actions=["payment_failed"],
        )
    mark_failed(db, order)
    write_audit_event(
        db,
        "payment_failure",
        "Payment reported as failed. No successful charge is being claimed.",
        session_id=session.id,
        order_id=order.id,
    )
    remaining = max(0, order.max_attempts - order.payment_attempts)
    if remaining > 0:
        try:
            transition(order, "PAYMENT_RECOVERY")
            db.commit()
        except HTTPException:
            pass
        db.refresh(order)
        write_audit_event(
            db,
            "recovery_attempt",
            "Offered bounded recovery options after payment failure.",
            session_id=session.id,
            order_id=order.id,
        )
        message = (
            "Your payment didn't go through. Your order has not been charged "
            f"successfully. You have {remaining} recovery attempt(s) left: "
            "retry checkout, or generate a Razorpay payment link."
        )
        return _wrap(
            db,
            session,
            message,
            order=order_to_dict(order),
            payment=_payment_view(order),
            recovery_options=["retry_payment", "payment_link"],
            actions=["payment_failed"],
        )

    message = (
        "Your payment didn't go through, and recovery attempts are exhausted. "
        "Nothing extra will be charged. You can start a new cart if you want to try later."
    )
    return _wrap(
        db,
        session,
        message,
        order=order_to_dict(order),
        payment=_payment_view(order),
        actions=["payment_failed"],
    )


def _do_retry(db, session) -> dict:
    order = get_active_order(db, session.id)
    if not order:
        return _wrap(
            db,
            session,
            "There is no failed payment to retry.",
            actions=["retry_payment"],
        )
    if not can_retry(order):
        return _wrap(
            db,
            session,
            (
                f"Retry limit reached ({order.max_attempts}). "
                "I will not create another charge attempt."
            ),
            order=order_to_dict(order),
            actions=["retry_blocked"],
        )
    write_audit_event(
        db,
        "recovery_attempt",
        "User chose to retry payment.",
        session_id=session.id,
        order_id=order.id,
    )
    if order.status == "PAYMENT_FAILED":
        try:
            transition(order, "PAYMENT_RECOVERY")
            db.commit()
        except HTTPException:
            pass
    return _create_razorpay_order(db, session, order)


def _do_payment_link(db, session) -> dict:
    order = get_active_order(db, session.id)
    if not order:
        return _wrap(
            db,
            session,
            "There is no order to attach a payment link to.",
            actions=["payment_link"],
        )
    if not can_retry(order):
        return _wrap(
            db,
            session,
            "Retry limit reached, so I will not create another payment link.",
            order=order_to_dict(order),
            actions=["retry_blocked"],
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
            f"I could not create a Razorpay payment link. {exc} Nothing was charged.",
            session_id=session.id,
            order_id=order.id,
        )
        return _wrap(
            db,
            session,
            f"I could not create a Razorpay payment link. {exc} Nothing was charged.",
            order=order_to_dict(order),
            actions=["payment_link_failed"],
        )

    url = link.get("short_url")
    order.payment_link_url = url
    order.payment_attempts = (order.payment_attempts or 0) + 1
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
        "Created Razorpay Test Mode payment link as a recovery option.",
        session_id=session.id,
        order_id=order.id,
        metadata={"payment_link_id": link.get("id"), "url": url},
    )
    message = (
        "Here is a Razorpay Test Mode payment link. It is a payment link, "
        f"not a completed charge. Open it only if you want to continue: {url}"
    )
    return _wrap(
        db,
        session,
        message,
        order=order_to_dict(order),
        payment=_payment_view(order),
        actions=["payment_link"],
    )


def _do_audit(db, session) -> dict:
    events = list_audit_events(db, session.id, limit=25)
    message = (
        f"I logged {len(events)} audit events for this session. "
        "Open the Audit panel for the trail."
    )
    return _wrap(db, session, message, actions=["show_audit"])


def _payment_view(order) -> dict | None:
    if not order:
        return None
    return {
        "status": order.status,
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_key_id": public_key_id(),
        "amount": float(order.total_amount),
        "amount_paise": int(round(float(order.total_amount) * 100)),
        "currency": order.currency,
        "payment_link_url": order.payment_link_url,
        "attempts": order.payment_attempts,
        "max_attempts": order.max_attempts,
        "paid": order.status == "PAID",
    }


def _wrap(
    db,
    session,
    message: str,
    products=None,
    cart=None,
    order=None,
    payment=None,
    comparison=None,
    actions=None,
    needs_confirmation: bool = False,
    open_checkout: bool = False,
    recovery_options=None,
) -> dict:
    live_order = get_active_order(db, session.id)
    return {
        "message": message,
        "products": products or [],
        "cart": cart if cart is not None else get_cart(db, session.id),
        "order": order if order is not None else order_to_dict(live_order),
        "payment": payment if payment is not None else _payment_view(live_order),
        "comparison": comparison,
        "audit": list_audit_events(db, session.id, limit=25),
        "needs_confirmation": needs_confirmation,
        "open_checkout": open_checkout,
        "recovery_options": recovery_options or [],
        "actions": actions or [],
        "recommended_product_id": session.recommended_product_id,
    }
