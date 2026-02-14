"""Minimal funding watch script.

Reads URLs from sources.txt, tries to parse each URL as RSS first,
otherwise falls back to basic HTML parsing. Saves results to funding_watch.csv.
"""

from __future__ import annotations

import csv
from datetime import datetime
from typing import List, Dict

import feedparser
import requests
from bs4 import BeautifulSoup

SOURCES_FILE = "sources.txt"
OUTPUT_FILE = "funding_watch.csv"


def read_sources(path: str) -> List[str]:
    """Read source URLs from a text file (one URL per line)."""
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip() and not line.startswith("#")]


def parse_rss(url: str) -> List[Dict[str, str]]:
    """Try to parse URL as RSS/Atom feed.

    Returns a list of rows. Empty list means RSS was not usable.
    """
    feed = feedparser.parse(url)
    if not getattr(feed, "entries", None):
        return []

    rows: List[Dict[str, str]] = []
    for entry in feed.entries[:5]:  # Keep output small and beginner-friendly.
        rows.append(
            {
                "source_url": url,
                "title": getattr(entry, "title", "No title"),
                "link": getattr(entry, "link", url),
                "date": getattr(entry, "published", datetime.utcnow().date().isoformat()),
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

    return [
        {
            "source_url": url,
            "title": page_title,
            "link": first_link,
            "date": datetime.utcnow().date().isoformat(),
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
    fieldnames = ["source_url", "title", "link", "date"]
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
