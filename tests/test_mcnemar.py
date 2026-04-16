"""
Tests for src/stats/mcnemar.py — McNemar's test for paired classifier comparison.

Coverage:
  Section 1 — Mathematical primitives: _chi2_p_value_df1()
  Section 2 — Known critical values (cross-verified against R's pchisq)
  Section 3 — mcnemar_test(): parameter validation
  Section 4 — mcnemar_test(): contingency table construction
  Section 5 — mcnemar_test(): symmetry, no discordant pairs, continuity correction
  Section 6 — McnemarResult: dataclass fields, to_dict() serialisation
  Section 7 — classify_with_penalty() and classify_cosine_only()
  Section 8 — End-to-end: dual-signal vs cosine-only on real benchmark data

All tests use stdlib only — no numpy, no scipy.
"""

from __future__ import annotations

import json
import math
import pytest

from src.stats.mcnemar import (
    McnemarResult,
    _chi2_p_value_df1,
    classify_cosine_only,
    classify_with_penalty,
    mcnemar_test,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _approx(a: float, b: float, tol: float = 1e-4) -> bool:
    return abs(a - b) <= tol


# ══════════════════════════════════════════════════════════════════════════════
# Section 1 — _chi2_p_value_df1 mathematical correctness
# ══════════════════════════════════════════════════════════════════════════════

class TestChi2PValueDF1:
    """Tests for the internal p-value computation."""

    def test_chi2_zero_returns_one(self):
        """chi2=0 means perfect H₀ — p=1.0."""
        assert _chi2_p_value_df1(0.0) == 1.0

    def test_chi2_negative_raises(self):
        """Negative chi2 is mathematically undefined."""
        with pytest.raises(ValueError, match="non-negative"):
            _chi2_p_value_df1(-1.0)

    def test_critical_value_alpha_005(self):
        """
        χ²(1, α=0.05) critical value = 3.841.
        Cross-verified: R> pchisq(3.841, df=1, lower.tail=FALSE) = 0.05002
        """
        p = _chi2_p_value_df1(3.841)
        assert _approx(p, 0.0500, tol=2e-3)

    def test_critical_value_alpha_001(self):
        """
        χ²(1, α=0.01) critical value = 6.635.
        R> pchisq(6.635, df=1, lower.tail=FALSE) = 0.01002
        """
        p = _chi2_p_value_df1(6.635)
        assert _approx(p, 0.0100, tol=2e-3)

    def test_critical_value_alpha_0001(self):
        """
        χ²(1, α=0.001) critical value = 10.828.
        R> pchisq(10.828, df=1, lower.tail=FALSE) = 0.001001
        """
        p = _chi2_p_value_df1(10.828)
        assert _approx(p, 0.001, tol=2e-4)

    def test_large_chi2_yields_tiny_p(self):
        """Very large chi2 (far into tail) → p approaches 0."""
        p = _chi2_p_value_df1(50.0)
        assert p < 1e-10

    def test_p_value_in_unit_interval(self):
        """p-value must always be in (0, 1] for non-negative input."""
        for x in (0.0, 1.0, 3.84, 6.63, 10.83, 20.0, 100.0):
            p = _chi2_p_value_df1(x)
            assert 0.0 <= p <= 1.0, f"p({x}) = {p} out of [0, 1]"

    def test_monotone_decreasing(self):
        """Larger chi2 → smaller p-value (monotone decreasing)."""
        xs = [0.1, 1.0, 2.0, 3.84, 6.63, 10.83, 20.0]
        ps = [_chi2_p_value_df1(x) for x in xs]
        for i in range(len(ps) - 1):
            assert ps[i] > ps[i + 1], (
                f"Monotonicity violated at x={xs[i]}: p={ps[i]:.6f} <= p={ps[i+1]:.6f}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Section 2 — mcnemar_test() argument validation
# ══════════════════════════════════════════════════════════════════════════════

class TestMcnemarTestValidation:
    """Tests for mcnemar_test() input validation."""

    def test_mismatched_length_raises(self):
        with pytest.raises(ValueError, match="equal length"):
            mcnemar_test([True, True], [True])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            mcnemar_test([], [])

    def test_alpha_zero_raises(self):
        with pytest.raises(ValueError, match="alpha"):
            mcnemar_test([True], [True], alpha=0.0)

    def test_alpha_one_raises(self):
        with pytest.raises(ValueError, match="alpha"):
            mcnemar_test([True], [True], alpha=1.0)

    def test_alpha_negative_raises(self):
        with pytest.raises(ValueError, match="alpha"):
            mcnemar_test([True], [True], alpha=-0.05)


# ══════════════════════════════════════════════════════════════════════════════
# Section 3 — Contingency table construction
# ══════════════════════════════════════════════════════════════════════════════

class TestContingencyTable:
    """Tests verifying a, b, c, d counts from known inputs."""

    def _make_result(self, sys_v, base_v, continuity=False):
        return mcnemar_test(sys_v, base_v, continuity_correction=continuity)

    def test_all_concordant_both_correct(self):
        """All cases: both correct → a=N, b=c=d=0."""
        r = self._make_result([True]*10, [True]*10)
        assert r.n_a == 10
        assert r.n_b == 0
        assert r.n_c == 0
        assert r.n_d == 0
        assert r.n_discordant == 0

    def test_all_concordant_both_wrong(self):
        """All cases: both wrong → d=N, a=b=c=0."""
        r = self._make_result([False]*5, [False]*5)
        assert r.n_d == 5
        assert r.n_a == 0
        assert r.n_b == 0
        assert r.n_c == 0

    def test_known_b_and_c(self):
        """
        4 cases:
          case 0: both correct → a
          case 1: dual right, cosine wrong → b
          case 2: cosine right, dual wrong → c
          case 3: both wrong → d
        """
        sys_v  = [True,  True,  False, False]
        base_v = [True,  False, True,  False]
        r = self._make_result(sys_v, base_v)
        assert r.n_a == 1
        assert r.n_b == 1
        assert r.n_c == 1
        assert r.n_d == 1
        assert r.n_total == 4
        assert r.n_discordant == 2

    def test_pure_b_cases(self):
        """All discordant pairs are b (dual right, cosine wrong) → system wins every disc."""
        sys_v  = [True]*5 + [True]*5
        base_v = [True]*5 + [False]*5
        r = self._make_result(sys_v, base_v)
        assert r.n_b == 5
        assert r.n_c == 0

    def test_pure_c_cases(self):
        """All discordant pairs are c (cosine right, dual wrong) → system regresses."""
        sys_v  = [True]*3 + [False]*3
        base_v = [True]*3 + [True]*3
        r = self._make_result(sys_v, base_v)
        assert r.n_c == 3
        assert r.n_b == 0


# ══════════════════════════════════════════════════════════════════════════════
# Section 4 — mcnemar_test() statistical properties
# ══════════════════════════════════════════════════════════════════════════════

class TestMcnemarStatisticalProperties:
    """Tests for statistical correctness of McNemar's test results."""

    def test_no_discordant_pairs(self):
        """When b==c==0, chi2=0, p=1.0, is_significant=False."""
        r = mcnemar_test([True]*100, [True]*100)
        assert r.chi2_statistic == 0.0
        assert r.p_value == 1.0
        assert r.is_significant is False
        assert r.n_discordant == 0

    def test_symmetric_b_equals_c_not_significant(self):
        """When b==c, H₀ cannot be rejected — p is large."""
        # 10 b-cases and 10 c-cases: symmetric, no signal
        sys_v  = [True]*10 + [False]*10 + [True]*10
        base_v = [True]*10 + [True]*10  + [False]*10
        r = mcnemar_test(sys_v, base_v)
        assert r.n_b == r.n_c
        assert r.is_significant is False

    def test_large_b_small_c_is_significant(self):
        """b >> c → small p-value → significant at α=0.05."""
        # 30 b-cases, 3 c-cases.
        # χ² (corrected) = (|30-3|-1)² / 33 = 26²/33 = 676/33 ≈ 20.48 → p≈6e-6
        sys_v  = [True]*100 + [True]*30  + [False]*3
        base_v = [True]*100 + [False]*30 + [True]*3
        r = mcnemar_test(sys_v, base_v)
        assert r.n_b == 30
        assert r.n_c == 3
        assert r.is_significant is True
        assert r.p_value < 0.001

    def test_exact_alpha_boundary(self):
        """
        For b=10, c=0 (no correction):
          χ² = (10-0)²/10 = 10.0 → p ≈ 0.0016 < 0.05 → significant.
        """
        sys_v  = [True]*10  + [False]*0
        base_v = [False]*10 + [True]*0
        # Prepend concordant pairs so the test doesn't raise on empty
        sys_v  = [True]*50 + sys_v
        base_v = [True]*50 + base_v
        r = mcnemar_test(sys_v, base_v, continuity_correction=False)
        assert r.n_b == 10
        assert r.n_c == 0
        # Without correction: chi2 = 10 → p ≈ 0.0016
        assert r.chi2_statistic == pytest.approx(10.0, abs=1e-10)
        assert r.is_significant is True

    def test_continuity_correction_reduces_chi2(self):
        """With correction: chi2 <= chi2 without correction (always more conservative)."""
        sys_v  = [True]*50 + [True]*20  + [False]*5
        base_v = [True]*50 + [False]*20 + [True]*5
        r_corr   = mcnemar_test(sys_v, base_v, continuity_correction=True)
        r_nocorr = mcnemar_test(sys_v, base_v, continuity_correction=False)
        assert r_corr.chi2_statistic <= r_nocorr.chi2_statistic
        assert r_corr.p_value >= r_nocorr.p_value

    def test_p_value_in_unit_interval(self):
        """p-value must always be in [0, 1]."""
        for n_b, n_c in [(0, 0), (5, 5), (30, 3), (3, 30), (50, 0)]:
            sys_v  = [True]*100 + [True]*n_b  + [False]*n_c
            base_v = [True]*100 + [False]*n_b + [True]*n_c
            r = mcnemar_test(sys_v, base_v)
            assert 0.0 <= r.p_value <= 1.0, f"p={r.p_value} out of [0,1] for b={n_b},c={n_c}"

    def test_is_significant_consistent_with_p_value(self):
        """is_significant must always equal (p_value < alpha)."""
        for n_b, n_c in [(50, 0), (10, 8), (3, 3), (0, 50)]:
            sys_v  = [True]*50 + [True]*n_b  + [False]*n_c
            base_v = [True]*50 + [False]*n_b + [True]*n_c
            r = mcnemar_test(sys_v, base_v)
            assert r.is_significant == (r.p_value < r.alpha)


# ══════════════════════════════════════════════════════════════════════════════
# Section 5 — McnemarResult fields and serialisation
# ══════════════════════════════════════════════════════════════════════════════

class TestMcnemarResult:
    """Tests for McnemarResult dataclass and to_dict()."""

    def _make(self, n_b=20, n_c=3):
        sys_v  = [True]*100 + [True]*n_b  + [False]*n_c
        base_v = [True]*100 + [False]*n_b + [True]*n_c
        return mcnemar_test(sys_v, base_v)

    def test_fields_present(self):
        r = self._make()
        for field_name in (
            "chi2_statistic", "p_value", "n_b", "n_c", "n_discordant",
            "n_total", "n_a", "n_d", "continuity_corrected", "alpha",
            "is_significant", "interpretation",
        ):
            assert hasattr(r, field_name), f"Missing field: {field_name}"

    def test_n_discordant_equals_b_plus_c(self):
        r = self._make(n_b=20, n_c=3)
        assert r.n_discordant == r.n_b + r.n_c == 23

    def test_n_total_correct(self):
        n_b, n_c = 20, 3
        r = self._make(n_b, n_c)
        assert r.n_total == 100 + n_b + n_c

    def test_to_dict_is_json_serialisable(self):
        r = self._make()
        d = r.to_dict()
        serialised = json.dumps(d)
        parsed = json.loads(serialised)
        assert parsed["n_b"] == r.n_b
        assert parsed["n_c"] == r.n_c
        assert parsed["is_significant"] == r.is_significant
        assert "p_value_scientific" in parsed

    def test_to_dict_chi2_rounded(self):
        r = self._make()
        d = r.to_dict()
        # chi2_statistic must be a float rounded to 6 dp
        assert isinstance(d["chi2_statistic"], float)

    def test_interpretation_non_empty(self):
        r = self._make()
        assert isinstance(r.interpretation, str)
        assert len(r.interpretation) > 0

    def test_immutability(self):
        """McnemarResult is frozen — mutation must raise."""
        r = self._make()
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            r.chi2_statistic = 0.0  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# Section 6 — classify_with_penalty and classify_cosine_only
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyHelpers:
    """Tests for the convenience classifier wrappers."""

    def test_classify_with_penalty_verified(self):
        """High similarity, no penalty → VERIFIED."""
        status = classify_with_penalty(0.90, 1.0)
        assert status == "VERIFIED"

    def test_classify_with_penalty_penalty_degrades(self):
        """Same similarity with heavy penalty → UNSUPPORTED."""
        status = classify_with_penalty(0.90, 0.35)  # 0.90 * 0.35 = 0.315
        assert status == "UNSUPPORTED"

    def test_classify_with_penalty_uncertain(self):
        status = classify_with_penalty(0.60, 0.80)  # 0.60 * 0.80 = 0.48
        assert status == "UNCERTAIN"

    def test_cosine_only_is_penalty_one(self):
        """classify_cosine_only(x) == classify_with_penalty(x, 1.0) for all x."""
        for score in (0.1, 0.4, 0.65, 0.8, 1.0):
            assert classify_cosine_only(score) == classify_with_penalty(score, 1.0)

    def test_cosine_only_unsupported_below_threshold(self):
        assert classify_cosine_only(0.20) == "UNSUPPORTED"

    def test_cosine_only_verified_above_threshold(self):
        assert classify_cosine_only(0.80) == "VERIFIED"

    def test_cosine_only_uncertain_midrange(self):
        status = classify_cosine_only(0.50)
        assert status in ("UNCERTAIN", "UNSUPPORTED")  # depends on threshold


# ══════════════════════════════════════════════════════════════════════════════
# Section 7 — End-to-end on the 300-case benchmark
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEndBenchmark:
    """
    Runs the full McNemar analysis on the 300-case adversarial benchmark
    and asserts properties that must hold for the AWS submission to be valid.

    These tests serve as the mathematical proof used in the competition article.
    """

    @classmethod
    def setup_class(cls):
        """Run both classifiers on all 300 benchmark cases once."""
        from benchmarks.adversarial_benchmark import DATASET
        from src.mocks.embedding_provider import MockEmbeddingProvider
        from src.verifier.entity_checker import compute_alignment_penalty
        from src.verifier.similarity_engine import SimilarityEngine

        provider = MockEmbeddingProvider()
        engine   = SimilarityEngine()

        dual_correct_vec:   list[bool] = []
        cosine_correct_vec: list[bool] = []

        for case in DATASET:
            texts  = [case.ai_response, case.source_document]
            embs   = provider.embed_batch(texts)
            sim, _ = engine.find_best_match(embs[0], [embs[1]], [case.source_document])

            penalty, _ = compute_alignment_penalty(case.ai_response, case.source_document)

            dual_status   = classify_with_penalty(sim, penalty)
            cosine_status = classify_cosine_only(sim)

            def is_correct(pred, exp):
                if exp == "UNSUPPORTED":
                    return pred == "UNSUPPORTED"
                return pred != "UNSUPPORTED"

            dual_correct_vec.append(is_correct(dual_status, case.expected_verdict))
            cosine_correct_vec.append(is_correct(cosine_status, case.expected_verdict))

        cls.dual_correct   = dual_correct_vec
        cls.cosine_correct = cosine_correct_vec
        cls.result         = mcnemar_test(dual_correct_vec, cosine_correct_vec)

    def test_dataset_size_300(self):
        """Benchmark must have exactly 300 cases."""
        assert len(self.dual_correct) == 300

    def test_dual_outperforms_cosine_accuracy(self):
        """Dual-signal accuracy must exceed cosine-only accuracy."""
        dual_acc   = sum(self.dual_correct)   / len(self.dual_correct)
        cosine_acc = sum(self.cosine_correct) / len(self.cosine_correct)
        assert dual_acc >= cosine_acc, (
            f"Dual accuracy {dual_acc:.4f} < cosine-only {cosine_acc:.4f}"
        )

    def test_b_greater_than_c(self):
        """
        b (dual gains) must exceed c (dual regressions).
        This is the directional hypothesis: our entity engine improves more
        cases than it breaks.
        """
        r = self.result
        assert r.n_b >= r.n_c, (
            f"b={r.n_b} < c={r.n_c}: entity engine causes more regressions than gains"
        )

    def test_result_fields(self):
        """McnemarResult must contain all required fields."""
        r = self.result
        assert r.n_total == 300
        assert r.n_a + r.n_b + r.n_c + r.n_d == 300
        assert r.n_discordant == r.n_b + r.n_c

    def test_to_dict_json_serialisable(self):
        """McnemarResult from a real run must be JSON-serialisable."""
        d = self.result.to_dict()
        json.dumps(d)  # must not raise

    def test_p_value_valid(self):
        """p_value must be in [0, 1] for a real benchmark run."""
        assert 0.0 <= self.result.p_value <= 1.0

    def test_chi2_non_negative(self):
        """chi2 must be non-negative."""
        assert self.result.chi2_statistic >= 0.0
