import gzip
import json

from database import SessionLocal
from models import Review


REVIEWS_FILE = "../data/raw/All_Beauty (1).json.gz"
CATALOG_FILE = "../data/catalog.json"


def import_reviews():

    # Get the 50 products in our merchant catalog
    with open(CATALOG_FILE, "r", encoding="utf-8") as file:
        catalog = json.load(file)

    catalog_asins = {
        product["asin"]
        for product in catalog
    }

    db = SessionLocal()

    imported = 0

    try:
        with gzip.open(
            REVIEWS_FILE,
            "rt",
            encoding="utf-8"
        ) as file:

            for line in file:

                review = json.loads(line)

                asin = review.get("asin")

                # Only keep reviews for our 50 products
                if asin not in catalog_asins:
                    continue

                review_text = review.get("reviewText")

                if not review_text:
                    continue

                db.add(
                    Review(
                        asin=asin,
                        rating=float(review["overall"]),
                        review_text=review_text,
                    )
                )

                imported += 1

                # Commit periodically
                if imported % 1000 == 0:
                    db.commit()
                    print(f"Imported {imported} reviews...")

        db.commit()

        print()
        print("========== REVIEW IMPORT COMPLETE ==========")
        print(f"Reviews imported: {imported}")

    except Exception as e:

        db.rollback()

        print("Import failed:")
        print(e)

    finally:
        db.close()


if __name__ == "__main__":
    import_reviews()