"""
McNemar's Test for paired classifier comparison.

Implements a dependency-free McNemar's test to prove that TruthLayer's
dual-signal architecture (embedding cosine similarity + deterministic
entity contradiction engine) is statistically superior to a cosine-only
baseline classifier on the 300-case adversarial benchmark.

Background
----------
McNemar's test evaluates two binary classifiers on the **same** labelled
dataset by focusing on the discordant pairs — cases where one classifier
is correct and the other is not.  It does NOT require the classifiers to
have the same overall accuracy; it specifically tests whether the
disagreement is symmetric.

Contingency table (N = 300):
                         Baseline correct  |  Baseline wrong
  Dual-signal correct  |        a         |        b
  Dual-signal wrong    |        c         |        d

  a: Both correct (concordant — not relevant to the test)
  b: Dual-signal correct, baseline wrong  (our improvement)
  c: Baseline correct, dual-signal wrong  (our regression)
  d: Both wrong (concordant — not relevant to the test)

Test statistic (continuity-corrected):
    χ² = (|b - c| - 1)² / (b + c)

p-value:
    P(χ²₁ > observed_χ²)  under H₀: b == c

    Computed from the chi-squared distribution with df=1, which equals
    the squared standard normal:  χ²(1) = Z²  where Z ~ N(0,1).
    → p = P(χ²₁ > x) = erfc(√(x/2))  [from math module, zero deps]

Critical values (χ²₁, α):
    α = 0.05:  χ² > 3.841   (standard significance threshold)
    α = 0.01:  χ² > 6.635
    α = 0.001: χ² > 10.828

Interpretation (for TruthLayer):
    H₀ (null):       The dual-signal and cosine-only classifiers make
                     the same number of errors — b == c.
    H₁ (alternate): The dual-signal system makes fewer errors — b > c,
                     i.e., it fixes more cases than it breaks.

    Rejection of H₀ at α = 0.05 proves statistically significant
    improvement.  A p-value < 0.001 proves extreme significance.

Design constraints
------------------
- Zero external dependencies (stdlib math only)
- Pure functions: no global state, no side effects
- Full audit trail: McnemarResult exposes all intermediate quantities
- Yates' continuity correction applied by default (conservative)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1  Result type
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class McnemarResult:
    """
    Immutable result of a McNemar's test.

    Fields
    ------
    chi2_statistic    : The test statistic χ² (continuity-corrected by default).
    p_value           : Two-tailed p-value under H₀: b == c.
    n_b               : Discordant count where dual-signal is correct, baseline wrong.
    n_c               : Discordant count where baseline is correct, dual-signal wrong.
    n_discordant      : Total discordant pairs (n_b + n_c).
    n_total           : Total number of cases evaluated.
    n_a               : Both classifiers correct (concordant).
    n_d               : Both classifiers wrong (concordant).
    continuity_corrected : Whether Yates' continuity correction was applied.
    alpha             : Significance level used for is_significant.
    is_significant    : True if p_value < alpha.
    interpretation    : Human-readable conclusion string.
    """

    chi2_statistic:      float
    p_value:             float
    n_b:                 int     # dual correct, baseline wrong
    n_c:                 int     # baseline correct, dual wrong
    n_discordant:        int     # n_b + n_c
    n_total:             int
    n_a:                 int     # both correct
    n_d:                 int     # both wrong
    continuity_corrected: bool
    alpha:               float
    is_significant:      bool
    interpretation:      str

    def to_dict(self) -> dict:
        """Return all fields as a plain dict for JSON serialisation."""
        return {
            "chi2_statistic":       round(self.chi2_statistic, 6),
            "p_value":              self.p_value,
            "p_value_scientific":   f"{self.p_value:.4e}",
            "n_b":                  self.n_b,
            "n_c":                  self.n_c,
            "n_discordant":         self.n_discordant,
            "n_total":              self.n_total,
            "n_a":                  self.n_a,
            "n_d":                  self.n_d,
            "continuity_corrected": self.continuity_corrected,
            "alpha":                self.alpha,
            "is_significant":       self.is_significant,
            "interpretation":       self.interpretation,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2  Mathematical primitives (stdlib only)
# ═══════════════════════════════════════════════════════════════════════════════

def _chi2_p_value_df1(chi2: float) -> float:
    """
    Compute the right-tail p-value of a chi-squared statistic with df=1.

    For df=1, χ² = Z² where Z ~ N(0,1), so:
        P(χ²₁ > x) = P(|Z| > √x) = 2·(1 - Φ(√x))

    Using the complementary error function identity:
        1 - Φ(z) = erfc(z / √2) / 2
    Therefore:
        P(χ²₁ > x) = erfc(√x / √2) = erfc(√(x / 2))

    Derivation verified against R's pchisq(x, df=1, lower.tail=FALSE):
        x=3.841  → p ≈ 0.0500  (α=0.05  critical value)
        x=6.635  → p ≈ 0.0100  (α=0.01  critical value)
        x=10.828 → p ≈ 0.0010  (α=0.001 critical value)

    Args:
        chi2: Non-negative chi-squared statistic.

    Returns:
        p-value in (0.0, 1.0].

    Raises:
        ValueError: If chi2 is negative.
    """
    if chi2 < 0.0:
        raise ValueError(f"chi2 must be non-negative, got {chi2!r}")
    if chi2 == 0.0:
        return 1.0
    return math.erfc(math.sqrt(chi2 / 2.0))


def _build_interpretation(
    n_b: int,
    n_c: int,
    chi2: float,
    p_value: float,
    alpha: float,
    n_total: int,
) -> str:
    """
    Compose a one-paragraph human-readable interpretation of the test result.

    Used for reports, BENCHMARK.md, and the competition article.
    """
    direction = "improvement" if n_b > n_c else "regression"
    significance = "statistically significant" if p_value < alpha else "not statistically significant"
    alpha_pct = f"{alpha * 100:.0f}%"

    lines = [
        f"McNemar's test on {n_total} paired cases:",
        f"  b={n_b} (dual-signal correct, cosine-only wrong)",
        f"  c={n_c} (cosine-only correct, dual-signal wrong)",
        f"  χ²={chi2:.4f}, p={p_value:.4e}",
        f"Result: {significance} at α={alpha_pct}.",
    ]

    if p_value < alpha:
        if n_b > n_c:
            lines.append(
                f"The dual-signal architecture demonstrates statistically "
                f"significant {direction} over the cosine-only baseline "
                f"(p={p_value:.4e} < {alpha})."
            )
        else:
            lines.append(
                f"The dual-signal architecture shows statistically "
                f"significant {direction} relative to the cosine-only "
                f"baseline (p={p_value:.4e} < {alpha})."
            )
    else:
        lines.append(
            f"Insufficient evidence to reject H₀ at α={alpha_pct} "
            f"(p={p_value:.4e} >= {alpha})."
        )

    return "  ".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3  Core test function
# ═══════════════════════════════════════════════════════════════════════════════

def mcnemar_test(
    system_correct:   Sequence[bool],
    baseline_correct: Sequence[bool],
    alpha:            float = 0.05,
    continuity_correction: bool = True,
) -> McnemarResult:
    """
    Perform McNemar's test for paired binary classifiers.

    Args:
        system_correct:   Boolean sequence — True if the NEW system (dual-signal)
                          is correct on each case.
        baseline_correct: Boolean sequence — True if the BASELINE system
                          (cosine-only) is correct on each case.
                          Must be the same length as system_correct.
        alpha:            Significance level for is_significant.  Default 0.05.
        continuity_correction: If True (default), apply Yates' continuity
                          correction: χ² = (|b - c| - 1)² / (b + c).
                          If False: χ² = (b - c)² / (b + c).
                          Correction is recommended when n_discordant < 25.

    Returns:
        McnemarResult with the full audit trail.

    Raises:
        ValueError: If inputs have different lengths or are empty.
        ValueError: If alpha is not in (0, 1).
        ZeroDivisionError: Cannot be raised — guarded internally.
    """
    if len(system_correct) != len(baseline_correct):
        raise ValueError(
            f"system_correct and baseline_correct must have equal length, "
            f"got {len(system_correct)} and {len(baseline_correct)}"
        )
    if not system_correct:
        raise ValueError("Cannot run McNemar's test on empty sequences")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha!r}")

    n_total = len(system_correct)

    # Build the 2x2 contingency table.
    n_a = n_b = n_c = n_d = 0
    for s, b in zip(system_correct, baseline_correct):
        if s and b:
            n_a += 1          # both correct
        elif s and not b:
            n_b += 1          # dual correct, baseline wrong
        elif not s and b:
            n_c += 1          # baseline correct, dual wrong
        else:
            n_d += 1          # both wrong

    n_discordant = n_b + n_c

    # Edge case: no discordant pairs — classifiers agree on every case.
    if n_discordant == 0:
        return McnemarResult(
            chi2_statistic      = 0.0,
            p_value             = 1.0,
            n_b                 = n_b,
            n_c                 = n_c,
            n_discordant        = 0,
            n_total             = n_total,
            n_a                 = n_a,
            n_d                 = n_d,
            continuity_corrected= continuity_correction,
            alpha               = alpha,
            is_significant      = False,
            interpretation      = (
                f"No discordant pairs found across {n_total} cases. "
                "The two classifiers are identical on this dataset."
            ),
        )

    # Compute McNemar's chi-squared statistic.
    if continuity_correction:
        # Yates' continuity correction (conservative, preferred when n < 25).
        raw_diff = abs(n_b - n_c) - 1.0
        # Guard: if |b-c| == 0 with correction, chi2 = 0 (p = 1.0).
        if raw_diff < 0.0:
            raw_diff = 0.0
        chi2 = (raw_diff ** 2) / n_discordant
    else:
        chi2 = ((n_b - n_c) ** 2) / n_discordant

    p_value = _chi2_p_value_df1(chi2)
    is_sig  = p_value < alpha

    interpretation = _build_interpretation(
        n_b       = n_b,
        n_c       = n_c,
        chi2      = chi2,
        p_value   = p_value,
        alpha     = alpha,
        n_total   = n_total,
    )

    return McnemarResult(
        chi2_statistic      = chi2,
        p_value             = p_value,
        n_b                 = n_b,
        n_c                 = n_c,
        n_discordant        = n_discordant,
        n_total             = n_total,
        n_a                 = n_a,
        n_d                 = n_d,
        continuity_corrected= continuity_correction,
        alpha               = alpha,
        is_significant      = is_sig,
        interpretation      = interpretation,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4  Convenience: build correctness vectors from entity-checker output
# ═══════════════════════════════════════════════════════════════════════════════

def classify_with_penalty(
    similarity_score: float,
    alignment_penalty: float,
    verified_threshold:   float = 0.65,
    uncertain_threshold:  float = 0.40,
) -> str:
    """
    Apply the dual-signal classification rule used in production.

    Mirrors ConfidenceScorer.classify_claim() but takes the two raw signals
    as separate inputs (before multiplication) to allow independent inspection.

    Args:
        similarity_score:   Raw cosine similarity in [0, 1].
        alignment_penalty:  Penalty from compute_alignment_penalty(), in (0, 1].
        verified_threshold: Score >= this → VERIFIED.  Default 0.65.
        uncertain_threshold: Score >= this → UNCERTAIN.  Default 0.40.

    Returns:
        "VERIFIED" | "UNCERTAIN" | "UNSUPPORTED"
    """
    adjusted = similarity_score * alignment_penalty
    if adjusted >= verified_threshold:
        return "VERIFIED"
    if adjusted >= uncertain_threshold:
        return "UNCERTAIN"
    return "UNSUPPORTED"


def classify_cosine_only(
    similarity_score:     float,
    verified_threshold:   float = 0.65,
    uncertain_threshold:  float = 0.40,
) -> str:
    """
    Cosine-only baseline: classify using raw similarity with no entity check.

    This is the baseline against which McNemar's test proves our superiority.
    Identical to classify_with_penalty() but always uses penalty=1.0.

    Args:
        similarity_score:   Raw cosine similarity in [0, 1].
        verified_threshold: Score >= this → VERIFIED.  Default 0.65.
        uncertain_threshold: Score >= this → UNCERTAIN.  Default 0.40.

    Returns:
        "VERIFIED" | "UNCERTAIN" | "UNSUPPORTED"
    """
    return classify_with_penalty(
        similarity_score  = similarity_score,
        alignment_penalty = 1.0,
        verified_threshold   = verified_threshold,
        uncertain_threshold  = uncertain_threshold,
    )
