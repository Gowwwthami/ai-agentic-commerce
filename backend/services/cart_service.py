from fastapi import HTTPException

from models import CartItem, Product
from services.serializers import product_to_dict


def _line_dict(item: CartItem, product: Product) -> dict:
    qty = int(item.quantity)
    unit = float(item.unit_price)
    return {
        "id": item.id,
        "product_id": item.product_id,
        "name": product.name,
        "brand": product.brand,
        "image_url": product.image_url,
        "quantity": qty,
        "unit_price": unit,
        "line_total": round(qty * unit, 2),
        "currency": product.currency,
        "inventory": product.inventory,
        "available": product.available,
        "merchant": product.merchant,
    }


def get_cart(db, session_id: str) -> dict:
    items = (
        db.query(CartItem)
        .filter(CartItem.session_id == session_id)
        .order_by(CartItem.id.asc())
        .all()
    )
    lines = []
    subtotal = 0.0
    merchant = "GlowCart"
    for item in items:
        product = db.get(Product, item.product_id)
        if not product:
            continue
        line = _line_dict(item, product)
        lines.append(line)
        subtotal += line["line_total"]
        merchant = product.merchant or merchant

    return {
        "session_id": session_id,
        "items": lines,
        "item_count": sum(line["quantity"] for line in lines),
        "subtotal": round(subtotal, 2),
        "total": round(subtotal, 2),
        "currency": "INR",
        "merchant": merchant,
        "pricing_note": "Totals use DEMO/SYNTHETIC merchant INR prices. No tax added.",
    }


def add_to_cart(db, session_id: str, product_id: int, quantity: int = 1) -> dict:
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1.")

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if not product.available:
        raise HTTPException(
            status_code=409,
            detail="This product is currently unavailable.",
        )

    existing = (
        db.query(CartItem)
        .filter(
            CartItem.session_id == session_id,
            CartItem.product_id == product_id,
        )
        .first()
    )
    new_qty = quantity + (existing.quantity if existing else 0)
    if new_qty > product.inventory:
        raise HTTPException(
            status_code=409,
            detail=f"Only {product.inventory} units are in stock.",
        )

    if existing:
        existing.quantity = new_qty
        existing.unit_price = product.price
    else:
        db.add(
            CartItem(
                session_id=session_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=product.price,
            )
        )

    db.commit()
    cart = get_cart(db, session_id)
    cart["added_product"] = product_to_dict(product)
    return cart


def update_cart_item(db, session_id: str, item_id: int, quantity: int) -> dict:
    item = db.get(CartItem, item_id)
    if not item or item.session_id != session_id:
        raise HTTPException(status_code=404, detail="Cart item not found.")

    if quantity <= 0:
        db.delete(item)
        db.commit()
        return get_cart(db, session_id)

    product = db.get(Product, item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if quantity > product.inventory:
        raise HTTPException(
            status_code=409,
            detail=f"Only {product.inventory} units are in stock.",
        )

    item.quantity = quantity
    item.unit_price = product.price
    db.commit()
    return get_cart(db, session_id)


def remove_from_cart(db, session_id: str, item_id: int) -> dict:
    return update_cart_item(db, session_id, item_id, 0)
