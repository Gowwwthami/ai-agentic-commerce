from sqlalchemy import select, or_

from models import Product
from services.recommend_service import rank_products
from services.review_service import retrieve_review_evidence
from services.serializers import product_to_dict, review_to_dict


def search_catalog(
    db,
    query: str | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    brand: str | None = None,
    limit: int = 10,
    ranked: bool = True,
) -> dict:
    statement = select(Product).where(
        Product.available.is_(True),
        Product.inventory > 0,
    )

    if query:
        # Split multi-word query into individual tokens.
        # Strategy:
        # - Identify "anchor" tokens — words that map directly to product categories
        #   (foundation, mascara, lipstick, blush, etc.)
        # - Anchor tokens MUST match (AND logic)
        # - Modifier tokens (dark, skin, long-lasting, etc.) are optional (OR logic)
        # This prevents "foundation for dark skin" from matching blush products
        # just because their description mentions "skin".
        CATEGORY_ANCHORS = {
            "lipstick", "foundation", "mascara", "eyeliner", "blush",
            "eyeshadow", "concealer", "skincare", "primer", "bronzer",
            "highlighter", "lip", "gloss", "serum", "moisturizer",
            "moisturiser", "toner", "cleanser", "sunscreen",
        }

        tokens = [t.strip() for t in query.lower().split() if len(t.strip()) > 1]
        if tokens:
            anchor_tokens   = [t for t in tokens if t in CATEGORY_ANCHORS]
            modifier_tokens = [t for t in tokens if t not in CATEGORY_ANCHORS]

            def token_filter(tok: str):
                term = f"%{tok}%"
                return (
                    Product.name.ilike(term)
                    | Product.brand.ilike(term)
                    | Product.description.ilike(term)
                    | Product.category.ilike(term)
                )

            if anchor_tokens:
                # All anchor tokens must match (AND)
                for tok in anchor_tokens:
                    statement = statement.where(token_filter(tok))
                # Modifier tokens are optional (skip them — ranker handles relevance)
            else:
                # No category anchor — OR across all tokens
                token_clauses = [token_filter(t) for t in tokens]
                statement = statement.where(or_(*token_clauses))

    if max_price is not None:
        statement = statement.where(Product.price <= max_price)

    if min_rating is not None:
        statement = statement.where(Product.rating >= min_rating)

    if brand:
        statement = statement.where(Product.brand.ilike(f"%{brand}%"))

    products = list(
        db.execute(statement.limit(50)).scalars().all()
    )
    constraints = {
        "query": query,
        "max_price": max_price,
        "min_rating": min_rating,
        "brand": brand,
    }

    if ranked and products:
        ranked_products = rank_products(
            db,
            products,
            constraints=constraints,
            with_evidence=True,
            limit=limit,
        )
        return {
            "count": len(ranked_products),
            "products": ranked_products,
            "constraints": constraints,
        }

    return {
        "count": len(products[:limit]),
        "products": [product_to_dict(product) for product in products[:limit]],
        "constraints": constraints,
    }


def get_product_or_none(db, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_product_with_evidence(db, product_id: int) -> dict | None:
    product = get_product_or_none(db, product_id)
    if not product:
        return None
    payload = product_to_dict(product)
    evidence = retrieve_review_evidence(db, product)
    payload["review_evidence"] = evidence
    payload["pros"] = [item["label"] for item in evidence.get("pros", [])]
    payload["cons"] = [item["label"] for item in evidence.get("cons", [])]
    return payload


def list_reviews(db, product_id: int, limit: int = 5) -> dict | None:
    import models

    product = get_product_or_none(db, product_id)
    if not product:
        return None

    statement = (
        select(models.Review)
        .where(models.Review.asin == product.asin)
        .order_by(models.Review.id.desc())
        .limit(limit)
    )
    reviews = db.execute(statement).scalars().all()
    return {
        "product_id": product.id,
        "product_name": product.name,
        "reviews": [review_to_dict(review) for review in reviews],
    }
