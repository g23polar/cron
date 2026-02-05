"""
Google Calendar SMS job.

Fetches today's calendar events and sends SMS summary via AWS SNS.
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

from google_auth import get_access_token


def main(event, context):
    """Lambda handler - fetch calendar events and send SMS."""
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
    phone_number = os.environ.get("SMS_PHONE_NUMBER")

    if not calendar_id:
        print("Missing GOOGLE_CALENDAR_ID")
        return {"status": "error", "message": "Missing calendar ID"}

    if not phone_number:
        print("Missing SMS_PHONE_NUMBER")
        return {"status": "error", "message": "Missing phone number"}

    # Check for service account credentials
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64"):
        print("Missing GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        return {"status": "error", "message": "Missing Google credentials"}

    print("Fetching today's calendar events...")

    try:
        events = fetch_todays_events(calendar_id)
    except Exception as e:
        print(f"Failed to fetch events: {e}")
        return {"status": "error", "message": str(e)}

    message = format_events_for_sms(events)
    print(f"SMS message ({len(message)} chars):\n{message}")

    try:
        send_sms(phone_number, message)
        print("SMS sent successfully")
        return {"status": "success", "event_count": len(events)}
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return {"status": "error", "message": str(e)}


def fetch_todays_events(calendar_id: str) -> list:
    """Fetch today's events from Google Calendar API."""
    access_token = get_access_token()

    # Get today's date range in UTC
    # Using EST timezone offset (-5 hours) to get "today" in EST
    est_offset = timezone(timedelta(hours=-5))
    now_est = datetime.now(est_offset)
    today_start = now_est.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Convert to RFC3339 format
    time_min = today_start.isoformat()
    time_max = today_end.isoformat()

    encoded_calendar_id = urllib.parse.quote(calendar_id, safe="")
    params = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
    })

    url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events?{params}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data.get("items", [])


def format_events_for_sms(events: list) -> str:
    """Format calendar events into SMS-friendly text."""
    today = datetime.now(timezone(timedelta(hours=-5))).strftime("%a %b %d")

    if not events:
        return f"📅 {today}\nNo events scheduled."

    lines = [f"📅 {today}"]

    for event in events:
        summary = event.get("summary", "Untitled")

        # Handle all-day events vs timed events
        start = event.get("start", {})
        if "dateTime" in start:
            # Timed event - parse and format time in EST
            start_dt = datetime.fromisoformat(start["dateTime"])
            est_offset = timezone(timedelta(hours=-5))
            start_est = start_dt.astimezone(est_offset)
            time_str = start_est.strftime("%-I:%M%p").lower()
            lines.append(f"• {time_str} {summary}")
        else:
            # All-day event
            lines.append(f"• (all day) {summary}")

    return "\n".join(lines)


def send_sms(phone_number: str, message: str) -> None:
    """Send SMS via AWS SNS."""
    import boto3

    sns = boto3.client("sns")
    sns.publish(
        PhoneNumber=phone_number,
        Message=message,
    )
