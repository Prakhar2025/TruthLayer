# TruthLayer v2 — Technical Documentation

## Executive Summary

TruthLayer is a **production serverless API** that intercepts AI-generated text and passes it through a five-signal deterministic verification engine before it reaches users. Every AI output is decomposed into individual factual claims, which are verified against source documents using semantic embeddings from Amazon Bedrock Titan V2, corrected by four independent entity contradiction detectors, calibrated into posterior probabilities by Platt scaling, and cross-checked for internal self-consistency — all in under one second, at $1.50/month operational cost, with zero external Python dependencies.

TruthLayer is the only AI verification system with **statistically proven superiority** over cosine-only baselines, validated by McNemar's test (p < 0.001) on a 300-case adversarial benchmark, and the only system that detects when an AI response contradicts itself internally.

**AWS 10,000 AIdeas Competition — Top 50 Finalist. April 2026.**

---

## Live Deployment

| Resource | Value |
|----------|-------|
| **API Base URL** | `https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod` |
| **Region** | `us-east-1` |
| **Stack Name** | `truthlayer` |
| **Bedrock Model** | Amazon Titan Embeddings V2 (`amazon.titan-embed-text-v2:0`, 1024-dim) |
| **Dashboard** | [truth-layer.vercel.app](https://truth-layer.vercel.app) |
| **Health Check** | `GET /health` → `{"status": "healthy"}` |

---

## v2 Benchmark Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Precision** | **95.33%** | 300-case adversarial benchmark |
| **Recall** | **86.67%** | 300-case adversarial benchmark |
| **F1 Score** | **90.79%** | First crossing of 90% production barrier |
| **Accuracy** | **90.33%** | |
| **McNemar p-value** | **< 0.001** | Statistically proven superior |
| **Avg Latency** | ~925ms | End-to-end, Bedrock cold |
| **Cached Latency** | ~750ms | DynamoDB hit |
| **Test Suite** | **286 passing** | Zero regressions |
| **Operational Cost** | **~$1.50/month** | |
| **External Dependencies** | **Zero** | Python stdlib only |

---

## The Five Signals

| Signal | Technology | What It Catches |
|--------|-----------|-----------------|
| **1 — Semantic Embedding** | Bedrock Titan V2, 1024-dim cosine similarity | Semantic drift, topic mismatches |
| **2 — Numerical Contradiction** | Unit-aware regex, `(value, unit)` tuples | `400mg vs 40mg`, `99.9% vs 99.99%` |
| **3 — Negation / Antonyms** | S2A guard, 46 bidirectional antonym pairs | `"not permitted" vs "permitted"` |
| **4 — Temporal Contradiction** | Year disjointness, duration mismatch regex | `"adopted in 2014" vs "adopted in 2016"` |
| **5 — Intra-Response Consistency** | Pairwise `∀ i<j` entity check | AI self-contradictions (novel, unique) |

---

## Table of Contents

1. [System Architecture](./02_SYSTEM_ARCHITECTURE.md)
2. [API Specification](./03_API_SPECIFICATION.md)
3. [Database Schema Design](./04_DATABASE_SCHEMA.md)
4. [Core Algorithm Specification (v2)](./05_CORE_ALGORITHM.md)
5. [Verification Workflow](./06_VERIFICATION_WORKFLOW.md)
6. [Integration Guide](./07_INTEGRATION_GUIDE.md)
7. [Dashboard Specifications](./08_DASHBOARD_SPECS.md)
8. [Deployment Architecture](./09_DEPLOYMENT_ARCHITECTURE.md)
9. [Performance Benchmarks (v2)](./10_PERFORMANCE_BENCHMARKS.md)
10. [Risk Mitigation Plan](./11_RISK_MITIGATION.md)

**Top-level documents:**
- [README.md](../README.md) — project overview and quick start
- [BENCHMARK.md](../BENCHMARK.md) — research-grade benchmark whitepaper
- [CLAUDE.md](../CLAUDE.md) — full architecture reference for AI assistants

---

## Project Metadata

| Attribute | Value |
|-----------|-------|
| **Product Name** | TruthLayer |
| **Version** | **2.0** (Five-Signal Engine) |
| **Competition** | AWS 10,000 AIdeas 2026 — **Top 50 Finalist** |
| **Category** | AI Safety / Workplace Efficiency |
| **Infrastructure** | AWS Serverless (Lambda + API Gateway + DynamoDB + Bedrock) |
| **Primary Use Case** | AI output verification against source documents |
| **Secondary Capability** | Intra-response self-contradiction detection |
| **Target Customers** | Enterprise developers, regulated industries (healthcare, legal, finance) |
