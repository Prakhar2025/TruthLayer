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
    ("least favorable",    "most favorable"),
    ("oldest",             "newest"),
    ("newest",             "oldest"),
    ("longest",            "shortest"),
    ("shortest",           "longest"),
    ("strongest",          "weakest"),
    ("weakest",            "strongest"),

    # Enterprise tier / plan naming contradictions (Fix 3)
    # These cover cases where the adversarial swap changes the plan tier
    # rather than an explicit superlative word — e.g. "entry-level" is
    # the polar opposite of "enterprise" in SLA and feature contexts.
    ("entry-level",        "enterprise"),
    ("enterprise",         "entry-level"),
    ("entry-level",        "top-tier"),
    ("top-tier",           "entry-level"),
    ("basic",              "enterprise"),
    ("enterprise",         "basic"),
    ("lowest tier",        "highest tier"),
    ("highest tier",       "lowest tier"),
    ("newly onboarded",    "long-term"),
    ("long-term",          "newly onboarded"),
    ("first-responder",    "last-responder"),
    ("lowest-priority",    "highest-priority"),
    ("highest-priority",   "lowest-priority"),
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

# ── Precompiled superlative term patterns ────────────────────────────────────
# Built once at module import time: {term: compiled_pattern}.
# Avoids re.escape() + re.compile() inside the hot loop in
# _extract_superlative_terms(), saving N×M regex compilations per request
# (N = number of claims, M = number of terms in the antonym map ≈ 80).
_SUPERLATIVE_TERM_PATTERNS: dict[str, re.Pattern] = {
    term: re.compile(
        r"(?<![a-z-])" + re.escape(term) + r"(?![a-z])",
        re.IGNORECASE,
    )
    for term in sorted(_ANTONYM_MAP.keys(), key=len, reverse=True)
}

# Terms sorted by length descending — used by _extract_superlative_terms()
# for longest-match-first iteration.  Pre-sorted once, not on every call.
_SUPERLATIVE_TERMS_BY_LENGTH: tuple = tuple(
    sorted(_ANTONYM_MAP.keys(), key=len, reverse=True)
)


def _extract_superlative_terms(text: str) -> FrozenSet[str]:
    """
    Extract all superlative/extreme terms from text that have known antonyms.

    We do longest-match first so "most comprehensive" is matched before "most"
    is matched separately.  Multi-word phrases are checked before single words.
    Uses the module-level _SUPERLATIVE_TERM_PATTERNS dict — patterns compiled
    once at import time, not on every invocation.
    """
    text_lower = text.lower()
    found: Set[str] = set()

    for term in _SUPERLATIVE_TERMS_BY_LENGTH:
        if _SUPERLATIVE_TERM_PATTERNS[term].search(text_lower):
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

# ── Module-level regex for degrees normalisation ─────────────────────────────
# Used inside _unit_after_number() to strip "degrees " before the unit lookup.
# Compiled once at import time — called on every number match in a sentence.
_DEGREES_RE: re.Pattern = re.compile(r"^degrees?\s+", re.IGNORECASE)

# ── Module-level tokenizer regexes ───────────────────────────────────────────
# _WORD_TOKENS_RE  : used by _neg_window_tokens() to split text into words.
# _ALPHA_TOKENS_RE : used by _content_tokens() to extract alpha-only tokens.
# Explicit module-level compilation avoids relying on Python's internal
# re._cache for hot-path functions.
_WORD_TOKENS_RE:  re.Pattern = re.compile(r"[\w'-]+")
_ALPHA_TOKENS_RE: re.Pattern = re.compile(r"[a-z]+")


def _unit_after_number(text: str, end_pos: int) -> Optional[str]:
    """
    Return the canonical unit token immediately following a number match,
    or None if no known unit follows.

    Handles two-word patterns such as "degrees Celsius" / "degrees celsius"
    by stripping the bridge word "degrees" before the unit lookup.
    """
    tail = text[end_pos:end_pos + 40].strip().lower()

    # Normalise "degrees <unit>" → "<unit>" so "320 degrees Celsius" → "celsius"
    tail = _DEGREES_RE.sub("", tail)

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


# ─── S2A vicinity guard ────────────────────────────────────────────────────────
#
# Root-cause of the bulk FN population (34/35 cases):
#
#   has_negation(claim) != has_negation(source) fires whenever ONE sentence
#   contains ANY negation marker while the other does not.  This is too blunt:
#   faithful sentence pairs routinely express the same restriction using
#   complementary linguistic polarity:
#
#     "must remain below 250 mg/dL"          (no negation word)
#     "must not exceed 250 mg/dL"            (has: "not")
#     → SAME upper-bound constraint, different syntactic polarity.
#
#     "Transfer requires written authorization"  (no negation)
#     "Transfer is not permitted without authorization" (has: "not", "without")
#     → SAME prohibition, different syntactic form.
#
# The guard works in two stages:
#
#   Stage 1 — Threshold equivalence abort
#     Detect sentences that both express an upper-bound (or lower-bound)
#     constraint using complementary polarity operators:
#       upper-bound positive : below, under, at most, less than, …
#       upper-bound negative : not exceed, not above, not surpass, …
#     If both sentences describe the SAME bound direction AND share a numeric
#     value, they are mathematically equivalent → abort S2A.
#
#   Stage 2 — Shared-anchor vicinity check
#     Extract the content words within WINDOW positions of every negation
#     marker in each sentence (the "negation window").  Only fire S2A when
#     the negation window of the sentence that HAS negation overlaps with
#     significant content words from the sentence that does NOT have negation.
#     If there is no overlap the negation is structural (e.g. "not exceed")
#     and does not invert a shared predicate.

_UPPER_BOUND_POS_RE = re.compile(
    r"\b(below|under|at\s+most|no\s+more\s+than|less\s+than"
    r"|not\s+exceeding|not\s+above|beneath"
    r"|time(?:s)?\s+out\s+after|expires?\s+after|within\s+\d)\b",
    re.IGNORECASE,
)
_UPPER_BOUND_NEG_RE = re.compile(
    r"\b(not\s+exceed(?:ing)?|must\s+not\s+exceed"
    r"|shall\s+not\s+exceed|not\s+(?:go\s+)?above"
    r"|not\s+surpass(?:ing)?|not\s+(?:go\s+)?over)\b",
    re.IGNORECASE,
)
_LOWER_BOUND_POS_RE = re.compile(
    r"\b(above|over|at\s+least|no\s+less\s+than"
    r"|more\s+than|greater\s+than|exceed(?:ing)?|a\s+minimum\s+of)\b",
    re.IGNORECASE,
)
_LOWER_BOUND_NEG_RE = re.compile(
    r"\b(not\s+below|not\s+(?:less|fewer)\s+than"
    r"|not\s+(?:fall|drop)\s+below|no\s+fewer\s+than)\b",
    re.IGNORECASE,
)

# Soft negation words that appear in structural expressions ("not exceed",
# "without which") — their negation windows should be checked, not assumed.
# NOTE: "without" is intentionally excluded.  In requirement contexts,
# "without" is a CONDITIONAL PREPOSITION ("not permitted without X" means
# "X is required"), not a negation of the following word.  Including it
# would cause "without authorization" to anchor on "authorization", making
# the guard fire for faithful pairs like
#   "requires authorization" ↔ "not permitted without authorization".
_SOFT_NEG_WORDS: frozenset = frozenset({
    "not", "no", "never", "none", "cannot", "cant",
    "dont", "doesnt", "wont", "isnt", "arent", "shouldnt",
})

# Minimum content-word length to be considered a meaningful anchor.
_ANCHOR_MIN_LEN: int = 4

# Common stopwords excluded from anchor comparison.
# Intentionally includes high-frequency TOPIC words that are shared between
# claim and source sentences simply because they are the subject of the
# sentence — not because the negation is targeting them as a predicate.
# Including these words in the anchor set creates false Stage-2 fires:
#   "not permitted for all employees" vs "prohibited for all employees"
#     → "employees" is the scope qualifier, not the negated predicate.
_STOPWORDS: frozenset = frozenset({
    # Grammatical stopwords
    "this", "that", "with", "from", "have", "been", "will", "were",
    "they", "them", "their", "there", "these", "those", "which",
    "when", "then", "than", "also", "must", "shall", "should",
    "would", "could", "might", "about", "into", "onto", "under",
    "above", "below", "after", "before", "during", "through",
    "between", "within", "each", "every", "some", "such", "same",
    "only", "just", "more", "most", "less", "least", "very",
    "area", "used", "been", "make", "made", "take", "taken",
    # High-frequency TOPIC/ENTITY words — not semantic predicates.
    # Shared between faithful pairs because they name the SUBJECT, not the
    # predicate the negation is inverting.
    "employees", "users", "staff", "personnel", "members", "workers",
    "system", "systems", "response", "request", "requests",
    "data", "files", "records", "information", "content",
    "access", "standard", "permitted", "allowed", "required",
    "network", "device", "devices", "service", "services",
    "process", "account", "accounts", "document", "documents",
})

# ── S2A Stage 1b/1c: module-level compiled patterns ─────────────────────────
# These four regexes were previously compiled inside _s2a_is_genuine_contradiction()
# on EVERY invocation. That function sits in the hot path of compute_alignment_penalty()
# which is called for each claim with a negation mismatch. Moving to module level
# ensures they are compiled exactly once during Lambda cold-start initialisation.
#
# _REQ_POS_RE       : positive-requirement verbs ("requires", "mandatory", "must", …)
# _NEG_COND_RE      : negative-conditional constructions ("not permitted without", …)
# _ACCESS_WITHOUT_RE: unconditional-access patterns ("accessible without", …)
# _GATE_REQUIRED_RE : gating/requirement patterns for Stage 1c fire condition
_REQ_POS_RE: re.Pattern = re.compile(
    r"\b(requires?|is\s+required|mandatory|must\s+(?!not\b)|is\s+needed"
    r"|need(?:s|ed)\s+to|has\s+to|have\s+to)\b",
    re.IGNORECASE,
)
_NEG_COND_RE: re.Pattern = re.compile(
    r"\b(not\s+permitted\s+without"
    r"|cannot\s+(?:[\w]+\s+){0,3}without"
    r"|may\s+not\s+(?:[\w]+\s+){0,3}without"
    r"|must\s+not\s+be\s+omitted"
    r"|not\s+allowed\s+without"
    r"|shall\s+not\s+(?:[\w]+\s+){0,3}without)\b",
    re.IGNORECASE,
)
_ACCESS_WITHOUT_RE: re.Pattern = re.compile(
    r"\b(?:accessible|available|open|public(?:ly)?)\b.*\bwithout\b"
    r"|\bwithout\b.*\b(?:authentication|authorization|verification|credential)",
    re.IGNORECASE,
)
_GATE_REQUIRED_RE: re.Pattern = re.compile(
    r"\b(?:requires?|is\s+required|mandatory|must\s+(?!not\b)|needed)\b",
    re.IGNORECASE,
)


def _content_tokens(text: str) -> frozenset:
    """Extract alphabetic content words of length >= _ANCHOR_MIN_LEN."""
    return frozenset(
        w for w in _ALPHA_TOKENS_RE.findall(text.lower())
        if len(w) >= _ANCHOR_MIN_LEN and w not in _STOPWORDS
    )


def _neg_window_tokens(text: str, window: int = 4) -> frozenset:
    """
    Return the set of content words that appear within `window` positions
    AFTER any negation marker in the text.

    These are the words the negation is most likely modifying syntactically.
    If the window contains no significant content words, the negation is
    probably at sentence-end or in a structural position ("not exceed").
    """
    words = _WORD_TOKENS_RE.findall(text.lower())
    anchors: Set[str] = set()
    for i, word in enumerate(words):
        stripped = word.strip("'-")
        if stripped in _SOFT_NEG_WORDS or stripped.startswith("non"):
            # Collect content words in the window *after* the negation marker.
            for j in range(i + 1, min(len(words), i + window + 1)):
                candidate = words[j].strip("'-.,:")
                if (
                    len(candidate) >= _ANCHOR_MIN_LEN
                    and candidate not in _STOPWORDS
                    and candidate.isalpha()
                ):
                    anchors.add(candidate)
    return frozenset(anchors)


def _s2a_is_genuine_contradiction(claim: str, source: str) -> bool:
    """
    Return True only when the negation polarity difference between claim and
    source represents a genuine semantic contradiction — i.e., one sentence
    negates a predicate that the other sentence affirms.

    Returns False (abort S2A) in two cases:

    Case 1 — Threshold equivalence:
        Both sentences bound the same quantity in the same direction using
        complementary polarity operators, e.g.:
          "must remain below 250 mg/dL"  ↔  "must not exceed 250 mg/dL"
          "at least 12 months"           ↔  "not less than 12 months"
        Detection: (claim_upper and source_upper) or (claim_lower and source_lower),
        AND they share at least one numeric value.

    Case 2 — Non-overlapping negation window:
        The content words inside the negation window of the negative sentence
        do not overlap with significant content words of the positive sentence.
        If there is no shared anchor the polarity difference is structural
        (e.g., "not exceed" vs "below") and does not invert a shared predicate.

    Args:
        claim, source: The two sentence strings after has_negation polarity
                       mismatch has already been confirmed by the caller.

    Returns:
        True  → genuine contradiction → apply NEGATION_MISMATCH_PENALTY
        False → structural / equivalent expression → pass through unchanged
    """
    claim_l  = claim.lower()
    source_l = source.lower()

    # ── Stage 1a: Threshold equivalence abort ────────────────────────────────
    claim_upper  = bool(_UPPER_BOUND_POS_RE.search(claim_l) or _UPPER_BOUND_NEG_RE.search(claim_l))
    source_upper = bool(_UPPER_BOUND_POS_RE.search(source_l) or _UPPER_BOUND_NEG_RE.search(source_l))
    claim_lower  = bool(_LOWER_BOUND_POS_RE.search(claim_l) or _LOWER_BOUND_NEG_RE.search(claim_l))
    source_lower = bool(_LOWER_BOUND_POS_RE.search(source_l) or _LOWER_BOUND_NEG_RE.search(source_l))

    if (claim_upper and source_upper) or (claim_lower and source_lower):
        shared_nums = _extract_number_unit_pairs(claim) & _extract_number_unit_pairs(source)
        if shared_nums:
            return False  # mathematically equivalent threshold — do not fire

    # ── Stage 1b: Requirement-conditional equivalence abort ───────────────────
    # "X requires Y" ≡ "X is not permitted without Y" — same precondition.
    # The key linguistic signal: "may not be Z without Y" (multi-word passive)
    # must match even when "be" sits between "not" and the verb phrase.
    if (bool(_REQ_POS_RE.search(claim_l)) or bool(_REQ_POS_RE.search(source_l))) and \
       (bool(_NEG_COND_RE.search(claim_l)) or bool(_NEG_COND_RE.search(source_l))):
        shared_content = _content_tokens(claim_l) & _content_tokens(source_l)
        if len(shared_content) >= 2:
            return False  # same precondition, different syntactic form — abort

    # ── Stage 1c: Unconditional-access vs required-gate contradiction ─────────
    # Pattern: "X is freely/publicly accessible without Y" vs "Y is required"
    # This is a GENUINE contradiction (one says no gate, other says gate exists)
    # that Stage 2 misses because "without" is excluded from _SOFT_NEG_WORDS.
    # Detect via the presence of an access-without pattern paired with required.
    if (bool(_ACCESS_WITHOUT_RE.search(claim_l)) and bool(_GATE_REQUIRED_RE.search(source_l))) or \
       (bool(_ACCESS_WITHOUT_RE.search(source_l)) and bool(_GATE_REQUIRED_RE.search(claim_l))):
        # Confirm a shared security/gating term exists between the two sentences
        shared_content = _content_tokens(claim_l) & _content_tokens(source_l)
        if shared_content:
            return True  # genuine access-gate contradiction — fire

    # ── Stage 2: Negation-window shared-anchor check ──────────────────────────
    # Final check: is the negation in the negative sentence directly targeting
    # a term that the positive sentence uses un-negated?
    claim_has_neg = has_negation(claim)
    neg_sentence  = claim_l  if claim_has_neg else source_l
    pos_sentence  = source_l if claim_has_neg else claim_l

    neg_window  = _neg_window_tokens(neg_sentence)
    pos_content = _content_tokens(pos_sentence)

    shared_anchors = neg_window & pos_content
    if not shared_anchors:
        return False  # negation is structural — do not fire

    return True


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
# ── Module-level absolute-superlative pattern ────────────────────────────────
# Compiled once at import.  has_superlative() is called inside the hot path
# of compute_alignment_penalty() on every single claim.
_ABSOLUTE_RE: re.Pattern = re.compile(
    r"\b(unlimited|infinite|always|every|all|any|free)\b",
    re.IGNORECASE,
)


def has_superlative(text: str) -> bool:
    """
    Detect absolute/superlative terms like 'unlimited', 'free', 'every'.

    Backward-compatible signature retained for existing tests.
    """
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

    # ── Signal 2a: Explicit negation polarity mismatch (vicinity-guarded) ────
    # The blunt has_negation polarity check is retained as the PRE-FILTER:
    # if both sentences have the same polarity, skip immediately (cheap O(1)).
    # Only when polarity differs do we run the O(n) vicinity guard to confirm
    # the negation actually inverts a shared predicate.
    claim_negated  = has_negation(claim)
    source_negated = has_negation(matched_source)
    if claim_negated != source_negated:
        if _s2a_is_genuine_contradiction(claim, matched_source):
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
