"""Scrape family events from Eventbrite."""

from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from .city_events import fetch_with_brightdata, parse_fuzzy_date
from .libraries import is_baby_friendly, extract_age_range, clean_description

# Eventbrite search URLs for family/baby events near Palo Alto
EVENTBRITE_SEARCHES = [
    {
        "url": "https://www.eventbrite.com/d/ca--palo-alto/baby-and-toddler-events/",
        "label": "Baby & Toddler events in Palo Alto",
    },
    {
        "url": "https://www.eventbrite.com/d/ca--palo-alto/family-events/",
        "label": "Family events in Palo Alto",
    },
    {
        "url": "https://www.eventbrite.com/d/ca--palo-alto/kids-activities/",
        "label": "Kids activities in Palo Alto",
    },
]

# Approximate drive times from Palo Alto by city
CITY_DRIVE_TIMES = {
    "palo alto": "5 min",
    "stanford": "5 min",
    "menlo park": "10 min",
    "mountain view": "10 min",
    "los altos": "10 min",
    "los altos hills": "15 min",
    "sunnyvale": "15 min",
    "redwood city": "15 min",
    "portola valley": "15 min",
    "woodside": "15 min",
    "atherton": "10 min",
    "san carlos": "20 min",
    "cupertino": "20 min",
    "san mateo": "20 min",
    "belmont": "20 min",
    "campbell": "25 min",
    "santa clara": "20 min",
    "milpitas": "25 min",
    "san jose": "30 min",
    "saratoga": "25 min",
    "los gatos": "30 min",
    "half moon bay": "35 min",
    "pacifica": "35 min",
    "fremont": "30 min",
    "union city": "25 min",
    "hayward": "30 min",
    "san francisco": "45 min",
    "daly city": "35 min",
    "south san francisco": "30 min",
    "burlingame": "25 min",
    "oakland": "45 min",
    "berkeley": "50 min",
    "sausalito": "50 min",
    "santa cruz": "55 min",
    "monterey": "1 hr 30 min",
    "gilroy": "45 min",
    "watsonville": "1 hr",
    "davenport": "55 min",
}


def get_drive_time(city: str) -> str:
    """Look up approximate drive time from Palo Alto."""
    if not city:
        return "See map"
    return CITY_DRIVE_TIMES.get(city.lower().strip(), "See map")


def parse_eventbrite_page(html: str) -> list[dict]:
    """Parse Eventbrite search results page."""
    events = []
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    cutoff = now + timedelta(weeks=4)

    # Eventbrite uses various card structures
    event_cards = soup.select(
        "[data-testid='event-card'], .eds-event-card, "
        ".search-event-card, article, [class*='event-card']"
    )

    for card in event_cards:
        # Title
        title_el = card.select_one(
            "h2, h3, [data-testid='event-card-title'], .eds-event-card__formatted-name, "
            "[class*='title'], a"
        )
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        # Date
        date_el = card.select_one(
            "time, [data-testid='event-card-date'], [class*='date'], p"
        )
        event_date = None
        time_str = "See listing"
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

        # Location
        loc_el = card.select_one(
            "[data-testid='event-card-location'], [class*='location'], "
            "[class*='venue'], address"
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Try to extract city from location
        city = ""
        for known_city in CITY_DRIVE_TIMES:
            if known_city in location.lower():
                city = known_city.title()
                break

        # Price
        price_el = card.select_one(
            "[data-testid='event-card-price'], [class*='price'], [class*='cost']"
        )
        cost = price_el.get_text(strip=True) if price_el else "See listing"

        # Link
        link_el = card.select_one("a[href*='eventbrite.com']") or card.select_one("a[href]")
        url = ""
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"https://www.eventbrite.com{href}"

        # Description
        desc_el = card.select_one(
            "[class*='description'], [class*='summary'], p"
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

        combined = f"{title} {description}"

        events.append({
            "date": date_str,
            "day": day_str,
            "time": time_str,
            "event_name": title,
            "category": "Classes & Groups" if any(
                w in title.lower() for w in ["class", "lesson", "workshop", "group"]
            ) else "Community Events",
            "location": location or "See listing",
            "city": city,
            "drive_time": get_drive_time(city),
            "cost": cost,
            "age_range": extract_age_range(combined),
            "url": url,
            "description": _with_source(clean_description(description), "Eventbrite"),
        })

    return events


def _with_source(desc: str, source_name: str) -> str:
    tag = f"Source: {source_name}"
    return f"{desc} | {tag}" if desc else tag


def scrape_all() -> list[dict]:
    """Scrape Eventbrite for family/baby events."""
    all_events = []
    for search in EVENTBRITE_SEARCHES:
        print(f"  Fetching {search['label']}...")
        html = fetch_with_brightdata(search["url"])
        if not html:
            continue
        events = parse_eventbrite_page(html)
        all_events.extend(events)
        print(f"    Found {len(events)} events")
    return all_events
