"""
Build a multi-category beauty catalog for GlowCart.

Reads:
  data/raw/All_Beauty (1).json.gz   — full review corpus
  data/raw/meta_All_Beauty (1).json.gz — product metadata

Outputs:
  data/catalog.json  — 200-500 products across multiple beauty categories

Run from project root:
  python data/build_catalog.py
"""

import gzip
import json
import re
from collections import defaultdict

REVIEWS_FILE  = "data/raw/All_Beauty (1).json.gz"
METADATA_FILE = "data/raw/meta_All_Beauty (1).json.gz"
OUTPUT_FILE   = "data/catalog.json"

# ---------------------------------------------------------------------------
# Category definitions — (category_slug, display_name, keywords, per_cat_limit)
# We take the top N ranked products per category so no single category
# dominates the demo catalog.
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("lipstick",   "Lipstick",     ["lipstick", "lip color", "lip colour", "lip stick"],   80),
    ("foundation", "Foundation",   ["foundation", "bb cream", "cc cream"],                  60),
    ("mascara",    "Mascara",      ["mascara"],                                              40),
    ("eyeliner",   "Eyeliner",     ["eyeliner", "eye liner", "kohl"],                       30),
    ("eyeshadow",  "Eyeshadow",    ["eyeshadow", "eye shadow", "eye palette"],              30),
    ("blush",      "Blush",        ["blush", "rouge"],                                      30),
    ("concealer",  "Concealer",    ["concealer", "cover stick"],                            25),
    ("skincare",   "Skincare",     ["moisturizer", "moisturiser", "serum",
                                    "face cream", "face wash", "cleanser",
                                    "toner", "sunscreen"],                                  30),
    ("lip_gloss",  "Lip Gloss",    ["lip gloss", "lipgloss"],                               20),
    ("bronzer",    "Bronzer",      ["bronzer", "highlighter", "contour powder"],            20),
    ("primer",     "Primer",       ["face primer", "eye primer", " primer "],              15),
]

# Products whose titles contain these words are accessories, not cosmetics.
EXCLUDE_WORDS = [
    "brush", "applicator", "case", "holder", "container", "bag",
    "organizer", "sealer", "fixative", "remover", "sharpener",
    "display", "sponge", "blender", "spatula", "mirror",
    "150pcs", "12pcs", "6 pcs", "3pcs", "3psc", "pack of 3",
    "pack of 6", "pack of 12", "set of", "lot of",
    "refill", "replacement", "pencil sharpener",
    "gift set", "kit ", " kit,", "value pack",
    "duo ", " duo,", " duo.", " 2-pack", " 3-pack",
]

# Build fast lookup: lower-case keyword → (slug, display_name)
KEYWORD_TO_CAT = {}
for slug, display, keywords, _ in CATEGORIES:
    for kw in keywords:
        KEYWORD_TO_CAT[kw] = (slug, display)


def read_json_lines(filename):
    with gzip.open(filename, "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def parse_price(price) -> float | None:
    """Parse raw price string to float USD, reject implausible values."""
    if not price:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(price).split("-")[0].strip())
    try:
        v = float(cleaned)
        return v if 0 < v <= 500 else None
    except ValueError:
        return None


def classify(title: str) -> tuple[str, str] | None:
    """Return (slug, display_name) for the first matching category, or None."""
    lower = title.lower()
    if any(w in lower for w in EXCLUDE_WORDS):
        return None
    for _, _, keywords, _ in CATEGORIES:
        for kw in keywords:
            if kw in lower:
                return KEYWORD_TO_CAT[kw]
    return None


def ranking_score(rating: float, review_count: int) -> float:
    """Bayesian-style ranking to prefer well-reviewed items."""
    prior, prior_weight = 3.8, 20
    bayes = ((prior_weight * prior) + (review_count * rating)) / (prior_weight + review_count)
    import math
    volume = math.log1p(review_count)
    return bayes * 0.7 + volume * 0.3


# ---------------------------------------------------------------------------
# Step 1: Collect review stats from the full review corpus
# ---------------------------------------------------------------------------
print("Reading reviews …")
ratings:       dict[str, list[float]] = defaultdict(list)
review_texts:  dict[str, list[str]]   = defaultdict(list)

for review in read_json_lines(REVIEWS_FILE):
    asin = review.get("asin")
    if not asin:
        continue
    r = review.get("overall")
    if r is not None:
        ratings[asin].append(float(r))
    t = (review.get("reviewText") or "").strip()
    if t:
        review_texts[asin].append(t)

print(f"  Unique reviewed ASINs: {len(ratings)}")

# ---------------------------------------------------------------------------
# Step 2: Scan metadata, classify products, build per-category pools
# ---------------------------------------------------------------------------
print("Reading metadata and classifying products …")

# per_cat_pool: slug → list of product dicts (unsorted)
per_cat_pool: dict[str, list[dict]] = defaultdict(list)
seen_asins: set[str] = set()

for product in read_json_lines(METADATA_FILE):
    asin = product.get("asin")
    if not asin or asin in seen_asins:
        continue

    title = (product.get("title") or "").strip()
    if not title:
        continue

    cat = classify(title)
    if cat is None:
        continue

    slug, display_name = cat

    # Must have price
    price_usd = parse_price(product.get("price"))
    if price_usd is None:
        continue

    # Must have at least 3 reviews for any evidence
    asin_ratings = ratings.get(asin, [])
    if len(asin_ratings) < 3:
        continue

    avg_rating = sum(asin_ratings) / len(asin_ratings)
    review_count = len(asin_ratings)

    # Description — flatten list if needed
    description = product.get("description") or ""
    if isinstance(description, list):
        description = " ".join(str(d) for d in description).strip()
    description = description[:600] if description else ""

    # Image
    image_url = None
    if product.get("imageURLHighRes"):
        image_url = product["imageURLHighRes"][0]
    elif product.get("imageURL"):
        image_url = product["imageURL"][0]

    per_cat_pool[slug].append({
        "asin":          asin,
        "name":          title,
        "brand":         (product.get("brand") or "Unknown").strip(),
        "category":      slug,
        "display_category": display_name,
        "price_usd":     price_usd,
        "price_inr":     round(price_usd * 85),
        "rating":        round(avg_rating, 2),
        "review_count":  review_count,
        "description":   description,
        "image_url":     image_url,
        "_score":        ranking_score(avg_rating, review_count),
    })

    seen_asins.add(asin)

# ---------------------------------------------------------------------------
# Step 3: Sort each pool, take top N per category
# ---------------------------------------------------------------------------
print("\nCategory pools (before cap):")
for slug, _, _, cap in CATEGORIES:
    pool = per_cat_pool.get(slug, [])
    print(f"  {slug:<15} {len(pool):>4} usable  →  cap {cap}")

products: list[dict] = []
cat_limits = {slug: cap for slug, _, _, cap in CATEGORIES}

for slug, _, _, cap in CATEGORIES:
    pool = per_cat_pool.get(slug, [])
    pool.sort(key=lambda p: p["_score"], reverse=True)
    selected = pool[:cap]
    products.extend(selected)

# ---------------------------------------------------------------------------
# Step 4: Add merchant / demo fields; clean up internal keys
# ---------------------------------------------------------------------------
for p in products:
    p["currency"]  = "INR"
    p["inventory"] = 10
    p["merchant"]  = "GlowCart"
    p["available"] = True
    # Keep source_price_usd for auditability
    p["source_price_usd"] = p.pop("price_usd")
    # Remove internal score — not needed in catalog.json
    p.pop("_score", None)
    p.pop("display_category", None)

# ---------------------------------------------------------------------------
# Step 5: Final dedup (should be clean already, but be safe)
# ---------------------------------------------------------------------------
seen = set()
deduped = []
for p in products:
    if p["asin"] not in seen:
        deduped.append(p)
        seen.add(p["asin"])
products = deduped

# ---------------------------------------------------------------------------
# Step 6: Write catalog.json
# ---------------------------------------------------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Step 7: Summary
# ---------------------------------------------------------------------------
from collections import Counter
cat_tally = Counter(p["category"] for p in products)

print("\n========== CATALOG CREATED ==========")
print(f"Total products: {len(products)}")
print(f"Output: {OUTPUT_FILE}")
print("\nBy category:")
for slug, _, _, _ in CATEGORIES:
    n = cat_tally.get(slug, 0)
    print(f"  {slug:<15} {n:>4}")

print("\nFirst product per category:")
shown: set[str] = set()
for p in products:
    if p["category"] not in shown:
        print(f"  [{p['category']}] {p['name'][:60]}  ₹{p['price_inr']}  {p['rating']}★")
        shown.add(p["category"])
