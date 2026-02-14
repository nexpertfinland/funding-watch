"""Minimal funding watch script.

Reads URLs from sources.txt, tries to parse each URL as RSS first,
otherwise falls back to basic HTML parsing. Saves open/unknown results to funding_watch.csv.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, date
from typing import List, Dict, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

SOURCES_FILE = "sources.txt"
OUTPUT_FILE = "funding_watch.csv"

# Signals that a funding call is closed (Finnish + English).
CLOSED_SIGNALS = [
    "haku päättynyt",
    "haku on päättynyt",
    "ei haettavissa",
    "hakuaika päättyi",
    "suljettu",
    "closed",
    "application period ended",
    "no longer accepting applications",
    "deadline passed",
]


def read_sources(path: str) -> List[str]:
    """Read source URLs from a text file (one URL per line)."""
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip() and not line.startswith("#")]


def parse_date_string(value: str) -> Optional[date]:
    """Parse one date string from common Finnish/ISO formats.

    Supported examples: 14.2.2026, 14.02.2026, 2026-02-14
    """
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    # Handle day/month without leading zero (e.g. 14.2.2026)
    match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None


def find_date_in_text(text: str) -> Optional[date]:
    """Find first date mention from text using supported formats."""
    patterns = [
        r"\b\d{1,2}\.\d{1,2}\.\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            parsed = parse_date_string(match.group(0))
            if parsed:
                return parsed
    return None


def detect_status(text: str, date_string: str = "") -> str:
    """Return status for an item: open / unknown / closed."""
    lowered = text.lower()
    if any(signal in lowered for signal in CLOSED_SIGNALS):
        return "closed"

    closing_date = find_date_in_text(text) or parse_date_string(date_string)
    if closing_date:
        if closing_date < date.today():
            return "closed"
        return "open"

    return "unknown"


def is_open(text: str, date_string: str) -> bool:
    """Return True when item should be kept in output (open or unknown)."""
    return detect_status(text, date_string) in {"open", "unknown"}


def parse_rss(url: str) -> List[Dict[str, str]]:
    """Try to parse URL as RSS/Atom feed.

    Returns a list of rows. Empty list means RSS was not usable.
    """
    feed = feedparser.parse(url)
    if not getattr(feed, "entries", None):
        return []

    rows: List[Dict[str, str]] = []
    for entry in feed.entries[:5]:  # Keep output small and beginner-friendly.
        title = getattr(entry, "title", "No title")
        link = getattr(entry, "link", url)
        published = getattr(entry, "published", "")
        summary = getattr(entry, "summary", "")

        combined_text = f"{title} {summary}".strip()
        status = detect_status(combined_text, published)
        if is_open(combined_text, published):
            rows.append(
                {
                    "source_url": url,
                    "title": title,
                    "link": link,
                    "date": published or datetime.utcnow().date().isoformat(),
                    "status": status,
                }
            )
    return rows


def parse_html(url: str) -> List[Dict[str, str]]:
    """Fallback parser for regular HTML pages.

    Extracts page title and first link found on page.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    page_title = soup.title.string.strip() if soup.title and soup.title.string else "No title"
    first_link_tag = soup.find("a", href=True)
    first_link = first_link_tag["href"] if first_link_tag else url
    page_text = soup.get_text(" ", strip=True)

    status = detect_status(page_text, "")
    if not is_open(page_text, ""):
        return []

    return [
        {
            "source_url": url,
            "title": page_title,
            "link": first_link,
            "date": datetime.utcnow().date().isoformat(),
            "status": status,
        }
    ]


def collect_rows(sources: List[str]) -> List[Dict[str, str]]:
    """Collect rows from every source URL."""
    rows: List[Dict[str, str]] = []
    for url in sources:
        rss_rows = parse_rss(url)
        if rss_rows:
            rows.extend(rss_rows)
        else:
            rows.extend(parse_html(url))
    return rows


def write_csv(path: str, rows: List[Dict[str, str]]) -> None:
    """Write rows into CSV file with fixed columns."""
    fieldnames = ["source_url", "title", "link", "date", "status"]
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Run the full collection process."""
    sources = read_sources(SOURCES_FILE)
    rows = collect_rows(sources)
    write_csv(OUTPUT_FILE, rows)
    print(f"Done. Saved {len(rows)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
