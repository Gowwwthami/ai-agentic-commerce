import gzip
import json
from collections import defaultdict

REVIEWS_FILE = "data/raw/All_Beauty (1).json.gz"
METADATA_FILE = "data/raw/meta_All_Beauty (1).json.gz"


def read_json_lines(filename):
    with gzip.open(filename, "rt", encoding="utf-8") as file:
        for line in file:
            yield json.loads(line)


# --------------------------------------------------
# Step 1: Calculate rating statistics from reviews
# --------------------------------------------------

print("Reading reviews...")

ratings = defaultdict(list)

for review in read_json_lines(REVIEWS_FILE):
    asin = review.get("asin")
    rating = review.get("overall")

    if asin and rating is not None:
        ratings[asin].append(float(rating))


# --------------------------------------------------
# Step 2: Find usable lipstick products
# --------------------------------------------------

print("Reading product metadata...")

lipsticks = []

for product in read_json_lines(METADATA_FILE):

    title = product.get("title") or ""
    price = product.get("price")
    asin = product.get("asin")

    if "lipstick" not in title.lower():
        continue

    if not price:
        continue

    if asin not in ratings:
        continue

    product_ratings = ratings[asin]

    average_rating = sum(product_ratings) / len(product_ratings)

    lipsticks.append({
        "asin": asin,
        "title": title,
        "brand": product.get("brand"),
        "price": price,
        "rating": round(average_rating, 2),
        "review_count": len(product_ratings),
        "description": product.get("description"),
        "image": (
            product.get("imageURLHighRes", [None])[0]
            if product.get("imageURLHighRes")
            else None
        )
    })


# --------------------------------------------------
# Step 3: Sort by review count
# --------------------------------------------------

lipsticks.sort(
    key=lambda x: x["review_count"],
    reverse=True
)


# --------------------------------------------------
# Step 4: Display top 20
# --------------------------------------------------

print("\n========== TOP LIPSTICK PRODUCTS ==========\n")

for i, product in enumerate(lipsticks[:20], start=1):

    print(f"{i}. {product['title']}")
    print(f"   ASIN: {product['asin']}")
    print(f"   Brand: {product['brand']}")
    print(f"   Price: {product['price']}")
    print(f"   Rating: {product['rating']}/5")
    print(f"   Reviews: {product['review_count']}")
    print(f"   Image: {product['image']}")
    print()