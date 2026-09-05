"""
Part 3 test suite — comparison + activity audit.
Run: venv/Scripts/python.exe test_part3.py
"""
import sys, uuid, json
sys.path.insert(0, '.')

from database import SessionLocal
from agent.orchestrator import handle_chat, _do_compare, _do_search
from agent.intent import parse_fast_intent, parse_search_intent, ParsedIntent
from services.session_service import (
    get_or_create_session, last_comparison, set_last_comparison,
    last_product_ids, set_last_products,
)
from services.recommend_service import compare_all_products, rank_products
from services.audit_service import list_audit_events
from services.catalog_service import search_catalog

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    icon = "✓" if condition else "✗"
    print(f"  [{status}] {icon} {label}" + (f"\n         → {detail}" if detail else ""))
    results.append((status, label))
    return condition

def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

db  = SessionLocal()
sid = str(uuid.uuid4())
session = get_or_create_session(db, sid)

# ──────────────────────────────────────────────
section("1. BASIC SEARCHES (preserved)")
# ──────────────────────────────────────────────

for query, expected_cat in [
    ("show me the best foundation", "foundation"),
    ("show me lipstick under 9000",  "lipstick"),
    ("show me mascara",              "mascara"),
]:
    intent = parse_fast_intent(query) or parse_search_intent(query)
    r = search_catalog(db, query=intent.query, max_price=intent.max_price, limit=6, ranked=True)
    ok = len(r["products"]) > 0 and all(p["category"] == expected_cat for p in r["products"])
    check(f"Search '{query}' returns {expected_cat}", ok,
          f"{len(r['products'])} products, cats: {set(p['category'] for p in r['products'])}")

# ──────────────────────────────────────────────
section("2. RECOMMENDATION GENERATION")
# ──────────────────────────────────────────────

search_result = handle_chat(db, sid, "show me the best foundation")
prods = search_result.get("products", [])
check("Chat returns 6 products", len(prods) == 6, f"got {len(prods)}")
check("All products are foundation", all(p.get("category") == "foundation" for p in prods),
      str(set(p.get("category") for p in prods)))
check("Message is not empty", bool(search_result.get("message", "").strip()))

ids_in_session = last_product_ids(session)
db.refresh(session)
ids_in_session = last_product_ids(session)
check("Session stores 6 product IDs after search", len(ids_in_session) == 6,
      f"got {len(ids_in_session)}")

# ──────────────────────────────────────────────
section("3. MULTI-PRODUCT COMPARISON (core change)")
# ──────────────────────────────────────────────

# First: do a fresh search so session has 6 products
search2 = handle_chat(db, sid, "show me lipstick under 9000")
prods2 = search2.get("products", [])
check("Search returned 6 lipstick products", len(prods2) == 6, f"got {len(prods2)}")

db.refresh(session)

# Trigger comparison of all 6
comp_result = handle_chat(db, sid, "compare all of them")
comparison = comp_result.get("comparison")
check("Comparison object returned", comparison is not None)

if comparison:
    comp_products = comparison.get("products", [])
    check(
        "Comparison contains all 6 products (not just 2)",
        len(comp_products) == 6,
        f"got {len(comp_products)} products in comparison"
    )
    check("recommended_id is set", comparison.get("recommended_id") is not None)
    check("summary is not empty", bool(comparison.get("summary", "").strip()))
    check("reasons list is present", isinstance(comparison.get("reasons"), list) and len(comparison["reasons"]) > 0)
    check("best_value_id is set", comparison.get("best_value_id") is not None)
    check("highest_rated_id is set", comparison.get("highest_rated_id") is not None)
    check("budget_id is set", comparison.get("budget_id") is not None)
    # left/right backward compat
    check("left field present (backward compat)", comparison.get("left") is not None)
    check("right field present (backward compat)", comparison.get("right") is not None)

# ──────────────────────────────────────────────
section("4. compare_all_products() function")
# ──────────────────────────────────────────────

from models import Product
from sqlalchemy import select
db_prods = db.execute(
    select(Product).where(Product.available.is_(True)).limit(6)
).scalars().all()
payloads = rank_products(db, db_prods, constraints={}, with_evidence=True, limit=6)
c = compare_all_products(payloads)

check("compare_all_products returns all 6", len(c.get("products", [])) == 6,
      f"got {len(c.get('products', []))}")
check("Winner is identified", c.get("recommended_id") is not None)
check("Best value is identified", c.get("best_value_id") is not None)
check("Highest rated is identified", c.get("highest_rated_id") is not None)
check("Budget pick is identified", c.get("budget_id") is not None)
check("Summary generated", bool(c.get("summary")))
check("Backward compat left/right present", c.get("left") is not None and c.get("right") is not None)

# ──────────────────────────────────────────────
section("5. INTENT: 'compare all of them'")
# ──────────────────────────────────────────────

for phrase, expected_name in [
    ("compare all of them",      "compare_all"),
    ("compare all",              "compare_all"),
    ("compare every product",    "compare_all"),
    ("compare the first two",    "compare"),
    ("compare the first one",    "compare"),
    ("compare",                  "compare_all"),   # bare compare → all
]:
    intent = parse_fast_intent(phrase)
    ok = intent is not None and intent.name == expected_name
    check(f"parse_fast_intent('{phrase}') → {expected_name}", ok,
          f"got {intent}")

# ──────────────────────────────────────────────
section("6. 'compare the first two' → uses full result set context")
# ──────────────────────────────────────────────

# Do a fresh search with 6 results, then compare first two
sid2 = str(uuid.uuid4())
handle_chat(db, sid2, "show me mascara")
session2 = get_or_create_session(db, sid2)
db.refresh(session2)
ids2 = last_product_ids(session2)
check("Mascara search stored product IDs", len(ids2) >= 2, f"got {len(ids2)}")

comp2 = handle_chat(db, sid2, "compare the first two")
comp2_data = comp2.get("comparison")
check("compare the first two returns comparison", comp2_data is not None)
if comp2_data:
    # Should compare ALL available products, not just 2
    n = len(comp2_data.get("products", []))
    check(
        f"'compare the first two' compares all {len(ids2)} available products",
        n == len(ids2),
        f"got {n} products in comparison, session had {len(ids2)}"
    )

# ──────────────────────────────────────────────
section("7. COMPARISON PERSISTENCE")
# ──────────────────────────────────────────────

sid3 = str(uuid.uuid4())
session3 = get_or_create_session(db, sid3)

# Initially none
check("Fresh session has no comparison", last_comparison(session3) is None)

# Store a comparison
fake = {
    "products": [{"id": 10, "name": "A"}, {"id": 11, "name": "B"}],
    "recommended_id": 10,
    "recommended_name": "A",
    "summary": "A wins",
    "reasons": ["A has higher score."],
    "best_value_id": 11,
    "highest_rated_id": 10,
    "budget_id": 11,
    "left": {"id": 10, "name": "A"},
    "right": {"id": 11, "name": "B"},
}
set_last_comparison(db, session3, fake)
retrieved = last_comparison(session3)
check("Comparison round-trips via session",
      retrieved is not None and retrieved.get("recommended_id") == 10,
      str(retrieved))

# GET /session returns comparison
from services.audit_service import list_audit_events as lae
from services.cart_service import get_cart
from services.order_service import get_active_order, order_to_dict
from agent.orchestrator import _payment_view
from services.session_service import last_product_ids as lpids, last_comparison as lc
order3 = get_active_order(db, session3.id)
resp = {
    "session_id": session3.id,
    "comparison": lc(session3),
    "cart": get_cart(db, session3.id),
    "order": order_to_dict(order3),
    "payment": _payment_view(order3),
    "audit": lae(db, session3.id, limit=5),
}
check("GET /session includes comparison", resp["comparison"] is not None)
check("comparison.products survives round-trip",
      len(resp["comparison"].get("products", [])) == 2)

# ──────────────────────────────────────────────
section("8. AUDIT EVENTS")
# ──────────────────────────────────────────────

audit_events = list_audit_events(db, sid, limit=50)
check("Audit events exist", len(audit_events) > 0, f"got {len(audit_events)}")

event_types = {e["event_type"] for e in audit_events}
check("user_shopping_request event logged", "user_shopping_request" in event_types,
      str(event_types))
check("product_search event logged",         "product_search" in event_types,
      str(event_types))
check("recommendation_generated event logged","recommendation_generated" in event_types,
      str(event_types))
check("product_compared event logged",        "product_compared" in event_types,
      str(event_types))

# Find the compare event and check metadata
compare_event = next((e for e in audit_events if e["event_type"] == "product_compared"), None)
if compare_event:
    meta = compare_event.get("metadata", {})
    check("compare audit has product_count >= 6",
          meta.get("product_count", 0) >= 6,
          f"product_count={meta.get('product_count')}, ids={len(meta.get('ids', []))}")

# Check that events have metadata field
check("All audit events have metadata dict",
      all(isinstance(e.get("metadata"), dict) for e in audit_events))
check("All audit events have created_at",
      all(e.get("created_at") for e in audit_events))

# ──────────────────────────────────────────────
section("9. PAYMENT FLOW UNCHANGED")
# ──────────────────────────────────────────────

# We just verify that checkout/payment functions still work structurally
# (we can't actually call Razorpay in tests, but we can verify event types)
# Start a checkout to generate audit events
sid4 = str(uuid.uuid4())
handle_chat(db, sid4, "show me lipstick")
handle_chat(db, sid4, "add the first one to my cart")
checkout_result = handle_chat(db, sid4, "proceed to checkout")
audit4 = list_audit_events(db, sid4, limit=20)
audit4_types = {e["event_type"] for e in audit4}

check("checkout_started event written", "checkout_started" in audit4_types,
      str(audit4_types))
check("Checkout result has order", checkout_result.get("order") is not None)
check("Order status is PENDING_CONFIRMATION",
      checkout_result.get("order", {}).get("status") == "PENDING_CONFIRMATION",
      checkout_result.get("order", {}).get("status"))

db.close()

# ──────────────────────────────────────────────
section("RESULTS")
# ──────────────────────────────────────────────
total  = len(results)
passed = sum(1 for s, _ in results if s == PASS)
failed = total - passed

print(f"\n{passed}/{total} passed")
if failed:
    print(f"\nFailed:")
    for s, label in results:
        if s == FAIL:
            print(f"  ✗ {label}")
else:
    print("  All tests passed!")

sys.exit(failed)
