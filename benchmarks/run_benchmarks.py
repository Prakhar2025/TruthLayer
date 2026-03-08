#!/usr/bin/env python3
"""
TruthLayer Benchmark Suite

Measures real-world performance of the TruthLayer API across four dimensions:

1. Latency     — cold start, warm (no cache), warm (cache hit)
2. Precision   — when TruthLayer says VERIFIED, how often is it correct?
3. Recall      — of all truly-supported claims, how many did we catch?
4. Cache       — cache hit rate after warmup, DynamoDB speedup factor

Usage:
    export TRUTHLAYER_API_URL="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"
    export TRUTHLAYER_API_KEY="tl_your_key_here"
    python benchmarks/run_benchmarks.py

    # Save results to file:
    python benchmarks/run_benchmarks.py --output benchmarks/results/

Output:
    - Human-readable table printed to stdout
    - JSON results file saved to --output directory
    - Exit code 0 on success, 1 on API failure
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

# Add repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdk.python.truthlayer import TruthLayer, TruthLayerError, VerificationResult


# ─── Ground Truth Dataset ────────────────────────────────────────────────────
# Each entry: (ai_response, source_document, expected_verdict)
# expected_verdict: "VERIFIED" | "UNSUPPORTED"
# These are carefully crafted so the expected outcome is unambiguous.

SOURCE_DOC_REFUND = (
    "Our refund policy allows returns within 30 days of purchase. "
    "Items must be unused and in original packaging. "
    "Refunds are processed within 5-7 business days. "
    "Digital products are non-refundable. "
    "Return shipping is the customer's responsibility."
)

SOURCE_DOC_SLA = (
    "TechCorp guarantees 99.9% uptime for all production services. "
    "Scheduled maintenance windows occur Sundays 2-6 AM EST and are excluded from SLA. "
    "Downtime credits are calculated at 10x the hourly rate per hour below SLA. "
    "The SLA applies only to paid plans. Free tier has no uptime guarantee."
)

SOURCE_DOC_PRICING = (
    "The Starter plan costs $29 per month and includes up to 10,000 API calls. "
    "The Pro plan costs $99 per month with 100,000 API calls included. "
    "Enterprise pricing is available upon request. "
    "All plans include a 14-day free trial. No credit card required for trial."
)

# Format: (claim, source_doc, is_truly_supported)
# is_truly_supported=True  → TruthLayer should say VERIFIED or UNCERTAIN
# is_truly_supported=False → TruthLayer should say UNSUPPORTED
PRECISION_TEST_CASES: List[Tuple[str, str, bool]] = [
    # Truly supported claims
    ("Refunds are processed within 5-7 business days.", SOURCE_DOC_REFUND, True),
    ("Items must be unused and in original packaging.", SOURCE_DOC_REFUND, True),
    ("Digital products are non-refundable.", SOURCE_DOC_REFUND, True),
    ("Returns are accepted within 30 days of purchase.", SOURCE_DOC_REFUND, True),
    ("The service guarantees 99.9% uptime.", SOURCE_DOC_SLA, True),
    ("Maintenance windows are on Sundays from 2 to 6 AM EST.", SOURCE_DOC_SLA, True),
    ("Downtime credits are 10x the hourly rate.", SOURCE_DOC_SLA, True),
    ("The Starter plan is $29 per month.", SOURCE_DOC_PRICING, True),
    ("The Pro plan includes 100,000 API calls.", SOURCE_DOC_PRICING, True),
    ("All plans include a 14-day free trial.", SOURCE_DOC_PRICING, True),
    # Truly unsupported / hallucinated claims
    ("Return shipping is free on all orders.", SOURCE_DOC_REFUND, False),
    ("Refunds are processed within 24 hours.", SOURCE_DOC_REFUND, False),
    ("The SLA guarantees 99.99% uptime.", SOURCE_DOC_SLA, False),
    ("The free tier includes a 99.9% uptime SLA.", SOURCE_DOC_SLA, False),
    ("The Starter plan costs $19 per month.", SOURCE_DOC_PRICING, False),
    ("Enterprise plans start at $499 per month.", SOURCE_DOC_PRICING, False),
    ("The Pro plan includes unlimited API calls.", SOURCE_DOC_PRICING, False),
    ("No free trial is available on any plan.", SOURCE_DOC_PRICING, False),
]

# Document used for latency and cache benchmarks
LATENCY_TEST_CLAIM = "Refunds are processed within 5-7 business days."
LATENCY_TEST_SOURCE = SOURCE_DOC_REFUND


# ─── Result Types ─────────────────────────────────────────────────────────────

@dataclass
class LatencyResult:
    cold_start_ms: float
    warm_avg_ms: float
    cache_hit_avg_ms: float
    warm_samples: int
    cache_samples: int
    speedup_factor: float  # warm / cache_hit ratio


@dataclass
class PrecisionResult:
    total_cases: int
    true_positives: int   # truly supported, TL says VERIFIED/UNCERTAIN
    true_negatives: int   # truly unsupported, TL says UNSUPPORTED
    false_positives: int  # truly unsupported, TL says VERIFIED (missed hallucination)
    false_negatives: int  # truly supported, TL says UNSUPPORTED (over-flagged)
    precision: float      # TP / (TP + FP)
    recall: float         # TP / (TP + FN)
    f1_score: float       # harmonic mean of precision and recall
    accuracy: float       # (TP + TN) / total


@dataclass
class CacheResult:
    first_call_ms: float
    subsequent_avg_ms: float
    cache_hits_reported: int
    cache_misses_reported: int
    cache_hit_rate_pct: float


@dataclass
class BenchmarkResults:
    timestamp: str
    api_url: str
    latency: LatencyResult
    precision: PrecisionResult
    cache: CacheResult
    total_api_calls: int
    total_duration_sec: float


# ─── Core Benchmarks ──────────────────────────────────────────────────────────

def _timed_verify(
    client: TruthLayer,
    claim: str,
    source: str,
) -> Tuple[float, VerificationResult]:
    """Call verify() and return (elapsed_ms, VerificationResult)."""
    t0 = time.perf_counter()
    result = client.verify(ai_response=claim, source_documents=[source])
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, result


def run_latency_benchmark(
    client: TruthLayer,
    warm_samples: int = 5,
    cache_samples: int = 5,
) -> Tuple[LatencyResult, int]:
    """
    Measure three latency tiers:
    - Cold start: first ever call (Lambda cold start + Bedrock)
    - Warm:       subsequent calls, same text (embedding not cached yet in early calls)
    - Cache hit:  calls after first — embedding served from DynamoDB
    """
    print("\n  [1/3] Latency Benchmark")
    print(f"        Claim: \"{LATENCY_TEST_CLAIM}\"")

    calls = 0

    # Cold start: first call
    print("        Running cold start call...", end=" ", flush=True)
    cold_ms, _ = _timed_verify(client, LATENCY_TEST_CLAIM, LATENCY_TEST_SOURCE)
    calls += 1
    print(f"{cold_ms:.0f}ms")

    # Warm calls (no guaranteed cache — use different but similar texts)
    warm_times = []
    warm_texts = [
        "Items must be unused and in original packaging.",
        "Digital products are non-refundable.",
        "Return shipping is the customer's responsibility.",
        "Returns are accepted within 30 days of purchase.",
        "Refunds take between 5 and 7 business days to process.",
    ]
    print(f"        Running {warm_samples} warm calls (live Bedrock)...", end=" ", flush=True)
    for text in warm_texts[:warm_samples]:
        ms, _ = _timed_verify(client, text, LATENCY_TEST_SOURCE)
        warm_times.append(ms)
        calls += 1
    warm_avg = sum(warm_times) / len(warm_times)
    print(f"avg {warm_avg:.0f}ms")

    # Cache hit calls: repeat the SAME text — embedding should be in DynamoDB now
    cache_times = []
    print(f"        Running {cache_samples} cache-hit calls (same text)...", end=" ", flush=True)
    for _ in range(cache_samples):
        ms, _ = _timed_verify(client, LATENCY_TEST_CLAIM, LATENCY_TEST_SOURCE)
        cache_times.append(ms)
        calls += 1
    cache_avg = sum(cache_times) / len(cache_times)
    speedup = warm_avg / cache_avg if cache_avg > 0 else 0
    print(f"avg {cache_avg:.0f}ms (speedup: {speedup:.1f}x)")

    result = LatencyResult(
        cold_start_ms=round(cold_ms, 2),
        warm_avg_ms=round(warm_avg, 2),
        cache_hit_avg_ms=round(cache_avg, 2),
        warm_samples=warm_samples,
        cache_samples=cache_samples,
        speedup_factor=round(speedup, 2),
    )
    return result, calls


def run_precision_benchmark(client: TruthLayer) -> Tuple[PrecisionResult, int]:
    """
    Measure classification accuracy against known ground truth.

    Each test case has a known correct label (supported / unsupported).
    We compute precision, recall, F1, and accuracy from TruthLayer's output.
    """
    print(f"\n  [2/3] Precision Benchmark ({len(PRECISION_TEST_CASES)} test cases)")

    tp = tn = fp = fn = 0
    calls = 0

    for i, (claim, source, is_supported) in enumerate(PRECISION_TEST_CASES, 1):
        try:
            result = client.verify(ai_response=claim, source_documents=[source])
            calls += 1

            # Consider VERIFIED and UNCERTAIN as "supported" (TruthLayer said yes)
            tl_says_supported = result.verified_count > 0 or result.uncertain_count > 0

            if is_supported and tl_says_supported:
                tp += 1
                verdict = "✓ TP"
            elif not is_supported and not tl_says_supported:
                tn += 1
                verdict = "✓ TN"
            elif not is_supported and tl_says_supported:
                fp += 1
                verdict = "✗ FP  ← missed hallucination"
            else:  # is_supported and not tl_says_supported
                fn += 1
                verdict = "✗ FN  ← over-flagged"

            label = "SUPPORTED" if is_supported else "HALLUCINATED"
            print(f"        [{i:2d}] {verdict}  | {label:<11} | {claim[:55]}")

        except TruthLayerError as e:
            print(f"        [{i:2d}] ERROR: {e}")

    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    result = PrecisionResult(
        total_cases=total,
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision * 100, 2),
        recall=round(recall * 100, 2),
        f1_score=round(f1 * 100, 2),
        accuracy=round(accuracy * 100, 2),
    )
    return result, calls


def run_cache_benchmark(client: TruthLayer, repeat: int = 10) -> Tuple[CacheResult, int]:
    """
    Measure cache hit rate and speedup by calling the same text repeatedly.
    Uses metadata.cache_hits and cache_misses reported by the API.
    """
    print(f"\n  [3/3] Cache Benchmark ({repeat} repeated calls, same text)")

    total_cache_hits = 0
    total_cache_misses = 0
    times = []
    calls = 0

    for i in range(repeat):
        t0 = time.perf_counter()
        result = client.verify(
            ai_response=LATENCY_TEST_CLAIM,
            source_documents=[LATENCY_TEST_SOURCE],
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        times.append(elapsed_ms)
        calls += 1

        hits = result.metadata.get("cache_hits", 0)
        misses = result.metadata.get("cache_misses", 0)
        total_cache_hits += hits
        total_cache_misses += misses
        status = f"hits={hits} misses={misses}"
        print(f"        Call {i+1:2d}: {elapsed_ms:6.0f}ms | {status}")

    first_call_ms = times[0]
    subsequent_avg_ms = sum(times[1:]) / len(times[1:]) if len(times) > 1 else times[0]
    total_ops = total_cache_hits + total_cache_misses
    hit_rate = (total_cache_hits / total_ops * 100) if total_ops > 0 else 0.0

    cache_result = CacheResult(
        first_call_ms=round(first_call_ms, 2),
        subsequent_avg_ms=round(subsequent_avg_ms, 2),
        cache_hits_reported=total_cache_hits,
        cache_misses_reported=total_cache_misses,
        cache_hit_rate_pct=round(hit_rate, 2),
    )
    return cache_result, calls


# ─── Report ───────────────────────────────────────────────────────────────────

def print_report(results: BenchmarkResults) -> None:
    """Print a clean, article-ready summary table."""
    l = results.latency
    p = results.precision
    c = results.cache

    print("\n")
    print("=" * 65)
    print("  TruthLayer Benchmark Results")
    print(f"  {results.timestamp}  |  {results.api_url}")
    print("=" * 65)

    print("\n  ── Latency ──────────────────────────────────────────────")
    print(f"  Cold start (Lambda init + Bedrock):  {l.cold_start_ms:>8.0f} ms")
    print(f"  Warm / live Bedrock ({l.warm_samples} samples):    {l.warm_avg_ms:>8.0f} ms")
    print(f"  Cache hit / DynamoDB ({l.cache_samples} samples):  {l.cache_hit_avg_ms:>8.0f} ms")
    print(f"  Cache speedup factor:                {l.speedup_factor:>8.1f}x")

    print("\n  ── Precision & Recall ───────────────────────────────────")
    print(f"  Test cases:    {p.total_cases}")
    print(f"  True Positive: {p.true_positives}   (supported → VERIFIED/UNCERTAIN)")
    print(f"  True Negative: {p.true_negatives}   (hallucinated → UNSUPPORTED)")
    print(f"  False Positive:{p.false_positives}   (hallucination missed ← critical)")
    print(f"  False Negative:{p.false_negatives}   (over-flagged)")
    print(f"  Precision:     {p.precision:>6.1f}%")
    print(f"  Recall:        {p.recall:>6.1f}%")
    print(f"  F1 Score:      {p.f1_score:>6.1f}%")
    print(f"  Accuracy:      {p.accuracy:>6.1f}%")

    print("\n  ── Cache Performance ────────────────────────────────────")
    print(f"  First call:       {c.first_call_ms:>8.0f} ms")
    print(f"  Subsequent avg:   {c.subsequent_avg_ms:>8.0f} ms")
    print(f"  Cache hits:       {c.cache_hits_reported}")
    print(f"  Cache misses:     {c.cache_misses_reported}")
    print(f"  Cache hit rate:   {c.cache_hit_rate_pct:>6.1f}%")

    print("\n  ── Summary ──────────────────────────────────────────────")
    print(f"  Total API calls:  {results.total_api_calls}")
    print(f"  Total duration:   {results.total_duration_sec:.1f}s")
    print("=" * 65)
    print()


def save_results(results: BenchmarkResults, output_dir: str) -> str:
    """Save results as JSON to output_dir. Returns path to saved file."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    # Filename: results_YYYYMMDD_HHMMSS.json
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = path / f"results_{ts}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(asdict(results), f, indent=2)

    return str(filename)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="TruthLayer API Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output", "-o",
        default="",
        help="Directory to save JSON results (default: print only)",
    )
    parser.add_argument(
        "--warm-samples",
        type=int,
        default=5,
        help="Number of warm (live) latency samples (default: 5)",
    )
    parser.add_argument(
        "--cache-samples",
        type=int,
        default=5,
        help="Number of cache-hit latency samples (default: 5)",
    )
    parser.add_argument(
        "--cache-repeat",
        type=int,
        default=10,
        help="Total calls for cache hit rate measurement (default: 10)",
    )
    args = parser.parse_args()

    api_url = os.environ.get("TRUTHLAYER_API_URL", "")
    api_key = os.environ.get("TRUTHLAYER_API_KEY", "")

    if not api_url or not api_key:
        print("Error: Set required environment variables:")
        print('  export TRUTHLAYER_API_URL="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"')
        print('  export TRUTHLAYER_API_KEY="tl_your_key_here"')
        return 1

    client = TruthLayer(api_key=api_key, api_url=api_url, timeout=60)

    print("=" * 65)
    print("  TruthLayer Benchmark Suite")
    print(f"  API: {api_url}")
    print(f"  Started: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 65)

    # Verify API is reachable before wasting time on tests
    try:
        health = client.health()
        print(f"\n  API Health: {health.get('status', 'unknown')} ✓")
    except Exception as e:
        print(f"\n  Error: API unreachable — {e}")
        return 1

    suite_start = time.perf_counter()
    total_calls = 0

    try:
        latency_result, n = run_latency_benchmark(
            client,
            warm_samples=args.warm_samples,
            cache_samples=args.cache_samples,
        )
        total_calls += n

        precision_result, n = run_precision_benchmark(client)
        total_calls += n

        cache_result, n = run_cache_benchmark(client, repeat=args.cache_repeat)
        total_calls += n

    except TruthLayerError as e:
        print(f"\n  Fatal: TruthLayer API error — {e}")
        return 1

    total_duration = time.perf_counter() - suite_start

    results = BenchmarkResults(
        timestamp=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        api_url=api_url,
        latency=latency_result,
        precision=precision_result,
        cache=cache_result,
        total_api_calls=total_calls,
        total_duration_sec=round(total_duration, 2),
    )

    print_report(results)

    if args.output:
        saved_path = save_results(results, args.output)
        print(f"  Results saved to: {saved_path}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
