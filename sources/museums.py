"""Scrape museum and attraction event pages."""

import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from .city_events import fetch_with_brightdata, parse_fuzzy_date
from .libraries import is_baby_friendly, extract_age_range, clean_description

MUSEUM_SOURCES = [
    {
        "name": "Bay Area Discovery Museum",
        "url": "https://bayareadiscoverymuseum.org/visit/events",
        "city": "Sausalito",
        "drive_time": "50 min",
        "default_cost": "$25 per person (1+) / $23 seniors / free under 1",
        "default_age": "0-10 years",
    },
    {
        "name": "Children's Discovery Museum",
        "url": "https://www.cdm.org/visit/calendar/",
        "city": "San Jose",
        "drive_time": "30 min",
        "default_cost": "$22 adults & children / $20 seniors",
        "default_age": "0-10 years",
    },
    {
        "name": "Happy Hollow Park & Zoo",
        "url": "https://happyhollow.org/events/",
        "city": "San Jose",
        "drive_time": "30 min",
        "default_cost": "$15",
        "default_age": "0-8 years",
    },
    {
        "name": "Monterey Bay Aquarium",
        "url": "https://www.montereybayaquarium.org/visit/calendar",
        "city": "Monterey",
        "drive_time": "1 hr 30 min",
        "default_cost": "$60+ adults / free under 4 (must book online)",
        "default_age": "All ages",
    },
    {
        "name": "California Academy of Sciences",
        "url": "https://www.calacademy.org/events",
        "city": "San Francisco",
        "drive_time": "45 min",
        "default_cost": "$42-$48 adults / free under 2",
        "default_age": "All ages",
    },
    # Habitot removed — no longer has a fixed location (mobile/pop-up museum only as of 2026)
    {
        "name": "Palo Alto Junior Museum & Zoo",
        "url": "https://www.paloaltozoo.org/Programs/Family-Programs",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "default_cost": "$14 (weekday AM/weekends) / $10 (weekday PM) / free under 12 months",
        "default_age": "0-9 years",
    },
    {
        "name": "CuriOdyssey",
        "url": "https://curiodyssey.org/visit/events/",
        "city": "San Mateo",
        "drive_time": "20 min",
        "default_cost": "$15 adults / free under 18mo",
        "default_age": "0-10 years",
    },
    {
        "name": "Hiller Aviation Museum",
        "url": "https://www.hiller.org/whats-happening/",
        "city": "San Carlos",
        "drive_time": "15 min",
        "default_cost": "$18 adults / $11 youth/seniors / free under 4",
        "default_age": "All ages",  # Stroller-accessible but exhibits geared to older kids
    },
    {
        "name": "Randall Museum",
        "url": "https://randallmuseum.org/randall-museum-events/",
        "city": "San Francisco",
        "drive_time": "45 min",
        "default_cost": "Free",
        "default_age": "0-10 years",
    },
    {
        "name": "Oshman Family JCC",
        "url": "https://paloaltojcc.org/youth-family-upcoming-events/",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "default_cost": "Varies",
        "default_age": "0-5 years",
    },
    {
        "name": "Cantor Arts Center (Stanford)",
        "url": "https://museum.stanford.edu/programs/family-programs",
        "city": "Stanford",
        "drive_time": "5 min",
        "default_cost": "Free",
        "default_age": "All ages",
    },
]


def parse_museum_page(html: str, source: dict, weeks_ahead: int = 4) -> list[dict]:
    """Parse a museum events page for family events."""
    events = []
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    cutoff = now + timedelta(weeks=weeks_ahead)

    # Look for event cards/listings
    event_cards = soup.select(
        ".event-card, .event-item, .views-row, .event-listing, "
        "[class*='event'], article, .listing-item, .card, .tribe-events-single, "
        ".type-tribe_events, li[class*='event']"
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

        desc_el = card.select_one(
            ".description, .summary, p, [class*='desc'], [class*='excerpt']"
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Museums are inherently family-friendly, so less strict filtering
        combined = f"{title} {description}"

        # Try to extract date
        date_el = card.select_one(
            ".date, time, [class*='date'], [datetime], .tribe-event-date"
        )
        event_date = None
        time_str = "See website"

        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            event_date = parse_fuzzy_date(date_text)

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
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(source["url"])
                url = f"{parsed.scheme}://{parsed.netloc}{href}"

        events.append({
            "date": date_str,
            "day": day_str,
            "time": time_str,
            "event_name": title,
            "category": "Special Events",
            "location": source["name"],
            "city": source["city"],
            "drive_time": source["drive_time"],
            "cost": source.get("default_cost", "See website"),
            "age_range": source.get("default_age", "All ages"),
            "url": url,
            "description": _with_source(clean_description(description), source["name"]),
        })

    return events


def _with_source(desc: str, source_name: str) -> str:
    tag = f"Source: {source_name}"
    return f"{desc} | {tag}" if desc else tag


def scrape_all(weeks_ahead: int = 4) -> list[dict]:
    """Scrape all museum/attraction event pages."""
    all_events = []
    for source in MUSEUM_SOURCES:
        print(f"  Fetching {source['name']}...")
        html = fetch_with_brightdata(source["url"])
        if not html:
            continue
        events = parse_museum_page(html, source, weeks_ahead=weeks_ahead)
        all_events.extend(events)
        print(f"    Found {len(events)} events")
    return all_events
