from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, func

from database import SessionLocal
from models import Product, Review


router = APIRouter(tags=["Commerce"])


@router.get("/products/search")
def search_products(
    query: str | None = Query(default=None),
    max_price: float | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    db = SessionLocal()

    try:
        statement = select(Product).where(
            Product.available.is_(True),
            Product.inventory > 0,
        )

        if query:
            search_term = f"%{query.lower()}%"

            statement = statement.where(
                Product.name.ilike(search_term)
                | Product.brand.ilike(search_term)
                | Product.description.ilike(search_term)
            )

        if max_price is not None:
            statement = statement.where(
                Product.price <= max_price
            )

        if min_rating is not None:
            statement = statement.where(
                Product.rating >= min_rating
            )

        statement = statement.order_by(
            Product.rating.desc(),
            Product.review_count.desc(),
        ).limit(limit)

        products = db.execute(statement).scalars().all()

        return {
            "count": len(products),
            "products": [
                product_to_dict(product)
                for product in products
            ],
        }

    finally:
        db.close()


@router.get("/products/{product_id}")
def get_product(product_id: int):
    db = SessionLocal()

    try:
        product = db.get(Product, product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        return product_to_dict(product)

    finally:
        db.close()


@router.get("/products/{product_id}/reviews")
def get_product_reviews(
    product_id: int,
    limit: int = Query(default=5, ge=1, le=20),
):
    db = SessionLocal()

    try:
        product = db.get(Product, product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        statement = (
            select(Review)
            .where(Review.asin == product.asin)
            .order_by(Review.id.desc())
            .limit(limit)
        )

        reviews = db.execute(statement).scalars().all()

        return {
            "product_id": product.id,
            "product_name": product.name,
            "reviews": [
                {
                    "rating": float(review.rating),
                    "text": review.review_text,
                }
                for review in reviews
            ],
        }

    finally:
        db.close()


def product_to_dict(product):
    return {
        "id": product.id,
        "asin": product.asin,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "description": product.description,
        "price": float(product.price),
        "currency": product.currency,
        "rating": (
            float(product.rating)
            if product.rating is not None
            else None
        ),
        "review_count": product.review_count,
        "image_url": product.image_url,
        "inventory": product.inventory,
        "available": product.available,
        "merchant": product.merchant,
    }