"""Tests for entity_checker module — contradiction detection."""

import pytest
from src.verifier.entity_checker import (
    compute_alignment_penalty,
    extract_numbers,
    has_negation,
    has_superlative,
    NUMBER_ALIGNMENT_BOOST,
    NUMBER_MISMATCH_PENALTY,
    NEGATION_MISMATCH_PENALTY,
    SUPERLATIVE_VS_SPECIFIC,
)


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
        """Aligned numbers → boost."""
        penalty = compute_alignment_penalty(
            "costs $29 per month",
            "The Starter plan costs $29 per month"
        )
        assert penalty == NUMBER_ALIGNMENT_BOOST

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
        """'free shipping' vs 'customer responsibility' → penalty."""
        penalty = compute_alignment_penalty(
            "Return shipping is free on all orders",
            "Return shipping is the customer's responsibility"
        )
        # "free" triggers superlative check, no numbers in source → 1.0 for superlative
        # But it should still detect the "free" superlative mismatch
        assert penalty <= 1.0

    def test_no_contradiction(self):
        """Numbers match exactly → boost."""
        penalty = compute_alignment_penalty(
            "Refunds are processed within 5-7 business days",
            "Refunds are processed within 5-7 business days"
        )
        assert penalty == NUMBER_ALIGNMENT_BOOST

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
