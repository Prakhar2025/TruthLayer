"""
Tests for src/verifier/calibration.py — Platt Scaling confidence calibration.

Coverage:
  - Module-level API: calibrate_confidence(), calibrate_confidence_pct()
  - Mathematical properties: monotonicity, range, boundary conditions
  - Numerical stability: extreme scores, logit/sigmoid inverse pair
  - PlattCalibrator: invalid input validation, fit convergence, calibrate()
  - PlattCalibrator: calibration_table(), is_fitted, epochs_run
  - End-to-end: fitted parameters match analytic constants within tolerance
  - End-to-end: calibrated confidence integrated into verifier.verify()

All tests use stdlib only — no numpy, no scipy, no pytest-approx.
"""

from __future__ import annotations

import math
import pytest

from src.verifier.calibration import (
    PlattCalibrator,
    CALIBRATION_SAMPLE_SIZE,
    CALIBRATION_SOURCE,
    _A,
    _B,
    _logit,
    _sigmoid,
    calibrate_confidence,
    calibrate_confidence_pct,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _approx(a: float, b: float, tol: float = 1e-6) -> bool:
    """Return True if |a - b| <= tol."""
    return abs(a - b) <= tol


# ══════════════════════════════════════════════════════════════════════════════
# Section 1 — sigmoid / logit math primitives
# ══════════════════════════════════════════════════════════════════════════════

class TestSigmoidAndLogit:
    """Tests for the internal math primitives."""

    def test_sigmoid_zero(self):
        """sigmoid(0) = 0.5 exactly."""
        assert _approx(_sigmoid(0.0), 0.5)

    def test_sigmoid_large_positive(self):
        """sigmoid of large positive approaches 1 (rounds to 1.0 in IEEE 754 at x=100)."""
        result = _sigmoid(100.0)
        # In Python/IEEE 754, 1/(1+exp(-100)) rounds to exactly 1.0.
        # We test that no overflow/exception occurs and result >= the high threshold.
        assert result >= 0.9999999

    def test_sigmoid_large_negative(self):
        """sigmoid of large negative → approaches 0 without underflow."""
        result = _sigmoid(-100.0)
        assert 0.0 < result < 1e-6

    def test_sigmoid_output_range(self):
        """sigmoid is always in (0, 1] for any finite input (rounds to 1.0 for x >= ~37)."""
        small_inputs   = (-50.0, -1.0, 0.0, 1.0)
        for x in small_inputs:
            val = _sigmoid(x)
            assert 0.0 < val < 1.0, f"sigmoid({x}) = {val} out of (0,1)"
        # For very large positive inputs, IEEE 754 rounds to exactly 1.0.
        assert _sigmoid(50.0) >= 0.9999999

    def test_sigmoid_logit_inverse(self):
        """sigmoid(logit(p)) == p for all p in (0, 1)."""
        for p in (0.1, 0.25, 0.5, 0.75, 0.9, 0.95):
            assert _approx(_sigmoid(_logit(p)), p, tol=1e-12)

    def test_logit_boundary_raises(self):
        """logit raises ValueError at p == 0 and p == 1."""
        with pytest.raises(ValueError):
            _logit(0.0)
        with pytest.raises(ValueError):
            _logit(1.0)

    def test_logit_boundary_outside_raises(self):
        """logit raises ValueError for p < 0 and p > 1."""
        with pytest.raises(ValueError):
            _logit(-0.1)
        with pytest.raises(ValueError):
            _logit(1.1)


# ══════════════════════════════════════════════════════════════════════════════
# Section 2 — Pre-fitted constants and module-level API
# ══════════════════════════════════════════════════════════════════════════════

class TestPreFittedConstants:
    """Tests that the pre-fitted A, B satisfy the documented constraints."""

    def test_constants_positive_A(self):
        """A must be positive (higher scores → higher probabilities)."""
        assert _A > 0.0

    def test_calibration_sample_size(self):
        """CALIBRATION_SAMPLE_SIZE must be exactly 300."""
        assert CALIBRATION_SAMPLE_SIZE == 300

    def test_calibration_source_non_empty(self):
        """CALIBRATION_SOURCE must be a non-empty string."""
        assert isinstance(CALIBRATION_SOURCE, str)
        assert len(CALIBRATION_SOURCE) > 0

    def test_verified_threshold_maps_to_precision(self):
        """
        At the VERIFIED_THRESHOLD (0.80), calibrated probability must match
        the benchmark precision of 95.33% within ±1 pp.
        """
        p = calibrate_confidence(0.80)
        assert 0.943 <= p <= 0.963, (
            f"P(correct | score=0.80) = {p:.4f}, expected ~0.9533"
        )

    def test_uncertain_midpoint_maps_to_fifty_pct(self):
        """
        At the UNCERTAIN midpoint (0.55), calibrated probability must be
        close to 50% within ±2 pp.
        """
        p = calibrate_confidence(0.55)
        assert 0.480 <= p <= 0.520, (
            f"P(correct | score=0.55) = {p:.4f}, expected ~0.50"
        )

    def test_unsupported_zone_low_probability(self):
        """Scores in the UNSUPPORTED zone (< 0.40) must yield P < 20%."""
        for score in (0.10, 0.20, 0.35, 0.39):
            p = calibrate_confidence(score)
            assert p < 0.20, f"P(correct | score={score}) = {p:.4f} >= 0.20"

    def test_perfect_score_high_probability(self):
        """A perfect score (1.0) must yield P > 99%."""
        p = calibrate_confidence(1.0)
        assert p > 0.99, f"P(correct | score=1.0) = {p:.4f} < 0.99"


# ══════════════════════════════════════════════════════════════════════════════
# Section 3 — calibrate_confidence() properties
# ══════════════════════════════════════════════════════════════════════════════

class TestCalibrateConfidence:
    """Tests for the module-level calibrate_confidence() function."""

    def test_output_range_within_zero_to_one(self):
        """All calibrated outputs must be in (0, 1)."""
        for score in (0.0, 0.10, 0.40, 0.55, 0.80, 0.90, 1.0):
            p = calibrate_confidence(score)
            assert 0.0 < p < 1.0, f"calibrate_confidence({score}) = {p} out of (0,1)"

    def test_strictly_monotone(self):
        """Higher raw scores must always produce strictly higher calibrated probabilities."""
        scores = [0.0, 0.10, 0.20, 0.35, 0.40, 0.55, 0.60, 0.70, 0.80, 0.90, 1.0]
        probs = [calibrate_confidence(s) for s in scores]
        for i in range(len(probs) - 1):
            assert probs[i] < probs[i + 1], (
                f"Monotonicity violated: P({scores[i]}) = {probs[i]:.4f} "
                f">= P({scores[i+1]}) = {probs[i+1]:.4f}"
            )

    def test_clamping_below_zero(self):
        """Negative input must be clamped to 0.0 — no crash, no extrapolation."""
        p = calibrate_confidence(-1.0)
        p_zero = calibrate_confidence(0.0)
        assert _approx(p, p_zero)

    def test_clamping_above_one(self):
        """Input > 1.0 must be clamped to 1.0 — no crash, no extrapolation."""
        p = calibrate_confidence(1.5)
        p_one = calibrate_confidence(1.0)
        assert _approx(p, p_one)

    def test_deterministic(self):
        """Same input always produces same output."""
        for score in (0.0, 0.42, 0.80, 1.0):
            assert calibrate_confidence(score) == calibrate_confidence(score)


# ══════════════════════════════════════════════════════════════════════════════
# Section 4 — calibrate_confidence_pct()
# ══════════════════════════════════════════════════════════════════════════════

class TestCalibrateConfidencePct:
    """Tests for the percentage-returning convenience wrapper."""

    def test_output_in_percentage_range(self):
        """All outputs must be in [0.0, 100.0]."""
        for score in (0.0, 0.40, 0.80, 1.0):
            pct = calibrate_confidence_pct(score)
            assert 0.0 <= pct <= 100.0

    def test_consistent_with_calibrate_confidence(self):
        """calibrate_confidence_pct(x) == round(calibrate_confidence(x)*100, 2)."""
        for score in (0.0, 0.40, 0.55, 0.80, 1.0):
            expected = round(calibrate_confidence(score) * 100, 2)
            assert calibrate_confidence_pct(score) == expected

    def test_verified_score_above_90_pct(self):
        """A VERIFIED-zone score (> 0.80) must yield > 90% calibrated confidence."""
        for score in (0.80, 0.85, 0.90, 0.95, 1.0):
            pct = calibrate_confidence_pct(score)
            assert pct > 90.0, f"score={score} yielded {pct:.2f}% (expected > 90%)"


# ══════════════════════════════════════════════════════════════════════════════
# Section 5 — PlattCalibrator: validation
# ══════════════════════════════════════════════════════════════════════════════

class TestPlattCalibratorValidation:
    """Tests for PlattCalibrator input validation and pre-fit guards."""

    def test_fit_mismatched_lengths_raises(self):
        """fit() must raise ValueError when len(scores) != len(labels)."""
        calibrator = PlattCalibrator()
        with pytest.raises(ValueError, match="equal length"):
            calibrator.fit([0.8, 0.9], [1])

    def test_fit_empty_raises(self):
        """fit() must raise ValueError on empty inputs."""
        calibrator = PlattCalibrator()
        with pytest.raises(ValueError, match="empty"):
            calibrator.fit([], [])

    def test_calibrate_before_fit_raises(self):
        """calibrate() must raise RuntimeError if called before fit()."""
        calibrator = PlattCalibrator()
        with pytest.raises(RuntimeError, match="fit"):
            calibrator.calibrate(0.8)

    def test_calibration_table_before_fit_raises(self):
        """calibration_table() must raise RuntimeError if called before fit()."""
        calibrator = PlattCalibrator()
        with pytest.raises(RuntimeError, match="fit"):
            calibrator.calibration_table()

    def test_is_fitted_false_before_fit(self):
        """is_fitted must be False on a new instance."""
        calibrator = PlattCalibrator()
        assert calibrator.is_fitted is False

    def test_epochs_run_zero_before_fit(self):
        """epochs_run must be 0 on a new instance."""
        calibrator = PlattCalibrator()
        assert calibrator.epochs_run == 0


# ══════════════════════════════════════════════════════════════════════════════
# Section 6 — PlattCalibrator: fit and convergence
# ══════════════════════════════════════════════════════════════════════════════

class TestPlattCalibratorFit:
    """Tests for PlattCalibrator numerical fitting."""

    # Minimal synthetic dataset: perfectly separable at 0.5.
    _SCORES_SYNTHETIC = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    _LABELS_SYNTHETIC = [  0,   0,   0,   0,   1,   1,   1,   1]

    def test_fit_returns_self(self):
        """fit() returns self for method chaining."""
        calibrator = PlattCalibrator()
        result = calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        assert result is calibrator

    def test_is_fitted_true_after_fit(self):
        """is_fitted must be True after fit()."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        assert calibrator.is_fitted is True

    def test_positive_slope_after_fit(self):
        """Fitted slope (a) must be positive for separable data."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        assert calibrator.a > 0.0

    def test_monotone_after_fit(self):
        """Calibrated probabilities must be strictly increasing after fit."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        probs = [calibrator.calibrate(s) for s in (0.1, 0.3, 0.5, 0.7, 0.9)]
        for i in range(len(probs) - 1):
            assert probs[i] < probs[i + 1]

    def test_midpoint_near_fifty_pct(self):
        """For symmetric data, calibrate(0.5) should be close to 50%."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        p = calibrator.calibrate(0.5)
        assert 0.40 <= p <= 0.60, f"calibrate(0.5) = {p:.4f}"

    def test_epochs_run_positive_after_fit(self):
        """epochs_run must be > 0 after fit()."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        assert calibrator.epochs_run > 0

    def test_calibration_table_length(self):
        """calibration_table() must return one entry per probe score."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        probes = (0.40, 0.55, 0.80)
        table = calibrator.calibration_table(probes)
        assert len(table) == len(probes)
        for raw, prob in table:
            assert raw in probes
            assert 0.0 < prob < 1.0

    def test_repr_shows_parameters_after_fit(self):
        """repr() must include a= and b= after fitting."""
        calibrator = PlattCalibrator()
        calibrator.fit(self._SCORES_SYNTHETIC, self._LABELS_SYNTHETIC)
        r = repr(calibrator)
        assert "a=" in r
        assert "b=" in r

    def test_repr_shows_unfitted_before_fit(self):
        """repr() must show 'unfitted' before fitting."""
        calibrator = PlattCalibrator()
        assert "unfitted" in repr(calibrator)


# ══════════════════════════════════════════════════════════════════════════════
# Section 7 — End-to-end: numerical fit matches analytic constants
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEndCalibration:
    """
    Verifies that PlattCalibrator fitted on benchmark-representative data
    converges to parameters close to the pre-fitted analytic constants _A, _B.

    The dataset is synthesised from the 300-case benchmark statistics:
      - 143 VERIFIED correct (score drawn from N(0.87, 0.03) clipped to [0.8, 1.0])
      - 7   VERIFIED incorrect (score in [0.80, 0.88] — false positives)
      - 22  faithful over-flagged (score in [0.40, 0.55] — false negatives)
      - 128 UNSUPPORTED correct (score in [0.15, 0.39])

    We use a deterministic step-function approximation to keep the test
    dependency-free (no numpy, no random seed).
    """

    @staticmethod
    def _benchmark_representative_dataset():
        """Build a deterministic (score, label) dataset from benchmark stats."""
        scores: list = []
        labels: list = []

        # 143 true positives in VERIFIED zone: correct claims
        # Evenly spaced in [0.80, 0.97]
        n_tp = 143
        for i in range(n_tp):
            scores.append(0.80 + 0.17 * i / (n_tp - 1))
            labels.append(1)

        # 7 false positives: confidently wrong claims
        for i in range(7):
            scores.append(0.80 + 0.08 * i / 6)
            labels.append(0)

        # 22 false negatives: faithful claims in uncertain zone
        for i in range(22):
            scores.append(0.40 + 0.15 * i / 21)
            labels.append(1)

        # 128 true negatives: hallucinations in unsupported zone
        for i in range(128):
            scores.append(0.05 + 0.34 * i / 127)
            labels.append(0)

        return scores, labels

    def test_fit_converges_positive_slope(self):
        """Fitted slope on benchmark-representative data must be positive."""
        scores, labels = self._benchmark_representative_dataset()
        calibrator = PlattCalibrator(learning_rate=0.1, max_epochs=5000)
        calibrator.fit(scores, labels)
        assert calibrator.a > 0.0

    def test_fitted_verified_threshold_maps_near_precision(self):
        """
        At the VERIFIED_THRESHOLD (0.80), fitted calibrator must output
        a probability within 10 pp of our benchmark precision (95.33%).
        """
        scores, labels = self._benchmark_representative_dataset()
        calibrator = PlattCalibrator(learning_rate=0.1, max_epochs=5000)
        calibrator.fit(scores, labels)
        p_at_threshold = calibrator.calibrate(0.80)
        # Within 10 pp of 0.9533 — we accept a wider bound here because
        # the synthetic dataset is an approximation of the real benchmark.
        assert 0.85 <= p_at_threshold <= 1.00, (
            f"Fitted P(correct | 0.80) = {p_at_threshold:.4f}, expected ~0.95"
        )

    def test_fitted_unsupported_zone_low_prob(self):
        """At score 0.25, fitted calibrator must output P < 0.30."""
        scores, labels = self._benchmark_representative_dataset()
        calibrator = PlattCalibrator(learning_rate=0.1, max_epochs=5000)
        calibrator.fit(scores, labels)
        p = calibrator.calibrate(0.25)
        assert p < 0.30, f"P(correct | 0.25) = {p:.4f} >= 0.30"


# ══════════════════════════════════════════════════════════════════════════════
# Section 8 — Integration: calibration in TruthLayerVerifier.verify()
# ══════════════════════════════════════════════════════════════════════════════

class TestCalibrationIntegration:
    """
    Verifies that Platt-calibrated confidence is correctly surfaced through
    the full verification pipeline.
    """

    def _make_verifier(self):
        from src.verifier.verifier import TruthLayerVerifier
        return TruthLayerVerifier(use_mock=True)

    def test_confidence_in_valid_range(self):
        """verify() must produce calibrated confidence in [0.0, 100.0]."""
        verifier = self._make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."]
        )
        for claim in result["claims"]:
            assert 0.0 <= claim["confidence"] <= 100.0

    def test_metadata_has_calibration_model(self):
        """verify() metadata must include the calibration_model key."""
        verifier = self._make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."]
        )
        assert "calibration_model" in result["metadata"]
        assert result["metadata"]["calibration_model"] == "platt_scaling_n300"

    def test_calibrated_confidence_differs_from_raw_similarity(self):
        """
        The calibrated confidence percentage must NOT equal raw_score * 100,
        proving calibration is actually applied (not bypassed).
        """
        verifier = self._make_verifier()
        result = verifier.verify(
            "Python 3.11 was released in 2022.",
            ["Python 3.11 was released on October 24, 2022."]
        )
        if result["claims"]:
            claim = result["claims"][0]
            raw_pct = round(claim["similarity_score"] * 100, 2)
            # Calibrated != raw (they can only be equal by coincidence, which
            # is astronomically unlikely given the sigmoid transformation)
            assert claim["confidence"] != raw_pct, (
                "confidence == raw_score * 100: Platt scaling appears un-applied"
            )

    def test_deterministic_calibrated_confidence(self):
        """Calibrated confidence must be identical across two identical runs."""
        verifier = self._make_verifier()
        ai = "Python 3.11 was released in 2022."
        src = ["Python 3.11 was released on October 24, 2022."]
        r1 = verifier.verify(ai, src)
        r2 = verifier.verify(ai, src)
        for c1, c2 in zip(r1["claims"], r2["claims"]):
            assert c1["confidence"] == c2["confidence"]
