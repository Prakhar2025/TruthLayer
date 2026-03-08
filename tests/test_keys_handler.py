"""
Tests for the API key generation Lambda handler.

Tests cover input validation, key generation, rate limiting,
and error handling — all using mocked DynamoDB.
"""

import json
import sys
import os
import importlib.util
from unittest.mock import MagicMock, patch

import pytest

# Add repo root
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _repo_root)

# Import handler directly via importlib (the directory is named "lambda" which
# is a Python reserved keyword — can't use normal import syntax)
_handler_path = os.path.join(_repo_root, "lambda", "keys", "handler.py")
_spec = importlib.util.spec_from_file_location("keys_handler", _handler_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

handler_fn = _module.handler


def _make_event(body: dict, method: str = "POST") -> dict:
    """Create a minimal API Gateway event."""
    return {
        "httpMethod": method,
        "body": json.dumps(body),
        "headers": {},
    }


@pytest.fixture(autouse=True)
def reset_table():
    """Reset the global table reference before each test."""
    _module._keys_table = None


@pytest.fixture
def mock_table():
    """Provide a mocked DynamoDB table and inject it into the handler."""
    table = MagicMock()
    table.scan.return_value = {"Count": 0}
    table.put_item.return_value = {}

    # Inject the mock table directly — bypasses boto3 entirely
    _module._keys_table = table
    yield table
    _module._keys_table = None


class TestKeysHandler:

    def test_options_returns_200(self):
        """CORS preflight returns 200."""
        event = _make_event({}, method="OPTIONS")
        result = handler_fn(event, None)
        assert result["statusCode"] == 200

    def test_get_returns_405(self):
        """GET method returns 405 Method Not Allowed."""
        event = _make_event({}, method="GET")
        result = handler_fn(event, None)
        assert result["statusCode"] == 405
        body = json.loads(result["body"])
        assert body["error"] == "METHOD_NOT_ALLOWED"

    def test_missing_owner_returns_400(self, mock_table):
        """Missing owner field returns 400."""
        event = _make_event({"email": "test@example.com"})
        result = handler_fn(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"] == "MISSING_FIELD"
        assert "owner" in body["message"]

    def test_missing_email_returns_400(self, mock_table):
        """Missing email field returns 400."""
        event = _make_event({"owner": "Test User"})
        result = handler_fn(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"] == "MISSING_FIELD"
        assert "email" in body["message"]

    def test_invalid_email_returns_400(self, mock_table):
        """Email without proper format returns 400."""
        event = _make_event({"owner": "Test", "email": "notanemail"})
        result = handler_fn(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"] == "INVALID_EMAIL"

    def test_successful_key_generation(self, mock_table):
        """Valid request creates key and returns 201."""
        event = _make_event({
            "owner": "Test User",
            "email": "test@example.com",
            "use_case": "Testing",
        })
        result = handler_fn(event, None)
        assert result["statusCode"] == 201

        body = json.loads(result["body"])
        assert body["api_key"].startswith("tl_")
        assert len(body["api_key"]) == 46  # tl_ + 43 chars from token_urlsafe(32)
        assert body["owner"] == "Test User"
        assert "verify" in body["permissions"]
        assert body["rate_limit"] == 1000

        # Verify put_item was called with hash, NOT raw key
        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]["Item"]
        assert "api_key_hash" in item
        assert item["api_key_hash"] != body["api_key"]  # hash != raw
        assert len(item["api_key_hash"]) == 64  # SHA-256 hex digest

    def test_key_limit_reached_returns_429(self, mock_table):
        """More than 5 active keys per email returns 429."""
        mock_table.scan.return_value = {"Count": 5}
        event = _make_event({
            "owner": "Test",
            "email": "overuse@example.com",
        })
        result = handler_fn(event, None)
        assert result["statusCode"] == 429
        body = json.loads(result["body"])
        assert body["error"] == "KEY_LIMIT_REACHED"

    def test_invalid_json_body_returns_400(self):
        """Invalid JSON body returns 400."""
        event = {
            "httpMethod": "POST",
            "body": "not-json{{{",
            "headers": {},
        }
        result = handler_fn(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"] == "INVALID_JSON"

    def test_cors_headers_present(self, mock_table):
        """All responses include CORS headers."""
        event = _make_event({"owner": "Test", "email": "t@e.com"})
        result = handler_fn(event, None)
        headers = result["headers"]
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "Content-Type" in headers

    def test_null_body_handled(self, mock_table):
        """Null body doesn't crash — treated as empty JSON."""
        event = {"httpMethod": "POST", "body": None, "headers": {}}
        result = handler_fn(event, None)
        assert result["statusCode"] == 400  # missing owner
