"""Scrape city event calendars."""

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from .libraries import is_baby_friendly, extract_age_range, clean_description

CITY_SOURCES = [
    {
        "name": "City of Palo Alto",
        "url": "https://www.cityofpaloalto.org/Events-Directory",
        "city": "Palo Alto",
        "drive_time": "5 min",
    },
    {
        "name": "City of Mountain View",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/events",
        "city": "Mountain View",
        "drive_time": "10 min",
    },
    {
        "name": "Stanford Events",
        "url": "https://events.stanford.edu/search?category=family",
        "city": "Stanford",
        "drive_time": "5 min",
    },
    {
        "name": "Palo Alto Online Community Calendar",
        "url": "https://www.paloaltoonline.com/calendar/?d=month&t=all",
        "city": "Palo Alto",
        "drive_time": "5 min",
    },
    {
        "name": "Palo Alto Daily Post Events",
        "url": "https://paloaltodailypost.com/events/",
        "city": "Palo Alto",
        "drive_time": "5 min",
    },
    {
        "name": "Funcheap - Kids & Families",
        "url": "https://sf.funcheap.com/category/event/event-types/kids-families/",
        "city": "Various (Bay Area)",
        "drive_time": "Varies",
    },
    {
        "name": "Macaroni Kid Palo Alto",
        "url": "https://paloalto.macaronikid.com/events",
        "city": "Palo Alto",
        "drive_time": "5 min",
    },
]


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def fetch_with_brightdata(url: str) -> str | None:
    """Fetch a URL via direct HTTP request."""
    try:
        resp = requests.get(url, timeout=30, headers=_HEADERS)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  Warning: Direct fetch failed for {url}: {e}")
        return None


def parse_city_events_page(html: str, source: dict) -> list[dict]:
    """Parse a city events page and extract baby-friendly events."""
    events = []
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    cutoff = now + timedelta(weeks=4)

    # Generic event extraction — look for common event card patterns
    # City websites vary widely, so we try multiple selectors
    event_cards = (
        soup.select(".event-card, .event-item, .views-row, .event-listing, "
                     "[class*='event'], article, .listing-item, .card")
    )

    for card in event_cards:
        title_el = card.select_one(
            "h2, h3, h4, .event-title, .title, [class*='title'], a"
        )
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        # Get description
        desc_el = card.select_one(
            ".description, .summary, .event-description, p, [class*='desc']"
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

        combined = f"{title} {description}"
        if not is_baby_friendly(combined):
            continue

        # Try to extract date
        date_el = card.select_one(
            ".date, time, .event-date, [class*='date'], [datetime]"
        )
        event_date = None
        time_str = "See website"

        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            event_date = parse_fuzzy_date(date_text)

        if not event_date:
            # Try to find any date-like text in the card
            card_text = card.get_text()
            event_date = parse_fuzzy_date(card_text)

        if event_date:
            if event_date < now.date() or event_date > cutoff.date():
                continue
            date_str = event_date.isoformat()
            day_str = event_date.strftime("%A")
        else:
            date_str = "TBD"
            day_str = ""

        # Extract link
        link_el = card.select_one("a[href]")
        url = ""
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("/"):
                # Make absolute URL from source
                from urllib.parse import urlparse
                parsed = urlparse(source["url"])
                url = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif href.startswith("http"):
                url = href

        events.append({
            "date": date_str,
            "day": day_str,
            "time": time_str,
            "event_name": title,
            "category": "Community Events",
            "location": source["name"],
            "city": source["city"],
            "drive_time": source["drive_time"],
            "cost": "See website",
            "age_range": extract_age_range(combined),
            "url": url,
            "description": _with_source(clean_description(description), source["name"]),
        })

    return events


def _with_source(desc: str, source_name: str) -> str:
    """Append source attribution to description."""
    tag = f"Source: {source_name}"
    return f"{desc} | {tag}" if desc else tag


def parse_fuzzy_date(text: str):
    """Try to extract a date from fuzzy text."""
    if not text:
        return None

    # Try common date formats
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',                          # 2026-07-19
        r'(\w+ \d{1,2},?\s*\d{4})',                       # July 19, 2026
        r'(\d{1,2}/\d{1,2}/\d{2,4})',                     # 7/19/2026
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            for fmt in ["%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%m/%d/%y"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
    return None


def scrape_all() -> list[dict]:
    """Scrape all city event sources."""
    all_events = []
    for source in CITY_SOURCES:
        print(f"  Fetching {source['name']}...")
        html = fetch_with_brightdata(source["url"])
        if not html:
            continue
        events = parse_city_events_page(html, source)
        all_events.extend(events)
        print(f"    Found {len(events)} baby-friendly events")
    return all_events
