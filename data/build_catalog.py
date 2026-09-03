import gzip
import json
import re
from collections import defaultdict

REVIEWS_FILE = "data/raw/All_Beauty (1).json.gz"
METADATA_FILE = "data/raw/meta_All_Beauty (1).json.gz"

OUTPUT_FILE = "data/catalog.json"


def read_json_lines(filename):
    with gzip.open(filename, "rt", encoding="utf-8") as file:
        for line in file:
            yield json.loads(line)


def parse_price(price):
    if not price:
        return None

    price = str(price).strip()

    match = re.fullmatch(
        r"\$?\s*(\d+(?:\.\d{1,2})?)",
        price
    )

    if not match:
        return None

    try:
        value = float(match.group(1))

        if value <= 0 or value > 1000:
            return None

        return value

    except ValueError:
        return None


# --------------------------------------------------
# Step 1: Calculate review statistics
# --------------------------------------------------

print("Reading reviews...")

ratings = defaultdict(list)
review_texts = defaultdict(list)

for review in read_json_lines(REVIEWS_FILE):

    asin = review.get("asin")
    rating = review.get("overall")
    review_text = review.get("reviewText")

    if not asin:
        continue

    if rating is not None:
        ratings[asin].append(float(rating))

    if review_text:
        review_texts[asin].append(review_text)


# --------------------------------------------------
# Step 2: Build products
# --------------------------------------------------

print("Reading metadata...")

exclude_words = [
    "brush",
    "applicator",
    "case",
    "holder",
    "container",
    "bag",
    "organizer",
    "sealer",
    "fixative",
    "remover",
    "sharpener",
    "display",
    "liner",
    "pencil",
    "150pcs",
    "12pcs",
    "6 pcs",
    "3pcs",
    "pack of 3",
    "pack of 6",
    "pack of 12",
]

products = []
seen_asins = set()

for product in read_json_lines(METADATA_FILE):

    asin = product.get("asin")
    title = product.get("title") or ""
    title_lower = title.lower()

    # Must be a lipstick
    if "lipstick" not in title_lower:
        continue

    # Skip duplicates
    if asin in seen_asins:
        continue

    # Must have reviews
    if asin not in ratings:
        continue

    # Remove non-lipstick products
    if any(word in title_lower for word in exclude_words):
        continue

    price_usd = parse_price(product.get("price"))

    if price_usd is None:
        continue

    product_ratings = ratings[asin]

    average_rating = sum(product_ratings) / len(product_ratings)

    # Description
    description = product.get("description")

    if isinstance(description, list):
        description = " ".join(description)

    description = description or ""

    # Image
    image_url = None

    if product.get("imageURLHighRes"):
        image_url = product["imageURLHighRes"][0]

    elif product.get("imageURL"):
        image_url = product["imageURL"][0]

    # Convert historical USD price to a synthetic INR
    # merchant price.
    #
    # This is NOT the original Amazon price.
    demo_price_inr = round(price_usd * 85)

    products.append({
        "asin": asin,
        "name": title,
        "brand": product.get("brand") or "Unknown",
        "price_inr": demo_price_inr,
        "source_price_usd": price_usd,
        "rating": round(average_rating, 2),
        "review_count": len(product_ratings),
        "description": description,
        "image_url": image_url,
        "reviews": review_texts[asin][:5],
    })

    seen_asins.add(asin)


# --------------------------------------------------
# Step 3: Sort by review confidence
# --------------------------------------------------

def ranking_score(product):

    rating = product["rating"]
    review_count = product["review_count"]

    return rating * (1 + 0.15 * min(review_count, 50))


products.sort(
    key=ranking_score,
    reverse=True
)


# --------------------------------------------------
# Step 4: Select top 50
# --------------------------------------------------

products = products[:50]


# --------------------------------------------------
# Step 5: Add merchant fields
# --------------------------------------------------

for product in products:

    product["currency"] = "INR"

    # Synthetic merchant information for the demo.
    product["inventory"] = 10

    product["merchant"] = "GlowCart"

    product["available"] = True


# --------------------------------------------------
# Step 6: Save JSON
# --------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        products,
        file,
        indent=2,
        ensure_ascii=False
    )


print("\n========== CATALOG CREATED ==========")
print(f"Products: {len(products)}")
print(f"Output: {OUTPUT_FILE}")

print("\nFirst 10 products:\n")

for i, product in enumerate(products[:10], start=1):

    print(
        f"{i}. {product['name']} | "
        f"₹{product['price_inr']} | "
        f"{product['rating']}★ | "
        f"{product['review_count']} reviews"
    )