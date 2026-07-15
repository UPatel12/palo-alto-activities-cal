"""Scrape library events from event listing pages and LibCal APIs."""

import re
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar

# Library event listing pages (web scraping fallback when iCal not available)
# Only libraries within ~15 min of Palo Alto
LIBRARY_SOURCES = {
    "Palo Alto City Library": {
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "type": "bibliocommons",
        "city": "Palo Alto",
        "drive_time": "5 min",
    },
    "Mountain View Public Library": {
        "url": "https://mountainview.libcal.com/calendar",
        "type": "web",
        "city": "Mountain View",
        "drive_time": "10 min",
    },
    "Menlo Park Library": {
        "url": "https://menlopark.org/706/Library-Events-Programs",
        "type": "web",
        "city": "Menlo Park",
        "drive_time": "10 min",
    },
    "Sunnyvale Public Library": {
        "url": "https://www.library.sunnyvale.ca.gov/events/calendar-month-view",
        "type": "web",
        "city": "Sunnyvale",
        "drive_time": "15 min",
    },
}

# Keywords that indicate baby/toddler/family-friendly events
BABY_KEYWORDS = [
    "baby", "babies", "toddler", "infant", "storytime", "story time",
    "lap sit", "lapsit", "rhyme", "wiggle", "tiny tot", "little ones",
    "0-2", "0-3", "0-5", "ages 0", "ages 1", "ages 2",
    "newborn", "crawl", "family", "all ages", "preschool",
    "music and movement", "play", "sing", "sensory",
    "parent", "caregiver", "mommy", "daddy",
]


def is_baby_friendly(text: str) -> bool:
    """Check if event text suggests it's suitable for babies/toddlers."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in BABY_KEYWORDS)


def parse_ical_feed(
    feed_url: str,
    library_name: str,
    city: str,
    drive_time: str,
    weeks_ahead: int = 4,
) -> list[dict]:
    """Parse an iCal feed and return baby-friendly events."""
    events = []
    now = datetime.now()
    cutoff = now + timedelta(weeks=weeks_ahead)

    try:
        resp = requests.get(feed_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Warning: Could not fetch {library_name}: {e}")
        return events

    try:
        cal = Calendar.from_ical(resp.text)
    except Exception as e:
        print(f"  Warning: Could not parse iCal for {library_name}: {e}")
        return events

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("SUMMARY", ""))
        description = str(component.get("DESCRIPTION", ""))
        location = str(component.get("LOCATION", ""))

        # Filter for baby-friendly events
        combined_text = f"{summary} {description}"
        if not is_baby_friendly(combined_text):
            continue

        # Parse dates
        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")
        if not dtstart:
            continue

        dt = dtstart.dt
        # Handle date vs datetime
        if isinstance(dt, datetime):
            event_date = dt.date()
            start_time = dt.strftime("%-I:%M %p")
        else:
            event_date = dt
            start_time = "All Day"

        if isinstance(dtend, type(None)):
            end_time = ""
        else:
            dt_end = dtend.dt
            if isinstance(dt_end, datetime):
                end_time = dt_end.strftime("%-I:%M %p")
            else:
                end_time = ""

        # Filter to upcoming events within window
        if event_date < now.date() or event_date > cutoff.date():
            continue

        time_str = start_time if not end_time else f"{start_time} - {end_time}"

        # Guess age range from description
        age_range = extract_age_range(combined_text)

        # Guess cost
        cost = "Free" if "free" in combined_text.lower() or "library" in library_name.lower() else "Free"

        events.append({
            "date": event_date.isoformat(),
            "day": event_date.strftime("%A"),
            "time": time_str,
            "event_name": summary.strip(),
            "category": "Library & Storytimes",
            "location": location.strip() or library_name,
            "city": city,
            "drive_time": drive_time,
            "cost": cost,
            "age_range": age_range,
            "url": str(component.get("URL", "")),
            "description": clean_description(description),
        })

    return events


def extract_age_range(text: str) -> str:
    """Try to extract age range from event text."""
    text_lower = text.lower()

    # BiblioCommons audience tags: "Babies (under 2), Toddlers (18 mos. to 3 yrs), Kids (6-11)"
    audiences = []
    if "babies (under 2)" in text_lower or "babies" in text_lower and "under 2" in text_lower:
        audiences.append("babies")
    if "toddler" in text_lower and ("18 mo" in text_lower or "1-3" in text_lower or "18m" in text_lower):
        audiences.append("toddlers")
    elif "toddler" in text_lower:
        audiences.append("toddlers")
    if "pre-schooler" in text_lower or "preschooler" in text_lower or "3-5" in text_lower:
        audiences.append("preschool")
    if "kids (6-11)" in text_lower or "children (6-11)" in text_lower:
        audiences.append("kids")

    if audiences:
        if audiences == ["babies"]:
            return "0-2 years"
        if audiences == ["toddlers"]:
            return "18 mo - 3 years"
        if audiences == ["preschool"]:
            return "3-5 years"
        if audiences == ["kids"]:
            return "6-11 years"
        if "babies" in audiences and "toddlers" in audiences and "preschool" not in audiences:
            return "0-3 years"
        if "babies" in audiences and "toddlers" in audiences and "preschool" in audiences:
            return "0-5 years"
        if "babies" in audiences and "preschool" in audiences:
            return "0-5 years"
        if "toddlers" in audiences and "preschool" in audiences:
            return "18 mo - 5 years"

    # Explicit age patterns: "ages 0-2", "for ages 3-5", "0-5 years", "2-6 year olds"
    match = re.search(r'ages?\s*:?\s*(\d+)\s*[-–to]+\s*(\d+)', text_lower)
    if match:
        return f"{match.group(1)}-{match.group(2)} years"

    # "for X-Y year olds"
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*year', text_lower)
    if match:
        return f"{match.group(1)}-{match.group(2)} years"

    # "under X" or "up to age X"
    match = re.search(r'(?:under|up to age?)\s*(\d+)', text_lower)
    if match:
        return f"0-{match.group(1)} years"

    # "X months and up" or "Xmo+"
    match = re.search(r'(\d+)\s*(?:months?|mo)\s*(?:and up|\+|and older)', text_lower)
    if match:
        return f"{match.group(1)} mo+"

    # "grades X-Y"
    match = re.search(r'grade[s]?\s*(\d+)\s*[-–]\s*(\d+)', text_lower)
    if match:
        g1, g2 = int(match.group(1)), int(match.group(2))
        return f"{g1+5}-{g2+5} years"

    # Keywords
    if any(w in text_lower for w in ["baby", "babies", "infant", "newborn", "lapsit", "lap sit"]):
        return "0-18 months"
    if "toddler" in text_lower:
        return "1-3 years"
    if "preschool" in text_lower or "pre-school" in text_lower:
        return "3-5 years"
    if "all ages" in text_lower:
        return "All ages"
    if "family" in text_lower:
        return "All ages"

    return "All ages"


def clean_description(desc: str) -> str:
    """Clean up iCal description text."""
    if not desc:
        return ""
    # Remove HTML tags
    desc = re.sub(r'<[^>]+>', ' ', desc)
    # Remove extra whitespace
    desc = re.sub(r'\s+', ' ', desc).strip()
    # Truncate to reasonable length
    if len(desc) > 200:
        desc = desc[:197] + "..."
    return desc


def scrape_library_web_page(url: str, library_name: str, city: str, drive_time: str,
                            weeks_ahead: int = 4) -> list[dict]:
    """Scrape a library events web page for baby-friendly events."""
    from .city_events import fetch_with_brightdata, parse_fuzzy_date

    events = []
    now = datetime.now()
    cutoff = now + timedelta(weeks=weeks_ahead)

    html = fetch_with_brightdata(url)
    if not html:
        return events

    soup = BeautifulSoup(html, "html.parser")

    # Try common event card selectors used by library websites
    event_cards = soup.select(
        ".event-card, .event-item, .views-row, [class*='event'], article, "
        ".listing-item, .card, .s-lc-ea-tbl tr, [class*='calendar'], "
        "li[class*='event'], .eventlist-event"
    )

    for card in event_cards:
        title_el = card.select_one(
            "h2, h3, h4, .event-title, .title, [class*='title'], a, "
            ".s-lc-ea-ttl"
        )
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        desc_el = card.select_one("p, .description, [class*='desc'], .summary")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Extract audience/age tags from BiblioCommons cards
        audience_el = card.select_one(
            "[class*='audience'], [class*='age'], [class*='tag'], "
            "[class*='badge'], [class*='category']"
        )
        audience_text = audience_el.get_text(strip=True) if audience_el else ""

        # Use full card text as fallback for audience detection
        card_text = card.get_text(" ", strip=True)

        combined = f"{title} {description} {audience_text} {card_text}"
        if not is_baby_friendly(combined):
            continue

        # Try to extract date AND time from the same element
        # BiblioCommons format: "Tuesday, July 14on July 14, 2026, 10:30am–11:00am"
        date_el = card.select_one(
            ".date, time, [class*='date'], [datetime], .s-lc-ea-dt"
        )
        event_date = None
        time_str = "See website"

        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            event_date = parse_fuzzy_date(date_text)

            # Try to extract time from the same text blob
            # Matches: "10:30am–11:00am", "3:00pm–4:00pm", "10:00am–12:00pm"
            time_match = re.search(
                r'(\d{1,2}:\d{2}\s*[aApP][mM])\s*[-–]\s*(\d{1,2}:\d{2}\s*[aApP][mM])',
                date_text
            )
            if time_match:
                def fmt_time(t):
                    t = t.strip()
                    # Normalize am/pm to uppercase AM/PM
                    t = re.sub(r'([aA][mM])', 'AM', t)
                    t = re.sub(r'([pP][mM])', 'PM', t)
                    return t
                time_str = f"{fmt_time(time_match.group(1))} - {fmt_time(time_match.group(2))}"
            else:
                # Single time: "10:30am"
                single_match = re.search(r'(\d{1,2}:\d{2}\s*[aApP][mM])', date_text)
                if single_match:
                    time_str = re.sub(r'([aA][mM])', 'AM',
                                re.sub(r'([pP][mM])', 'PM', single_match.group(1).strip()))

        if event_date:
            if event_date < now.date() or event_date > cutoff.date():
                continue
            date_str = event_date.isoformat()
            day_str = event_date.strftime("%A")
        else:
            date_str = "TBD"
            day_str = ""

        link_el = card.select_one("a[href]")
        event_url = ""
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("http"):
                event_url = href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                event_url = f"{parsed.scheme}://{parsed.netloc}{href}"

        # Try to extract branch/location name from the card
        branch_name = library_name
        loc_el = card.select_one(
            "[class*='location'], [class*='branch'], [class*='venue'], "
            "[class*='library-name'], address"
        )
        if loc_el:
            loc_text = loc_el.get_text(strip=True)
            # Clean up "Event location:" prefix from BiblioCommons
            loc_text = re.sub(r"Event location:\s*", "", loc_text).strip()
            # Fix doubled text (e.g. "Los Altos LibraryLos Altos Library")
            half = len(loc_text) // 2
            if half > 3 and loc_text[:half] == loc_text[half:]:
                loc_text = loc_text[:half]
            if loc_text and len(loc_text) > 3 and loc_text.lower() != "online event":
                branch_name = loc_text

        # Determine city from branch name if it's a county system
        branch_city = city
        if "county" in city.lower() or "various" in city.lower():
            # Try to extract city from branch name (e.g. "Los Altos Library" -> "Los Altos")
            branch_match = re.match(r"(.+?)\s+Library", branch_name)
            if branch_match:
                branch_city = branch_match.group(1)

        desc = clean_description(description)
        source = f"Source: {library_name}"
        if desc:
            desc = f"{desc} | {source}"
        else:
            desc = source

        events.append({
            "date": date_str,
            "day": day_str,
            "time": time_str,
            "event_name": title,
            "category": "Library & Storytimes",
            "location": branch_name,
            "city": branch_city,
            "drive_time": drive_time,
            "cost": "Free",
            "age_range": extract_age_range(combined),
            "url": event_url,
            "description": desc,
        })

    return events


def scrape_all(weeks_ahead: int = 8) -> list[dict]:
    """Scrape all library sources and return baby-friendly events."""
    all_events = []
    for name, info in LIBRARY_SOURCES.items():
        print(f"  Fetching {name}...")
        events = scrape_library_web_page(
            url=info["url"],
            library_name=name,
            city=info["city"],
            drive_time=info["drive_time"],
            weeks_ahead=weeks_ahead,
        )
        all_events.extend(events)
        print(f"    Found {len(events)} baby-friendly events")

    return all_events
