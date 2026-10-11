"""
In-memory keyword ranking engine for LapLink Smart Search.
Features weighted fields, exact/stem/prefix/fuzzy token matching, and query coverage boost.
No substring matching inside tokens to eliminate false positives.
"""
import difflib
from typing import List, Tuple, Dict, Any

from .normalize import tokenize, stem

FIELD_WEIGHTS = {
    'N': 3.0,  # Name
    'B': 2.5,  # Brand
    'C': 2.0,  # Category & Subcategory
    'T': 1.5,  # AI Search Tags
    'S': 1.0,  # Product Specs
    'D': 0.5,  # Description
}


def keyword_rank(query: str, index: Dict[str, Any]) -> List[Tuple[int, float]]:
    """
    Ranks products in index by keyword relevance to query.
    Returns list of (product_id, score) sorted descending by score (> 0 only).
    """
    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    vocab = index.get("vocab", set())
    products = index.get("items", [])

    total_tokens = len(q_tokens)

    # Precompute per-token properties
    token_meta = []
    for q in q_tokens:
        q_stem = stem(q)
        q_len = len(q)
        fuzzy_candidates = []
        if q_len >= 4 and q not in vocab:
            fuzzy_candidates = difflib.get_close_matches(q, vocab, n=3, cutoff=0.8)

        token_meta.append({
            "token": q,
            "stem": q_stem,
            "len": q_len,
            "fuzzy": set(fuzzy_candidates),
        })

    results = []

    for item in products:
        fields = item.get("fields", {})
        stems_dict = item.get("stems", {})
        matched_tokens = 0
        score_sum = 0.0

        for tm in token_meta:
            q = tm["token"]
            q_stem = tm["stem"]
            q_len = tm["len"]
            fuzzy_set = tm["fuzzy"]

            best_credit = 0.0

            for code, weight in FIELD_WEIGHTS.items():
                f_tokens = fields.get(code, set())
                if not f_tokens:
                    continue

                f_stems = stems_dict.get(code, set())

                # 1. Exact match
                if q in f_tokens:
                    credit = 1.0 * weight
                    if credit > best_credit:
                        best_credit = credit
                    continue  # Maximum possible credit for this field

                # Tokens of len <= 2 only count as exact matches
                if q_len <= 2:
                    continue

                # 2. Stem match
                if q_stem and q_stem in f_stems:
                    credit = 0.9 * weight
                    if credit > best_credit:
                        best_credit = credit

                # 3. Prefix match (len >= 3)
                if q_len >= 3:
                    if any(t.startswith(q) for t in f_tokens):
                        credit = 0.7 * weight
                        if credit > best_credit:
                            best_credit = credit

                # 4. Fuzzy match (len >= 4, q not in vocab)
                if fuzzy_set and any(cand in f_tokens for cand in fuzzy_set):
                    credit = 0.6 * weight
                    if credit > best_credit:
                        best_credit = credit

            if best_credit > 0:
                matched_tokens += 1
                score_sum += best_credit

        if matched_tokens > 0:
            coverage = matched_tokens / total_tokens
            final_score = score_sum * coverage
            results.append((item["id"], round(final_score, 4)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results
