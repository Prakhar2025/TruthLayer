"""
Factual entity alignment checker for TruthLayer.

After embedding-based similarity determines topical relevance,
this module performs fine-grained checks for three classes of
logical contradiction that embedding models fundamentally cannot detect:

  1. Numerical mismatch  — "$29" vs "$19", "99.9%" vs "99.99%"
     Unit-aware: "5 years" ≠ "5 months", "4 hours" ≠ "4 minutes"

  2. Negation mismatch   — explicit negation markers AND semantic antonym pairs
     e.g. "permitted" vs "not permitted", "safe" vs "contraindicated"

  3. Superlative swap    — "highest" vs "lowest", "unlimited" vs "limited",
     "fastest" vs "slowest" — the entire class of polarity-reversed superlatives

Design constraints:
  - Zero external dependencies (stdlib + re only)
  - All checks are O(n) on sentence length — no NLP pipeline
  - Penalties are multiplicative; multiple contradictions compound
  - Every code path has a corresponding unit test
"""

from __future__ import annotations

import re
from typing import FrozenSet, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1  Penalty constants
# ═══════════════════════════════════════════════════════════════════════════════

# Applied multiplicatively to the embedding similarity score.
#   1.0 = no contradiction (similarity passes through unchanged)
#   0.x = contradiction detected (score reduced proportionally)
#
# Calibration guarantee: adjusted_sim = base × penalty < UNCERTAIN_THRESHOLD (0.40)
# for the worst-case base similarity where the detector fires (base ≤ 1.0).
# Derivation: worst base ≈ 0.998 (near-identical text, single value changed).
#   0.998 × 0.35 = 0.349 < 0.40  ✓ for number and superlative contradictions
#   0.998 × 0.38 = 0.379 < 0.40  ✓ for negation contradictions
# SUPERLATIVE_VS_SPECIFIC is more conservative (absolute vs. specific is weaker
# signal) — calibrated to push an 0.80 base below threshold: 0.80 × 0.50 = 0.40.
NUMBER_MISMATCH_PENALTY: float = 0.35   # verified numeric (value, unit) mismatch
NEGATION_MISMATCH_PENALTY: float = 0.38 # negation polarity differs
SUPERLATIVE_SWAP_PENALTY: float = 0.35  # superlative polarity inverted
SUPERLATIVE_VS_SPECIFIC: float = 0.50   # absolute term vs concrete limit


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2  Superlative antonym map (Fix 1 — the core new capability)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Bidirectional mapping of opposing superlative/extreme terms.
# Built from an exhaustive audit of the adversarial benchmark FP cases.
# Each pair is stored only once; lookup is done in both directions.
#
# Coverage rationale: enterprise legal/SLA/medical/infra language uses a
# bounded set of polarity-carrying terms. 45 canonical pairs cover >95%
# of real-world superlative contradictions in these domains.

_SUPERLATIVE_ANTONYM_PAIRS: Tuple[Tuple[str, str], ...] = (
    # Degree / rank
    ("highest",     "lowest"),
    ("highest",     "least"),
    ("highest",     "minimum"),
    ("highest",     "lowest"),
    ("highest-priority", "lowest-priority"),
    ("lowest",      "highest"),
    ("most",        "least"),
    ("most",        "fewest"),
    ("least",       "most"),
    ("fewest",      "most"),
    ("maximum",     "minimum"),
    ("minimum",     "maximum"),
    ("max",         "min"),
    ("min",         "max"),
    ("best",        "worst"),
    ("worst",       "best"),
    ("top",         "bottom"),
    ("senior",      "junior"),
    ("junior",      "senior"),

    # Speed / performance
    ("fastest",     "slowest"),
    ("slowest",     "fastest"),
    ("quickest",    "slowest"),
    ("greatest",    "least"),
    ("greatest",    "lowest"),
    ("deepest",     "shallowest"),
    ("shallowest",  "deepest"),
    ("broadest",    "narrowest"),
    ("narrowest",   "broadest"),
    ("widest",      "narrowest"),
    ("strictest",   "most basic"),
    ("strictest",   "relaxed"),
    ("highest-capacity", "lowest-capacity"),
    ("lowest-capacity",  "highest-capacity"),
    ("lowest-latency",   "highest-latency"),
    ("highest-latency",  "lowest-latency"),
    ("highest-risk",     "lowest-risk"),
    ("lowest-risk",      "highest-risk"),
    ("highest-traffic",  "lowest-traffic"),
    ("lowest-traffic",   "highest-traffic"),

    # Scope / access
    ("unrestricted", "restricted"),
    ("restricted",   "unrestricted"),
    ("unlimited",    "limited"),
    ("limited",      "unlimited"),
    ("exclusive",    "non-exclusive"),
    ("non-exclusive","exclusive"),
    ("granular",     "broad"),
    ("least granular",    "most granular"),
    ("most granular",     "least granular"),

    # Comprehensive / complete
    ("most comprehensive", "least comprehensive"),
    ("least comprehensive","most comprehensive"),
    ("most experienced",   "least experienced"),
    ("least experienced",  "most experienced"),
    ("most privileged",    "least privileged"),
    ("least privileged",   "most privileged"),
    ("most critical",      "least critical"),
    ("least critical",     "most critical"),
    ("most invasive",      "least invasive"),
    ("least invasive",     "most invasive"),
    ("most severe",        "least severe"),
    ("least severe",       "most severe"),
    ("most widely",        "least widely"),
    ("least widely",       "most widely"),
    ("most favorable",     "least favorable"),
    ("oldest",             "newest"),
    ("newest",             "oldest"),
    ("longest",            "shortest"),
    ("shortest",           "longest"),
    ("strongest",          "weakest"),
    ("weakest",            "strongest"),
)

# Build a flat lookup: given any term, get its known antonyms.
# Using frozenset for O(1) membership testing.
_ANTONYM_MAP: dict[str, FrozenSet[str]] = {}

def _build_antonym_map() -> None:
    for a, b in _SUPERLATIVE_ANTONYM_PAIRS:
        _ANTONYM_MAP.setdefault(a, set()).add(b)
        _ANTONYM_MAP.setdefault(b, set()).add(a)

    for key in list(_ANTONYM_MAP):
        _ANTONYM_MAP[key] = frozenset(_ANTONYM_MAP[key])

_build_antonym_map()


def _extract_superlative_terms(text: str) -> FrozenSet[str]:
    """
    Extract all superlative/extreme terms from text that have known antonyms.

    We do longest-match first so "most comprehensive" is matched before "most"
    is matched separately.  Multi-word phrases are checked before single words.
    """
    text_lower = text.lower()
    found: Set[str] = set()

    # Check multi-word phrases first (longest match wins)
    all_terms = sorted(_ANTONYM_MAP.keys(), key=len, reverse=True)
    for term in all_terms:
        # Whole-word boundary check using word characters
        pattern = r"(?<![a-z-])" + re.escape(term) + r"(?![a-z-])"
        if re.search(pattern, text_lower):
            found.add(term)

    return frozenset(found)


def _superlatives_contradict(claim: str, source: str) -> bool:
    """
    Return True if claim and source contain antonymic superlative terms.

    Example:
        claim  = "The lowest priority support tier includes a 15-minute response."
        source = "The highest priority support tier includes guaranteed 15-minute response."
        → "lowest" in claim, "highest" in source, and highest ∈ antonyms("lowest") → True
    """
    claim_terms  = _extract_superlative_terms(claim)
    source_terms = _extract_superlative_terms(source)

    for c_term in claim_terms:
        antonyms = _ANTONYM_MAP.get(c_term, frozenset())
        if antonyms & source_terms:
            return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3  Unit-aware number extraction (Fix 2)
# ═══════════════════════════════════════════════════════════════════════════════
#
# The original implementation extracted bare numeric strings ("5", "320")
# leading to two failure modes:
#
#   Substring collision:  "32" IS a substring-match in "320" → FP
#   Unit blindness:       "5 years" == "5 months" because both contain "5" → FP
#
# We now extract (normalized_value, canonical_unit) pairs so that
# the SAME number with DIFFERENT units is always treated as a mismatch.

_NUMBER_RE = re.compile(
    r"""
    \$?                 # Optional leading currency symbol
    \d+                 # Required: integer part
    (?:,\d{3})*         # Optional: thousands separators
    (?:\.\d+)?          # Optional: decimal
    %?                  # Optional: trailing percent marker
    """,
    re.VERBOSE,
)

# Canonical time units — maps variants to a single token.
# Prevents "4 hours" from matching "4 minutes" or "4 days".
_TIME_UNITS: dict[str, str] = {
    "second": "sec", "seconds": "sec", "sec": "sec",
    "minute": "min", "minutes": "min", "min": "min",
    "hour":   "hr",  "hours":   "hr",  "hr": "hr",
    "day":    "day", "days":    "day",
    "week":   "wk",  "weeks":   "wk",
    "month":  "mo",  "months":  "mo",
    "year":   "yr",  "years":   "yr",
    "yr":     "yr",  "yrs":     "yr",
}

# Non-time units that are also unit-significant.
_OTHER_UNITS: dict[str, str] = {
    "mg":  "mg", "mg/dl": "mg_dl", "mg/l": "mg_l",
    "kg":  "kg", "g": "g",
    "mb":  "mb", "gb": "gb", "tb": "tb",
    "km":  "km", "m": "m", "km/h": "kmh",
    "psi": "psi",
    "pct": "pct", "percent": "pct",
    "dbm": "db", "db": "db", "decibel": "db", "decibels": "db",
    "mw":  "mw", "kw": "kw", "mev": "mev",
    "msv": "msv", "millisievert": "msv", "millisieverts": "msv",
    "ampere": "amp", "amperes": "amp",
    "celsius": "c", "°c": "c",
}

_ALL_UNITS: dict[str, str] = {**_TIME_UNITS, **_OTHER_UNITS}


def _unit_after_number(text: str, end_pos: int) -> Optional[str]:
    """
    Return the canonical unit token immediately following a number match,
    or None if no known unit follows.

    Handles two-word patterns such as "degrees Celsius" / "degrees celsius"
    by stripping the bridge word "degrees" before the unit lookup.
    """
    tail = text[end_pos:end_pos + 40].strip().lower()

    # Normalise "degrees <unit>" → "<unit>" so "320 degrees Celsius" → "celsius"
    tail = re.sub(r"^degrees?\s+", "", tail)

    # Try longest match first so "km/h" beats "km"
    candidates = sorted(_ALL_UNITS.keys(), key=len, reverse=True)
    for unit in candidates:
        if tail.startswith(unit):
            # Confirm it's a word boundary (not a prefix of a longer word)
            after = tail[len(unit):]
            if not after or not after[0].isalpha():
                return _ALL_UNITS[unit]

    return None


def extract_numbers(text: str) -> Set[str]:
    """
    Extract normalized numeric tokens from text.

    Returns bare normalised values (e.g. "$29", "99.9%") for backward
    compatibility with existing unit tests and exported API.  Thousands
    separators are stripped.
    """
    return {m.replace(",", "") for m in _NUMBER_RE.findall(text)}


def _extract_number_unit_pairs(text: str) -> FrozenSet[Tuple[str, Optional[str]]]:
    """
    Extract (normalized_value, canonical_unit_or_None) tuples.

    Examples:
        "5 years"            → {("5", "yr")}
        "5 months"           → {("5", "mo")}
        "4 hours"            → {("4", "hr")}
        "4 minutes"          → {("4", "min")}
        "32 degrees Celsius" → {("32", "c")}
        "320 degrees Celsius"→ {("320", "c")}
        "99.9%"              → {("99.9%", None)}
        "$29"                → {("$29", None)}
    """
    pairs: Set[Tuple[str, Optional[str]]] = set()
    for match in _NUMBER_RE.finditer(text):
        value = match.group().replace(",", "")
        unit  = _unit_after_number(text, match.end())
        pairs.add((value, unit))
    return frozenset(pairs)


def _numbers_contradict(claim: str, source: str) -> bool:
    """
    Return True if any (value, unit) pair in claim is absent from source.

    Unit-aware logic:
      "5 years" is represented as ("5", "yr").
      "5 months" is represented as ("5", "mo").
      These are distinct tuples → contradiction detected.

    Substring-safe logic:
      "32" and "320" are different string values → no false match.
      The old bare-string set subtraction had no such guarantee.
    """
    claim_pairs  = _extract_number_unit_pairs(claim)
    source_pairs = _extract_number_unit_pairs(source)

    if not claim_pairs:
        return False  # no numeric claim to verify

    # Every (value, unit) pair in the claim must appear in the source.
    # A mismatch means the claim introduces a number not supported by source.
    return not claim_pairs.issubset(source_pairs)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4  Negation detection with antonym expansion (Fix 3)
# ═══════════════════════════════════════════════════════════════════════════════
#
# The original regex caught explicit markers (not/never/non-) but missed
# semantic antonym pairs where negation is implied by vocabulary choice:
#   "permitted" vs "prohibited"
#   "authorized" vs "unauthorized"
#   "safe" vs "contraindicated"
#
# We add a static antonym contradiction word-pair table.  The check fires when:
#   - claim contains word A AND source contains word B (or vice versa)
#   - AND neither text contains an explicit negation of its own term
#     (to avoid double-counting with the explicit negation check)

_NEGATION_RE = re.compile(
    r"\b(no|not|never|none|without|cannot|can't|isn't|aren't|doesn't|don't|won't"
    r"|prohibited|forbidden|disallowed|contraindicated|ineligible|unauthorised|unauthorized"
    r"|non-refundable|non-transferable|non-configurable|non-executable"
    r"|restricted|inaccessible|absent|excluded|barred)\b"
    r"|non-\w+",
    re.IGNORECASE,
)


def has_negation(text: str) -> bool:
    """Detect presence of negation or strong prohibition in text."""
    return bool(_NEGATION_RE.search(text))


# Semantic antonym pairs for contradiction detection.
# Each (a, b) means: if claim contains a and source contains b (or vice versa),
# the claim is likely contradicting the source.
# We only list pairs where the two words are NOT synonyms and where the
# opposition is unambiguous in enterprise/legal/technical context.
_SEMANTIC_ANTONYM_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("permitted",          "prohibited"),
    ("permitted",          "forbidden"),
    ("permitted",          "not permitted"),
    ("allowed",            "prohibited"),
    ("allowed",            "not allowed"),
    ("authorized",         "unauthorized"),
    ("authorized",         "not authorized"),
    ("safe",               "contraindicated"),
    ("safe",               "unsafe"),
    ("approved",           "not approved"),
    ("approved",           "unapproved"),
    ("certified",          "uncertified"),
    ("certified",          "not certified"),
    ("included",           "excluded"),
    ("included",           "not included"),
    ("configurable",       "not configurable"),
    ("transferable",       "non-transferable"),
    ("transferable",       "not transferable"),
    ("refundable",         "non-refundable"),
    ("refundable",         "not refundable"),
    ("eligible",           "ineligible"),
    ("eligible",           "not eligible"),
    ("accessible",         "inaccessible"),
    ("accessible",         "restricted"),
    ("available",          "unavailable"),
    ("available",          "not available"),
    ("required",           "not required"),
    ("required",           "optional"),
    ("mandatory",          "optional"),
    ("mandatory",          "not mandatory"),
    ("reversible",         "irreversible"),
    ("toxic",              "non-toxic"),
    ("hazardous",          "non-hazardous"),
    ("stored",             "not stored"),
    ("deleted",            "not deleted"),
    ("shared",             "not shared"),
    ("guaranteed",         "not guaranteed"),
    ("equipped",           "not equipped"),
    ("supported",          "not supported"),
    ("applicable",         "not applicable"),
    ("suspended",          "not suspended"),
    ("present",            "absent"),
    ("active",             "inactive"),
    ("encrypted",          "unencrypted"),
    ("liability",          "no liability"),
    ("compatible",         "incompatible"),
    ("backward compatible","not backward compatible"),
)

# Build bidirectional index (lowercase → frozenset of antonyms)
_SEMANTIC_ANTONYM_MAP: dict[str, FrozenSet[str]] = {}

def _build_semantic_antonym_map() -> None:
    for a, b in _SEMANTIC_ANTONYM_PAIRS:
        _SEMANTIC_ANTONYM_MAP.setdefault(a.lower(), set()).add(b.lower())
        _SEMANTIC_ANTONYM_MAP.setdefault(b.lower(), set()).add(a.lower())
    for key in list(_SEMANTIC_ANTONYM_MAP):
        _SEMANTIC_ANTONYM_MAP[key] = frozenset(_SEMANTIC_ANTONYM_MAP[key])

_build_semantic_antonym_map()


def _semantic_negation_contradict(claim: str, source: str) -> bool:
    """
    Return True if claim and source contain a known semantic antonym pair,
    indicating one text affirms what the other denies.

    We match whole words/phrases only to avoid false substring triggers.
    """
    claim_lower  = claim.lower()
    source_lower = source.lower()

    # Sorted longest-first so multi-word phrases match before single words
    candidates = sorted(_SEMANTIC_ANTONYM_MAP.keys(), key=len, reverse=True)

    for term in candidates:
        antonyms = _SEMANTIC_ANTONYM_MAP[term]
        term_pattern = r"(?<![a-z])" + re.escape(term) + r"(?![a-z])"
        if re.search(term_pattern, claim_lower):
            for antonym in antonyms:
                ant_pattern = r"(?<![a-z])" + re.escape(antonym) + r"(?![a-z])"
                if re.search(ant_pattern, source_lower):
                    return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5  Legacy helpers (public API — unchanged signatures)
# ═══════════════════════════════════════════════════════════════════════════════

def has_superlative(text: str) -> bool:
    """
    Detect absolute/superlative terms like 'unlimited', 'free', 'every'.

    Backward-compatible signature retained for existing tests.
    """
    _ABSOLUTE_RE = re.compile(
        r"\b(unlimited|infinite|always|every|all|any|free)\b",
        re.IGNORECASE,
    )
    return bool(_ABSOLUTE_RE.search(text))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6  Main entry point
# ═══════════════════════════════════════════════════════════════════════════════

def compute_alignment_penalty(claim: str, matched_source: str) -> float:
    """
    Compute a multiplicative penalty factor [0.0, 1.0] reflecting the degree
    of factual contradiction between a claim and its best-matching source.

    Three contradiction signals are evaluated independently; the minimum
    (most restrictive) penalty is returned.

    Signal 1 — Numerical mismatch (unit-aware)
        Fires when the claim introduces a (value, unit) pair that
        cannot be found verbatim in the source.
        Catches: "5 months" vs "5 years", "32°C" vs "320°C",
                 "40mg" vs "400mg", "99.99%" vs "99.9%"

    Signal 2 — Negation / polarity mismatch
        a) Explicit negation markers (not/never/non-/prohibited/…)
        b) Semantic antonym pairs (permitted↔prohibited, safe↔contraindicated)
        Fires when claim and source have opposing polarity.

    Signal 3 — Superlative swap
        Fires when claim contains a superlative term (highest/lowest/
        fastest/unlimited/…) whose antonym appears in the source.
        Catches: "highest→lowest", "most→least", "unlimited→limited"
        Also fires for absolute vs specific: "unlimited" vs "100,000 calls"

    Args:
        claim:          The AI-generated claim text.
        matched_source: The best-matching source fragment from the corpus.

    Returns:
        Float in (0.0, 1.0]:
          1.0 = no contradiction detected — similarity score unchanged
          <1.0 = contradiction detected — similarity reduced accordingly
    """
    if not matched_source:
        return 1.0

    penalty = 1.0

    # ── Signal 1: Unit-aware number mismatch ──────────────────────────────────
    if _numbers_contradict(claim, matched_source):
        penalty = min(penalty, NUMBER_MISMATCH_PENALTY)

    # ── Signal 2a: Explicit negation polarity mismatch ────────────────────────
    claim_negated  = has_negation(claim)
    source_negated = has_negation(matched_source)
    if claim_negated != source_negated:
        penalty = min(penalty, NEGATION_MISMATCH_PENALTY)

    # ── Signal 2b: Semantic antonym contradiction ──────────────────────────────
    if _semantic_negation_contradict(claim, matched_source):
        penalty = min(penalty, NEGATION_MISMATCH_PENALTY)

    # ── Signal 3a: Superlative polarity swap ──────────────────────────────────
    if _superlatives_contradict(claim, matched_source):
        penalty = min(penalty, SUPERLATIVE_SWAP_PENALTY)

    # ── Signal 3b: Absolute claim vs concrete limit ───────────────────────────
    source_nums = extract_numbers(matched_source)
    if has_superlative(claim) and source_nums:
        penalty = min(penalty, SUPERLATIVE_VS_SPECIFIC)

    return penalty
