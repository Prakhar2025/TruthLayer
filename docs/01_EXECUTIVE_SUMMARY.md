# TruthLayer Technical Documentation

## Executive Summary

TruthLayer is a real-time AI hallucination firewall that verifies AI-generated outputs against authoritative source documents using semantic similarity matching powered by Amazon Bedrock Titan Embeddings V2.

The system intercepts AI responses, extracts individual factual claims, embeds each claim using 1024-dimensional vectors, matches them against uploaded reference documents via cosine similarity, and returns confidence-scored verification results — all within a sub-500ms latency target (sub-100ms roadmap with embedding caching).

Built entirely on AWS serverless architecture (Lambda, API Gateway, DynamoDB, and Amazon Bedrock), TruthLayer operates within AWS Free Tier constraints while providing enterprise-grade verification capabilities. The platform includes a real-time Next.js dashboard for monitoring verification metrics, developer-friendly REST APIs for seamless integration, and a color-coded trust scoring system (🟢 VERIFIED / 🟡 UNCERTAIN / 🔴 UNSUPPORTED) for immediate visual feedback on AI output reliability.

---

## Live Deployment

| Resource | Value |
|----------|-------|
| **API Base URL** | `https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod` |
| **Region** | `us-east-1` |
| **Stack Name** | `truthlayer` |
| **Bedrock Model** | Amazon Titan Embeddings V2 (`amazon.titan-embed-text-v2:0`) |
| **Health Check** | `GET /health` → `{"status": "healthy"}` |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| **Verification Precision** | 94.53% (measured on live deployment) |
| **Warm Latency** | ~450ms (Bedrock embedding call dominates) |
| **Cold Start** | ~600ms (p99) |
| **Lambda Memory** | 1024 MB (verify), 256 MB (health) |
| **Embedding Dimensions** | 1024 (Titan V2) |
| **Classification Thresholds** | VERIFIED ≥ 0.80 · UNCERTAIN ≥ 0.55 · UNSUPPORTED < 0.55 |

---

## Table of Contents

1. [System Architecture](./02_SYSTEM_ARCHITECTURE.md)
2. [API Specification](./03_API_SPECIFICATION.md)
3. [Database Schema Design](./04_DATABASE_SCHEMA.md)
4. [Core Algorithm Specification](./05_CORE_ALGORITHM.md)
5. [Verification Workflow](./06_VERIFICATION_WORKFLOW.md)
6. [Integration Guide](./07_INTEGRATION_GUIDE.md)
7. [Dashboard Specifications](./08_DASHBOARD_SPECS.md)
8. [Deployment Architecture](./09_DEPLOYMENT_ARCHITECTURE.md)
9. [Performance Benchmarks](./10_PERFORMANCE_BENCHMARKS.md)
10. [Risk Mitigation Plan](./11_RISK_MITIGATION.md)

---

## Project Metadata

| Attribute | Value |
|-----------|-------|
| **Product Name** | TruthLayer |
| **Version** | 1.0.0 |
| **Competition** | AWS 10,000 AIdeas 2025 — Top 1,000 Semi-Finalist |
| **Category** | Workplace Efficiency |
| **Target Latency** | < 500ms (< 100ms with caching — roadmap) |
| **Infrastructure** | AWS Serverless (Free Tier + Bedrock) |
| **Primary Use Case** | AI output verification against source documents |
| **Target Customers** | Enterprise developers, regulated industries (healthcare, legal, finance) |
