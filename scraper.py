#!/usr/bin/env python3
"""
Palo Alto Baby Activities Calendar Scraper

Scrapes multiple sources for baby-friendly activities within 1 hour of
Palo Alto and outputs a consolidated CSV file.

Usage:
    python scraper.py              # Scrape all sources
    python scraper.py --recurring  # Only generate recurring/static events (no web scraping)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sources import libraries, city_events, museums, farms_outdoors, eventbrite, recurring


COLUMNS = [
    "date", "day", "time", "event_name", "category",
    "location", "city", "drive_time", "cost", "age_range",
    "url", "description",
]
# cost_label is derived, not scraped — added after processing

OUTPUT_DIR = Path(__file__).parent / "output"


WINDOW_END = datetime(2026, 10, 31).date()  # Halloween 2026
# Round up so scrapers reach at least WINDOW_END; the exact window is enforced
# afterwards by filter_date_window().
WEEKS_AHEAD = max(1, -(-(WINDOW_END - datetime.now().date()).days // 7))


def scrape_all_sources(recurring_only: bool = False) -> pd.DataFrame:
    """Run all scrapers and combine results."""
    all_events = []

    # Tier 3: Recurring/static events (always runs, no network needed)
    print("\n[Recurring & Seasonal Events]")
    all_events.extend(recurring.scrape_all(weeks_ahead=WEEKS_AHEAD))

    if not recurring_only:
        # Tier 1: Library iCal feeds
        print("\n[Library Events - iCal Feeds]")
        all_events.extend(libraries.scrape_all(weeks_ahead=WEEKS_AHEAD))

        # Tier 2: City events via web scraping
        print("\n[City Events]")
        all_events.extend(city_events.scrape_all(weeks_ahead=WEEKS_AHEAD))

        # Tier 2: Museums & attractions
        print("\n[Museums & Attractions]")
        all_events.extend(museums.scrape_all(weeks_ahead=WEEKS_AHEAD))

        # Tier 2: Farms & outdoor activities
        print("\n[Farms & Outdoor]")
        all_events.extend(farms_outdoors.scrape_all(weeks_ahead=WEEKS_AHEAD))

        # Eventbrite disabled — blocks direct requests, needs headless browser
        # all_events.extend(eventbrite.scrape_all())

    df = pd.DataFrame(all_events, columns=COLUMNS)
    return df


def clean_event_names(df: pd.DataFrame) -> pd.DataFrame:
    """Remove scraping artifacts from event names."""
    if df.empty:
        return df

    # Remove "In Progress" status badges scraped from library sites
    df["event_name"] = df["event_name"].str.replace(r"In Progress$", "", regex=True).str.strip()
    # Remove "Featured" prefix
    df["event_name"] = df["event_name"].str.replace(r"^Featured", "", regex=True).str.strip()
    # Remove duplicate event name (sometimes name is repeated)
    df["event_name"] = df["event_name"].apply(
        lambda x: x[:len(x)//2].strip() if isinstance(x, str) and len(x) > 20
        and x[:len(x)//2].strip().lower() == x[len(x)//2:].strip().lower()
        else x
    )
    # Fix unicode encoding issues
    df["event_name"] = df["event_name"].str.replace("\u2019", "'", regex=False)
    df["event_name"] = df["event_name"].str.replace("\u2013", "-", regex=False)
    df["event_name"] = df["event_name"].str.replace("\u2014", "-", regex=False)
    df["description"] = df["description"].str.replace("\u2019", "'", regex=False)
    df["description"] = df["description"].str.replace("\u2013", "-", regex=False)
    df["description"] = df["description"].str.replace("\u2014", "-", regex=False)

    # Extract times from descriptions when time is "See website"/"See schedule"/"See listing"
    import re
    placeholder_times = ["See website", "See schedule", "See listing"]
    for idx, row in df.iterrows():
        if row["time"] in placeholder_times and row["description"]:
            desc = str(row["description"])
            # Full range: "10:00 AM - 11:00 AM"
            range_match = re.search(
                r'(\d{1,2}:\d{2}\s*[APap][Mm])\s*[-–to]+\s*(\d{1,2}:\d{2}\s*[APap][Mm])',
                desc
            )
            if range_match:
                df.at[idx, "time"] = f"{range_match.group(1).strip().upper()} - {range_match.group(2).strip().upper()}"
                continue
            # Short range: "10:30-11 AM" or "10:30-11:00 AM"
            short_range = re.search(
                r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}(?::\d{2})?)\s*([APap][Mm])',
                desc
            )
            if short_range:
                start = short_range.group(1)
                end = short_range.group(2)
                ampm = short_range.group(3).upper()
                if ":" not in end:
                    end = f"{end}:00"
                df.at[idx, "time"] = f"{start} {ampm} - {end} {ampm}"
                continue
            # Single time: "at 10:30 AM" or "10:30 AM"
            single_match = re.search(r'(?:at\s+)?(\d{1,2}:\d{2}\s*[APap][Mm])', desc)
            if single_match:
                df.at[idx, "time"] = single_match.group(1).strip().upper()

    # Fix known incorrect ages for specific events
    age_fixes = {
        "LIBI Play Space": "0-3 years",
        "Bunny Hive: Art and Music Pop-Up": "2 weeks - 5 years",
        "Lil' Barnyard Bonanza at the OFJCC": "All ages (family event)",
        "Doodle and Discover Wednesdays": "2-6 years",
    }
    for event_name, correct_age in age_fixes.items():
        mask = df["event_name"].str.contains(event_name, case=False, na=False)
        df.loc[mask, "age_range"] = correct_age

    # Fix known cost overrides (verified from official sources)
    cost_fixes = {
        "Doodle and Discover Wednesdays": "Free",
        "Bunny Hive": "Call to confirm price — Blossom Birth (650) 327-2477",
        "LIBI Play Space": "Free (no membership required)",
        "Lil' Barnyard Bonanza at the OFJCC": "Free",
        "Kids Rock": "Free",
        "Sing Along w/ Puppets": "$20 adults / free under 1 (EBT: $5 — email boxoffice@playtheatreco.org)",
        "Vivid: Immerse Your Senses": "Included with Cal Academy admission ($49-55 adults / free under 2)",
        "Music Fun in the Sun": "$22 adults / free under 1 (included with CDM admission)",
        "Music Fun Under The Sun": "$22 adults / free under 1 (included with CDM admission)",
        "Saturday Science Drop-in": "$10 adult+child / ages 4+ (baby can tag along free)",
        "Afternoon Art Drop-in": "$5 per person / ages 4+ (baby can tag along free)",
    }
    for event_name, correct_cost in cost_fixes.items():
        mask = df["event_name"].str.contains(event_name, case=False, na=False)
        df.loc[mask, "cost"] = correct_cost

    # Fix known times for specific events (from their websites)
    time_fixes = {
        "LIBI Play Space": "9:30 AM - 12:00 PM",
        "Bunny Hive: Art and Music Pop-Up": "10:00 AM - 11:30 AM",
        "Lil' Barnyard Bonanza at the OFJCC": "4:00 PM - 5:00 PM",
        "Doodle and Discover Wednesdays": "1:00 PM - 5:30 PM",
    }
    for event_name, correct_time in time_fixes.items():
        mask = df["event_name"].str.contains(event_name, case=False, na=False)
        df.loc[mask, "time"] = correct_time

    return df


def filter_junk_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove non-event rows (nav links, scraping artifacts, adult-only events)."""
    if df.empty:
        return df

    original_len = len(df)

    # Remove navigation/UI elements scraped as events
    junk_patterns = [
        r"^View all dates",
        r"^Find more events",
        r"^All Ages$",
        r"^Babies",
        r"^Toddlers",
        r"^Preschoolers",
        r"^Jump to main content",
        r"^Plan Your Trip",
        r"^Merch$",
        r"^House\s*Step inside",
        r"^\d+\.\w",                # Eventbrite category numbers
        r"Find more events in:",    # Library nav links
        r"^Early Learning",
        r"^StorytimeFind",
        r"^Parenting.*Find",
        r"^See more$",
        r"^Register$",
        r"^POPULAR EVENTS$",
        r"^Something for everyone",
        r"^See all",
        r"^Load more",
        r"^Show more",
        r"^Back to",
        r"^Learn More$",
        r"^Read More$",
        r"^Sign Up$",
        r"^Buy Tickets$",
        # Sunnyvale calendar navigation / operational notices
        r"Library Closes at",
        r"Previous Month",           # already exists below, keep both
        # Randall / Hiller scraping artifacts
        r"^Event Details$",
        r"^Repeating Event$",
        r"^at The Hiller",
        r"^Anderson Collection",
        # CDM scraping artifacts
        r"^Always on$",
        r"^Ongoing$",
        r"^Art Activity$",
        r"^Special Event$",
        # Cal Academy exhibits/permanent galleries scraped as events
        r"^Osher Rainforest$",
        r"^Steinhart Aquarium$",
        r"^Morrison Planetarium$",
        r"^Kimball Natural History",
        r"^Wander Woods$",
        r"^Curiosity Grove$",
        r"^Philippine Coral Reef$",
        r"^Tusher African Hall$",
        r"^Living Roof$",
        r"^Human Odyssey$",
        r"^Nature Lab$",
        r"^Color of Life$",
        r"^California Coast$",
        r"^Water Planet$",
        r"^Shake House$",
        r"^Venom: Fangs",
        r"^Hidden Wonders",
        r"^Twilight Zone:",
        r"^Gems and Minerals",
        r"^New Science:",
        r"^Academy in Action$",
        r"^New & featured$",
        r"^California: State",
        r"^Incoming!$",
        r"^Tiny Chef",
        r"^Anderson Collection",
        r"^at The Hiller",           # Hiller nav element
        r"Museum Closes Early",      # Museum closure notice
        r"^Always on$",
        r"^Ongoing$",
        r"^Repeating Event$",
        r"^Event Details$",
        r"^Special Event$",
        r"^Art Activity$",
        r"^july,\s*\d{4}$",         # Month header
        r"Previous Month",           # Calendar navigation
        # Funcheap pricing elements
        r"^\$\d+\*\*",
        r"^FREE\*\*",
        # Adult-topic events
        r"inherited.*trauma",
        r"bike safety",
        r"creating lasting friendships",
        r"how labor progresses",
        r"pregnancy.*relationship",
        # R-rated film
        r"family movie:?\s*goat",
        # Toddler Time (18 mo minimum, baby is 7 months)
        r"^toddler time\b",
        # LEGO classes (18 mo minimum)
        r"^lego tuesdays",
        r"^lego fridays",
        # Preschool-age structured programs
        r"^preschool little learners",
        r"^circus of smiles",
        # Adult-only library events
        r"^documentary:",
        r"book sale",
        r"^bioblitz",          # Nature data-collection event, not baby-specific
        # More scraping artifacts
        r"^Registration:?$",
        r"^Learn More About",
        r"^Gizdich Ranch$",    # Standalone duplicate
        r"^Berry Picking at Gizdich Ranch",  # Closed for 2026 berry season
        r"^Event filters?$",  # Sunnyvale library UI element
    ]
    junk_regex = "|".join(junk_patterns)
    df = df[~df["event_name"].str.contains(junk_regex, case=False, regex=True, na=False)]

    # Remove adult-only events that slipped through baby filter
    adult_patterns = [
        r"for adults",
        r"21\+",
        r"nightlife",
        r"nitelife",
        r"emo nite",
        r"wine tasting",
        r"bar crawl",
        r"business advising",
        r"business ownership summit",
        r"english conversation club",
        r"computer class",
        r"tech help",
        r"tech mentor",
        r"volunteen",
        r"coloring for adults",
        r"chess club",
        r"quantum hypnosis",
        r"startup.* pitch",
        r"fifa.*watch party",
        r"soulcollage",
        r"connecting with your ancestors",
    ]
    adult_regex = "|".join(adult_patterns)
    df = df[~df["event_name"].str.contains(adult_regex, case=False, regex=True, na=False)]
    df = df[~df["description"].str.contains(adult_regex, case=False, regex=True, na=False)]

    # Remove rows where event name is extremely long (calendar HTML dumps)
    df = df[df["event_name"].str.len() < 200]

    # Remove events where minimum age is clearly above 7 months old
    # These are structured activities (not general "all ages" venues)
    too_old_patterns = [
        r"^toddler time",       # 18 mo minimum
        r"^preschool",          # 3+ years
        r"lego tuesdays",       # 18 mo minimum
        r"lego fridays",        # 18 mo minimum
        r"circus of smiles",    # 3-5 years
        r"watercolor painting", # 6-11 years
        r"digital discovery",   # grades 4-6
    ]
    too_old_regex = "|".join(too_old_patterns)
    df = df[~df["event_name"].str.contains(too_old_regex, case=False, regex=True, na=False)]

    # Also filter by age_range field for structured activities
    # Keep "All ages", "0-X", "X mo", baby/infant ranges
    # Remove if age_range explicitly starts at 18mo+, 2yr+, 3yr+ for non-venue events
    too_old_ages = ["18 mo - 3 years", "18 mo - 5 years", "3-5 years", "6-11 years", "8-14 years", "2-6 years"]
    # Only remove if it's a structured event (not a park/farm/farmers market which welcomes all ages)
    venue_keywords = ["park", "farm", "market", "beach", "trail", "zoo", "museum", "aquarium",
                     "garden", "playground", "fairyland"]
    for age in too_old_ages:
        mask = df["age_range"] == age
        is_venue = df["event_name"].str.lower().str.contains("|".join(venue_keywords), na=False)
        df = df[~(mask & ~is_venue)]

    # Remove Eventbrite ticket status "descriptions" that aren't real descriptions
    ticket_noise = ["Sales end soon", "Just added", "Almost full", "Going fast"]
    df.loc[df["description"].isin(ticket_noise), "description"] = ""

    removed = original_len - len(df)
    if removed > 0:
        print(f"  Removed {removed} junk/adult-only rows")

    return df


def filter_date_window(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only events between today and WINDOW_END. TBD rows are always kept."""
    if df.empty:
        return df

    today = datetime.now().date()
    parsed = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce").dt.date
    in_window = parsed.notna() & (parsed >= today) & (parsed <= WINDOW_END)
    keep = in_window | (df["date"] == "TBD")

    dropped = len(df) - int(keep.sum())
    if dropped > 0:
        print(f"  Dropped {dropped} events outside {today} — {WINDOW_END}")

    return df[keep]


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate events based on URL and name+date+location."""
    if df.empty:
        return df

    # First: deduplicate by URL (prefer rows with real dates over TBD)
    has_url = df["url"].str.len() > 0
    url_rows = df[has_url].copy()
    no_url_rows = df[~has_url].copy()

    if not url_rows.empty:
        # Deduplicate by URL+date (not URL alone) so recurring events on the same
        # URL but different dates all survive. Only collapse same URL on same date.
        url_rows["_url_date_key"] = url_rows["url"] + "|" + url_rows["date"]
        url_rows["_has_date"] = url_rows["date"] != "TBD"
        url_rows = url_rows.sort_values("_has_date", ascending=False)
        url_rows = url_rows.drop_duplicates(subset="_url_date_key", keep="first")
        url_rows = url_rows.drop(columns=["_has_date", "_url_date_key"])

    df = pd.concat([url_rows, no_url_rows], ignore_index=True)

    # Second: deduplicate by name + date + location
    df["_dedup_key"] = (
        df["event_name"].str.lower().str.strip()
        + "|" + df["date"]
        + "|" + df["location"].str.lower().str.strip()
    )
    df = df.drop_duplicates(subset="_dedup_key", keep="first")
    df = df.drop(columns="_dedup_key")

    # Third: if a TBD row exists but we already have a dated row with same URL, drop TBD
    if not df.empty:
        tbd_mask = df["date"] == "TBD"
        dated_urls = set(df.loc[~tbd_mask & (df["url"].str.len() > 0), "url"])
        df = df[~(tbd_mask & df["url"].isin(dated_urls))]

    return df


def derive_cost_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add a cost_label column: Free / Free for baby / Paid."""
    import re

    def label(cost: str) -> str:
        c = str(cost).lower().strip()
        if not c or c in ("see website", "see schedule", "see listing", "varies"):
            return "Check website"
        # Explicitly free (including parenthetical notes)
        if re.match(r"^free\b", c):
            return "Free"
        if c in ("free entry", "free admission"):
            return "Free"
        # Paid but first class is free
        if "first class free" in c or "first class is free" in c:
            return "Paid (first class free)"
        # Free for baby specifically
        baby_free_patterns = [
            r"free under \d",
            r"free for under",
            r"free.*under \d+ month",
            r"free.*baby",
            r"free.*infant",
            r"free.*under 1",
            r"free.*under 2",
            r"free.*under 3",
            r"free.*under 4",
        ]
        if any(re.search(p, c) for p in baby_free_patterns):
            return "Free for baby"
        # No entry fee (farms)
        if "no entry fee" in c:
            return "Free entry / Pay per pick"
        # Paid
        if any(c.startswith(ch) for ch in ("$", "~$")):
            return "Paid"
        if re.search(r"\$\d+", c):
            return "Paid"
        return "Check website"

    df["cost_label"] = df["cost"].apply(label)
    return df


def sort_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by date and clean up the dataframe."""
    if df.empty:
        return df

    # Sort: real dates first, then TBD
    has_date = df["date"] != "TBD"
    dated = df[has_date].copy()
    undated = df[~has_date].copy()

    if not dated.empty:
        dated = dated.sort_values("date")

    df = pd.concat([dated, undated], ignore_index=True)

    # Fill empty cells
    df = df.fillna("")

    return df


def main():
    parser = argparse.ArgumentParser(description="Scrape baby-friendly activities near Palo Alto")
    parser.add_argument("--recurring", action="store_true",
                        help="Only generate recurring/static events (no web scraping)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output CSV file path")
    args = parser.parse_args()

    print("=" * 60)
    print("  Palo Alto Baby Activities Calendar Scraper")
    print(f"  {datetime.now().strftime('%B %d, %Y %I:%M %p')}")
    print(f"  Window: {datetime.now().date()} -> {WINDOW_END} ({WEEKS_AHEAD} weeks)")
    print("=" * 60)

    # Scrape
    df = scrape_all_sources(recurring_only=args.recurring)

    # Process
    print(f"\n[Processing]")
    print(f"  Total raw events: {len(df)}")

    df = clean_event_names(df)
    df = filter_junk_rows(df)
    print(f"  After cleanup: {len(df)}")

    df = filter_date_window(df)
    df = deduplicate(df)
    print(f"  After dedup: {len(df)}")

    df = sort_and_clean(df)
    df = derive_cost_labels(df)

    # Output
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = args.output or str(OUTPUT_DIR / "activities.csv")
    df.to_csv(output_path, index=False)

    print(f"\n  Saved {len(df)} events to {output_path}")

    # Generate HTML calendar and ICS files
    from generate_outputs import generate_html, generate_ics
    generate_html(df, str(OUTPUT_DIR / "calendar.html"))
    generate_ics(df, str(OUTPUT_DIR))

    # Print summary
    print(f"\n[Summary by Category]")
    if not df.empty:
        for cat, count in df["category"].value_counts().items():
            print(f"  {cat}: {count}")

    print(f"\n[Summary by Day]")
    if not df.empty:
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            count = len(df[df["day"] == day])
            if count > 0:
                print(f"  {day}: {count}")

    print("\nDone!")


if __name__ == "__main__":
    main()
