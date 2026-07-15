#!/usr/bin/env python3
"""
Generate HTML calendar and ICS files from the activities CSV.

Usage:
    python generate_outputs.py                    # Generate from default CSV
    python generate_outputs.py --csv path/to.csv  # Generate from specific CSV
"""

import argparse
import json
import re
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
from icalendar import Calendar as ICalendar, Event as IEvent, vText

OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_CSV = OUTPUT_DIR / "activities.csv"
TIMEZONE = "America/Los_Angeles"

CATEGORY_COLORS = {
    "Library & Storytimes": "#e67e22",
    "Outdoor & Nature": "#27ae60",
    "Community Events": "#3498db",
    "Special Events": "#9b59b6",
    "Classes & Groups": "#e91e63",
}

CATEGORY_ICONS = {
    "Library & Storytimes": "book",
    "Outdoor & Nature": "leaf",
    "Community Events": "calendar",
    "Special Events": "star",
    "Classes & Groups": "users",
}


def parse_drive_time_minutes(dt_str: str) -> int:
    """Convert drive time string to minutes for filtering."""
    if not dt_str or dt_str in ("See map", "Varies"):
        return 999
    dt_str = str(dt_str).lower().strip()
    # "1 hr 30 min" -> 90
    hr_match = re.search(r"(\d+)\s*hr", dt_str)
    min_match = re.search(r"(\d+)\s*min", dt_str)
    total = 0
    if hr_match:
        total += int(hr_match.group(1)) * 60
    if min_match:
        total += int(min_match.group(1))
    if total == 0:
        # Try "15-30 min" -> use lower bound
        range_match = re.search(r"(\d+)\s*[-–]", dt_str)
        if range_match:
            total = int(range_match.group(1))
    return total if total > 0 else 999


def parse_time_for_ics(time_str: str):
    """Try to parse start/end times from the time string. Returns (start_hour, start_min, end_hour, end_min) or None."""
    if not time_str:
        return None
    pattern = r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*[-–]\s*(\d{1,2}):(\d{2})\s*(AM|PM)"
    match = re.search(pattern, time_str, re.IGNORECASE)
    if not match:
        return None
    sh, sm, sa = int(match.group(1)), int(match.group(2)), match.group(3).upper()
    eh, em, ea = int(match.group(4)), int(match.group(5)), match.group(6).upper()
    if sa == "PM" and sh != 12:
        sh += 12
    if sa == "AM" and sh == 12:
        sh = 0
    if ea == "PM" and eh != 12:
        eh += 12
    if ea == "AM" and eh == 12:
        eh = 0
    return (sh, sm, eh, em)


def prepare_events(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of event dicts with enriched fields."""
    events = []
    for _, row in df.iterrows():
        event = {
            "date": str(row.get("date", "")),
            "day": str(row.get("day", "")),
            "time": str(row.get("time", "")),
            "event_name": str(row.get("event_name", "")),
            "category": str(row.get("category", "")),
            "location": str(row.get("location", "")),
            "city": str(row.get("city", "")),
            "drive_time": str(row.get("drive_time", "")),
            "drive_time_minutes": parse_drive_time_minutes(str(row.get("drive_time", ""))),
            "cost": str(row.get("cost", "")),
            "cost_label": str(row.get("cost_label", "Check website")),
            "age_range": str(row.get("age_range", "")),
            "url": str(row.get("url", "")),
            "description": str(row.get("description", "")),
        }
        events.append(event)
    return events


# ─── ICS Generation ───────────────────────────────────────────────

def generate_ics(df: pd.DataFrame, output_dir: str):
    """Generate ICS files from the DataFrame."""
    output_path = Path(output_dir)
    events = prepare_events(df)

    # Single combined calendar
    _write_ics_file(events, output_path / "activities.ics", "Baby Activities Near Palo Alto")
    print(f"  ICS file saved to {output_path / 'activities.ics'}")


ICS_DAY_MAP = {0: "MO", 1: "TU", 2: "WE", 3: "TH", 4: "FR", 5: "SA", 6: "SU"}


def _detect_recurrence(dates: list[date]) -> dict | None:
    """Detect weekly recurrence pattern from a list of dates.
    Returns RRULE params dict or None if not recurring."""
    if len(dates) < 2:
        return None

    sorted_dates = sorted(dates)

    # Check if all dates fall on the same day(s) of week
    weekdays = set(d.weekday() for d in sorted_dates)

    # Weekly: same single day of week, dates are 7 days apart
    if len(weekdays) == 1:
        gaps = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates)-1)]
        if all(g == 7 for g in gaps):
            return {
                "freq": "WEEKLY",
                "byday": ICS_DAY_MAP[sorted_dates[0].weekday()],
                "until": sorted_dates[-1],
            }

    # Multiple days per week (e.g. Tue-Sun for farms, Sat+Sun for parks)
    if len(weekdays) >= 2:
        # Check if these are consistent weekly repeats
        week_groups = {}
        for d in sorted_dates:
            week_num = d.isocalendar()[1]
            week_groups.setdefault(week_num, set()).add(d.weekday())

        # If every week has the same set of days, it's a multi-day weekly recurrence
        day_sets = list(week_groups.values())
        if len(day_sets) >= 2 and all(s == day_sets[0] for s in day_sets):
            byday = ",".join(ICS_DAY_MAP[d] for d in sorted(weekdays))
            return {
                "freq": "WEEKLY",
                "byday": byday,
                "until": sorted_dates[-1],
            }

    return None


def _write_ics_file(events: list[dict], path: Path, cal_name: str, color: str = None):
    """Write events to an ICS file, merging recurring events into single entries with RRULE."""
    cal = ICalendar()
    cal.add("prodid", "-//PaloAltoActivitiesCal//Baby Activities//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", cal_name)
    cal.add("x-wr-timezone", TIMEZONE)
    if color:
        cal.add("x-apple-calendar-color", color)

    # Group events by (name, location, time) to detect recurring ones
    groups = {}
    one_offs = []

    for event in events:
        if event["date"] == "TBD" or not event["date"]:
            continue
        try:
            event_date = date.fromisoformat(event["date"])
        except ValueError:
            continue

        key = (event["event_name"], event["location"], event["time"])
        if key not in groups:
            groups[key] = {"event": event, "dates": []}
        groups[key]["dates"].append(event_date)

    # Process each group
    for key, group in groups.items():
        event = group["event"]
        dates = group["dates"]
        recurrence = _detect_recurrence(dates) if len(dates) >= 2 else None
        first_date = min(dates)

        ie = IEvent()
        ie.add("summary", event["event_name"])

        # Parse time
        time_parts = parse_time_for_ics(event["time"])
        if time_parts:
            sh, sm, eh, em = time_parts
            ie.add("dtstart", datetime(first_date.year, first_date.month, first_date.day, sh, sm))
            ie.add("dtend", datetime(first_date.year, first_date.month, first_date.day, eh, em))
        else:
            ie.add("dtstart", first_date)

        # Add RRULE for recurring events
        if recurrence:
            until_date = recurrence["until"]
            byday = recurrence["byday"].split(",") if "," in recurrence["byday"] else recurrence["byday"]
            rrule = {"freq": recurrence["freq"], "byday": byday,
                     "until": datetime(until_date.year, until_date.month, until_date.day, 23, 59, 59)}
            ie.add("rrule", rrule)

        # Location
        loc_parts = [event["location"], event["city"]]
        ie.add("location", vText(", ".join(p for p in loc_parts if p)))

        # Description with metadata
        desc_parts = []
        # Cost label first — most important info
        cost_label = event.get("cost_label", "")
        if cost_label == "Free":
            desc_parts.append("✅ FREE")
        elif cost_label == "Free for baby":
            desc_parts.append("✅ FREE for baby (adult fee applies)")
        elif cost_label == "Free entry / Pay per pick":
            desc_parts.append("✅ Free entry (pay per pound for produce)")
        elif cost_label == "Paid":
            desc_parts.append(f"💰 PAID: {event['cost']}")
        elif event["cost"] and event["cost"] not in ("See website", "See schedule", "See listing", "Varies"):
            desc_parts.append(f"Cost: {event['cost']}")

        if event["description"]:
            desc_parts.append(event["description"])
        if event["cost"] and cost_label not in ("Free", "Free for baby"):
            desc_parts.append(f"Cost: {event['cost']}")
        if event["age_range"]:
            desc_parts.append(f"Ages: {event['age_range']}")
        if event["drive_time"]:
            desc_parts.append(f"Drive: {event['drive_time']} from Palo Alto")
        if event["url"]:
            desc_parts.append(f"Link: {event['url']}")
        desc_parts.append(f"[{event['category']}]")
        ie.add("description", vText("\n".join(desc_parts)))

        if event["url"]:
            ie.add("url", event["url"])

        ie.add("categories", [event["category"]])

        # Stable UID based on name + location (not date, since it's recurring)
        uid_source = f"{event['event_name']}|{event['location']}"
        uid_hash = hash(uid_source) & 0xFFFFFFFF
        ie.add("uid", f"{uid_hash}@paloaltoactivities")

        cal.add_component(ie)

    path.write_bytes(cal.to_ical())


# ─── HTML Generation ──────────────────────────────────────────────

def generate_html(df: pd.DataFrame, output_path: str):
    """Generate a self-contained HTML calendar page."""
    events = prepare_events(df)
    events_json = json.dumps(events, ensure_ascii=False)
    generated_date = datetime.now().strftime("%B %d, %Y")
    event_count = len(events)
    dated_count = sum(1 for e in events if e["date"] != "TBD")

    html = HTML_TEMPLATE.replace("__EVENT_DATA__", events_json)
    html = html.replace("__GENERATED_DATE__", generated_date)
    html = html.replace("__EVENT_COUNT__", str(event_count))
    html = html.replace("__DATED_COUNT__", str(dated_count))
    html = html.replace("__CATEGORY_COLORS__", json.dumps(CATEGORY_COLORS))

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"  Calendar HTML saved to {output_path}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Baby Activities · Palo Alto</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --c-library:   #F97316;
  --c-outdoor:   #16A34A;
  --c-community: #2563EB;
  --c-special:   #9333EA;
  --c-classes:   #DB2777;

  --bg:        #F2F2F7;
  --surface:   #FFFFFF;
  --surface2:  #F8F8FA;
  --text:      #111827;
  --text2:     #6B7280;
  --border:    #E5E7EB;
  --accent:    #2563EB;
  --r:         14px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg:       #1C1C1E;
    --surface:  #2C2C2E;
    --surface2: #3A3A3C;
    --text:     #F2F2F7;
    --text2:    #AEAEB2;
    --border:   #48484A;
  }
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

/* ── Layout ────────────────────────────── */
.wrap {
  max-width: 680px;
  margin: 0 auto;
  padding: 0 16px 60px;
}

/* ── Header ────────────────────────────── */
.header {
  padding: 20px 0 14px;
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 100;
  border-bottom: 1px solid var(--border);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.header-row1 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.app-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -.3px;
}
.app-sub {
  font-size: 11px;
  color: var(--text2);
  margin-top: 1px;
}

/* View toggle */
.view-seg {
  display: flex;
  background: var(--surface2);
  border-radius: 9px;
  padding: 3px;
  gap: 2px;
  border: 1px solid var(--border);
  flex-shrink: 0;
}
.vseg-btn {
  padding: 5px 14px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  background: none;
  color: var(--text2);
  cursor: pointer;
  transition: all .15s;
}
.vseg-btn.on {
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 1px 4px rgba(0,0,0,.14);
}

/* Category chips */
.chips-row {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: 2px;
  margin-bottom: 10px;
  -webkit-overflow-scrolling: touch;
  -webkit-mask-image: linear-gradient(to right, black 85%, transparent 100%);
  mask-image: linear-gradient(to right, black 85%, transparent 100%);
}
.chips-row::-webkit-scrollbar { display: none; }

.chip {
  flex-shrink: 0;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1.5px solid transparent;
  color: #fff;
  transition: all .15s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.chip.off {
  background: var(--surface) !important;
  color: var(--text2) !important;
  border-color: var(--border);
}

/* Bottom filter row */
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dist-select {
  font-size: 12px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 20px;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  padding-right: 24px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}
.evt-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text2);
  font-weight: 500;
  white-space: nowrap;
}

/* ── Calendar Card ─────────────────────── */
.cal-card {
  background: var(--surface);
  border-radius: var(--r);
  border: 1px solid var(--border);
  overflow: hidden;
  margin-top: 16px;
}

.cal-nav {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
}
.cal-nav-btn {
  width: 32px; height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface2);
  color: var(--text);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background .12s;
}
.cal-nav-btn:active { background: var(--border); }
.cal-month-label {
  flex: 1;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -.2px;
}

/* DOW headers */
.dow-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  padding: 8px 12px 4px;
  gap: 4px;
}
.dow-lbl {
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: .3px;
}

/* Grid */
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  padding: 0 12px 12px;
}

.day-cell {
  border-radius: 8px;
  padding: 5px 4px;
  min-height: 64px;
  cursor: pointer;
  position: relative;
  background: var(--surface2);
  transition: background .1s;
  -webkit-tap-highlight-color: transparent;
  overflow: hidden;
}
.day-cell:active { background: var(--border); }
.day-cell.faded { opacity: .3; pointer-events: none; }
.day-cell.today { background: #EFF6FF; }
@media (prefers-color-scheme: dark) {
  .day-cell.today { background: #1E3A5F; }
}
.day-cell.sel {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.day-num {
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  line-height: 20px;
  margin-bottom: 2px;
}
.day-cell.today .day-num {
  background: var(--accent);
  color: #fff;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  margin: 0 auto 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.pip {
  display: block;
  height: 4px;
  border-radius: 3px;
  margin-bottom: 2px;
  opacity: .85;
}
.day-overflow {
  position: absolute;
  bottom: 3px;
  right: 4px;
  font-size: 9px;
  font-weight: 700;
  color: var(--text2);
}

/* Tap hint */
.tap-hint {
  text-align: center;
  padding: 10px;
  font-size: 12px;
  color: var(--text2);
  border-top: 1px solid var(--border);
}

/* ── Day Sheet ─────────────────────────── */
.day-sheet {
  background: var(--surface);
  border-radius: var(--r);
  border: 1px solid var(--border);
  overflow: hidden;
  margin-top: 12px;
  display: none;
}
.day-sheet.open { display: block; }

.sheet-header {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  gap: 10px;
}
.sheet-date-pill {
  background: var(--accent);
  color: #fff;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.sheet-title {
  font-size: 15px;
  font-weight: 700;
  flex: 1;
}
.sheet-close {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--surface2);
  border: 1px solid var(--border);
  font-size: 15px;
  color: var(--text2);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.sheet-events { padding: 8px 0 4px; }

/* ── Event Card ────────────────────────── */
.ecard {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background .1s;
  -webkit-tap-highlight-color: transparent;
}
.ecard:last-child { border-bottom: none; }
.ecard:active { background: var(--surface2); }

.ecard-bar {
  width: 4px;
  border-radius: 4px;
  flex-shrink: 0;
  align-self: stretch;
  min-height: 40px;
}
.ecard-body { flex: 1; min-width: 0; }

.ecard-cost {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 5px;
  margin-bottom: 4px;
  letter-spacing: .2px;
}
.cost-free     { background: #DCFCE7; color: #166534; }
.cost-freebaby { background: #DBEAFE; color: #1E40AF; }
.cost-paid     { background: #FEF9C3; color: #854D0E; }
.cost-check    { background: var(--surface2); color: var(--text2); }

.ecard-name {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
  margin-bottom: 5px;
}
.ecard-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: var(--text2);
}
.emeta {
  display: flex;
  align-items: center;
  gap: 3px;
}

/* Expanded detail */
.ecard-detail {
  display: none;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 13px;
  color: var(--text2);
  line-height: 1.55;
}
.ecard.expanded .ecard-detail { display: block; }
.ecard-detail p { margin-bottom: 6px; }

.detail-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 8px;
  padding: 8px 16px;
  background: var(--text);
  color: var(--bg);
  border-radius: 10px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}

/* ── List View ─────────────────────────── */
.list-wrap { margin-top: 16px; }

.list-month {
  font-size: 13px;
  font-weight: 700;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: .5px;
  padding: 16px 4px 6px;
}

.list-day-hdr {
  display: flex;
  align-items: baseline;
  padding: 12px 16px 8px;
  border-radius: var(--r) var(--r) 0 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-bottom: none;
  margin-top: 8px;
}
.list-day-name { font-size: 15px; font-weight: 700; }
.list-day-date { font-size: 13px; color: var(--text2); margin-left: 6px; }
.list-day-count { margin-left: auto; font-size: 12px; color: var(--text2); }

.list-day-cards {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 var(--r) var(--r);
  overflow: hidden;
  margin-bottom: 0;
}

/* TBD */
.tbd-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding: 14px 16px;
  background: var(--surface);
  border-radius: var(--r);
  border: 1px solid var(--border);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: var(--text2);
}
.tbd-cards { display: none; margin-top: 6px; background: var(--surface); border-radius: var(--r); border: 1px solid var(--border); overflow: hidden; }
.tbd-cards.open { display: block; }

/* Empty */
.empty-state {
  padding: 48px 20px;
  text-align: center;
  color: var(--text2);
  font-size: 14px;
}
.empty-state .big { font-size: 36px; margin-bottom: 10px; }
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <div class="header">
    <div class="header-row1">
      <div>
        <div class="app-title">Baby Activities</div>
        <div class="app-sub">Palo Alto &amp; nearby · Updated __GENERATED_DATE__ · __EVENT_COUNT__ events</div>
      </div>
      <div class="view-seg">
        <button class="vseg-btn on" data-view="month">Cal</button>
        <button class="vseg-btn" data-view="list">List</button>
      </div>
    </div>
    <div class="chips-row" id="chips"></div>
    <div class="filter-row">
      <select class="dist-select" id="distSel">
        <option value="999">Any distance</option>
        <option value="10">≤ 10 min</option>
        <option value="15">≤ 15 min</option>
        <option value="20">≤ 20 min</option>
        <option value="30">≤ 30 min</option>
        <option value="45">≤ 45 min</option>
        <option value="60">≤ 1 hour</option>
      </select>
      <span class="evt-count" id="evtCount"></span>
    </div>
  </div>

  <!-- Month view -->
  <div id="monthView">
    <div class="cal-card">
      <div class="cal-nav">
        <button class="cal-nav-btn" onclick="navM(-1)">‹</button>
        <span class="cal-month-label" id="calLabel"></span>
        <button class="cal-nav-btn" onclick="navM(1)">›</button>
      </div>
      <div class="dow-row">
        <div class="dow-lbl">Su</div><div class="dow-lbl">Mo</div>
        <div class="dow-lbl">Tu</div><div class="dow-lbl">We</div>
        <div class="dow-lbl">Th</div><div class="dow-lbl">Fr</div>
        <div class="dow-lbl">Sa</div>
      </div>
      <div class="cal-grid" id="calGrid"></div>
      <div class="tap-hint" id="tapHint">Tap a day to see events</div>
    </div>

    <!-- Day sheet -->
    <div class="day-sheet" id="daySheet"></div>
  </div>

  <!-- List view -->
  <div id="listView" style="display:none" class="list-wrap"></div>

</div>

<script>
const EVENTS = __EVENT_DATA__;
const CAT_COLORS = __CATEGORY_COLORS__;
const CATS = Object.keys(CAT_COLORS);
const CAT_SHORT = {
  'Library & Storytimes': 'Library',
  'Outdoor & Nature': 'Outdoor',
  'Community Events': 'Community',
  'Special Events': 'Special',
  'Classes & Groups': 'Classes',
};

const today = new Date(); today.setHours(0,0,0,0);
const todayStr = today.toISOString().slice(0,10);

const S = {
  view: 'month',
  mOff: 0,
  selDate: null,
  cats: new Set(CATS),
  dist: 999,
};

// ── Boot ──────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // chips
  const cRow = document.getElementById('chips');
  CATS.forEach(cat => {
    const c = document.createElement('div');
    c.className = 'chip';
    c.style.background = CAT_COLORS[cat];
    c.textContent = CAT_SHORT[cat] || cat;
    c.onclick = () => {
      if (S.cats.has(cat)) { S.cats.delete(cat); c.classList.add('off'); c.style.background=''; }
      else { S.cats.add(cat); c.classList.remove('off'); c.style.background=CAT_COLORS[cat]; }
      draw();
    };
    cRow.appendChild(c);
  });

  // view toggle
  document.querySelectorAll('.vseg-btn').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('.vseg-btn').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      S.view = b.dataset.view; S.selDate = null;
      draw();
    };
  });

  document.getElementById('distSel').onchange = e => { S.dist = +e.target.value; draw(); };
  draw();
});

function evts() {
  return EVENTS.filter(e => S.cats.has(e.category) && e.drive_time_minutes <= S.dist);
}

function draw() {
  const all = evts();
  const dated = all.filter(e => e.date && e.date !== 'TBD');
  const tbd   = all.filter(e => !e.date || e.date === 'TBD');
  document.getElementById('evtCount').textContent = `${dated.length} events`;

  if (S.view === 'month') {
    document.getElementById('monthView').style.display = '';
    document.getElementById('listView').style.display  = 'none';
    drawCal(dated, tbd);
  } else {
    document.getElementById('monthView').style.display = 'none';
    document.getElementById('listView').style.display  = '';
    drawList(dated, tbd);
  }
}

// ── Month ─────────────────────────────────
function drawCal(dated) {
  const map = {};
  dated.forEach(e => (map[e.date] = map[e.date] || []).push(e));

  const base = new Date(today.getFullYear(), today.getMonth() + S.mOff, 1);
  document.getElementById('calLabel').textContent =
    base.toLocaleDateString('en-US', {month:'long', year:'numeric'});

  const startDow = base.getDay();
  const dim = new Date(base.getFullYear(), base.getMonth()+1, 0).getDate();
  const cells = Math.ceil((startDow + dim) / 7) * 7;

  let html = '';
  for (let i = 0; i < cells; i++) {
    const d = new Date(base.getFullYear(), base.getMonth(), 1 - startDow + i);
    const ds = d.toISOString().slice(0,10);
    const thisMonth = d.getMonth() === base.getMonth();
    const isToday = ds === todayStr;
    const isSel = S.selDate === ds;
    const evs = map[ds] || [];

    let cls = 'day-cell';
    if (!thisMonth) cls += ' faded';
    if (isToday)   cls += ' today';
    if (isSel)     cls += ' sel';

    const pips = evs.slice(0,4).map(e =>
      `<span class="pip" style="background:${CAT_COLORS[e.category]||'#aaa'}"></span>`
    ).join('');
    const over = evs.length > 4 ? `<span class="day-overflow">+${evs.length-4}</span>` : '';

    html += `<div class="${cls}" onclick="selDay('${ds}')">
      <div class="day-num">${d.getDate()}</div>${pips}${over}</div>`;
  }
  document.getElementById('calGrid').innerHTML = html;

  if (S.selDate) drawSheet(S.selDate, map[S.selDate]||[]);
  else { const s=document.getElementById('daySheet'); s.classList.remove('open'); s.innerHTML=''; }

  document.getElementById('tapHint').textContent =
    S.selDate ? '' : 'Tap a day to see events ↑';
}

function navM(d) { S.mOff += d; S.selDate = null; draw(); }

function selDay(ds) {
  if (S.selDate === ds) { S.selDate = null; }
  else { S.selDate = ds; }
  draw();
  if (S.selDate) setTimeout(()=>{
    document.getElementById('daySheet').scrollIntoView({behavior:'smooth',block:'nearest'});
  }, 60);
}

function drawSheet(ds, evs) {
  const sheet = document.getElementById('daySheet');
  const d = new Date(ds+'T12:00:00');
  const dayName = d.toLocaleDateString('en-US',{weekday:'long'});
  const dateStr = d.toLocaleDateString('en-US',{month:'short',day:'numeric'});

  let html = `<div class="sheet-header">
    <span class="sheet-date-pill">${dateStr}</span>
    <span class="sheet-title">${dayName}${ds===todayStr?' · Today':''} · ${evs.length} event${evs.length!==1?'s':''}</span>
    <button class="sheet-close" onclick="selDay('${ds}')">✕</button>
  </div><div class="sheet-events">`;

  if (!evs.length) {
    html += `<div class="empty-state"><div class="big">🌿</div>Nothing scheduled — enjoy a free day!</div>`;
  } else {
    evs.forEach(e => html += card(e));
  }
  html += `</div>`;
  sheet.innerHTML = html;
  sheet.classList.add('open');
  bindCards(sheet);
}

// ── List ──────────────────────────────────
function drawList(dated, tbd) {
  const lv = document.getElementById('listView');
  const map = {};
  dated.forEach(e => (map[e.date]=map[e.date]||[]).push(e));
  const dates = Object.keys(map).sort();

  if (!dates.length && !tbd.length) {
    lv.innerHTML = `<div class="empty-state"><div class="big">🔍</div>No events match your filters.</div>`;
    return;
  }

  let html = '', lastMo = '';
  dates.forEach(ds => {
    const d = new Date(ds+'T12:00:00');
    const mo = d.toLocaleDateString('en-US',{month:'long',year:'numeric'});
    if (mo !== lastMo) { html += `<div class="list-month">${mo}</div>`; lastMo=mo; }
    const dn = d.toLocaleDateString('en-US',{weekday:'long'});
    const dd = d.toLocaleDateString('en-US',{month:'short',day:'numeric'});
    const isT = ds===todayStr;
    html += `<div class="list-day-hdr">
      <span class="list-day-name" style="${isT?'color:var(--accent)':''}">${dn}</span>
      <span class="list-day-date">${dd}${isT?' · Today':''}</span>
      <span class="list-day-count">${map[ds].length}</span>
    </div><div class="list-day-cards">`;
    map[ds].forEach(e => html += card(e));
    html += `</div>`;
  });

  if (tbd.length) {
    html += `<div class="tbd-row" onclick="this.querySelector('span').textContent=this.nextSibling.classList.toggle('open')?'▲':'▼'">
      Upcoming – dates TBD (${tbd.length}) <span>▼</span></div>
      <div class="tbd-cards">`;
    tbd.forEach(e => html += card(e));
    html += `</div>`;
  }

  lv.innerHTML = html;
  bindCards(lv);
}

// ── Card ──────────────────────────────────
function card(e) {
  const color = CAT_COLORS[e.category] || '#aaa';
  const cl = e.cost_label || '';
  let cc='cost-check', ct='Check website';
  if (cl==='Free')                          { cc='cost-free';     ct='FREE'; }
  else if (cl==='Free for baby')            { cc='cost-freebaby'; ct='FREE for baby'; }
  else if (cl.startsWith('Free entry'))     { cc='cost-freebaby'; ct='Free entry'; }
  else if (cl.includes('first class free')) { cc='cost-freebaby'; ct='1st class free'; }
  else if (cl==='Paid')                     { cc='cost-paid';     ct=e.cost||'Paid'; }

  const timeOk = e.time && !['See website','See listing','See schedule','Anytime',''].includes(e.time);
  const desc = (e.description||'').split('|')[0].trim();
  const drOk = e.drive_time && !['See map','Varies',''].includes(e.drive_time);

  return `<div class="ecard" onclick="this.classList.toggle('expanded')">
    <div class="ecard-bar" style="background:${color}"></div>
    <div class="ecard-body">
      <span class="ecard-cost ${cc}">${x(ct)}</span>
      <div class="ecard-name">${x(e.event_name)}</div>
      <div class="ecard-meta">
        ${timeOk?`<span class="emeta">${ico('clock')} ${x(e.time)}</span>`:''}
        ${e.city?`<span class="emeta">${ico('pin')} ${x(e.city)}${drOk?' · '+x(e.drive_time):''}</span>`:''}
        ${e.age_range?`<span class="emeta">${ico('star')} ${x(e.age_range)}</span>`:''}
      </div>
      <div class="ecard-detail">
        ${desc?`<p>${x(desc)}</p>`:''}
        ${e.cost&&cl!=='Free'?`<p><b>Cost:</b> ${x(e.cost)}</p>`:''}
        ${e.url?`<a class="detail-link" href="${x(e.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">More info ↗</a>`:''}
      </div>
    </div>
  </div>`;
}

function ico(t) {
  if (t==='clock') return `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
  if (t==='pin')   return `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`;
  if (t==='star')  return `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/></svg>`;
  return '';
}

function x(s) {
  if (!s) return '';
  const d=document.createElement('div'); d.textContent=s; return d.innerHTML;
}

function bindCards(root) {
  root.querySelectorAll('.ecard').forEach(c => {
    c.addEventListener('click', ev => { if(!ev.target.closest('.detail-link')) c.classList.toggle('expanded'); });
  });
}
</script>
</body>
</html>
"""



# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate calendar HTML and ICS from activities CSV")
    parser.add_argument("--csv", type=str, default=str(DEFAULT_CSV), help="Path to activities CSV")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV not found at {csv_path}")
        print("Run 'python scraper.py' first to generate the CSV.")
        return

    print(f"\n[Generating Calendar Outputs]")
    df = pd.read_csv(csv_path).fillna("")

    output_dir = csv_path.parent
    generate_html(df, str(output_dir / "calendar.html"))
    generate_ics(df, str(output_dir))

    print(f"\n  Open calendar: file://{output_dir / 'calendar.html'}")
    print(f"  Import ICS: {output_dir / 'activities.ics'}")
    print(f"  Per-category ICS files also generated for color-coded calendars")


if __name__ == "__main__":
    main()
