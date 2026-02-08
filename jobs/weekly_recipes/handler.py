"""
Weekly vegan recipes job.

Fetches recipes from Nora Cooks dinner and lunch categories and emails 5 picks via SES.
"""

from __future__ import annotations

import json
import os
import random
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Iterable, List, Optional

RECIPE_PAGES = [
    "https://www.noracooks.com/category/meal-type/dinner/",
    "https://www.noracooks.com/category/meal-type/lunch/",
]

EXCLUDED_PATH_PREFIXES = {
    "category",
    "tag",
    "page",
    "wp-content",
    "wp-json",
    "author",
}

EXCLUDED_PATH_FRAGMENTS = {
    "privacy",
    "terms",
    "contact",
    "about",
    "disclaimer",
    "shop",
    "store",
    "print",
}


def main(event, context):
    """Lambda handler - fetch recipes and send email."""
    recipient = os.environ.get("RECIPIENT_EMAIL")
    sender = os.environ.get("SENDER_EMAIL")  # Must be verified in SES

    if not all([recipient, sender]):
        print("Missing required environment variables")
        return {"status": "error", "message": "Missing config"}

    recipes = []
    for url in RECIPE_PAGES:
        try:
            html = fetch_url(url)
            recipes.extend(extract_recipes(html, base_url=url))
        except Exception as exc:
            print(f"Failed to fetch or parse {url}: {exc}")

    recipes = dedupe_recipes(recipes)

    est_now = datetime.now(timezone(timedelta(hours=-5)))
    week_label = est_now.strftime("Week of %b %d, %Y")

    if not recipes:
        subject = f"Weekly Vegan Recipes - {week_label} - No recipes found"
        body = (
            "No recipes were found this week. "
            "Please check the source pages or parser rules.\n\n"
            "Sources:\n"
            f"- {RECIPE_PAGES[0]}\n"
            f"- {RECIPE_PAGES[1]}\n"
        )
    else:
        selected = pick_weekly_recipes(recipes, count=5, now=est_now)
        subject = f"Weekly Vegan Recipes - {week_label}"
        body = format_recipes(selected, week_label)

    print(f"Sending email: {subject}")
    success = send_email(sender, recipient, subject, body)

    if success:
        return {"status": "success", "recipe_count": len(recipes)}
    return {"status": "error", "message": "Failed to send email"}


class AnchorExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: List[dict] = []
        self._current: Optional[dict] = None
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag != "a":
            return
        attr_map = {key: value for key, value in attrs}
        self._current = {
            "href": attr_map.get("href"),
            "title_attr": attr_map.get("title"),
            "aria_label": attr_map.get("aria-label"),
        }
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current is None:
            return
        text = " ".join(self._text_parts).strip()
        text = " ".join(text.split())
        self._current["text"] = text
        self.anchors.append(self._current)
        self._current = None
        self._text_parts = []


def fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch content from a URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CronBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def extract_recipes(html: str, base_url: str) -> List[dict]:
    """Extract candidate recipe links from HTML."""
    parser = AnchorExtractor()
    parser.feed(html)

    recipes = []
    for anchor in parser.anchors:
        href = anchor.get("href")
        if not href:
            continue
        url = urllib.parse.urljoin(base_url, href)
        url = strip_url(url)

        if not is_recipe_url(url):
            continue

        title = pick_title(anchor)
        if not title:
            continue

        recipes.append({"title": title, "url": url})

    return recipes


def pick_title(anchor: dict) -> Optional[str]:
    """Choose the best title from anchor data."""
    candidates = [anchor.get("text"), anchor.get("aria_label"), anchor.get("title_attr")]
    for candidate in candidates:
        if not candidate:
            continue
        cleaned = " ".join(candidate.split()).strip()
        if 4 <= len(cleaned) <= 120:
            return cleaned
    return None


def is_recipe_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    host = parsed.netloc.lower()
    if host not in {"www.noracooks.com", "noracooks.com"}:
        return False

    path = parsed.path.strip("/")
    if not path:
        return False

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return False

    if segments[0].lower() in EXCLUDED_PATH_PREFIXES:
        return False

    for fragment in EXCLUDED_PATH_FRAGMENTS:
        if fragment in path.lower():
            return False

    return True


def strip_url(url: str) -> str:
    """Remove query params and fragments and normalize trailing slashes."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if path != "/":
        path = path.rstrip("/")
    cleaned = parsed._replace(query="", fragment="", path=path)
    return cleaned.geturl()


def dedupe_recipes(recipes: Iterable[dict]) -> List[dict]:
    """Deduplicate recipes by URL."""
    seen = set()
    deduped = []
    for recipe in recipes:
        url = recipe["url"].lower()
        if url in seen:
            continue
        seen.add(url)
        deduped.append(recipe)
    return deduped


def pick_weekly_recipes(recipes: List[dict], count: int, now: datetime) -> List[dict]:
    """Pick a deterministic set of recipes for the week."""
    year, week, _ = now.isocalendar()
    seed = f"{year}-W{week}"
    chooser = random.Random(seed)

    if len(recipes) <= count:
        return recipes

    return chooser.sample(recipes, count)


def format_recipes(recipes: List[dict], week_label: str) -> str:
    lines = [f"Weekly vegan recipe picks ({week_label})", ""]

    for idx, recipe in enumerate(recipes, start=1):
        lines.append(f"{idx}. {recipe['title']}")
        lines.append(f"   {recipe['url']}")
        lines.append("")

    lines.append("Sources:")
    for url in RECIPE_PAGES:
        lines.append(f"- {url}")

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
