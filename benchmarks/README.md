# TruthLayer Benchmark Suite

Measures real API performance. Produces article-ready numbers.

## Run

```bash
export TRUTHLAYER_API_URL="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"
export TRUTHLAYER_API_KEY="tl_your_key_here"

# Print results only
python benchmarks/run_benchmarks.py

# Save JSON results
python benchmarks/run_benchmarks.py --output benchmarks/results/
```

## What It Measures

### 1. Latency (3 tiers)
| Tier | What | Expected |
|------|------|----------|
| Cold start | First Lambda call (container init + Bedrock) | ~400–900ms |
| Warm / live | Subsequent unique texts — Bedrock called | ~100–200ms |
| Cache hit | Repeated same text — served from DynamoDB | ~20–60ms |

### 2. Precision & Recall
18 hand-crafted test cases with known ground truth:
- 10 genuinely supported claims → should be VERIFIED/UNCERTAIN
- 8 hallucinated claims → should be UNSUPPORTED

Metrics computed:
- **Precision** — when TruthLayer says VERIFIED, how often correct?
- **Recall** — of all truly supported claims, how many caught?
- **F1 Score** — harmonic mean of precision and recall
- **Accuracy** — overall classification accuracy

### 3. Cache Hit Rate
10 repeated calls with identical text. Reports:
- `cache_hits` and `cache_misses` from API metadata
- Cache hit rate percentage after warmup

## Sample Output

```
=================================================================
  TruthLayer Benchmark Results
  2026-03-05 12:30:00 UTC  |  https://...amazonaws.com/prod
=================================================================

  ── Latency ──────────────────────────────────────────────
  Cold start (Lambda init + Bedrock):       847 ms
  Warm / live Bedrock (5 samples):          134 ms
  Cache hit / DynamoDB (5 samples):          23 ms
  Cache speedup factor:                      5.8x

  ── Precision & Recall ───────────────────────────────────
  Test cases:    18
  True Positive: 10   (supported → VERIFIED/UNCERTAIN)
  True Negative:  7   (hallucinated → UNSUPPORTED)
  False Positive: 1   (hallucination missed ← critical)
  False Negative: 0   (over-flagged)
  Precision:      91.7%
  Recall:        100.0%
  F1 Score:       95.7%
  Accuracy:       94.4%

  ── Cache Performance ────────────────────────────────────
  First call:           312 ms
  Subsequent avg:        28 ms
  Cache hits:            18
  Cache misses:           9
  Cache hit rate:       66.7%
=================================================================
```

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | (none) | Directory to save JSON results |
| `--warm-samples` | 5 | Warm latency sample count |
| `--cache-samples` | 5 | Cache-hit latency sample count |
| `--cache-repeat` | 10 | Calls for cache hit rate test |
