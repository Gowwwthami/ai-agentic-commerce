import json

from database import SessionLocal
from models import Product


CATALOG_FILE = "../data/catalog.json"


def import_catalog():

    with open(CATALOG_FILE, "r", encoding="utf-8") as file:
        products = json.load(file)

    db = SessionLocal()

    try:
        for item in products:

            product = Product(
                asin=item["asin"],
                name=item["name"],
                brand=item["brand"],
                category="lipstick",
                description=item["description"],
                price=item["price_inr"],
                currency=item["currency"],
                rating=item["rating"],
                review_count=item["review_count"],
                image_url=item["image_url"],
                inventory=item["inventory"],
                merchant=item["merchant"],
                available=item["available"],
            )

            db.add(product)

        db.commit()

        print(f"Successfully imported {len(products)} products!")

    except Exception as e:

        db.rollback()

        print("Import failed:")
        print(e)

    finally:
        db.close()


if __name__ == "__main__":
    import_catalog()