"""
Premier League daily matches job.

Fetches today's Premier League matches from API-Football and sends email via SES.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone


def main(event, context):
    """Lambda handler - fetch matches and send email."""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    recipient = os.environ.get("RECIPIENT_EMAIL")
    sender = os.environ.get("SENDER_EMAIL")  # Must be verified in SES

    if not all([api_key, recipient, sender]):
        print("Missing required environment variables")
        return {"status": "error", "message": "Missing config"}

    # Get today's date in UTC
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Fetching Premier League matches for {today}")

    matches = fetch_matches(api_key, today)

    if matches is None:
        return {"status": "error", "message": "Failed to fetch matches"}

    if not matches:
        print("No matches today")
        # Still send email to confirm no matches
        subject = f"Premier League - {today} - No matches"
        body = "No Premier League matches scheduled for today."
    else:
        subject = f"Premier League - {today} - {len(matches)} match(es)"
        body = format_matches(matches)

    print(f"Sending email: {subject}")
    success = send_email(sender, recipient, subject, body)

    if success:
        return {"status": "success", "matches": len(matches) if matches else 0}
    else:
        return {"status": "error", "message": "Failed to send email"}


def fetch_matches(api_key: str, date: str) -> list | None:
    """Fetch Premier League matches for a given date from API-Football."""
    # Premier League ID is 39
    url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?league=39&season=2024&date={date}"

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", [])
    except Exception as e:
        print(f"API error: {e}")
        return None


def format_matches(matches: list) -> str:
    """Format matches into a readable email body."""
    lines = ["Today's Premier League Matches:", ""]

    for match in matches:
        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        venue = fixture.get("venue", {})

        home = teams.get("home", {}).get("name", "Unknown")
        away = teams.get("away", {}).get("name", "Unknown")

        # Parse kickoff time
        timestamp = fixture.get("timestamp", 0)
        kickoff = datetime.fromtimestamp(timestamp, timezone.utc)
        kickoff_str = kickoff.strftime("%H:%M UTC")

        venue_name = venue.get("name", "Unknown venue")

        lines.append(f"  {home} vs {away}")
        lines.append(f"    Kickoff: {kickoff_str}")
        lines.append(f"    Venue: {venue_name}")
        lines.append("")

    return "\n".join(lines)


def send_email(sender: str, recipient: str, subject: str, body: str) -> bool:
    """Send email via AWS SES."""
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
    except Exception as e:
        print(f"SES error: {e}")
        return False
