"""
Import reviews for all catalog products from the Amazon All Beauty corpus.

Clears existing reviews for catalog ASINs and re-imports, so running this
after a catalog rebuild gives correct review coverage.

Run from the backend/ directory:
  python import_reviews.py
"""

import gzip
import json
import os

from database import SessionLocal
from models import Review
from sqlalchemy import select, delete

REVIEWS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "raw", "All_Beauty (1).json.gz"
)
CATALOG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "catalog.json"
)


def import_reviews() -> None:
    # Load the catalog to get the set of ASINs we actually care about
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    catalog_asins: set[str] = {item["asin"] for item in catalog}
    print(f"Catalog ASINs to cover: {len(catalog_asins)}")

    db = SessionLocal()
    imported = 0

    try:
        # Remove existing reviews for these ASINs so we start clean
        print("Removing existing reviews for catalog ASINs …")
        deleted = db.execute(
            delete(Review).where(Review.asin.in_(catalog_asins))
        ).rowcount
        db.commit()
        print(f"  Removed {deleted} old review rows.")

        # Stream through the raw corpus
        print("Importing reviews from corpus …")
        batch: list[Review] = []

        with gzip.open(REVIEWS_FILE, "rt", encoding="utf-8") as f:
            for line in f:
                review = json.loads(line)

                asin = review.get("asin")
                if asin not in catalog_asins:
                    continue

                review_text = (review.get("reviewText") or "").strip()
                if not review_text:
                    continue

                rating = review.get("overall")
                if rating is None:
                    continue

                batch.append(
                    Review(
                        asin        = asin,
                        rating      = float(rating),
                        review_text = review_text,
                    )
                )
                imported += 1

                if len(batch) >= 2000:
                    db.add_all(batch)
                    db.commit()
                    batch.clear()
                    print(f"  … {imported} reviews imported")

        if batch:
            db.add_all(batch)
            db.commit()

        print(f"\n========== REVIEW IMPORT COMPLETE ==========")
        print(f"Reviews imported: {imported}")

        # Per-ASIN coverage check
        from sqlalchemy import func
        covered = db.execute(
            select(func.count(Review.asin.distinct()))
        ).scalar()
        print(f"ASINs with at least one review: {covered} / {len(catalog_asins)}")

    except Exception as exc:
        db.rollback()
        print(f"Import failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_reviews()
