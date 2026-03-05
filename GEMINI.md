# TruthLayer — AI Context for Gemini

> Read CLAUDE.md first — it contains the full architecture, rules, and commands.
> This file contains Gemini-specific guidance and session continuity notes.

---

## Session Continuity

When starting a new session, always:
1. Read `CLAUDE.md` for full architecture context
2. Run `git log --oneline -5` to see recent changes
3. Run `pytest tests/ -v` to verify tests pass before making changes

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
**This is NOT a real failure.** Verify the build succeeded by checking:
```powershell
Test-Path .aws-sam\build\VerifyFunction\handler.py  # Should return True
```

### sam deploy Exit Code
Same issue — `sam deploy` returns exit code 1 on Windows but CloudFormation updates successfully.
Verify by checking output for `UPDATE_COMPLETE` strings.

### API Key Generation
The generate_api_key.py script outputs emoji characters (🔑, ⚠️) that cause encoding errors on Windows.
Use this inline alternative to capture the full key:
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

### Testing Auth Without cURL
Use PowerShell `Invoke-WebRequest`:
```powershell
# 401 — no key
Invoke-WebRequest -Uri "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/verify" -Method POST -ContentType "application/json" -Body '{"ai_response":"test","source_documents":["test"]}' -UseBasicParsing

# 200 — valid key
Invoke-WebRequest -Uri "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/verify" -Method POST -ContentType "application/json" -Headers @{"x-api-key"="YOUR_KEY"} -Body '{"ai_response":"Python 3.11 is faster.","source_documents":["Python 3.11 has speedup."]}' -UseBasicParsing
```

---

## Known Issues & Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Lambda returns SERVICE_UNAVAILABLE on auth | Missing `DynamoDBReadPolicy` for `ApiKeysTable` | Add policy to template.yaml |
| `src/lib/` not committing | `lib/` in root .gitignore caught dashboard path | Changed to `/lib/` (root-only) |
| Badges stacking vertically in README | Missing `<p align="center">` opening tag | Always ensure tag is at line 1 |
| sam build reports exit 1 | PowerShell stderr noise | Not a real error, check .aws-sam/build/ |
| `content` in DynamoDB ProjectionExpression | `content` is a reserved word — throws ValidationException | Use `ExpressionAttributeNames={"#c": "content"}` |
| `layer/python/` showing in git status | Files were committed before gitignore rule | Run `git rm -r --cached layer/python/` once |

---

## Active API Key
The current API key is in `dashboard/.env.local` (NOT committed).
The key format is `tl_{43_chars}`. Never commit real keys.

## AWS Budget
Set to **$20/month**. Alerts at 85% ($17) and 100% ($20).

---

## Competition Deadline
**March 13, 2026** — Semi-finalist prototype article due.
Status: Embedding caching ✓, Document IDs ✓, Rate limiting ✓, 3 integrations ✓
