# TruthLayer — LangChain Integration

[![PyPI](https://img.shields.io/badge/pip-truthlayer--sdk-blue)](https://pypi.org/project/truthlayer-sdk)
[![LangChain](https://img.shields.io/badge/LangChain-compatible-green)](https://python.langchain.com)

Add automatic AI hallucination detection to any LangChain chain in one line.

---

## Install

```bash
pip install truthlayer-sdk langchain-core
```

---

## Two Integration Modes

### Mode 1: Output Parser — Blocks Hallucinations

Intercepts the LLM output **before** it reaches the user. Raises `HallucinationDetectedError` if the response doesn't meet your trust threshold.

```python
from integrations.langchain.truthlayer_langchain import (
    TruthLayerOutputParser,
    HallucinationDetectedError,
)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Your source of truth
COMPANY_POLICY = """
Refunds are processed within 5-7 business days.
Products must be returned within 30 days.
Shipping costs are non-refundable.
"""

parser = TruthLayerOutputParser(
    api_key="tl_your_key_here",
    api_url="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod",
    source_documents=[COMPANY_POLICY],
    min_trust_score=75.0,  # Block if < 75% claims verified
)

prompt = ChatPromptTemplate.from_messages([
    ("system", f"Answer using only this policy:\n{COMPANY_POLICY}"),
    ("human", "{question}"),
])

chain = prompt | ChatOpenAI(model="gpt-4") | parser

try:
    result = chain.invoke({"question": "What is the refund timeline?"})
    print(f"Trust score: {result.trust_score:.1f}%")  # 91.6%
    print(f"Safe to send: {result.is_safe}")           # True
    print(result.text)  # The original LLM response

except HallucinationDetectedError as e:
    print(f"Blocked: {e}")
    print(f"Unsupported claims: {e.output.unsupported_claims}")
    # Route to human review
```

---

### Mode 2: Callback Handler — Passive Monitoring

Runs verification **after** every LLM call without changing the output. Use for logging, analytics, and alerting.

```python
from integrations.langchain.truthlayer_langchain import TruthLayerCallbackHandler
from langchain_openai import ChatOpenAI

def alert_on_hallucination(result):
    """Called when hallucination is detected — send to Slack, PagerDuty, etc."""
    print(f"⚠ Hallucination detected: {result.unsupported_count} unsupported claims")

handler = TruthLayerCallbackHandler(
    api_key="tl_your_key_here",
    api_url="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod",
    source_documents=[COMPANY_POLICY],
    on_hallucination=alert_on_hallucination,
)

llm = ChatOpenAI(model="gpt-4", callbacks=[handler])

# Use normally — verification runs in background
response = llm.invoke("What is the refund policy?")
print(response.content)

# Check aggregated metrics after multiple calls
print(handler.summary())
# {
#   "total_calls": 10,
#   "hallucination_count": 2,
#   "hallucination_rate_pct": 20.0,
#   "avg_latency_ms": 134.5
# }
```

---

## Using Pre-Uploaded Documents

Instead of sending source text on every call, upload once and reuse by ID:

```python
from sdk.python.truthlayer import TruthLayer

client = TruthLayer(api_key="tl_xxx", api_url="https://...")

# Upload once
doc = client.upload_document(content=COMPANY_POLICY, title="Return Policy")
doc_id = doc["document_id"]

# Verify using ID (much faster — no re-embedding)
parser = TruthLayerOutputParser(
    api_key="tl_xxx",
    api_url="https://...",
    document_ids=[doc_id],   # ← reference by ID
    min_trust_score=75.0,
)
```

---

## VerifiedOutput Fields

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Original LLM response |
| `trust_score` | `float` | 0-100, % of claims verified |
| `is_safe` | `bool` | `trust_score >= min_trust_score` |
| `verified_claims` | `list` | Claims with VERIFIED status |
| `unsupported_claims` | `list` | Claims NOT in source docs |
| `uncertain_claims` | `list` | Claims with low confidence |
| `result.latency_ms` | `float` | TruthLayer API response time |

---

## Error Handling

```python
from integrations.langchain.truthlayer_langchain import HallucinationDetectedError
from sdk.python.truthlayer import TruthLayerError

try:
    result = chain.invoke({"question": "..."})
except HallucinationDetectedError as e:
    # LLM hallucinated — e.output has full details
    for claim in e.output.unsupported_claims:
        print(f"Unsupported: {claim.text}")
except TruthLayerError as e:
    # API unavailable — use fail_open=True to bypass
    print(f"TruthLayer error: {e}")
```

Use `fail_open=True` if you want the chain to continue even when TruthLayer is unreachable:

```python
parser = TruthLayerOutputParser(..., fail_open=True)
```
