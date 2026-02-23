#!/bin/bash
# TruthLayer API Test Script
# Run this after deployment to verify all endpoints work

API_URL="${1:-https://YOUR-API-URL/prod}"
API_KEY="${2:-your-api-key}"

echo "=================================================="
echo "  TruthLayer API Test Suite"
echo "  API: $API_URL"
echo "=================================================="

# 1. Health Check
echo ""
echo "--- 1. Health Check ---"
curl -s "$API_URL/health" | python -m json.tool
echo ""

# 2. Upload a Document
echo "--- 2. Upload Document ---"
DOC_RESPONSE=$(curl -s -X POST "$API_URL/documents" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "title": "Python 3.11 Release Notes",
    "content": "Python 3.11 was officially released on October 24, 2022. This release includes performance improvements of up to 25% faster than Python 3.10. New features include exception groups (PEP 654) and improved error messages with fine-grained location information."
  }')
echo "$DOC_RESPONSE" | python -m json.tool
DOC_ID=$(echo "$DOC_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('document_id', ''))" 2>/dev/null)
echo "Document ID: $DOC_ID"
echo ""

# 3. List Documents
echo "--- 3. List Documents ---"
curl -s "$API_URL/documents" \
  -H "x-api-key: $API_KEY" | python -m json.tool
echo ""

# 4. Verify AI Response
echo "--- 4. Verify AI Response ---"
curl -s -X POST "$API_URL/verify" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "ai_response": "Python 3.11 was released in October 2022. It is 25% faster than Python 3.10 and includes exception groups.",
    "source_documents": [
      "Python 3.11 was officially released on October 24, 2022. This release includes performance improvements of up to 25% faster than Python 3.10. New features include exception groups (PEP 654) and improved error messages."
    ]
  }' | python -m json.tool
echo ""

# 5. Get Analytics
echo "--- 5. Analytics Summary ---"
curl -s "$API_URL/analytics?action=summary" \
  -H "x-api-key: $API_KEY" | python -m json.tool
echo ""

# 6. Delete Document (if created)
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "" ]; then
  echo "--- 6. Delete Document ---"
  curl -s -X DELETE "$API_URL/documents/$DOC_ID" \
    -H "x-api-key: $API_KEY" | python -m json.tool
  echo ""
fi

echo "=================================================="
echo "  ✅ All tests complete!"
echo "=================================================="
