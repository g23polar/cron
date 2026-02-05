"""
Google Service Account authentication using JWT.

Creates a signed JWT and exchanges it for an access token.
"""

import base64
import json
import os
import time
import urllib.request
import urllib.parse

import jwt


TOKEN_URI = "https://oauth2.googleapis.com/token"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def get_service_account_credentials() -> dict:
    """Load service account credentials from base64-encoded env var."""
    encoded = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
    if not encoded:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON_B64 not set")

    decoded = base64.b64decode(encoded)
    return json.loads(decoded)


def create_signed_jwt(credentials: dict, scope: str) -> str:
    """Create a signed JWT for Google OAuth2."""
    now = int(time.time())

    payload = {
        "iss": credentials["client_email"],
        "scope": scope,
        "aud": TOKEN_URI,
        "iat": now,
        "exp": now + 3600,  # 1 hour expiry
    }

    return jwt.encode(
        payload,
        credentials["private_key"],
        algorithm="RS256",
    )


def exchange_jwt_for_access_token(signed_jwt: str) -> str:
    """Exchange signed JWT for an access token."""
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": signed_jwt,
    }).encode("utf-8")

    req = urllib.request.Request(TOKEN_URI, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["access_token"]


def get_access_token() -> str:
    """Get a valid access token for Google Calendar API."""
    credentials = get_service_account_credentials()
    signed_jwt = create_signed_jwt(credentials, CALENDAR_SCOPE)
    return exchange_jwt_for_access_token(signed_jwt)
