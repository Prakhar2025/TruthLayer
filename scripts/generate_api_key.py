"""
Generate a TruthLayer API key and store it in DynamoDB.

Usage:
    python scripts/generate_api_key.py [owner_name]

Example:
    python scripts/generate_api_key.py "Prakhar"
"""

import hashlib
import secrets
import sys
import time
import os

import boto3


def generate_api_key(owner="default"):
    """Generate a new API key and store the hash in DynamoDB."""

    # Generate a secure API key
    raw_key = f"tl_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Store in DynamoDB
    region = os.environ.get("AWS_REGION", "us-east-1")
    table_name = os.environ.get("APIKEYS_TABLE", "TruthLayerApiKeys")

    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    table.put_item(Item={
        "api_key_hash": key_hash,
        "owner": owner,
        "created_at": int(time.time()),
        "is_active": True,
        "permissions": ["verify", "documents", "analytics"],
        "rate_limit": 1000,  # requests per day
        "usage_count": 0,
    })

    print("\n" + "=" * 60)
    print("  🔑 TruthLayer API Key Generated")
    print("=" * 60)
    print(f"\n  Owner: {owner}")
    print(f"  API Key: {raw_key}")
    print(f"  Key Hash: {key_hash[:16]}...")
    print(f"\n  ⚠️  Save this key! It cannot be retrieved later.")
    print(f"\n  Usage:")
    print(f"    curl -H 'x-api-key: {raw_key}' https://YOUR-API/prod/verify")
    print("=" * 60)

    return raw_key


if __name__ == "__main__":
    owner = sys.argv[1] if len(sys.argv) > 1 else "default"
    generate_api_key(owner)
