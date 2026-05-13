"""
Broadway Direct lottery entry job.

Authenticates with Broadway Direct, discovers all shows currently running
a lottery, picks 2 at random, submits a 2-ticket entry for each, and
emails a confirmation summary via SES.

NOTE: Broadway Direct runs a React SPA backed by an undocumented REST API.
All endpoint constants and response field names are marked with "# VERIFY:"
comments — confirm them by inspecting network requests in browser DevTools
(Network tab → XHR/Fetch) while logging in and entering a lottery manually
at https://lottery.broadwaydirect.com before deploying.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Endpoint constants — VERIFY all of these against live network traffic
# ---------------------------------------------------------------------------
BASE_URL = "https://lottery.broadwaydirect.com"
LOGIN_URL = f"{BASE_URL}/api/v1/users/sign_in"              # VERIFY
LOTTERIES_URL = f"{BASE_URL}/api/v1/lotteries"              # VERIFY
ENTRY_URL_TEMPLATE = f"{BASE_URL}/api/v1/lotteries/{{lottery_id}}/entries"  # VERIFY

TICKETS_PER_ENTRY = 2
MAX_SHOWS = 2

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def main(event, context):
    """Lambda handler — orchestrates login → discover → pick → enter → email."""
    email = os.environ.get("BROADWAY_DIRECT_EMAIL")
    password = os.environ.get("BROADWAY_DIRECT_PASSWORD")
    first_name = os.environ.get("ENTRANT_FIRST_NAME")
    last_name = os.environ.get("ENTRANT_LAST_NAME")
    date_of_birth = os.environ.get("ENTRANT_DATE_OF_BIRTH")  # MM/DD/YYYY
    country = os.environ.get("ENTRANT_COUNTRY", "USA")
    zip_code = os.environ.get("ENTRANT_ZIP")
    recipient = os.environ.get("RECIPIENT_EMAIL")
    sender = os.environ.get("SENDER_EMAIL")

    missing = [
        k for k, v in {
            "BROADWAY_DIRECT_EMAIL": email,
            "BROADWAY_DIRECT_PASSWORD": password,
            "ENTRANT_FIRST_NAME": first_name,
            "ENTRANT_LAST_NAME": last_name,
            "ENTRANT_DATE_OF_BIRTH": date_of_birth,
            "ENTRANT_ZIP": zip_code,
            "RECIPIENT_EMAIL": recipient,
            "SENDER_EMAIL": sender,
        }.items()
        if not v
    ]
    if missing:
        print(f"Missing required environment variables: {missing}")
        return {"status": "error", "message": f"Missing config: {missing}"}

    entrant = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "date_of_birth": date_of_birth,
        "country": country,
        "zip": zip_code,
    }

    est_now = datetime.now(timezone(timedelta(hours=-5)))
    date_label = est_now.strftime("%a %b %d, %Y")

    # Step 1: authenticate
    print("Logging in to Broadway Direct...")
    opener = _build_opener()
    token = _login(opener, email, password)
    if not token:
        _send_error_email(sender, recipient, date_label, "Login failed — check credentials")
        return {"status": "error", "message": "Login failed"}

    # Step 2: fetch active lotteries
    print("Fetching active lotteries...")
    shows = _fetch_active_lotteries(opener, token)
    if shows is None:
        _send_error_email(sender, recipient, date_label, "Failed to fetch lottery listings")
        return {"status": "error", "message": "Failed to fetch lotteries"}

    if not shows:
        print("No active lotteries found this week")
        send_email(
            sender, recipient,
            subject=f"Broadway Lottery - {date_label} - No active lotteries",
            body="No Broadway Direct lotteries are currently active. Nothing was entered.",
        )
        return {"status": "success", "entered": []}

    # Step 3: pick up to 2 at random (true randomness — no seed)
    selected = random.sample(shows, min(MAX_SHOWS, len(shows)))
    print(f"Selected {len(selected)} show(s): {[s['name'] for s in selected]}")

    # Step 4: enter each selected lottery
    results = []
    for show in selected:
        print(f"Entering lottery for: {show['name']}")
        success, message = _enter_lottery(opener, token, show)
        results.append({"show": show["name"], "success": success, "message": message})
        if not success:
            print(f"Entry failed for {show['name']}: {message}")

    # Step 5: email confirmation
    subject, body = _format_email(results, date_label)
    print(f"Sending confirmation email: {subject}")
    send_email(sender, recipient, subject, body)

    entered = [r["show"] for r in results if r["success"]]
    return {"status": "success", "entered": entered}


# ---------------------------------------------------------------------------
# HTTP session helpers
# ---------------------------------------------------------------------------

def _build_opener() -> urllib.request.OpenerDirector:
    """Build a urllib opener with cookie jar and browser-like headers."""
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        ("Accept", "application/json, text/plain, */*"),
        ("Accept-Language", "en-US,en;q=0.9"),
        ("Origin", BASE_URL),
        ("Referer", f"{BASE_URL}/"),
    ]
    return opener


def _post_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    payload: dict,
    token: Optional[str] = None,
) -> Optional[dict]:
    """POST JSON body; return parsed response dict or None on error."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")  # VERIFY: auth header format
    try:
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"POST {url} error: {exc}")
        return None


def _get_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    token: Optional[str] = None,
) -> Optional[dict | list]:
    """GET JSON; return parsed response or None on error."""
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")  # VERIFY: auth header format
    try:
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"GET {url} error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Broadway Direct API calls
# ---------------------------------------------------------------------------

def _login(
    opener: urllib.request.OpenerDirector,
    email: str,
    password: str,
) -> Optional[str]:
    """
    POST credentials to Broadway Direct and return the auth token.

    VERIFY before deploying:
      - LOGIN_URL endpoint path
      - Request body field names (likely "email" / "password" but may differ)
      - Where the token lives in the response JSON:
          response["token"]  OR  response["data"]["token"]  OR  response["auth_token"]
    """
    payload = {
        "email": email,       # VERIFY: field name
        "password": password, # VERIFY: field name
    }
    resp = _post_json(opener, LOGIN_URL, payload)
    if not resp:
        print("Login request returned no response")
        return None

    # VERIFY: adjust key path to match actual response shape
    token = (
        resp.get("token")
        or resp.get("auth_token")
        or (resp.get("data") or {}).get("token")
    )
    if not token:
        print(f"Auth token not found in login response. Keys: {list(resp.keys())}")
        return None

    print("Login successful")
    return str(token)


def _fetch_active_lotteries(
    opener: urllib.request.OpenerDirector,
    token: str,
) -> Optional[list[dict]]:
    """
    Fetch all shows currently running a Broadway Direct lottery.
    Returns list of {"name": str, "id": str}, or None on request error.

    VERIFY before deploying:
      - LOTTERIES_URL endpoint path
      - Whether response is a bare list or wrapped: {"data": [...]} / {"lotteries": [...]}
      - Field names for show name:  "show_name" / "name" / "title"
      - Field name for lottery ID:  "id" / "lottery_id"
    """
    resp = _get_json(opener, LOTTERIES_URL, token)
    if resp is None:
        print("Lottery listings request failed")
        return None

    # Unwrap if necessary — VERIFY the actual response shape
    if isinstance(resp, list):
        items = resp
    elif isinstance(resp, dict):
        items = resp.get("data") or resp.get("lotteries") or resp.get("results") or []
    else:
        print(f"Unexpected lottery response type: {type(resp)}")
        return None

    shows = []
    for item in items:
        # VERIFY: correct field names for name and ID
        name = item.get("show_name") or item.get("name") or item.get("title")
        show_id = item.get("id") or item.get("lottery_id")
        if name and show_id:
            shows.append({"name": str(name), "id": str(show_id)})
        else:
            print(f"Skipping item missing name or id: {item}")

    print(f"Found {len(shows)} active lottery show(s)")
    return shows


def _enter_lottery(
    opener: urllib.request.OpenerDirector,
    token: str,
    show: dict,
) -> tuple[bool, str]:
    """
    Submit a 2-ticket lottery entry for one show.
    Returns (success: bool, message: str).

    VERIFY before deploying:
      - ENTRY_URL_TEMPLATE path pattern
      - Request body field name for ticket count: "num_tickets" / "ticket_count" / "quantity"
      - How success is signalled in the response:
          HTTP 201  OR  response["status"] in ("entered", "success", "confirmed")
    """
    url = ENTRY_URL_TEMPLATE.format(lottery_id=show["id"])
    payload = {
        "num_tickets": TICKETS_PER_ENTRY,  # VERIFY: field name
    }
    resp = _post_json(opener, url, payload, token)
    if resp is None:
        return False, "Request failed or timed out"

    # VERIFY: success indicator in response
    status = resp.get("status") or ""
    if status in ("entered", "success", "confirmed", "created"):
        return True, "Entered successfully"

    # Surface whatever error the API returned
    error_msg = resp.get("message") or resp.get("error") or resp.get("errors") or str(resp)
    print(f"Unexpected entry response for '{show['name']}': {resp}")
    return False, str(error_msg)


# ---------------------------------------------------------------------------
# Email formatting and sending
# ---------------------------------------------------------------------------

def _format_email(results: list[dict], date_label: str) -> tuple[str, str]:
    """Build confirmation email subject and body from entry results."""
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    if failures:
        subject = (
            f"Broadway Lottery - {date_label} - "
            f"{len(successes)} entered, {len(failures)} failed"
        )
    else:
        subject = f"Broadway Lottery - {date_label} - {len(successes)} show(s) entered ✓"

    lines = [f"Broadway Direct lottery entries — {date_label}", ""]

    if successes:
        lines.append("Entered successfully:")
        for r in successes:
            lines.append(f"  ✓ {r['show']} ({TICKETS_PER_ENTRY} tickets)")
        lines.append("")

    if failures:
        lines.append("Failed to enter:")
        for r in failures:
            lines.append(f"  ✗ {r['show']}: {r['message']}")
        lines.append("")

    lines.append("Broadway Direct will email you directly if you win a lottery.")
    lines.append(f"View your entries: {BASE_URL}")

    return subject, "\n".join(lines)


def _send_error_email(
    sender: str, recipient: str, date_label: str, reason: str
) -> None:
    """Send a brief job-failure notification."""
    send_email(
        sender, recipient,
        subject=f"Broadway Lottery - {date_label} - Job Error",
        body=(
            f"The Broadway lottery job failed to run.\n\n"
            f"Reason: {reason}\n\n"
            f"Check CloudWatch Logs for details."
        ),
    )


def send_email(sender: str, recipient: str, subject: str, body: str) -> bool:
    """Send an email via AWS SES."""
    import boto3

    ses = boto3.client("ses")
    try:
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        print("Email sent successfully")
        return True
    except Exception as exc:
        print(f"SES error: {exc}")
        return False
