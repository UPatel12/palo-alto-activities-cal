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
*{box-sizing:border-box;margin:0;padding:0}

body{
  font-family:-apple-system,BlinkMacSystemFont,'Google Sans','Segoe UI',sans-serif;
  background:#f8f9fa;
  color:#202124;
  -webkit-font-smoothing:antialiased;
}

/* ── Top bar ──────────────────────────── */
.topbar{
  display:flex;
  align-items:center;
  padding:12px 20px;
  background:#fff;
  border-bottom:1px solid #e0e0e0;
  gap:16px;
  position:sticky;
  top:0;
  z-index:100;
}
.topbar h1{
  font-size:20px;
  font-weight:400;
  color:#202124;
  letter-spacing:-.2px;
}
.topbar h1 span{color:#1a73e8}

.view-tabs{
  display:flex;
  background:#f1f3f4;
  border-radius:24px;
  padding:3px;
  gap:2px;
  margin-left:auto;
}
.vtab{
  padding:6px 18px;
  border-radius:20px;
  font-size:13px;
  font-weight:500;
  border:none;
  background:none;
  color:#5f6368;
  cursor:pointer;
  transition:.15s;
}
.vtab.on{background:#fff;color:#1a73e8;box-shadow:0 1px 3px rgba(0,0,0,.12)}

/* ── Filters strip ───────────────────── */
.filterbar{
  background:#fff;
  border-bottom:1px solid #e0e0e0;
  padding:10px 20px;
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap:nowrap;
  overflow-x:auto;
  scrollbar-width:none;
}
.filterbar::-webkit-scrollbar{display:none}

.cat-chip{
  display:inline-flex;
  align-items:center;
  gap:5px;
  padding:5px 12px;
  border-radius:16px;
  font-size:12px;
  font-weight:500;
  cursor:pointer;
  border:1.5px solid transparent;
  white-space:nowrap;
  color:#fff;
  transition:.15s;
  user-select:none;
  -webkit-tap-highlight-color:transparent;
}
.cat-chip.off{
  background:#fff !important;
  color:#5f6368 !important;
  border-color:#dadce0 !important;
}
.cat-chip .dot{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.7)}

.dist-sel{
  margin-left:auto;
  flex-shrink:0;
  padding:6px 12px;
  border-radius:16px;
  border:1.5px solid #dadce0;
  background:#fff;
  color:#202124;
  font-size:12px;
  font-weight:500;
  cursor:pointer;
}

/* ── Calendar month layout ───────────── */
.cal-wrap{max-width:900px;margin:0 auto;padding:20px 16px}

.month-nav{
  display:flex;
  align-items:center;
  gap:8px;
  margin-bottom:16px;
}
.nav-month-label{
  font-size:22px;
  font-weight:400;
  color:#202124;
  flex:1;
}
.nav-today-btn{
  padding:7px 16px;
  border-radius:4px;
  border:1px solid #dadce0;
  background:#fff;
  font-size:13px;
  font-weight:500;
  color:#3c4043;
  cursor:pointer;
}
.nav-today-btn:hover{background:#f8f9fa}
.nav-arrow{
  width:36px;height:36px;
  border-radius:50%;
  border:none;
  background:none;
  font-size:18px;
  color:#5f6368;
  cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:.1s;
}
.nav-arrow:hover{background:#f1f3f4}

/* DOW header row */
.dow-header{
  display:grid;
  grid-template-columns:repeat(7,1fr);
  margin-bottom:4px;
}
.dow-cell{
  text-align:right;
  padding:4px 10px 4px 0;
  font-size:11px;
  font-weight:500;
  color:#70757a;
  text-transform:uppercase;
  letter-spacing:.4px;
}

/* Grid */
.month-grid{
  display:grid;
  grid-template-columns:repeat(7,1fr);
  border-left:1px solid #e0e0e0;
  border-top:1px solid #e0e0e0;
}
.day-cell{
  border-right:1px solid #e0e0e0;
  border-bottom:1px solid #e0e0e0;
  padding:4px 4px 6px;
  min-height:90px;
  cursor:pointer;
  transition:background .1s;
  position:relative;
  background:#fff;
}
.day-cell:hover{background:#f8f9fa}
.day-cell.other-month{background:#f8f9fa}
.day-cell.other-month .day-num{color:#b0b3b8}
.day-cell.today .day-num-inner{
  background:#1a73e8;
  color:#fff;
  border-radius:50%;
  width:26px;height:26px;
  display:flex;align-items:center;justify-content:center;
}
.day-cell.selected{background:#e8f0fe}
.day-cell.selected:hover{background:#dce8fc}

.day-num{
  text-align:right;
  padding:2px 6px 4px;
  font-size:12px;
  font-weight:500;
  color:#202124;
  display:flex;
  justify-content:flex-end;
}

/* Event chips in grid */
.grid-event{
  display:block;
  font-size:11px;
  font-weight:500;
  padding:1px 5px;
  border-radius:3px;
  margin:1px 2px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
  cursor:pointer;
  color:#fff;
  line-height:16px;
}
.more-chip{
  font-size:11px;
  color:#70757a;
  font-weight:500;
  padding:1px 5px;
  display:block;
  cursor:pointer;
}

/* ── Day Panel (slides in below grid) ── */
.day-panel{
  background:#fff;
  border:1px solid #e0e0e0;
  border-radius:8px;
  margin-top:12px;
  overflow:hidden;
  display:none;
}
.day-panel.open{display:block}

.panel-header{
  display:flex;
  align-items:center;
  padding:14px 20px;
  border-bottom:1px solid #e0e0e0;
}
.panel-date-num{
  font-size:26px;
  font-weight:400;
  color:#202124;
  margin-right:12px;
}
.panel-date-label{
  flex:1;
}
.panel-dow{
  font-size:13px;
  font-weight:500;
  color:#202124;
}
.panel-month{
  font-size:12px;
  color:#70757a;
}
.panel-close{
  width:32px;height:32px;
  border-radius:50%;
  border:none;
  background:none;
  font-size:18px;
  color:#5f6368;
  cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}
.panel-close:hover{background:#f1f3f4}

.panel-events{padding:8px 0}

/* ── Event row (in panel + list) ──────── */
.evt-row{
  display:flex;
  align-items:flex-start;
  padding:10px 20px;
  gap:14px;
  cursor:pointer;
  border-bottom:1px solid #f1f3f4;
  transition:background .1s;
}
.evt-row:last-child{border-bottom:none}
.evt-row:hover{background:#f8f9fa}
.evt-row:active{background:#f1f3f4}

.evt-color-bar{
  width:4px;
  border-radius:4px;
  flex-shrink:0;
  margin-top:2px;
  min-height:36px;
}
.evt-content{flex:1;min-width:0}

.evt-cost{
  display:inline-block;
  font-size:10px;
  font-weight:700;
  padding:1px 7px;
  border-radius:3px;
  margin-bottom:3px;
  letter-spacing:.3px;
}
.cost-free    {background:#e6f4ea;color:#137333}
.cost-fbaby   {background:#e8f0fe;color:#1558d6}
.cost-paid    {background:#fef7e0;color:#7d5000}
.cost-check   {background:#f1f3f4;color:#5f6368}

.evt-title{
  font-size:13px;
  font-weight:500;
  color:#202124;
  line-height:1.4;
  margin-bottom:3px;
}
.evt-meta{
  font-size:12px;
  color:#70757a;
  display:flex;
  flex-wrap:wrap;
  gap:10px;
}
.evt-meta-item{display:flex;align-items:center;gap:3px}

/* Expand detail */
.evt-detail{
  display:none;
  margin-top:10px;
  padding:12px;
  background:#f8f9fa;
  border-radius:6px;
  font-size:12px;
  color:#5f6368;
  line-height:1.6;
}
.evt-row.open .evt-detail{display:block}
.evt-detail p{margin-bottom:6px}
.evt-link{
  display:inline-flex;
  align-items:center;
  gap:4px;
  margin-top:6px;
  color:#1a73e8;
  text-decoration:none;
  font-weight:500;
  font-size:12px;
}
.evt-link:hover{text-decoration:underline}

/* ── List view ────────────────────────── */
.list-wrap{max-width:900px;margin:0 auto;padding:20px 16px 60px}

.list-month-hdr{
  font-size:14px;
  font-weight:500;
  color:#70757a;
  padding:16px 0 8px;
  text-transform:uppercase;
  letter-spacing:.5px;
}
.list-day-group{
  background:#fff;
  border:1px solid #e0e0e0;
  border-radius:8px;
  overflow:hidden;
  margin-bottom:12px;
}
.list-day-hdr{
  display:flex;
  align-items:center;
  padding:10px 20px;
  background:#f8f9fa;
  border-bottom:1px solid #e0e0e0;
  gap:8px;
}
.list-day-num{
  font-size:24px;
  font-weight:300;
  color:#202124;
  width:36px;
  flex-shrink:0;
}
.list-day-today .list-day-num{
  background:#1a73e8;
  color:#fff;
  width:36px;height:36px;
  border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:16px;
  font-weight:500;
}
.list-day-info{flex:1}
.list-day-name{font-size:13px;font-weight:500;color:#202124}
.list-day-date{font-size:12px;color:#70757a}
.list-event-count{font-size:12px;color:#70757a}

/* TBD */
.tbd-hdr{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:12px 20px;
  background:#fff;
  border:1px solid #e0e0e0;
  border-radius:8px;
  cursor:pointer;
  font-size:13px;
  font-weight:500;
  color:#5f6368;
  margin-top:12px;
}
.tbd-body{display:none;background:#fff;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;overflow:hidden}
.tbd-body.open{display:block}

/* empty */
.empty-day{padding:20px;text-align:center;color:#9aa0a6;font-size:13px}

@media(max-width:600px){
  .topbar{padding:10px 12px}
  .topbar h1{font-size:16px}
  .filterbar{padding:8px 12px}
  .cal-wrap{padding:12px 8px}
  .month-nav{margin-bottom:10px}
  .nav-month-label{font-size:18px}
  .day-cell{min-height:60px}
  .grid-event{display:none}
  .more-chip{font-size:10px;text-align:center;padding:0}
  .day-panel,.list-day-group{border-radius:0;border-left:none;border-right:none}
}
</style>
</head>
<body>

<!-- Top bar -->
<div class="topbar">
  <h1>Baby <span>Activities</span></h1>
  <div class="view-tabs">
    <button class="vtab on" data-view="month">Month</button>
    <button class="vtab" data-view="list">List</button>
  </div>
</div>

<!-- Filter bar -->
<div class="filterbar" id="filterbar"></div>

<!-- Month view -->
<div id="monthView">
  <div class="cal-wrap">
    <div class="month-nav">
      <span class="nav-month-label" id="monthLabel"></span>
      <button class="nav-today-btn" onclick="goToday()">Today</button>
      <button class="nav-arrow" onclick="navM(-1)">&#8249;</button>
      <button class="nav-arrow" onclick="navM(1)">&#8250;</button>
    </div>
    <div class="dow-header" id="dowHeader"></div>
    <div class="month-grid" id="monthGrid"></div>
    <div class="day-panel" id="dayPanel"></div>
  </div>
</div>

<!-- List view -->
<div id="listView" style="display:none">
  <div class="list-wrap" id="listWrap"></div>
</div>

<script>
const EVENTS = __EVENT_DATA__;
const CAT_COLORS = __CATEGORY_COLORS__;
const CATS = Object.keys(CAT_COLORS);
const CAT_SHORT = {
  'Library & Storytimes':'Library',
  'Outdoor & Nature':'Outdoor',
  'Community Events':'Community',
  'Special Events':'Special',
  'Classes & Groups':'Classes',
};

const t0 = new Date(); t0.setHours(0,0,0,0);
const todayStr = t0.toISOString().slice(0,10);

const S = { view:'month', mOff:0, sel:null, cats:new Set(CATS), dist:999 };

// ── Boot ─────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  // Filter bar: chips + dist
  const fb = document.getElementById('filterbar');
  CATS.forEach(cat => {
    const c = document.createElement('div');
    c.className = 'cat-chip';
    c.style.background = CAT_COLORS[cat];
    c.innerHTML = `<span class="dot"></span>${CAT_SHORT[cat]||cat}`;
    c.onclick = () => {
      if (S.cats.has(cat)) { S.cats.delete(cat); c.classList.add('off'); c.style.background=''; }
      else { S.cats.add(cat); c.classList.remove('off'); c.style.background=CAT_COLORS[cat]; }
      render();
    };
    fb.appendChild(c);
  });
  const sel = document.createElement('select');
  sel.className = 'dist-sel';
  sel.innerHTML = `<option value="999">Any distance</option>
    <option value="10">≤ 10 min</option><option value="15">≤ 15 min</option>
    <option value="20">≤ 20 min</option><option value="30">≤ 30 min</option>
    <option value="45">≤ 45 min</option><option value="60">≤ 1 hour</option>`;
  sel.onchange = e => { S.dist = +e.target.value; render(); };
  fb.appendChild(sel);

  document.querySelectorAll('.vtab').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('.vtab').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      S.view = b.dataset.view; S.sel = null;
      render();
    };
  });

  // DOW headers
  const dh = document.getElementById('dowHeader');
  ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
    const el = document.createElement('div');
    el.className = 'dow-cell'; el.textContent = d;
    dh.appendChild(el);
  });

  render();
});

function evts() {
  return EVENTS.filter(e => S.cats.has(e.category) && e.drive_time_minutes <= S.dist);
}

function render() {
  const all = evts();
  const dated = all.filter(e => e.date && e.date !== 'TBD');
  const tbd   = all.filter(e => !e.date || e.date === 'TBD');
  if (S.view === 'month') {
    document.getElementById('monthView').style.display = '';
    document.getElementById('listView').style.display  = 'none';
    renderMonth(dated, tbd);
  } else {
    document.getElementById('monthView').style.display = 'none';
    document.getElementById('listView').style.display  = '';
    renderList(dated, tbd);
  }
}

// ── Month view ────────────────────────────
function renderMonth(dated) {
  const map = {};
  dated.forEach(e => (map[e.date]=map[e.date]||[]).push(e));

  const base = new Date(t0.getFullYear(), t0.getMonth()+S.mOff, 1);
  document.getElementById('monthLabel').textContent =
    base.toLocaleDateString('en-US',{month:'long',year:'numeric'});

  const startDow = base.getDay();
  const dim = new Date(base.getFullYear(), base.getMonth()+1, 0).getDate();
  const cells = Math.ceil((startDow+dim)/7)*7;

  let html = '';
  for (let i=0; i<cells; i++) {
    const d = new Date(base.getFullYear(), base.getMonth(), 1-startDow+i);
    const ds = d.toISOString().slice(0,10);
    const thisMonth = d.getMonth()===base.getMonth();
    const isToday = ds===todayStr;
    const isSel = S.sel===ds;
    const ev = map[ds]||[];

    let cls = 'day-cell';
    if (!thisMonth) cls += ' other-month';
    if (isToday)   cls += ' today';
    if (isSel)     cls += ' selected';

    const numHtml = isToday
      ? `<div class="day-num"><span class="day-num-inner">${d.getDate()}</span></div>`
      : `<div class="day-num">${d.getDate()}</div>`;

    // Show up to 3 event chips with names, then "+N more"
    const MAX = 3;
    const chips = ev.slice(0,MAX).map(e =>
      `<span class="grid-event" style="background:${CAT_COLORS[e.category]||'#aaa'}" title="${esc(e.event_name)}">${esc(e.event_name)}</span>`
    ).join('');
    const more = ev.length > MAX ? `<span class="more-chip">+${ev.length-MAX} more</span>` : '';
    // Mobile: just show count
    const mobileCount = ev.length > 0 ? `<span class="more-chip" style="display:none" id="mc-${ds}">${ev.length}</span>` : '';

    html += `<div class="${cls}" onclick="selDay('${ds}')">${numHtml}${chips}${more}</div>`;
  }

  document.getElementById('monthGrid').innerHTML = html;

  // Re-render panel
  if (S.sel) renderPanel(S.sel, map[S.sel]||[]);
  else { const p=document.getElementById('dayPanel'); p.classList.remove('open'); p.innerHTML=''; }
}

function navM(d) { S.mOff+=d; S.sel=null; render(); }
function goToday() { S.mOff=0; S.sel=null; render(); }

function selDay(ds) {
  S.sel = S.sel===ds ? null : ds;
  render();
  if (S.sel) setTimeout(()=>document.getElementById('dayPanel').scrollIntoView({behavior:'smooth',block:'nearest'}),60);
}

function renderPanel(ds, evs) {
  const panel = document.getElementById('dayPanel');
  const d = new Date(ds+'T12:00:00');
  const isToday = ds===todayStr;

  let html = `<div class="panel-header">
    <div class="panel-date-num">${d.getDate()}</div>
    <div class="panel-date-label">
      <div class="panel-dow">${d.toLocaleDateString('en-US',{weekday:'long'})}${isToday?' · Today':''}</div>
      <div class="panel-month">${d.toLocaleDateString('en-US',{month:'long',year:'numeric'})} · ${evs.length} event${evs.length!==1?'s':''}</div>
    </div>
    <button class="panel-close" onclick="selDay('${ds}')">✕</button>
  </div><div class="panel-events">`;

  if (!evs.length) html += `<div class="empty-day">No events — enjoy a free day!</div>`;
  else evs.forEach(e => html += evtRow(e));
  html += `</div>`;

  panel.innerHTML = html;
  panel.classList.add('open');
  bindEvts(panel);
}

// ── List view ──────────────────────────────
function renderList(dated, tbd) {
  const lw = document.getElementById('listWrap');
  const map = {};
  dated.forEach(e => (map[e.date]=map[e.date]||[]).push(e));
  const dates = Object.keys(map).sort();

  if (!dates.length && !tbd.length) {
    lw.innerHTML = `<div class="empty-day" style="padding:60px">No events match your filters.</div>`;
    return;
  }

  let html='', lastMo='';
  dates.forEach(ds => {
    const d = new Date(ds+'T12:00:00');
    const mo = d.toLocaleDateString('en-US',{month:'long',year:'numeric'});
    if (mo!==lastMo) { html+=`<div class="list-month-hdr">${mo}</div>`; lastMo=mo; }

    const isT = ds===todayStr;
    const numHtml = isT
      ? `<div class="list-day-num list-day-today" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;background:#1a73e8;color:#fff;font-size:16px;font-weight:500">${d.getDate()}</div>`
      : `<div class="list-day-num">${d.getDate()}</div>`;

    html += `<div class="list-day-group">
      <div class="list-day-hdr">
        ${numHtml}
        <div class="list-day-info">
          <div class="list-day-name">${d.toLocaleDateString('en-US',{weekday:'long'})}${isT?' · Today':''}</div>
          <div class="list-day-date">${d.toLocaleDateString('en-US',{month:'long',day:'numeric'})}</div>
        </div>
        <div class="list-event-count">${map[ds].length} event${map[ds].length!==1?'s':''}</div>
      </div>`;
    map[ds].forEach(e => html += evtRow(e));
    html += `</div>`;
  });

  if (tbd.length) {
    html += `<div class="tbd-hdr" onclick="this.nextElementSibling.classList.toggle('open');this.querySelector('.arr').textContent=this.nextElementSibling.classList.contains('open')?'▲':'▼'">
      Upcoming — dates to be announced (${tbd.length}) <span class="arr">▼</span></div>
      <div class="tbd-body">`;
    tbd.forEach(e => html += evtRow(e));
    html += `</div>`;
  }

  lw.innerHTML = html;
  bindEvts(lw);
}

// ── Event row ──────────────────────────────
function evtRow(e) {
  const color = CAT_COLORS[e.category]||'#aaa';
  const cl = e.cost_label||'';
  let cc='cost-check', ct='Check website';
  if (cl==='Free')                        {cc='cost-free';  ct='FREE'}
  else if (cl==='Free for baby')          {cc='cost-fbaby'; ct='FREE for baby'}
  else if (cl.startsWith('Free entry'))   {cc='cost-fbaby'; ct='Free entry'}
  else if (cl.includes('first class'))    {cc='cost-fbaby'; ct='First class free'}
  else if (cl==='Paid')                   {cc='cost-paid';  ct=e.cost||'Paid'}

  const timeOk = e.time && !['See website','See listing','See schedule','Anytime',''].includes(e.time);
  const drOk   = e.drive_time && !['See map','Varies',''].includes(e.drive_time);
  const desc    = (e.description||'').split('|')[0].trim();

  return `<div class="evt-row" onclick="this.classList.toggle('open')">
    <div class="evt-color-bar" style="background:${color}"></div>
    <div class="evt-content">
      <span class="evt-cost ${cc}">${esc(ct)}</span>
      <div class="evt-title">${esc(e.event_name)}</div>
      <div class="evt-meta">
        ${timeOk?`<span class="evt-meta-item">${svgClock()} ${esc(e.time)}</span>`:''}
        ${e.city?`<span class="evt-meta-item">${svgPin()} ${esc(e.city)}${drOk?' · '+esc(e.drive_time):''}</span>`:''}
        ${e.age_range?`<span class="evt-meta-item">${svgAge()} ${esc(e.age_range)}</span>`:''}
      </div>
      <div class="evt-detail">
        ${desc?`<p>${esc(desc)}</p>`:''}
        ${e.cost&&cl!=='Free'?`<p><b>Cost:</b> ${esc(e.cost)}</p>`:''}
        ${e.url?`<a class="evt-link" href="${esc(e.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Open event page ↗</a>`:''}
      </div>
    </div>
  </div>`;
}

function svgClock(){return`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`}
function svgPin(){return`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`}
function svgAge(){return`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`}

function bindEvts(root){
  root.querySelectorAll('.evt-row').forEach(r=>{
    r.addEventListener('click', e=>{if(!e.target.closest('.evt-link'))r.classList.toggle('open')});
  });
}
function esc(s){if(!s)return'';const d=document.createElement('div');d.textContent=s;return d.innerHTML}
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
