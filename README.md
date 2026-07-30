# Baby Activities Calendar — Palo Alto

A scraper that pulls **1,000+ baby-friendly events** near Palo Alto and generates a mobile-friendly calendar you can browse and import into Apple Calendar or Google Calendar.

Covers today through **October 31** and refreshes weekly. The window is set by `WINDOW_END` in `scraper.py`.

---

## What it does

- Scrapes libraries, museums, farms, city events, summer concerts, outdoor movies, and more
- Filters for events suitable for babies and young children (7 months+)
- Verifies costs — most events are **free** or **free for babies**
- Outputs a self-contained **HTML calendar app** and an **ICS file** you can subscribe to

---

## Output

| File | What it is |
|---|---|
| `output/calendar.html` | Open in any browser — month grid view, filters by category and drive time |
| `output/activities.ics` | Import into Apple Calendar / Google Calendar |
| `output/activities.csv` | Raw data — open in Google Sheets |

---

## Sources

**Libraries** (within 15 min of Palo Alto)
- Palo Alto City Library — all 5 branches
- Mountain View Public Library
- Menlo Park Library
- Sunnyvale Public Library

**Museums & attractions**
- Palo Alto Junior Museum & Zoo
- Children's Discovery Museum (San Jose)
- California Academy of Sciences
- Hiller Aviation Museum (San Carlos)
- Randall Museum (SF)
- Oshman Family JCC (Palo Alto)
- CuriOdyssey (San Mateo)
- Bay Area Discovery Museum (Sausalito)
- Monterey Bay Aquarium

**Outdoor & farms**
- Deer Hollow Farm (free, Cupertino)
- Emma Prusch Farm Park (free, San Jose)
- Ardenwood Historic Farm (Fremont)
- Hidden Villa (Los Altos Hills)
- Webb Ranch U-Pick (Saturdays only, Portola Valley)
- Swanton Berry Farm (Davenport)
- Lemos Farm (Half Moon Bay)
- Filoli Gardens (Woodside)
- Children's Fairyland (Oakland)
- San Francisco Zoo

**Free summer events (curated)**
- 10 farmers markets across the Peninsula
- Palo Alto Twilight Concert Series
- Mountain View Concerts on the Plaza (Fridays)
- Mountain View Music on Castro (Wednesdays)
- Menlo Park Summer Concert Series
- Redwood City Music on the Square
- Los Altos Summer Concert Series
- Campbell Summer Concert Series
- Sunnyvale Downtown Summer Series
- Palo Alto Family Movie Nights
- Redwood City Movies on the Square
- Sunnyvale Sunset Movie Series
- Mountain View Outdoor Movie Series
- Palo Alto Festival of the Arts (Aug 22–23)
- Shakespeare in the Park (Redwood City)
- PV Palooza (Aug 29)
- Coyote Point Summerfest (Aug 15)
- Redwood City Kids Rock! (morning concerts)

**Fall 2026**
- The Great Glass Pumpkin Patch, Palo Alto Art Center (Sept 26–27, free)
- Half Moon Bay Art & Pumpkin Festival (Oct 17–18, free)
- Webb Ranch pumpkin patch (late Sept–Oct 31 — confirm dates)
- Halloween events in Menlo Park, Mountain View, and at the Junior Museum & Zoo are
  listed as TBD until each city publishes its 2026 date

**Baby classes** (weekly reminders)
- My Gym Palo Alto
- The Little Gym Mountain View
- Music Together Menlo Park
- British Swim School
- FIT4MOM Stroller Strides
- Gymboree San Mateo
- La Petite Playhouse open play (Redwood City)

---

## The web app

**https://upatel12.github.io/palo-alto-activities-cal/**

A phone-first page that regroups the calendar into how you actually plan:
**Places** you can turn up to, **Every week** regulars, and **What's on** by date.
Filter by free-only and drive time.

```bash
# Rebuild after a scrape, then publish
python generate_app.py --standalone --out output/index.html
git add -f output/index.html && git commit -m "Update app"
git subtree push --prefix output origin gh-pages   # or push index.html to gh-pages
```

The `--standalone` flag matters: without it the page is emitted as a fragment with
no `<head>`, so a browser gets no viewport meta tag and renders it at desktop width
on phones.

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

---

## Usage

```bash
# Scrape all sources and generate calendar + ICS
python3 scraper.py

# Fast run — recurring/curated events only (no web scraping)
python3 scraper.py --recurring

# Regenerate HTML calendar and ICS from existing CSV (no scraping)
python3 generate_outputs.py
```

Open `output/calendar.html` in your browser. Import `output/activities.ics` into Apple Calendar or Google Calendar.

---

## Auto-refresh (weekly)

A macOS launchd plist is included to auto-run the scraper every Sunday at 8 PM.
Replace `/PATH/TO/palo-alto-activities-cal` in the plist with your own checkout path first:

```bash
sed -i '' "s|/PATH/TO/palo-alto-activities-cal|$(pwd)|g" com.paloalto.activities.scraper.plist
cp com.paloalto.activities.scraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.paloalto.activities.scraper.plist
```

---

## Project structure

```
scraper.py              # Main orchestrator — runs all scrapers, cleans, deduplicates
generate_outputs.py     # Generates HTML calendar and ICS from CSV
sources/
  libraries.py          # Library event scrapers (BiblioCommons)
  city_events.py        # City calendar scrapers
  museums.py            # Museum and attraction event scrapers
  farms_outdoors.py     # Farm and outdoor venue scrapers
  eventbrite.py         # Eventbrite scraper (disabled — blocked without headless browser)
  recurring.py          # Curated recurring events (farmers markets, classes, summer events)
output/                 # Generated files (gitignored)
requirements.txt
.env.example
```

---

## Cost legend

The calendar flags every event with a cost badge:

| Badge | Meaning |
|---|---|
| 🟢 FREE | Completely free for everyone |
| 🔵 FREE for baby | Adult pays, baby gets in free |
| 🟡 Paid | Fee required |
| First class free | Paid class with a free intro session |

The majority of events in this calendar are free or free for babies under 2.
