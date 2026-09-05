import re

from sqlalchemy import select

from models import Product, Review

PRO_PATTERNS = [
    (
        "long-lasting",
        (
            "long.?last",
            "lasts? all day",
            "16.?hour",
            "kiss.?proof",
            "staying power",
            "stays on",
        ),
    ),
    (
        "comfortable",
        ("comfort", "creamy", "smooth", "glides"),
    ),
    (
        "good color",
        (
            "great colo(u)?r",
            "beautiful colo(u)?r",
            "perfect colo(u)?r",
            "gorgeous",
            "pigment",
        ),
    ),
    (
        "easy application",
        ("easy to apply", "goes on", "application"),
    ),
    (
        "moisturizing",
        ("moistur", "hydrat", "not dry"),
    ),
]

CON_PATTERNS = [
    (
        "drying",
        (r"\bdry(ing|s|ed)?\b", "chapped", "cakey"),
    ),
    (
        "poor packaging",
        ("packag", "broke", "smush", "melted"),
    ),
    (
        "color mismatch",
        (
            "not the colo(u)?r",
            "different colo(u)?r",
            "too (orange|dark|light|pink)",
            "mismatch",
        ),
    ),
    (
        "transfer issues",
        ("transfer", "stain", "smudge", "on (cups|glasses|napkin)"),
    ),
    (
        "fades quickly",
        ("didn'?t last", "fade", "reapply", "wears off"),
    ),
]


def _match_themes(text: str, patterns: list[tuple]) -> list[str]:
    lowered = text.lower()
    matched = []
    for label, regexes in patterns:
        if any(re.search(rx, lowered) for rx in regexes):
            matched.append(label)
    return matched


def retrieve_review_evidence(db, product: Product, limit: int = 12) -> dict:
    statement = (
        select(Review)
        .where(Review.asin == product.asin)
        .order_by(Review.rating.desc(), Review.id.desc())
        .limit(max(limit // 2, 4))
    )
    high = list(db.execute(statement).scalars().all())

    low_statement = (
        select(Review)
        .where(Review.asin == product.asin)
        .order_by(Review.rating.asc(), Review.id.desc())
        .limit(max(limit // 2, 4))
    )
    low = list(db.execute(low_statement).scalars().all())

    by_id = {review.id: review for review in high + low}
    reviews = list(by_id.values())

    pro_counts: dict[str, int] = {}
    con_counts: dict[str, int] = {}
    pro_excerpts: dict[str, list[str]] = {}
    con_excerpts: dict[str, list[str]] = {}
    samples = []

    for review in reviews:
        text = (review.review_text or "").strip()
        if not text:
            continue
        excerpt = text[:220]
        samples.append(
            {
                "rating": float(review.rating),
                "text": excerpt,
            }
        )
        for label in _match_themes(text, PRO_PATTERNS):
            pro_counts[label] = pro_counts.get(label, 0) + 1
            pro_excerpts.setdefault(label, []).append(excerpt)
        for label in _match_themes(text, CON_PATTERNS):
            con_counts[label] = con_counts.get(label, 0) + 1
            con_excerpts.setdefault(label, []).append(excerpt)

    pros = [
        {
            "label": label,
            "mentions": count,
            "excerpts": pro_excerpts.get(label, [])[:2],
        }
        for label, count in sorted(
            pro_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:4]
    ]
    cons = [
        {
            "label": label,
            "mentions": count,
            "excerpts": con_excerpts.get(label, [])[:2],
        }
        for label, count in sorted(
            con_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:4]
    ]

    pro_total = sum(pro_counts.values())
    con_total = sum(con_counts.values())
    denom = pro_total + con_total
    if denom == 0:
        evidence_score = 0.5
    else:
        evidence_score = round(0.5 + 0.5 * ((pro_total - con_total) / denom), 3)

    return {
        "pros": pros,
        "cons": cons,
        "samples": samples[:8],
        "evidence_score": evidence_score,
        "reviews_examined": len(reviews),
    }


def evidence_labels(evidence: dict) -> tuple[list[str], list[str]]:
    pros = [item["label"] for item in evidence.get("pros", [])]
    cons = [item["label"] for item in evidence.get("cons", [])]
    return pros, cons
