import gzip
import json


REVIEWS_FILE = "data/raw/All_Beauty (1).json.gz"
METADATA_FILE = "data/raw/meta_All_Beauty (1).json.gz"


def read_json_lines(filename):
    with gzip.open(filename, "rt", encoding="utf-8") as file:
        for line in file:
            yield json.loads(line)


# --------------------------------------------------
# STEP 1: Collect ALL review ASINs
# --------------------------------------------------

print("Reading full review dataset...")

review_count = 0
review_asins = set()

for review in read_json_lines(REVIEWS_FILE):
    review_count += 1
    review_asins.add(review["asin"])

print(f"Total reviews: {review_count}")
print(f"Unique reviewed products: {len(review_asins)}")


# --------------------------------------------------
# STEP 2: Analyze metadata
# --------------------------------------------------

print("\nReading metadata...")

metadata_count = 0

products_with_price = 0
products_with_reviews = 0
products_with_price_and_reviews = 0

lipstick_products = 0
lipstick_with_price = 0
lipstick_with_reviews = 0
lipstick_usable = 0


for product in read_json_lines(METADATA_FILE):

    metadata_count += 1

    asin = product.get("asin")
    title = (product.get("title") or "").lower()
    price = product.get("price")

    has_price = bool(price)
    has_reviews = asin in review_asins

    if has_price:
        products_with_price += 1

    if has_reviews:
        products_with_reviews += 1

    if has_price and has_reviews:
        products_with_price_and_reviews += 1

    # ----------------------------------------------
    # Lipstick
    # ----------------------------------------------

    if "lipstick" in title:

        lipstick_products += 1

        if has_price:
            lipstick_with_price += 1

        if has_reviews:
            lipstick_with_reviews += 1

        if has_price and has_reviews:
            lipstick_usable += 1


# --------------------------------------------------
# STEP 3: Print results
# --------------------------------------------------

print("\n========== FULL DATASET SUMMARY ==========")

print(f"Metadata products: {metadata_count}")
print(f"Products with price: {products_with_price}")
print(f"Products with reviews: {products_with_reviews}")
print(f"Products with price + reviews: {products_with_price_and_reviews}")

print("\n========== LIPSTICK ==========")

print(f"Lipstick products: {lipstick_products}")
print(f"Lipsticks with price: {lipstick_with_price}")
print(f"Lipsticks with reviews: {lipstick_with_reviews}")
print(f"Lipsticks with price + reviews: {lipstick_usable}")