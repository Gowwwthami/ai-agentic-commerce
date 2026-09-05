import math

from services.review_service import retrieve_review_evidence
from services.serializers import product_to_dict


def bayesian_rating(
    rating: float | None,
    review_count: int,
    prior: float = 3.8,
    prior_weight: int = 25,
) -> float:
    observed = prior if rating is None else float(rating)
    count = max(0, int(review_count or 0))
    return ((prior_weight * prior) + (count * observed)) / (prior_weight + count)


def price_fit_score(price: float, max_price: float | None) -> float:
    if max_price is None or max_price <= 0:
        return 0.7
    if price > max_price:
        return 0.0
    room = 1.0 - (price / max_price)
    return 0.55 + 0.45 * room


def volume_score(review_count: int) -> float:
    return min(1.0, math.log1p(review_count) / math.log1p(400))


def score_product(product, constraints: dict, evidence: dict | None = None) -> dict:
    rating = float(product.rating) if product.rating is not None else None
    count = int(product.review_count or 0)
    price = float(product.price)
    max_price = constraints.get("max_price")
    min_rating = constraints.get("min_rating")

    bayes = bayesian_rating(rating, count)
    volume = volume_score(count)
    price_fit = price_fit_score(price, max_price)
    evidence_score = (evidence or {}).get("evidence_score", 0.5)
    available = (
        1.0
        if product.available and product.inventory > 0
        else 0.0
    )

    rating_gate = 1.0
    if min_rating is not None and rating is not None and rating < min_rating:
        rating_gate = 0.2

    total = (
        0.38 * (bayes / 5.0)
        + 0.24 * volume
        + 0.16 * price_fit
        + 0.12 * float(evidence_score)
        + 0.10 * available
    ) * rating_gate

    factors = {
        "bayesian_rating": round(bayes, 3),
        "catalog_rating": rating,
        "review_count": count,
        "review_volume_score": round(volume, 3),
        "price": price,
        "price_fit": round(price_fit, 3),
        "evidence_score": round(float(evidence_score), 3),
        "availability": available,
        "inventory": product.inventory,
    }
    return {"score": round(total, 4), "factors": factors}


def rank_products(
    db,
    products: list,
    constraints: dict | None = None,
    with_evidence: bool = True,
    limit: int = 3,
) -> list[dict]:
    constraints = constraints or {}
    ranked = []
    for product in products:
        if with_evidence:
            evidence = retrieve_review_evidence(db, product)
        else:
            evidence = {
                "evidence_score": 0.5,
                "pros": [],
                "cons": [],
                "samples": [],
            }
        scored = score_product(product, constraints, evidence)
        payload = product_to_dict(product)
        payload["score"] = scored["score"]
        payload["score_factors"] = scored["factors"]
        payload["pros"] = [item["label"] for item in evidence.get("pros", [])]
        payload["cons"] = [item["label"] for item in evidence.get("cons", [])]
        payload["review_evidence"] = evidence
        payload["why"] = _deterministic_why(payload, constraints)
        ranked.append(payload)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def _deterministic_why(payload: dict, constraints: dict) -> str:
    parts = []
    rating = payload.get("rating")
    count = payload.get("review_count") or 0
    price = payload.get("price")
    max_price = constraints.get("max_price")

    if rating is not None:
        parts.append(
            f"catalog rating {rating:.1f} from {count} reviews"
        )
    else:
        parts.append(f"{count} stored reviews")

    if price is not None:
        if max_price is not None:
            parts.append(
                f"priced at ₹{price:.0f} within your ₹{max_price:.0f} budget"
                " (synthetic demo pricing)"
            )
        else:
            parts.append(
                f"priced at ₹{price:.0f} (synthetic demo pricing)"
            )

    pros = payload.get("pros") or []
    if pros:
        parts.append("review text supports: " + ", ".join(pros[:3]))
    cons = payload.get("cons") or []
    if cons:
        parts.append("watch-outs in reviews: " + ", ".join(cons[:2]))

    return "; ".join(parts)


def compare_payloads(
    left: dict,
    right: dict,
    constraints: dict | None = None,
) -> dict:
    """Legacy pairwise comparison — delegates to compare_all_products."""
    result = compare_all_products([left, right], constraints=constraints)
    # Keep old shape for backward compatibility
    result["left"] = left
    result["right"] = right
    return result


def compare_all_products(
    products: list[dict],
    constraints: dict | None = None,
) -> dict:
    """
    Compare N products and identify winner, best value, highest rated,
    and budget pick. Returns a shape that supports both multi-product
    and legacy pairwise comparison.
    """
    if not products:
        return {}
    constraints = constraints or {}

    if len(products) == 1:
        p = products[0]
        return {
            "products": products,
            "left": p,
            "right": p,
            "recommended_id": p["id"],
            "recommended_name": p["name"],
            "reasons": ["Only one product available."],
            "summary": f"{p['name']} is the only option.",
            "constraints": constraints,
            "best_value_id": p["id"],
            "highest_rated_id": p["id"],
            "budget_id": p["id"],
        }

    # Winner: highest recommendation score
    winner = max(products, key=lambda p: p.get("score", 0))

    # Best value: highest score-to-price ratio (price > 0)
    def value_ratio(p):
        price = p.get("price") or 0
        score = p.get("score") or 0
        return (score / price) if price > 0 else 0

    best_value = max(products, key=value_ratio)

    # Highest rated: highest catalog rating
    highest_rated = max(
        products,
        key=lambda p: (p.get("rating") or 0, p.get("review_count") or 0),
    )

    # Budget pick: lowest price among available
    budget = min(
        products,
        key=lambda p: p.get("price") or float("inf"),
    )

    reasons = _build_comparison_reasons(products, winner)

    # Summary sentence
    summary_parts = [
        f"After comparing {len(products)} options, I recommend {winner['name']}."
    ]
    summary_parts.extend(reasons[:3])
    if best_value["id"] != winner["id"]:
        summary_parts.append(
            f"For best value, consider {best_value['name']} "
            f"(₹{best_value['price']:.0f})."
        )
    if highest_rated["id"] != winner["id"] and highest_rated["id"] != best_value["id"]:
        summary_parts.append(
            f"{highest_rated['name']} has the highest catalog rating "
            f"({highest_rated.get('rating')})."
        )

    # Keep left/right for pairwise backward compat (best two by score)
    sorted_by_score = sorted(products, key=lambda p: p.get("score", 0), reverse=True)
    left  = sorted_by_score[0]
    right = sorted_by_score[1] if len(sorted_by_score) > 1 else sorted_by_score[0]

    return {
        "products": products,
        "left": left,
        "right": right,
        "recommended_id": winner["id"],
        "recommended_name": winner["name"],
        "reasons": reasons,
        "summary": " ".join(summary_parts),
        "constraints": constraints,
        "best_value_id": best_value["id"],
        "highest_rated_id": highest_rated["id"],
        "budget_id": budget["id"],
    }


def _build_comparison_reasons(products: list[dict], winner: dict) -> list[str]:
    reasons = []

    # Review count leader
    most_reviewed = max(products, key=lambda p: p.get("review_count") or 0)
    if most_reviewed["id"] == winner["id"]:
        reasons.append(
            f"{winner['name']} has the most stored reviews "
            f"({winner.get('review_count') or 0})."
        )

    # Rating
    if winner.get("rating") is not None:
        higher_rated = [
            p for p in products
            if p["id"] != winner["id"]
            and (p.get("rating") or 0) > (winner.get("rating") or 0)
        ]
        if not higher_rated:
            reasons.append(
                f"{winner['name']} has the highest or joint-highest catalog rating "
                f"({winner.get('rating')})."
            )

    # Score
    reasons.append(
        f"Recommendation score favors {winner['name']} "
        f"({winner.get('score')}) using rating, review volume, "
        "price fit, availability, and stored review evidence."
    )

    return reasons
