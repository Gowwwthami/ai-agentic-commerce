import re
from dataclasses import asdict, dataclass


ORDINAL_MAP = {
    "first": 0,
    "1st": 0,
    "second": 1,
    "2nd": 1,
    "third": 2,
    "3rd": 2,
}


@dataclass
class ParsedIntent:
    name: str
    query: str | None = None
    max_price: float | None = None
    min_rating: float | None = None
    brand: str | None = None
    product_index: int | None = None
    use_recommended: bool = False
    quantity: int = 1
    source: str = "rules"


def to_dict(intent: ParsedIntent) -> dict:
    return asdict(intent)


def parse_price(text: str) -> float | None:
    patterns = [
        r"(?:under|below|less than|upto|up to|max(?:imum)?)\s*₹?\s*([0-9]{2,6})",
        r"₹\s*([0-9]{2,6})",
    ]
    lowered = text.lower().replace(",", "")
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return float(match.group(1))
    return None


def parse_fast_intent(message: str) -> ParsedIntent | None:
    text = message.strip()
    lowered = text.lower()

    if re.search(r"\b(retry|try again|pay again)\b", lowered):
        return ParsedIntent(name="retry_payment")
    if re.search(
        r"payment link|another payment|other (?:payment )?method|upi link",
        lowered,
    ):
        return ParsedIntent(name="payment_link")
    if re.search(
        r"payment failed|didn'?t go through|payment did not",
        lowered,
    ):
        return ParsedIntent(name="payment_failed")
    if re.search(r"\b(audit|what happened|show (?:the )?log)\b", lowered):
        return ParsedIntent(name="show_audit")
    if re.search(
        r"proceed to checkout|go to checkout|\bcheckout\b|place order",
        lowered,
    ):
        return ParsedIntent(name="start_checkout")
    if re.search(r"\bbuy (?:it|now|this)\b", lowered):
        return ParsedIntent(name="buy_it")
    if re.search(
        r"^(yes|yep|yeah|confirm|go ahead|place (?:the )?order|pay now)[.! ]*$",
        lowered,
    ):
        return ParsedIntent(name="confirm_checkout")
    if re.search(
        r"\b(show(?: me)?(?: my)? cart|view cart|what'?s in (?:my )?cart)\b",
        lowered,
    ):
        return ParsedIntent(name="get_cart")
    if re.search(r"\bremove\b", lowered):
        return ParsedIntent(
            name="remove_from_cart",
            product_index=_ordinal(lowered),
        )
    if re.search(r"\bcompare\b", lowered):
        # "compare all" or "compare all of them" → compare full result set
        if re.search(r"\b(all|every|each|all of them|all of these|everything)\b", lowered):
            return ParsedIntent(name="compare_all")
        # "compare" with no ordinal and no clear target → compare all
        ordinal_idx = _ordinal(lowered)
        if ordinal_idx is None and not re.search(
            r"\b(first|second|third|1st|2nd|3rd|this|it|them|these)\b", lowered
        ):
            # generic "compare" → compare the full result set
            return ParsedIntent(name="compare_all")
        return ParsedIntent(
            name="compare",
            product_index=ordinal_idx,
        )
    if re.search(
        r"best reviews|better reviews|which (?:one )?is better|long-?lasting",
        lowered,
    ):
        return ParsedIntent(name="compare_best")
    if re.search(r"\badd\b|\bcart\b", lowered):
        intent = ParsedIntent(
            name="add_to_cart",
            product_index=_ordinal(lowered),
        )
        if "recommended" in lowered or "the one you" in lowered:
            intent.use_recommended = True
        return intent
    if re.search(
        r"lipstick|recommend|highly rated|good reviews|under|show me",
        lowered,
    ):
        return _search_intent(text, lowered)
    # Fall through to a generic search for any message that looks like a
    # product query (contains nouns/adjectives not matched above).
    # This catches "foundation for dark skin", "mascara under 500", etc.
    if re.search(r"\b(foundation|mascara|blush|eyeliner|concealer|serum|moisturizer|"
                 r"skincare|makeup|cosmetic|beauty|skin|hair|nail|color|colour|"
                 r"shade|product|cream|lotion|powder|eyeshadow|liner|gloss|"
                 r"tint|balm|primer|bronzer|highlighter|contour)\b", lowered):
        return _search_intent(text, lowered)
    return None


def parse_search_intent(message: str) -> ParsedIntent:
    return _search_intent(message, message.lower())


def _search_intent(text: str, lowered: str) -> ParsedIntent:
    intent = ParsedIntent(name="search", query=None)
    intent.max_price = parse_price(text)
    if re.search(
        r"highly rated|good reviews|best reviews|well reviewed",
        lowered,
    ):
        intent.min_rating = 3.8
    brands = [
        "rimmel",
        "maybelline",
        "revlon",
        "l'oreal",
        "loreal",
        "e.l.f",
        "elf",
        "nyx",
        "covergirl",
        "lakme",
        "mac",
        "nars",
        "physicians formula",
    ]
    for brand in brands:
        if brand in lowered:
            intent.brand = "e.l.f." if brand in {"e.l.f", "elf"} else brand
            break

    # Extract meaningful search terms, stripping:
    # - common filler/instruction words
    # - pure numbers (already captured in max_price)
    # - very short tokens
    stop_words = {
        "find", "me", "show", "i", "want", "a", "an", "the", "some", "please",
        "can", "you", "get", "search", "for", "look", "up", "give",
        "need", "recommend", "best", "good", "top", "nice", "great",
        "highly", "rated", "under", "below", "within", "budget", "cheap",
        "affordable", "expensive", "with", "and", "or", "of", "to",
        "is", "are", "my", "your", "its", "it", "this", "that",
        "very", "really", "quite", "just", "only",
    }
    # Extract only alphabetic words (no digits — those are price constraints)
    words = re.findall(r"[a-z]+", lowered)
    query_words = [w for w in words if w not in stop_words and len(w) > 2]

    # The first meaningful product/category word is the primary query.
    # Keep all unique meaningful words joined — catalog_service will split them.
    if query_words:
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for w in query_words:
            if w not in seen:
                deduped.append(w)
                seen.add(w)
        intent.query = " ".join(deduped)
    return intent


def _ordinal(lowered: str) -> int | None:
    for word, index in ORDINAL_MAP.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return index
    return None
