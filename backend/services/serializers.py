from models import Product, Review


def product_to_dict(product: Product) -> dict:
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
        "pricing_note": "DEMO/SYNTHETIC merchant pricing in INR",
    }


def review_to_dict(review: Review) -> dict:
    return {
        "rating": float(review.rating),
        "text": review.review_text,
    }
