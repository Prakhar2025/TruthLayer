"""AWS Lambda handler for health check endpoint."""

import json
import time


def handler(event, context):
    """Simple health check handler."""
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "OK"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
                "Access-Control-Allow-Methods": "GET,OPTIONS",
            }
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "healthy",
            "service": "TruthLayer",
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "region": context.invoked_function_arn.split(":")[3] if context else "local"
        }),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        }
    }
