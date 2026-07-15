"""Scrape farm and outdoor activity pages."""

from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from .city_events import fetch_with_brightdata, parse_fuzzy_date
from .libraries import clean_description

FARM_SOURCES = [
    {
        "name": "Webb Ranch",
        "url": "https://www.webbranchinc.com",
        "city": "Portola Valley",
        "drive_time": "15 min",
        "activity": "U-Pick berries & pumpkins",
    },
    {
        "name": "Swanton Berry Farm",
        "url": "https://www.swantonberryfarm.com",
        "city": "Davenport",
        "drive_time": "55 min",
        "activity": "Organic strawberry picking",
    },
    {
        "name": "Gizdich Ranch",
        "url": "https://www.gizdich-ranch.com",
        "city": "Watsonville",
        "drive_time": "1 hr",
        "activity": "Apple & berry picking, pies",
    },
    {
        "name": "Deer Hollow Farm",
        "url": "https://www.deerhollowfarm.org",
        "city": "Mountain View",
        "drive_time": "10 min",
        "activity": "Free farm visit, animals, nature walks",
    },
    {
        "name": "Hidden Villa",
        "url": "https://www.hiddenvilla.org/visit",
        "city": "Los Altos Hills",
        "drive_time": "15 min",
        "activity": "Farm animals, hiking trails, organic farm",
    },
    {
        "name": "Lemos Farm",
        "url": "https://www.lemosfarm.com",
        "city": "Half Moon Bay",
        "drive_time": "35 min",
        "activity": "Pony rides, train rides, petting zoo",
    },
    {
        "name": "Filoli Gardens",
        "url": "https://filoli.org/visit/",
        "city": "Woodside",
        "drive_time": "20 min",
        "activity": "Historic gardens, nature walks, family programs",
    },
]


def parse_farm_page(html: str, source: dict) -> list[dict]:
    """Parse a farm/outdoor page for events and activities."""
    events = []
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    cutoff = now + timedelta(weeks=4)

    # Look for event listings, hours, or seasonal info
    event_cards = soup.select(
        ".event-card, .event-item, [class*='event'], article, "
        ".listing-item, .card, [class*='program']"
    )

    for card in event_cards:
        title_el = card.select_one("h2, h3, h4, a, .title, [class*='title']")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        desc_el = card.select_one("p, .description, [class*='desc']")
        description = desc_el.get_text(strip=True) if desc_el else ""

        date_el = card.select_one(".date, time, [class*='date'], [datetime]")
        event_date = None
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

        link_el = card.select_one("a[href]")
        url = link_el.get("href", "") if link_el else ""
        if url and not url.startswith("http"):
            from urllib.parse import urlparse
            parsed = urlparse(source["url"])
            url = f"{parsed.scheme}://{parsed.netloc}{url}"

        events.append({
            "date": date_str,
            "day": day_str,
            "time": "See website",
            "event_name": title,
            "category": "Outdoor & Nature",
            "location": source["name"],
            "city": source["city"],
            "drive_time": source["drive_time"],
            "cost": "See website",
            "age_range": "All ages",
            "url": url,
            "description": _with_source(clean_description(description), source["name"]),
        })

    return events


def _with_source(desc: str, source_name: str) -> str:
    tag = f"Source: {source_name}"
    return f"{desc} | {tag}" if desc else tag


def scrape_all() -> list[dict]:
    """Scrape all farm/outdoor sources."""
    all_events = []
    for source in FARM_SOURCES:
        print(f"  Fetching {source['name']}...")
        html = fetch_with_brightdata(source["url"])
        if not html:
            continue
        events = parse_farm_page(html, source)
        all_events.extend(events)
        print(f"    Found {len(events)} events")
    return all_events
