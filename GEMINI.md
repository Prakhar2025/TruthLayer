# TruthLayer — AI Context for Gemini

> Read CLAUDE.md first — it contains the full v2 architecture, rules, and commands.
> This file contains Gemini-specific guidance and session continuity notes.

---

## Session Continuity

When starting a new session, always:
1. Read `CLAUDE.md` for full v2 architecture context
2. Run `git log --oneline -5` to see recent changes
3. Run `pytest tests/ -v` to verify all **286 tests** pass before making changes

---

## v2 Architecture Summary

TruthLayer v2 is a **five-signal deterministic verification engine**:

| Signal | File | Description |
|--------|------|-------------|
| Signal 1 | `embeddings/bedrock_provider.py` | Titan V2 cosine similarity |
| Signal 2 | `verifier/entity_checker.py` | Numerical contradiction (unit-aware) |
| Signal 3 | `verifier/entity_checker.py` | Negation + semantic antonyms (S2A guard) |
| Signal 4 | `verifier/entity_checker.py` | Temporal contradiction (year + duration) |
| Signal 5 | `verifier/verifier.py` | Intra-response pairwise consistency |
| Calibration | `verifier/calibration.py` | Platt scaling σ(12.07·x − 6.64) |
| Stats proof | `stats/mcnemar.py` | McNemar's test via math.erfc |

---

## Gemini-Specific Notes

### Build Process (Critical)
Before EVERY `sam build`, copy src/ to layer:
```python
import shutil
shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)
```
Without this, Lambda Layer will NOT have the latest `src/` code.

### sam build Exit Code
`sam build` on Windows PowerShell always returns exit code 1 (PowerShell stderr noise).
**This is NOT a real failure.** Verify success by checking:
```powershell
Test-Path .aws-sam\build\VerifyFunction\handler.py  # Should return True
```

### sam deploy Exit Code
Same issue — `sam deploy` returns exit code 1 on Windows but CloudFormation updates successfully.
Verify by checking output for `UPDATE_COMPLETE` strings.

### API Key Generation
The generate_api_key.py script outputs emoji characters that cause encoding errors on Windows.
Use this inline alternative:
```python
python -c "
import hashlib, secrets, time, boto3
raw_key = 'tl_' + secrets.token_urlsafe(32)
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('TruthLayerApiKeys')
table.put_item(Item={'api_key_hash': key_hash, 'owner': 'Name', 'created_at': int(time.time()), 'is_active': True, 'permissions': ['verify', 'documents', 'analytics'], 'rate_limit': 1000, 'usage_count': 0})
with open('tmp_key.txt', 'w') as f: f.write(raw_key)
print('Length: ' + str(len(raw_key)))
"
Get-Content tmp_key.txt
Remove-Item tmp_key.txt
```

### Testing Auth Without cURL (Windows PowerShell)
```powershell
# 401 — no key
Invoke-WebRequest -Uri "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/verify" -Method POST -ContentType "application/json" -Body '{"ai_response":"test","source_documents":["test"]}' -UseBasicParsing

# 200 — valid key
Invoke-WebRequest -Uri "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/verify" -Method POST -ContentType "application/json" -Headers @{"x-api-key"="YOUR_KEY"} -Body '{"ai_response":"Python 3.11 is faster.","source_documents":["Python 3.11 has speedup."]}' -UseBasicParsing
```

### Unicode in PowerShell Scripts
Windows PowerShell uses cp1252 encoding by default. Any script that prints Unicode characters (α, χ², →, ✓) will crash with `UnicodeEncodeError`. Always use ASCII equivalents in scripts that print to stdout.

---

## Known Issues & Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Lambda returns SERVICE_UNAVAILABLE on auth | Missing `DynamoDBReadPolicy` for `ApiKeysTable` | Add policy to template.yaml |
| `src/lib/` not committing | `lib/` in root .gitignore caught dashboard path | Changed to `/lib/` (root-only) |
| Badges stacking vertically in README | Missing `<p align="center">` opening tag | Ensure tag is at line 1 |
| sam build reports exit 1 | PowerShell stderr noise | Not a real error, check .aws-sam/build/ |
| `content` in DynamoDB ProjectionExpression | `content` is a reserved word | `ExpressionAttributeNames={"#c": "content"}` |
| `layer/python/` showing in git status | Files committed before gitignore rule | `git rm -r --cached layer/python/` |
| S2A fires on faithful negation pairs | Blunt `has_negation()` check | `_s2a_is_genuine_contradiction()` 3-stage tree |
| `without` in negation window causes false fire | `"without"` is conditional prep, not predicate negator | Removed from `_SOFT_NEG_WORDS` |
| Unicode in run_mcnemar.py output | PowerShell cp1252 can't render α, χ², → | Replaced with ASCII: alpha, chi2, -> |

---

## Active API Key
Current API key is in `dashboard/.env.local` (NOT committed).
Format: `tl_{43_chars}`. Never commit real keys.

## AWS Budget
Set to **$20/month**. Alerts at 85% ($17) and 100% ($20).

---

## Competition Deadline
**April 17, 2026** — Top 50 Finalist article due.  
Community voting April 17–23. Winners announced April 30.

## Current Benchmark State (April 2026)
| Metric | Value | Notes |
|--------|-------|-------|
| Precision | **95.33%** | 7 hallucinations escaped (Cat B+C edge cases) |
| Recall | **86.67%** | 22 faithful over-flagged (13 Type A embedding floor) |
| F1 | **90.79%** | First time crossing 90% production barrier |
| Accuracy | **90.33%** | |
| Latency | ~925ms | Avg end-to-end across 300 cases |
| Tests | **286** | All passing, zero regressions |
| McNemar p | **< 0.001** | χ² > 10.828 at Bedrock embeddings |

## Completed v2 Features (All Committed)
- ✅ Signal 4: Temporal Contradiction Engine (`feat(verifier): add temporal contradiction detection`)
- ✅ Platt Scaling Calibration (`feat(verifier): implement Platt Scaling confidence calibration`)
- ✅ McNemar's Test Statistical Proof (`feat(stats): implement McNemar's test`)
- ✅ Intra-Response Consistency (`feat(verifier): intra-response consistency check — Signal 5`)
- ✅ Documentation v2 (`docs: v2 documentation — README, BENCHMARK, CLAUDE, GEMINI`)
