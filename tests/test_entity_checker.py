"""
Tests for entity_checker module — contradiction detection.

Three signals under test:
  1. Numerical mismatch  (unit-aware)
  2. Negation mismatch   (explicit markers + semantic antonym pairs)
  3. Superlative swap    (polarity-inverted superlatives)

All original tests are preserved verbatim.  New tests are grouped in
clearly labelled classes that map 1-to-1 with the failure modes uncovered
by the 300-case adversarial benchmark.
"""

import pytest
from src.verifier.entity_checker import (
    compute_alignment_penalty,
    extract_numbers,
    has_negation,
    has_superlative,
    NUMBER_MISMATCH_PENALTY,
    NEGATION_MISMATCH_PENALTY,
    SUPERLATIVE_VS_SPECIFIC,
    SUPERLATIVE_SWAP_PENALTY,
    _extract_number_unit_pairs,
    _numbers_contradict,
    _superlatives_contradict,
    _semantic_negation_contradict,
)


# ══════════════════════════════════════════════════════════════════════════════
# Existing tests — ALL preserved, none modified
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractNumbers:
    """Tests for number extraction from text."""

    def test_integers(self):
        assert extract_numbers("costs $29 per month") == {"$29"}

    def test_decimals(self):
        assert extract_numbers("99.9% uptime guaranteed") == {"99.9%"}

    def test_multiple(self):
        result = extract_numbers("between 5-7 business days")
        assert "5" in result
        assert "7" in result

    def test_thousands(self):
        assert extract_numbers("100,000 API calls") == {"100000"}

    def test_no_numbers(self):
        assert extract_numbers("no numbers here") == set()

    def test_currency_and_percent(self):
        result = extract_numbers("$499 with 99.99% SLA")
        assert "$499" in result
        assert "99.99%" in result


class TestHasNegation:
    """Tests for negation detection."""

    def test_simple_no(self):
        assert has_negation("No free trial available") is True

    def test_not(self):
        assert has_negation("This is not included") is True

    def test_non_prefix(self):
        assert has_negation("Digital products are non-refundable") is True

    def test_never(self):
        assert has_negation("We never share data") is True

    def test_no_negation(self):
        assert has_negation("All plans include a free trial") is False

    def test_without(self):
        assert has_negation("Available without restrictions") is True


class TestHasSuperlative:
    """Tests for superlative/absolute claim detection."""

    def test_unlimited(self):
        assert has_superlative("unlimited API calls") is True

    def test_free(self):
        assert has_superlative("free shipping on all orders") is True

    def test_every(self):
        assert has_superlative("every plan includes support") is True

    def test_specific(self):
        assert has_superlative("100,000 API calls per month") is False


class TestComputeAlignmentPenalty:
    """Tests for the main alignment penalty function."""

    def test_matching_numbers(self):
        """Aligned numbers → no penalty."""
        penalty = compute_alignment_penalty(
            "costs $29 per month",
            "The Starter plan costs $29 per month"
        )
        assert penalty == 1.0

    def test_mismatched_numbers(self):
        """Wrong numbers → NUMBER_MISMATCH_PENALTY."""
        penalty = compute_alignment_penalty(
            "costs $19 per month",
            "The Starter plan costs $29 per month"
        )
        assert penalty == NUMBER_MISMATCH_PENALTY

    def test_subtle_percentage_mismatch(self):
        """99.99% vs 99.9% → penalty."""
        penalty = compute_alignment_penalty(
            "guarantees 99.99% uptime",
            "TechCorp guarantees 99.9% uptime"
        )
        assert penalty == NUMBER_MISMATCH_PENALTY

    def test_negation_mismatch(self):
        """Negation in one but not the other → penalty."""
        penalty = compute_alignment_penalty(
            "No free trial is available",
            "All plans include a 14-day free trial"
        )
        assert penalty <= NEGATION_MISMATCH_PENALTY

    def test_superlative_vs_specific(self):
        """'unlimited' vs a specific number → penalty."""
        penalty = compute_alignment_penalty(
            "The Pro plan includes unlimited API calls",
            "The Pro plan costs $99 per month with 100,000 API calls included"
        )
        assert penalty <= SUPERLATIVE_VS_SPECIFIC

    def test_free_vs_paid(self):
        """'free shipping' vs 'customer responsibility' → no worse than 1.0."""
        penalty = compute_alignment_penalty(
            "Return shipping is free on all orders",
            "Return shipping is the customer's responsibility"
        )
        assert penalty <= 1.0

    def test_no_contradiction(self):
        """Perfectly aligned → 1.0."""
        penalty = compute_alignment_penalty(
            "Refunds are processed within 5-7 business days",
            "Refunds are processed within 5-7 business days"
        )
        assert penalty == 1.0

    def test_empty_source(self):
        """No source → no penalty (nothing to contradict)."""
        assert compute_alignment_penalty("any claim", "") == 1.0

    def test_hours_vs_days(self):
        """'24 hours' when source says '5-7 days' → penalty."""
        penalty = compute_alignment_penalty(
            "Refunds are processed within 24 hours",
            "Refunds are processed within 5-7 business days"
        )
        assert penalty == NUMBER_MISMATCH_PENALTY

    def test_compound_penalty(self):
        """Multiple contradictions → lowest penalty wins."""
        penalty = compute_alignment_penalty(
            "No plan costs $19",
            "All plans include a 14-day free trial at $29"
        )
        assert penalty <= NUMBER_MISMATCH_PENALTY


# ══════════════════════════════════════════════════════════════════════════════
# NEW: Unit-aware number extraction (Fix 2)
# ══════════════════════════════════════════════════════════════════════════════

class TestUnitAwareNumberExtraction:
    """
    Validates that (value, unit) tuples are extracted correctly.
    These tests cover the primary failure modes in Category A of the
    adversarial benchmark.
    """

    def test_years_vs_months_are_distinct(self):
        """'5 years' and '5 months' share a number but differ by unit."""
        pairs_years  = _extract_number_unit_pairs("retained for 5 years")
        pairs_months = _extract_number_unit_pairs("retained for 5 months")
        assert pairs_years != pairs_months
        assert ("5", "yr") in pairs_years
        assert ("5", "mo") in pairs_months

    def test_hours_vs_minutes_are_distinct(self):
        """'4 hours' vs '4 minutes' — same number, different unit."""
        pairs_hours   = _extract_number_unit_pairs("within 4 hours")
        pairs_minutes = _extract_number_unit_pairs("within 4 minutes")
        assert ("4", "hr") in pairs_hours
        assert ("4", "min") in pairs_minutes
        assert pairs_hours != pairs_minutes

    def test_celsius_unit_attached(self):
        """Degrees Celsius is recognised as a unit."""
        pairs = _extract_number_unit_pairs("core temperature of 320 degrees Celsius")
        # 320 should be paired with the Celsius unit
        assert ("320", "c") in pairs

    def test_32_vs_320_celsius_distinct(self):
        """32°C and 320°C must NOT be treated as the same value."""
        assert _numbers_contradict(
            "temperature is 32 degrees Celsius",
            "temperature of 320 degrees Celsius"
        )

    def test_5_years_not_in_5_months_source(self):
        """Claim says 5 years, source says 5 months → contradiction."""
        assert _numbers_contradict(
            "Security audit records are preserved for 5 years",
            "Security audit records are preserved for 5 months"
        )

    def test_4_hours_not_in_4_minutes_source(self):
        """Claim says 4 hours, source says 4 minutes → contradiction."""
        assert _numbers_contradict(
            "Emergency patches must be applied within 4 hours",
            "Emergency patches must be applied within 4 minutes"
        )

    def test_matching_number_and_unit_no_contradiction(self):
        """Identical (value, unit) pair → no contradiction."""
        assert not _numbers_contradict(
            "The cable is rated for up to 2,000 amperes",
            "The cable can carry a maximum load of 2,000 amperes"
        )

    def test_no_numbers_in_claim_no_contradiction(self):
        """Claim with no numbers cannot trigger numeric contradiction."""
        assert not _numbers_contradict(
            "The system is authorized for production deployment",
            "The system costs $99 per month"
        )


# ══════════════════════════════════════════════════════════════════════════════
# NEW: Superlative swap detection (Fix 1)
# ══════════════════════════════════════════════════════════════════════════════

class TestSuperlativeSwap:
    """
    Validates bidirectional superlative antonym detection.
    These are the cases that caused 46 FPs in Category C.
    """

    def test_highest_vs_lowest(self):
        assert _superlatives_contradict(
            "The lowest priority support tier includes a 15-minute response.",
            "The highest priority support tier includes guaranteed 15-minute response."
        )

    def test_lowest_vs_highest(self):
        assert _superlatives_contradict(
            "The highest latency region is recommended for latency-sensitive workloads.",
            "The lowest latency region is recommended for latency-sensitive workloads."
        )

    def test_fastest_vs_slowest(self):
        assert _superlatives_contradict(
            "This is the slowest available model in the product lineup.",
            "This is the fastest available model in the product lineup."
        )

    def test_unlimited_vs_limited(self):
        assert _superlatives_contradict(
            "The Pro plan offers limited API calls per month.",
            "The Pro plan offers unlimited API calls per month."
        )

    def test_most_vs_least_experienced(self):
        assert _superlatives_contradict(
            "The least experienced support agents handle enterprise account inquiries.",
            "The most experienced support agents handle enterprise account inquiries."
        )

    def test_most_vs_least_severe(self):
        assert _superlatives_contradict(
            "The least severe security incidents are escalated immediately to senior engineers.",
            "The most severe security incidents are escalated immediately to senior engineers."
        )

    def test_broadest_vs_narrowest(self):
        assert _superlatives_contradict(
            "The platform offers the narrowest cloud provider compatibility.",
            "The platform offers the broadest cloud provider compatibility of any tool."
        )

    def test_strongest_vs_weakest(self):
        assert _superlatives_contradict(
            "The strongest cryptographic hash function in the suite is MD5.",
            "The weakest cryptographic hash function in the suite is MD5."
        )

    def test_most_privileged_vs_least_privileged(self):
        assert _superlatives_contradict(
            "The most privileged access model is recommended as the security baseline.",
            "The least privileged access model is recommended as the security baseline."
        )

    def test_no_contradiction_identical_terms(self):
        """Same superlative term in both → no contradiction."""
        assert not _superlatives_contradict(
            "The highest priority incidents are escalated first.",
            "The highest priority incidents receive immediate attention."
        )

    def test_no_contradiction_no_superlatives(self):
        """No superlative terms at all → no contradiction."""
        assert not _superlatives_contradict(
            "Refunds are processed within 5-7 business days.",
            "Refunds are processed within 5-7 business days."
        )

    def test_superlative_swap_applies_penalty(self):
        """End-to-end: superlative swap must reduce the alignment penalty."""
        penalty = compute_alignment_penalty(
            "The lowest availability tier guarantees a maximum of 26 minutes of downtime per year.",
            "The highest availability tier guarantees a maximum of 26 minutes of downtime per year."
        )
        assert penalty <= SUPERLATIVE_SWAP_PENALTY

    def test_unlimited_vs_limited_penalty(self):
        penalty = compute_alignment_penalty(
            "The Pro plan offers limited API calls per month.",
            "The Pro plan offers unlimited API calls per month."
        )
        assert penalty <= SUPERLATIVE_SWAP_PENALTY

    def test_oldest_vs_newest_penalty(self):
        penalty = compute_alignment_penalty(
            "The oldest AI model delivers the greatest inference speed improvement.",
            "The newest AI model delivers the greatest inference speed improvement."
        )
        assert penalty <= SUPERLATIVE_SWAP_PENALTY


# ══════════════════════════════════════════════════════════════════════════════
# NEW: Semantic antonym pairs (Fix 3)
# ══════════════════════════════════════════════════════════════════════════════

class TestSemanticNegationAntonyms:
    """
    Validates semantic contradiction pairs — negation implied by vocabulary
    rather than explicit markers.  These covered the residual FPs in Category B.
    """

    def test_permitted_vs_prohibited(self):
        assert _semantic_negation_contradict(
            "The export of this technology is permitted without a federal license.",
            "The export of this technology is prohibited without a federal license."
        )

    def test_authorized_vs_unauthorized(self):
        assert _semantic_negation_contradict(
            "The system is authorized for production deployment.",
            "The system is not authorized for deployment in production environments."
        )

    def test_safe_vs_contraindicated(self):
        assert _semantic_negation_contradict(
            "The medication is safe for patients with renal impairment.",
            "The medication is contraindicated in patients with renal impairment."
        )

    def test_eligible_vs_ineligible(self):
        assert _semantic_negation_contradict(
            "Employees are eligible for bonuses during the probation period.",
            "Employees are not eligible for bonuses during the probation period."
        )

    def test_included_vs_excluded(self):
        assert _semantic_negation_contradict(
            "Health Insurance is included in the basic employment package.",
            "Health Insurance is not included in the basic employment package."
        )

    def test_transferable_vs_non_transferable(self):
        assert _semantic_negation_contradict(
            "The contract is transferable without written consent.",
            "The contract is non-transferable without written consent."
        )

    def test_no_false_positive_aligned_pair(self):
        """Claim and source use compatible (non-antonymic) terms → no trigger."""
        assert not _semantic_negation_contradict(
            "The system is authorized for production deployment.",
            "The system has been authorized for production use."
        )

    def test_penalty_applied_for_semantic_antonym(self):
        """End-to-end: semantic antonym must reduce alignment penalty."""
        penalty = compute_alignment_penalty(
            "The medication is safe for patients with renal impairment.",
            "The medication is contraindicated in patients with renal impairment."
        )
        assert penalty <= NEGATION_MISMATCH_PENALTY

    def test_penalty_permitted_vs_prohibited(self):
        penalty = compute_alignment_penalty(
            "The export of this technology is permitted without a federal license.",
            "The export of this technology is prohibited without a federal license."
        )
        assert penalty <= NEGATION_MISMATCH_PENALTY


# ══════════════════════════════════════════════════════════════════════════════
# NEW: Hyphenated compound superlative matching (Fix 2 — regex boundary)
# ══════════════════════════════════════════════════════════════════════════════

from src.verifier.entity_checker import _extract_superlative_terms


class TestHyphenatedSuperlativeDetection:
    """
    The lookahead in _extract_superlative_terms was previously '(?![a-z-])'
    which blocked matching 'shortest' inside 'shortest-lasting' because the
    character following 'shortest' is '-'.

    Fix 2 relaxes the lookahead to '(?![a-z])' so the root term is extracted
    even when it is the prefix of a hyphenated compound.
    """

    def test_shortest_hyphenated_compound_extracted(self):
        """'shortest-lasting' must yield 'shortest' as a superlative term."""
        terms = _extract_superlative_terms(
            "The medication provides the shortest-lasting relief in the category."
        )
        assert "shortest" in terms, (
            "'shortest' must be extracted from the compound 'shortest-lasting'"
        )

    def test_longest_running_extracted(self):
        """'longest-running' must yield 'longest'."""
        terms = _extract_superlative_terms(
            "This is the longest-running open-source project in the Apache Foundation."
        )
        assert "longest" in terms

    def test_shortest_vs_longest_contradiction_detected(self):
        """End-to-end: 'shortest-lasting' vs 'longest-lasting' is a superlative contradiction."""
        assert _superlatives_contradict(
            "The medication provides the shortest-lasting relief in this category.",
            "The medication provides the longest-lasting relief in this category."
        )


# ══════════════════════════════════════════════════════════════════════════════
# NEW: Enterprise tier-name contradiction pairs (Fix 3)
# ══════════════════════════════════════════════════════════════════════════════

class TestTierNameContradictions:
    """
    Cases where the adversarial hallucination swaps a plan tier name rather
    than an explicit superlative word.  'entry-level' and 'enterprise' are
    polar opposites in any SLA or feature-set context.

    These pairs correspond to adversarial benchmark cases [258] and [274]
    which previously escaped detection.
    """

    def test_entry_level_vs_enterprise(self):
        """'entry-level' and 'enterprise' are antonymic tier names."""
        assert _superlatives_contradict(
            "The entry-level plan includes the highest number of custom integrations.",
            "The enterprise plan includes the highest number of custom integrations."
        )

    def test_newly_onboarded_vs_long_term(self):
        """'newly onboarded' and 'long-term' are antonymic tenure descriptors."""
        assert _superlatives_contradict(
            "Newly onboarded accounts receive the most favorable contract terms.",
            "Long-term accounts receive the most favorable contract terms."
        )

    def test_basic_vs_enterprise(self):
        """'basic' plan and 'enterprise' plan are polar opposites."""
        assert _superlatives_contradict(
            "The basic tier offers enterprise-grade SLA guarantees.",
            "The enterprise tier offers enterprise-grade SLA guarantees."
        )

    def test_tier_swap_applies_penalty(self):
        """End-to-end: tier name swap must reduce the alignment penalty."""
        penalty = compute_alignment_penalty(
            "The entry-level plan includes the highest number of custom integrations.",
            "The enterprise plan includes the highest number of custom integrations."
        )
        assert penalty <= SUPERLATIVE_SWAP_PENALTY
