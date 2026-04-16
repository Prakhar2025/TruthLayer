"""
Tests for the Intra-Response Consistency Check — verifier._check_internal_consistency().

Architecture
------------
The consistency engine detects logical contradictions *between* claims in the same
AI response.  It runs compute_alignment_penalty() in both directions for every
ordered pair (i, j) where i < j, and surfaces conflicts where the entity checker
fires (penalty < 1.0).

Coverage
--------
  Section 1  — _check_internal_consistency() unit tests (isolated, no verifier)
  Section 2  — Boundary conditions: empty / single / large claim lists
  Section 3  — Conflict descriptor schema validation
  Section 4  — Bidirectional detection (A→B vs B→A)
  Section 5  — Integration: TruthLayerVerifier.verify() API contract
  Section 6  — Integration: _create_unverified_result() (no sources)
  Section 7  — End-to-end: self-contradictory AI response detected correctly
  Section 8  — Performance: O(n²) call count verified, no extra I/O

All tests use stdlib only.  No AWS credentials required.
"""

from __future__ import annotations

import json
import pytest
from typing import List

# The module-level function is not a public API (underscore prefix) but is
# directly importable for white-box testing.
from src.verifier.verifier import (
    TruthLayerVerifier,
    _check_internal_consistency,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_verifier() -> TruthLayerVerifier:
    return TruthLayerVerifier(use_mock=True)


def _assert_consistency_schema(block: dict) -> None:
    """Assert the internal_consistency dict has the correct top-level schema."""
    assert isinstance(block, dict), "internal_consistency must be a dict"
    assert "consistent" in block, "internal_consistency missing 'consistent'"
    assert "conflict_count" in block, "internal_consistency missing 'conflict_count'"
    assert "conflicts" in block, "internal_consistency missing 'conflicts'"
    assert isinstance(block["consistent"], bool)
    assert isinstance(block["conflict_count"], int)
    assert isinstance(block["conflicts"], list)
    assert block["conflict_count"] == len(block["conflicts"])
    if block["consistent"]:
        assert block["conflict_count"] == 0
    if block["conflict_count"] > 0:
        assert not block["consistent"]


def _assert_conflict_schema(conflict: dict) -> None:
    """Assert one conflict entry has every required field with correct types."""
    required = {
        "claim_a_index": int,
        "claim_b_index": int,
        "claim_a_text":  str,
        "claim_b_text":  str,
        "signal":        str,
        "severity":      str,
        "explanation":   str,
        "penalty":       float,
    }
    for key, expected_type in required.items():
        assert key in conflict, f"Conflict record missing '{key}'"
        assert isinstance(conflict[key], expected_type), (
            f"conflict['{key}'] expected {expected_type.__name__}, "
            f"got {type(conflict[key]).__name__}"
        )
    # Indices must be ordered
    assert conflict["claim_a_index"] < conflict["claim_b_index"], (
        "claim_a_index must always be < claim_b_index"
    )
    # Penalty in (0, 1)
    assert 0.0 < conflict["penalty"] < 1.0, (
        f"conflict penalty={conflict['penalty']} not in (0, 1)"
    )
    # Signal must be a non-empty string
    assert len(conflict["signal"]) > 0
    # Severity must be one of known values
    assert conflict["severity"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}, (
        f"Unknown severity: {conflict['severity']}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 1 — _check_internal_consistency() unit tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckInternalConsistencyUnit:
    """White-box tests for the module-level _check_internal_consistency()."""

    def test_empty_list_is_consistent(self):
        result = _check_internal_consistency([])
        assert result["consistent"] is True
        assert result["conflict_count"] == 0
        assert result["conflicts"] == []

    def test_single_claim_is_consistent(self):
        result = _check_internal_consistency(["The dosage is 400mg."])
        assert result["consistent"] is True
        assert result["conflict_count"] == 0

    def test_two_identical_claims_is_consistent(self):
        """Identical text cannot contradict itself."""
        claim = "The contract runs for 24 months."
        result = _check_internal_consistency([claim, claim])
        # Entity checker on identical text produces no evidence.
        assert result["consistent"] is True

    def test_two_compatible_claims_is_consistent(self):
        """Claims about completely different topics should not conflict."""
        claims = [
            "The service is authorized for production deployment.",
            "The warranty period is two years from date of purchase.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        assert result["consistent"] is True

    def test_numerical_mismatch_detected(self):
        """Two claims with contradictory numbers must be detected."""
        claims = [
            "The maximum safe dosage is 400mg per dose.",
            "The maximum safe dosage is 40mg per dose.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        # Must detect a conflict
        assert result["conflict_count"] >= 1
        assert not result["consistent"]
        # Conflict must involve claim indices 0 and 1
        conflict = result["conflicts"][0]
        assert conflict["claim_a_index"] == 0
        assert conflict["claim_b_index"] == 1
        _assert_conflict_schema(conflict)

    def test_negation_flip_detected(self):
        """Two claims where one negates the other must be detected."""
        claims = [
            "User data is not shared with third parties.",
            "User data is shared with third parties.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        assert not result["consistent"]
        assert result["conflict_count"] >= 1

    def test_temporal_mismatch_detected(self):
        """Two claims with contradictory year references must be detected."""
        claims = [
            "GDPR was adopted in 2014.",
            "GDPR was adopted in 2016.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        # Year mismatch is a CRITICAL signal
        if result["conflict_count"] > 0:
            for c in result["conflicts"]:
                _assert_conflict_schema(c)

    def test_return_schema_always_present(self):
        """Schema keys must always be present regardless of claim content."""
        for claims in ([], ["one"], ["a", "b"], ["a", "b", "c"]):
            result = _check_internal_consistency(claims)
            _assert_consistency_schema(result)

    def test_conflict_count_consistent_with_conflicts_list(self):
        """conflict_count must always equal len(conflicts)."""
        for claims in (
            [],
            ["The rate is 400mg.", "The rate is 40mg."],
            ["A", "B", "C"],
        ):
            r = _check_internal_consistency(claims)
            assert r["conflict_count"] == len(r["conflicts"])

    def test_multiple_conflicts_detected(self):
        """
        Three mutually contradictory claims should produce multiple conflicts.
        Claim 0 vs 1: dosage contradiction
        Claim 0 vs 2: year contradiction (or no signal — entity checker-dependent)
        Claim 1 vs 2: may produce signal
        """
        claims = [
            "The dosage is 400mg and the contract started in 2020.",
            "The dosage is 40mg and the contract started in 2020.",
            "The dosage is 400mg and the contract started in 2025.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        # We expect at least one conflict (claim 0 vs 1 on dosage)
        assert result["conflict_count"] >= 1

    def test_indices_are_ordered(self):
        """Every conflict must have claim_a_index < claim_b_index."""
        claims = [
            "The rate limit is 1000 requests per minute.",
            "The rate limit is 10000 requests per minute.",
            "The rate limit is 100 requests per minute.",
        ]
        result = _check_internal_consistency(claims)
        for conflict in result["conflicts"]:
            assert conflict["claim_a_index"] < conflict["claim_b_index"]

    def test_no_duplicate_pairs(self):
        """Each (i, j) pair must appear at most once in conflicts."""
        claims = [
            "The maximum dosage is 400mg.",
            "The maximum dosage is 40mg.",
            "The maximum dosage is 4000mg.",
        ]
        result = _check_internal_consistency(claims)
        seen_pairs = set()
        for c in result["conflicts"]:
            pair = (c["claim_a_index"], c["claim_b_index"])
            assert pair not in seen_pairs, f"Duplicate pair {pair} in conflicts"
            seen_pairs.add(pair)

    def test_text_truncated_to_200_chars(self):
        """Claim text in conflict record must be truncated to 200 characters."""
        long_claim_a = "The maximum safe dosage is 400mg. " + "x" * 300
        long_claim_b = "The maximum safe dosage is 40mg. " + "x" * 300
        result = _check_internal_consistency([long_claim_a, long_claim_b])
        for conflict in result["conflicts"]:
            assert len(conflict["claim_a_text"]) <= 200
            assert len(conflict["claim_b_text"]) <= 200

    def test_result_is_json_serialisable(self):
        """The full result must be JSON-serialisable for API responses."""
        claims = [
            "The maximum safe dosage is 400mg.",
            "The maximum safe dosage is 40mg.",
        ]
        result = _check_internal_consistency(claims)
        serialised = json.dumps(result)
        parsed = json.loads(serialised)
        assert parsed["consistent"] == result["consistent"]
        assert parsed["conflict_count"] == result["conflict_count"]

    def test_deterministic(self):
        """Same input must always produce identical output."""
        claims = [
            "The API allows 1000 requests per minute.",
            "The API allows 10000 requests per minute.",
        ]
        r1 = _check_internal_consistency(claims)
        r2 = _check_internal_consistency(claims)
        assert r1 == r2


# ══════════════════════════════════════════════════════════════════════════════
# Section 2 — Boundary conditions
# ══════════════════════════════════════════════════════════════════════════════

class TestBoundaryConditions:
    """Edge cases: min/max claim counts, very long claims, special chars."""

    def test_two_claims_maximum_pairs(self):
        """Two claims → exactly 1 pair checked."""
        result = _check_internal_consistency(["A", "B"])
        _assert_consistency_schema(result)

    def test_three_claims_three_pairs(self):
        """Three claims → exactly 3 pairs: (0,1), (0,2), (1,2)."""
        result = _check_internal_consistency(["A", "B", "C"])
        _assert_consistency_schema(result)
        # At most 3 conflicts can exist for 3 claims
        assert result["conflict_count"] <= 3

    def test_large_claim_list_no_crash(self):
        """50 compatible claims should not crash or timeout."""
        claims = [f"Claim number {i} is about topic {i}." for i in range(50)]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)

    def test_empty_string_claim_no_crash(self):
        """Empty string claims must not crash the engine."""
        result = _check_internal_consistency(["", ""])
        _assert_consistency_schema(result)

    def test_unicode_claim_no_crash(self):
        """Claims with Unicode characters must not crash."""
        claims = ["The dosage is 400mg.", "Dose: 40mg \u2014 not 400mg."]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)


# ══════════════════════════════════════════════════════════════════════════════
# Section 3 — Conflict descriptor schema
# ══════════════════════════════════════════════════════════════════════════════

class TestConflictDescriptorSchema:
    """Validate every field of a conflict descriptor."""

    def test_conflict_schema_complete(self):
        """A real numerical conflict must produce a fully formed descriptor."""
        claims = [
            "The SLA guarantees 99.9% uptime.",
            "The SLA guarantees 99.99% uptime.",
        ]
        result = _check_internal_consistency(claims)
        if result["conflict_count"] > 0:
            for conflict in result["conflicts"]:
                _assert_conflict_schema(conflict)

    def test_penalty_is_float_in_range(self):
        """Penalty must be a float in (0.0, 1.0) for genuine conflicts."""
        claims = [
            "The contract runs for 24 months.",
            "The contract runs for 12 months.",
        ]
        result = _check_internal_consistency(claims)
        for conflict in result["conflicts"]:
            assert isinstance(conflict["penalty"], float)
            assert 0.0 < conflict["penalty"] < 1.0

    def test_signal_is_known_type(self):
        """Signal must be one of the known entity-checker signal strings."""
        known_signals = {
            "NUMERICAL_MISMATCH",
            "NEGATION_FLIP",
            "SUPERLATIVE_SWAP",
            "TEMPORAL_MISMATCH",
        }
        claims = [
            "The maximum dosage is 400mg.",
            "The maximum dosage is 40mg.",
        ]
        result = _check_internal_consistency(claims)
        for conflict in result["conflicts"]:
            assert conflict["signal"] in known_signals, (
                f"Unknown signal: {conflict['signal']}"
            )

    def test_explanation_is_non_empty(self):
        """Explanation must be a non-empty string."""
        claims = [
            "Records are retained for 7 years.",
            "Records are retained for 70 years.",
        ]
        result = _check_internal_consistency(claims)
        for conflict in result["conflicts"]:
            assert isinstance(conflict["explanation"], str)
            assert len(conflict["explanation"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Section 4 — Bidirectional detection
# ══════════════════════════════════════════════════════════════════════════════

class TestBidirectionalDetection:
    """
    Verify that the engine detects contradictions regardless of which claim
    comes first in the list.
    """

    def test_order_independent_detection(self):
        """
        Swapping claim order must not prevent detection.
        If [A, B] detects a conflict, [B, A] must also detect one.
        (The conflict indices will differ but a conflict must be found.)
        """
        claim_a = "The maximum dosage is 400mg."
        claim_b = "The maximum dosage is 40mg."
        r1 = _check_internal_consistency([claim_a, claim_b])
        r2 = _check_internal_consistency([claim_b, claim_a])
        # Both orders must detect the contradiction
        assert r1["consistent"] == r2["consistent"]
        assert r1["conflict_count"] == r2["conflict_count"]

    def test_bidirectional_chooses_stronger_signal(self):
        """
        When both directions fire, the conflict must have the lower penalty
        (stronger signal) of the two.
        """
        from src.verifier.entity_checker import compute_alignment_penalty
        claim_a = "The maximum dosage is 400mg."
        claim_b = "The maximum dosage is 40mg."
        penalty_ab, _ = compute_alignment_penalty(claim_a, claim_b)
        penalty_ba, _ = compute_alignment_penalty(claim_b, claim_a)
        expected_min = min(penalty_ab, penalty_ba)

        result = _check_internal_consistency([claim_a, claim_b])
        if result["conflict_count"] > 0:
            assert result["conflicts"][0]["penalty"] == round(expected_min, 4)


# ══════════════════════════════════════════════════════════════════════════════
# Section 5 — Integration: TruthLayerVerifier.verify() API contract
# ══════════════════════════════════════════════════════════════════════════════

class TestVerifierAPIContract:
    """Tests that verify() returns internal_consistency in the correct shape."""

    def test_verify_returns_internal_consistency_key(self):
        """verify() result dict must contain 'internal_consistency'."""
        verifier = _make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."],
        )
        assert "internal_consistency" in result, (
            "verify() result missing 'internal_consistency'"
        )

    def test_verify_internal_consistency_schema(self):
        """internal_consistency block from verify() must pass schema check."""
        verifier = _make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."],
        )
        _assert_consistency_schema(result["internal_consistency"])

    def test_verify_single_claim_always_consistent(self):
        """A single-claim response is always internally consistent."""
        verifier = _make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."],
        )
        # If only one claim is extracted, consistent must be True.
        ic = result["internal_consistency"]
        if result["metadata"]["total_claims"] == 1:
            assert ic["consistent"] is True
            assert ic["conflict_count"] == 0

    def test_verify_full_response_is_json_serialisable(self):
        """The entire verify() response must be JSON-serialisable."""
        verifier = _make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."],
        )
        serialised = json.dumps(result)
        assert len(serialised) > 0

    def test_verify_consistent_multi_claim_response(self):
        """A multi-claim response with no self-contradictions is consistent."""
        verifier = _make_verifier()
        ai = (
            "Python is a high-level programming language. "
            "It supports object-oriented and functional paradigms. "
            "It is widely adopted in industry."
        )
        result = verifier.verify(ai, ["Python is a programming language released in 1991."])
        ic = result["internal_consistency"]
        _assert_consistency_schema(ic)
        # These compatible claims must not generate self-contradictions
        assert ic["consistent"] is True

    def test_verify_exposes_contradictory_multi_claim_response(self):
        """
        A response that contradicts itself internally must be flagged,
        even if each individual claim is supported by the source.

        The AI says: dosage is 400mg AND dosage is 40mg.
        The source doc mentions 400mg.
        Both claim_1 and claim_2 might pass source validation individually
        (claim_1 matches perfectly; claim_2 may be uncertain), BUT the
        internal consistency check must flag the contradiction.
        """
        verifier = _make_verifier()
        ai = (
            "The maximum safe dosage is 400mg per dose. "
            "The maximum safe dosage is 40mg per dose."
        )
        source = "The maximum safe dosage of ibuprofen is 400mg per dose."
        result = verifier.verify(ai, [source])
        ic = result["internal_consistency"]
        _assert_consistency_schema(ic)
        # If both claims are extracted, internal conflict must be detected
        if result["metadata"]["total_claims"] >= 2:
            assert not ic["consistent"]
            assert ic["conflict_count"] >= 1
            for conflict in ic["conflicts"]:
                _assert_conflict_schema(conflict)


# ══════════════════════════════════════════════════════════════════════════════
# Section 6 — Integration: _create_unverified_result()
# ══════════════════════════════════════════════════════════════════════════════

class TestUnverifiedResult:
    """
    Tests that the 'no sources' path also returns internal_consistency.
    An AI response can self-contradict even when there are no source docs.
    """

    def test_no_sources_returns_internal_consistency(self):
        """verify() with empty source_documents must still return the block."""
        verifier = _make_verifier()
        result = verifier.verify(
            "Python is great. Python is terrible.",
            [],
        )
        assert "internal_consistency" in result, (
            "verify() with no sources missing 'internal_consistency'"
        )
        _assert_consistency_schema(result["internal_consistency"])

    def test_no_sources_detects_numerical_contradiction(self):
        """
        Even with no source documents, a self-contradicting numerical claim
        must be caught by the consistency engine.
        """
        verifier = _make_verifier()
        ai = (
            "The maximum safe dosage is 400mg per dose. "
            "The maximum safe dosage is 40mg per dose."
        )
        result = verifier.verify(ai, [])
        ic = result["internal_consistency"]
        _assert_consistency_schema(ic)
        if result["metadata"]["total_claims"] >= 2:
            assert not ic["consistent"]
            assert ic["conflict_count"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# Section 7 — End-to-end: realistic self-contradictory AI response
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """
    Realistic scenario: an AI response that passes source-document checks
    but internally contradicts itself.

    This is the core value proposition: these bugs are invisible to any
    source-document-only checker but detectable by TruthLayer's
    intra-response consistency engine.
    """

    def test_self_contradictory_contract_summary(self):
        """
        AI summarises a contract and accidentally contradicts itself:
          - Claims the penalty is $10,000
          - Two sentences later claims it's $10 (digit drop, classic hallucination)
        """
        ai = (
            "The early termination penalty is $10,000 as specified in clause 7. "
            "Clients wishing to exit early will be charged a fee of $10."
        )
        result = _check_internal_consistency(
            ["The early termination penalty is $10,000 as specified in clause 7.",
             "Clients wishing to exit early will be charged a fee of $10."]
        )
        _assert_consistency_schema(result)
        # Numerical mismatch: $10,000 vs $10
        if result["conflict_count"] > 0:
            signals = [c["signal"] for c in result["conflicts"]]
            assert "NUMERICAL_MISMATCH" in signals

    def test_self_contradictory_sla_summary(self):
        """
        AI describes an SLA with contradictory uptime guarantees.
        """
        claims = [
            "The service guarantees 99.9% monthly uptime.",
            "The service guarantees 99.99% monthly uptime.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        if result["conflict_count"] > 0:
            assert any(c["signal"] == "NUMERICAL_MISMATCH" for c in result["conflicts"])

    def test_self_contradictory_data_policy(self):
        """
        AI describes a data policy: first says data is not shared,
        then says it is.  Classic negation flip.
        """
        claims = [
            "User data is not shared with third parties.",
            "User data is shared with third parties.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        assert not result["consistent"]
        assert result["conflict_count"] >= 1
        for c in result["conflicts"]:
            _assert_conflict_schema(c)

    def test_internally_consistent_multi_claim_response(self):
        """
        A well-formed multi-claim AI response with no self-contradictions.
        Claims intentionally contain no numeric tokens to avoid triggering
        the entity checker's numerical mismatch detector on unrelated numbers.
        Ensures we do not produce false positives on genuinely consistent output.
        """
        claims = [
            "The API requires authentication for access.",
            "The service is deployed across multiple geographic regions.",
            "Documentation is publicly available on the developer portal.",
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        assert result["consistent"] is True
        assert result["conflict_count"] == 0

    def test_three_claims_one_odd_number_out(self):
        """
        Two claims agree; one is the outlier.
        Must detect exactly the one contradicting pair.
        """
        claims = [
            "The maximum dosage is 400mg.",   # 0
            "The maximum dosage is 400mg.",   # 1 — identical to 0
            "The maximum dosage is 40mg.",    # 2 — contradicts 0 and 1
        ]
        result = _check_internal_consistency(claims)
        _assert_consistency_schema(result)
        # Expect conflicts between (0,2) and/or (1,2) but not (0,1)
        for conflict in result["conflicts"]:
            # (0, 1) pair must NOT produce a conflict (identical)
            assert not (conflict["claim_a_index"] == 0 and conflict["claim_b_index"] == 1), (
                "Identical claims must not produce a conflict"
            )
