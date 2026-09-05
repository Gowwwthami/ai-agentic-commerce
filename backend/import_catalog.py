"""
Import the multi-category catalog into PostgreSQL.

This script:
  - Clears existing products (and their cart/order references are preserved
    because we do NOT touch orders, carts, or sessions).
  - Inserts all products from data/catalog.json using the category field
    from the catalog itself (NOT hardcoded to 'lipstick').
  - Is idempotent on ASIN: products already in the DB are updated, not duplicated.

Run from the backend/ directory:
  python import_catalog.py
"""

import json
import os
import sys

from database import SessionLocal
from models import Product
from sqlalchemy import select

CATALOG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "catalog.json"
)


def import_catalog(clear_existing: bool = True) -> None:
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    db = SessionLocal()

    try:
        if clear_existing:
            print("Clearing existing products …")
            from models import CartItem
            from sqlalchemy import delete as sa_delete

            # Find product IDs currently referenced by cart items
            in_cart_rows = db.execute(select(CartItem.product_id)).all()
            in_cart = {row[0] for row in in_cart_rows}

            if in_cart:
                to_delete = (
                    db.execute(select(Product).where(Product.id.not_in(in_cart)))
                    .scalars()
                    .all()
                )
            else:
                to_delete = db.execute(select(Product)).scalars().all()

            for p in to_delete:
                db.delete(p)
            db.commit()
            print(f"  Removed {len(to_delete)} old products (kept {len(in_cart)} in active carts).")

        # Build ASIN → existing product map for upsert
        existing: dict[str, Product] = {
            row.asin: row
            for row in db.execute(select(Product)).scalars().all()
        }

        inserted = 0
        updated = 0

        for item in products:
            asin = item["asin"]

            if asin in existing:
                # Update in place
                p = existing[asin]
                p.name         = item["name"]
                p.brand        = item["brand"]
                # Use the category from catalog.json — NOT hardcoded 'lipstick'
                p.category     = item["category"]
                p.description  = item.get("description") or ""
                p.price        = item["price_inr"]
                p.currency     = item.get("currency", "INR")
                p.rating       = item["rating"]
                p.review_count = item["review_count"]
                p.image_url    = item.get("image_url")
                p.inventory    = item.get("inventory", 10)
                p.merchant     = item.get("merchant", "GlowCart")
                p.available    = item.get("available", True)
                updated += 1
            else:
                p = Product(
                    asin       = asin,
                    name       = item["name"],
                    brand      = item["brand"],
                    # Use the category from catalog.json — NOT hardcoded 'lipstick'
                    category   = item["category"],
                    description= item.get("description") or "",
                    price      = item["price_inr"],
                    currency   = item.get("currency", "INR"),
                    rating     = item["rating"],
                    review_count = item["review_count"],
                    image_url  = item.get("image_url"),
                    inventory  = item.get("inventory", 10),
                    merchant   = item.get("merchant", "GlowCart"),
                    available  = item.get("available", True),
                )
                db.add(p)
                inserted += 1

        db.commit()

        print(f"\nInserted: {inserted}")
        print(f"Updated:  {updated}")
        print(f"Total in catalog: {len(products)}")

        # Summary by category
        from collections import Counter
        cat_counts = Counter(item["category"] for item in products)
        print("\nBy category:")
        for cat, n in sorted(cat_counts.items()):
            print(f"  {cat:<15} {n:>4}")

    except Exception as exc:
        db.rollback()
        print(f"Import failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_catalog()
