"""
Factual entity alignment checker for TruthLayer.

After embedding-based similarity determines topical relevance,
this module performs fine-grained checks for numerical and semantic
contradictions that embedding models fundamentally cannot detect.

Embeddings capture MEANING but not PRECISION:
  - "$29/month" and "$19/month" embed nearly identically
  - "99.9%" and "99.99%" are indistinguishable to embeddings
  - "non-refundable" and "refundable" share high similarity

This module catches those contradictions by comparing literal entities.
"""

import re
from typing import Set


# ─── Penalty Factors ─────────────────────────────────────────────────────────
# Applied multiplicatively to the similarity score when contradictions found.
# Lower penalty = stronger downgrade.

NUMBER_MISMATCH_PENALTY = 0.5    # Claim has numbers not found in source
NEGATION_MISMATCH_PENALTY = 0.6  # One text negated, other isn't
SUPERLATIVE_VS_SPECIFIC = 0.6    # "unlimited" vs a specific number


# ─── Number Extraction ───────────────────────────────────────────────────────

_NUMBER_RE = re.compile(
    r"""
    \$?\d+              # Required: leading $ (optional) + digits
    (?:,\d{3})*         # Optional: thousands separators
    (?:\.\d+)?          # Optional: decimal part
    %?                  # Optional: percentage marker
    """,
    re.VERBOSE,
)


def extract_numbers(text: str) -> Set[str]:
    """
    Extract all numeric values from text and normalize them.

    Examples:
        "costs $29 per month"      → {"$29"}
        "99.9% uptime"             → {"99.9%"}
        "within 5-7 business days" → {"5", "7"}
        "100,000 API calls"        → {"100000"}
    """
    matches = _NUMBER_RE.findall(text)
    return {m.replace(",", "") for m in matches}


# ─── Negation Detection ─────────────────────────────────────────────────────

_NEGATION_RE = re.compile(
    r"\b(no|not|never|none|without|cannot|can't|isn't|aren't|doesn't|don't|won't)\b"
    r"|non-\w+",
    re.IGNORECASE,
)


def has_negation(text: str) -> bool:
    """Detect presence of negation in text."""
    return bool(_NEGATION_RE.search(text))


# ─── Superlative / Absolute Claim Detection ──────────────────────────────────

_SUPERLATIVE_RE = re.compile(
    r"\b(unlimited|infinite|always|every|all|any|free)\b",
    re.IGNORECASE,
)


def has_superlative(text: str) -> bool:
    """Detect absolute/superlative claims like 'unlimited', 'free', 'every'."""
    return bool(_SUPERLATIVE_RE.search(text))


# ─── Main Alignment Function ────────────────────────────────────────────────

def compute_alignment_penalty(claim: str, matched_source: str) -> float:
    """
    Compute a penalty factor based on factual alignment between claim
    and its best-matched source fragment.

    Args:
        claim:          The AI-generated claim text.
        matched_source: The best-matching source fragment (from similarity).

    Returns:
        Float between 0.0 and 1.0:
          - 1.0 = no contradictions detected (similarity unchanged)
          - <1.0 = contradiction found (similarity will be reduced)

    Examples:
        ("$29/month", "costs $29 per month")        → 1.0 (numbers match)
        ("$19/month", "costs $29 per month")        → 0.5 (number mismatch)
        ("99.99% uptime", "guarantees 99.9% uptime")→ 0.5 (number mismatch)
        ("free shipping", "customer's responsibility")→ 0.6 (superlative)
        ("no free trial", "includes a 14-day trial")→ 0.6 (negation mismatch)
    """
    if not matched_source:
        return 1.0

    penalty = 1.0

    # ── Check 1: Number mismatch ──────────────────────────────────────────
    # If the claim introduces numbers not found in the matched source,
    # it's likely fabricating specific values.
    claim_nums = extract_numbers(claim)
    source_nums = extract_numbers(matched_source)

    if claim_nums:
        unmatched = claim_nums - source_nums
        if unmatched:
            penalty = min(penalty, NUMBER_MISMATCH_PENALTY)

    # ── Check 2: Negation mismatch ────────────────────────────────────────
    # "non-refundable" (source) vs "refundable" (claim) or vice versa.
    claim_negated = has_negation(claim)
    source_negated = has_negation(matched_source)

    if claim_negated != source_negated:
        penalty = min(penalty, NEGATION_MISMATCH_PENALTY)

    # ── Check 3: Superlative vs specific value ────────────────────────────
    # Claim says "unlimited" but source gives a specific number.
    if has_superlative(claim) and source_nums:
        penalty = min(penalty, SUPERLATIVE_VS_SPECIFIC)

    return penalty
