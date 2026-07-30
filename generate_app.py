#!/usr/bin/env python3
"""Build the shareable web app from the activities CSV.

The calendar CSV is mostly repetition: a handful of standing venues emitted
once per open day. This regroups those rows into the three shapes a parent
actually plans around --

    places    somewhere you go; has opening days and hours
    regulars  a scheduled program that repeats on the same weekday
    events    a happening on a specific date

Usage:
    python generate_app.py                            # Artifact fragment
    python generate_app.py --standalone --out x.html  # full HTML document
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

from generate_outputs import parse_drive_time_minutes

OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_CSV = OUTPUT_DIR / "activities.csv"
DEFAULT_OUT = OUTPUT_DIR / "app.html"

# Classifying a recurring row as a place or a scheduled program is mostly a
# naming question, and the three lists below are checked in order.
#
# Order matters because city names collide with venue words: "Menlo Park
# Farmers' Market" and "Storytime at Pioneer Park" both contain "park" but are
# programs, so the program list has to win over the generic venue list.

# Unambiguous venues, even when the name also reads like a program.
STRONG_VENUE_RE = re.compile(
    r"\bplay space\b|\bplayhouse\b|\bopen play\b|\bpumpkin patch\b"
    r"|\bu-?pick\b|\bpicking at\b|\bfarm visit\b",
    re.I,
)

# Something that starts at a time and ends.
PROGRAM_RE = re.compile(
    r"\bstory\s?time\b|\blapsit\b|\bplaytime\b|\bconcert\b|\bmarket\b"
    r"|\bmusic\b|\bmovie\b|\bfilm\b|\bshakespeare\b|\bclass\b|\bswim\b"
    r"|\bgym\b|\bstroller\b|\bsing\b|\bdrop-?in\b|\bstorytelling\b",
    re.I,
)

# Somewhere you go.
VENUE_RE = re.compile(
    r"^visit\b|^explore\b|^picnic at\b|^walk at\b|^stroll\b"
    r"|\bpark\b|\bfarm\b|\bzoo\b|\bmuseum\b|\bplayground\b|\bbeach\b"
    r"|\bgarden|\btrail\b|\baquarium\b|\bpreserve\b|\bfairyland\b|\blibrary$",
    re.I,
)


def is_place(name: str) -> bool:
    """Whether a recurring row is somewhere you go rather than a scheduled program."""
    if STRONG_VENUE_RE.search(name):
        return True
    if PROGRAM_RE.search(name):
        return False
    return bool(VENUE_RE.search(name))


def slot_for(time_str: str) -> str:
    """Bucket a start time into the part of day parents plan around."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AaPp])[Mm]", time_str or "")
    if not m:
        return "anytime"
    hour = int(m.group(1)) % 12
    if m.group(3).lower() == "p":
        hour += 12
    if hour < 11:
        return "morning"
    if hour < 14:
        return "midday"
    if hour < 17:
        return "afternoon"
    return "evening"


def clean_desc(text: str) -> tuple[str, str]:
    """Split the trailing '| Source: X' tag off a description."""
    if "| Source:" in text:
        body, _, src = text.partition("| Source:")
        return body.strip(), src.strip()
    return text.strip(), ""


def build_payload(df: pd.DataFrame) -> dict:
    df = df.fillna("")
    dated = df[df["date"] != "TBD"].copy()
    dated["dt"] = pd.to_datetime(dated["date"], errors="coerce")
    dated = dated[dated["dt"].notna()]

    places, regulars, events = [], [], []

    for (name, location), grp in dated.groupby(["event_name", "location"], sort=False):
        first = grp.iloc[0]
        dates = sorted(grp["dt"].dt.date.unique())
        dows = sorted({d.weekday() for d in dates})
        desc, source = clean_desc(str(first["description"]))

        base = {
            "name": name,
            "loc": location,
            "city": str(first["city"]),
            "time": str(first["time"]),
            "cost": str(first["cost"]),
            "label": str(first["cost_label"]),
            "ages": str(first["age_range"]),
            "cat": str(first["category"]),
            "drive": str(first["drive_time"]),
            "mins": parse_drive_time_minutes(str(first["drive_time"])),
            "url": str(first["url"]),
            "desc": desc,
            "src": source,
            "slot": slot_for(str(first["time"])),
        }

        recurring = len(dates) >= 3

        if recurring and is_place(name):
            places.append({**base, "dows": dows,
                           "from": dates[0].isoformat(), "to": dates[-1].isoformat()})
        elif recurring:
            regulars.append({**base, "dows": dows,
                             "from": dates[0].isoformat(), "to": dates[-1].isoformat()})
        else:
            for d in dates:
                events.append({**base, "date": d.isoformat(), "dow": d.weekday()})

    tbd = []
    for _, row in df[df["date"] == "TBD"].iterrows():
        desc, source = clean_desc(str(row["description"]))
        tbd.append({
            "name": str(row["event_name"]), "loc": str(row["location"]),
            "city": str(row["city"]), "cost": str(row["cost"]),
            "label": str(row["cost_label"]), "ages": str(row["age_range"]),
            "cat": str(row["category"]), "drive": str(row["drive_time"]),
            "mins": parse_drive_time_minutes(str(row["drive_time"])),
            "url": str(row["url"]), "desc": desc, "src": source,
        })

    events.sort(key=lambda e: (e["date"], e["time"]))
    places.sort(key=lambda p: p["mins"])
    regulars.sort(key=lambda r: (r["dows"][0] if r["dows"] else 9, r["time"]))
    tbd.sort(key=lambda t: t["name"])

    return {
        "places": places, "regulars": regulars, "events": events, "tbd": tbd,
        "from": dated["dt"].min().date().isoformat(),
        "to": dated["dt"].max().date().isoformat(),
        "built": date.today().isoformat(),
    }


TITLE = "Baby Days"
BLURB = ("Baby-friendly places, weekly storytimes, and free events within an hour "
         "of Palo Alto.")

# Served straight from a web host, the page needs its own document wrapper.
# The Artifact host supplies one, so that variant omits it -- but a bare
# fragment has no viewport meta, which renders this phone-first layout at
# desktop width on a phone.
STANDALONE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{blurb}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{blurb}">
<meta name="twitter:card" content="summary">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#F2F2F7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
</head>
<body>
{content}
</body>
</html>
"""


def generate(df: pd.DataFrame, out_path: Path, standalone: bool = False) -> dict:
    payload = build_payload(df)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    content = PAGE.replace("__DATA__", data)

    if standalone:
        html = STANDALONE.format(title=TITLE, blurb=BLURB, content=content)
    else:
        html = f"<title>{TITLE}</title>\n{content}"

    out_path.write_text(html, encoding="utf-8")
    return payload


PAGE = r"""<style>
/* iOS system palette. Semantic greens/oranges are darkened for text use on
   light grounds, where Apple's display values fail contrast. */
:root{
  --bg:#F2F2F7; --surface:#FFFFFF; --press:#D1D1D6; --fill:rgba(118,118,128,.12);
  --label:#1C1C1E; --label2:#8E8E93; --label3:#C7C7CC;
  --sep:rgba(60,60,67,.20);
  --accent:#007AFF;
  --ok:#248A3D;   --ok-bg:rgba(52,199,89,.15);
  --pay:#B25000;  --pay-bg:rgba(255,149,0,.16);
  --neutral:#6C6C70; --neutral-bg:rgba(118,118,128,.12);
  --nav:rgba(242,242,247,.82);
  --seg-on:#FFFFFF;
  --shadow:0 3px 8px rgba(0,0,0,.10),0 1px 1px rgba(0,0,0,.04);
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#000000; --surface:#1C1C1E; --press:#2C2C2E; --fill:rgba(118,118,128,.24);
    --label:#FFFFFF; --label2:#98989F; --label3:#48484A;
    --sep:rgba(84,84,88,.65);
    --accent:#0A84FF;
    --ok:#30D158;  --ok-bg:rgba(48,209,88,.18);
    --pay:#FF9F0A; --pay-bg:rgba(255,159,10,.18);
    --neutral:#98989F; --neutral-bg:rgba(118,118,128,.24);
    --nav:rgba(0,0,0,.72);
    --seg-on:#636366;
    --shadow:0 3px 8px rgba(0,0,0,.5);
  }
}
:root[data-theme="dark"]{
  --bg:#000000; --surface:#1C1C1E; --press:#2C2C2E; --fill:rgba(118,118,128,.24);
  --label:#FFFFFF; --label2:#98989F; --label3:#48484A;
  --sep:rgba(84,84,88,.65);
  --accent:#0A84FF;
  --ok:#30D158;  --ok-bg:rgba(48,209,88,.18);
  --pay:#FF9F0A; --pay-bg:rgba(255,159,10,.18);
  --neutral:#98989F; --neutral-bg:rgba(118,118,128,.24);
  --nav:rgba(0,0,0,.72);
  --seg-on:#636366;
  --shadow:0 3px 8px rgba(0,0,0,.5);
}
:root[data-theme="light"]{
  --bg:#F2F2F7; --surface:#FFFFFF; --press:#D1D1D6; --fill:rgba(118,118,128,.12);
  --label:#1C1C1E; --label2:#8E8E93; --label3:#C7C7CC;
  --sep:rgba(60,60,67,.20);
  --accent:#007AFF;
  --ok:#248A3D;  --ok-bg:rgba(52,199,89,.15);
  --pay:#B25000; --pay-bg:rgba(255,149,0,.16);
  --neutral:#6C6C70; --neutral-bg:rgba(118,118,128,.12);
  --nav:rgba(242,242,247,.82);
  --seg-on:#FFFFFF;
  --shadow:0 3px 8px rgba(0,0,0,.10),0 1px 1px rgba(0,0,0,.04);
}

*{box-sizing:border-box}
body{
  margin:0;background:var(--bg);color:var(--label);
  font-family:var(--sans);font-size:17px;line-height:1.47;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}
.app{max-width:600px;margin:0 auto;padding:0 16px calc(56px + env(safe-area-inset-bottom))}

/* ── Large title ─────────────────────── */
.hero{padding:24px 0 10px}
.hero h1{
  margin:0;font-size:34px;line-height:1.12;font-weight:700;letter-spacing:-.022em;
  color:var(--label);
}
.hero p{margin:6px 0 0;font-size:15px;line-height:1.4;color:var(--label2);max-width:34em}

/* ── Sticky bar: segmented control + filters ── */
.bar{
  position:sticky;top:0;z-index:30;padding:10px 0 12px;
  background:var(--nav);
  -webkit-backdrop-filter:saturate(180%) blur(20px);
  backdrop-filter:saturate(180%) blur(20px);
}
.seg{display:flex;gap:2px;background:var(--fill);border-radius:9px;padding:2px}
.seg button{
  flex:1;min-width:0;border:0;border-radius:7px;padding:7px 2px;cursor:pointer;
  background:transparent;color:var(--label);font-family:inherit;
  font-size:13px;font-weight:500;letter-spacing:-.01em;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:background .18s ease;
}
.seg button[aria-selected="true"]{background:var(--seg-on);font-weight:600;box-shadow:var(--shadow)}
.seg button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}

.filters{display:flex;align-items:center;gap:8px;margin-top:10px}
.pill{
  border:0;border-radius:100px;padding:6px 13px;cursor:pointer;
  background:var(--fill);color:var(--accent);font-family:inherit;
  font-size:13px;font-weight:500;letter-spacing:-.01em;
}
.pill[aria-pressed="true"]{background:var(--accent);color:#fff}
.pill:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
select.pill{
  appearance:none;padding-right:26px;
  background-image:
    linear-gradient(45deg,transparent 50%,currentColor 50%),
    linear-gradient(135deg,currentColor 50%,transparent 50%);
  background-position:calc(100% - 15px) 52%,calc(100% - 10px) 52%;
  background-size:5px 5px,5px 5px;background-repeat:no-repeat;
}
.tally{margin-left:auto;font-size:13px;color:var(--label2);
  font-variant-numeric:tabular-nums;white-space:nowrap}

/* ── Day nav ─────────────────────────── */
.daynav{display:flex;align-items:center;gap:10px;padding:18px 0 2px}
.daynav h2{flex:1;margin:0;font-size:22px;font-weight:700;letter-spacing:-.021em}
.daynav h2 small{display:block;font-size:13px;font-weight:400;color:var(--label2);
  letter-spacing:0;margin-top:1px}
.step{
  width:32px;height:32px;flex:0 0 auto;border:0;border-radius:100px;cursor:pointer;
  background:var(--fill);color:var(--accent);font-size:16px;line-height:1;
  display:flex;align-items:center;justify-content:center;font-family:inherit;
}
.step:disabled{color:var(--label3);cursor:default}
.step:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* ── Grouped list ────────────────────── */
.hdr{
  font-size:13px;font-weight:400;color:var(--label2);
  text-transform:uppercase;letter-spacing:.05em;
  padding:22px 16px 7px;
}
.hdr .rt{float:right;text-transform:none;letter-spacing:0;font-variant-numeric:tabular-nums}
.group{background:var(--surface);border-radius:10px;overflow:hidden}
.group + .hdr{padding-top:26px}

.row{position:relative}
.row:not(:last-child)::after{
  content:"";position:absolute;left:16px;right:0;bottom:0;
  height:1px;background:var(--sep);transform:scaleY(.5);transform-origin:bottom;
}
/* The tappable summary is its own button; the detail sits outside it, because a
   button may only contain phrasing content and must never wrap a link. */
.summary{
  display:block;width:100%;text-align:left;padding:11px 16px;
  background:transparent;border:0;cursor:pointer;
  font-family:inherit;color:inherit;
  -webkit-tap-highlight-color:transparent;
}
.summary:active{background:var(--press)}
.summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}

.rtop{display:flex;align-items:flex-start;gap:10px}
.rtitle{
  flex:1;min-width:0;font-size:17px;font-weight:400;line-height:1.32;
  letter-spacing:-.021em;color:var(--label);
}
.chev{
  flex:0 0 auto;margin-top:4px;color:var(--label3);
  transition:transform .22s cubic-bezier(.4,0,.2,1);
}
.row.open .chev{transform:rotate(90deg)}

.badge{
  flex:0 0 auto;margin-top:1px;font-size:11px;font-weight:600;letter-spacing:.005em;
  padding:2px 7px;border-radius:100px;white-space:nowrap;
}
.b-ok{background:var(--ok-bg);color:var(--ok)}
.b-pay{background:var(--pay-bg);color:var(--pay)}
.b-neutral{background:var(--neutral-bg);color:var(--neutral)}

.sub{
  margin-top:2px;font-size:14px;line-height:1.35;color:var(--label2);
  letter-spacing:-.008em;font-variant-numeric:tabular-nums;
}
.sub span:not(:last-child)::after{content:" · ";color:var(--label3)}

/* Day-of-week strip */
.days{display:flex;gap:4px;margin-top:8px}
.day{
  flex:0 0 auto;min-width:30px;text-align:center;padding:3px 0;border-radius:6px;
  font-size:11px;font-weight:500;background:var(--fill);color:var(--label3);
  font-variant-numeric:tabular-nums;
}
.day.on{background:var(--accent);color:#fff}

/* Expanded detail */
.detail{display:none;padding:11px 16px 14px;border-top:1px solid var(--sep)}
.row.open .detail{display:block}
.detail p{margin:0 0 10px;font-size:15px;line-height:1.45;color:var(--label);
  letter-spacing:-.012em}
.detail dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font-size:14px}
.detail dt{color:var(--label2)}
.detail dd{margin:0;color:var(--label)}
.detail a{
  display:inline-block;margin-top:12px;color:var(--accent);
  font-size:15px;font-weight:500;text-decoration:none;
}
.detail a:hover{text-decoration:underline}
.detail a:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:3px}

/* ── Empty + footer ──────────────────── */
.blank{
  background:var(--surface);border-radius:10px;padding:34px 22px;text-align:center;
}
.blank b{display:block;font-size:17px;font-weight:600;margin-bottom:3px;letter-spacing:-.021em}
.blank span{font-size:15px;color:var(--label2)}

.legal{
  margin-top:34px;padding:0 4px;font-size:13px;line-height:1.45;color:var(--label2);
}
.legal p{margin:0 0 8px}

@media (max-width:400px){
  .app{padding:0 12px 48px}
  .hero h1{font-size:30px}
  .seg button{font-size:12px}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none !important;animation:none !important}
}
</style>

<div class="app">
  <header class="hero">
    <h1>Baby Days</h1>
    <p>Places, storytimes, and free events for babies and little kids, within an hour of Palo Alto.</p>
  </header>

  <div class="bar">
    <div class="seg" role="tablist">
      <button role="tab" id="t-today"  aria-selected="true"  onclick="go('today')">Today</button>
      <button role="tab" id="t-events" aria-selected="false" onclick="go('events')">What's on</button>
      <button role="tab" id="t-places" aria-selected="false" onclick="go('places')">Places</button>
      <button role="tab" id="t-weekly" aria-selected="false" onclick="go('weekly')">Weekly</button>
    </div>
    <div class="filters">
      <button class="pill" id="f-free" aria-pressed="false" onclick="toggleFree()">Free only</button>
      <select class="pill" id="f-dist" onchange="setDist(this.value)" aria-label="Maximum drive time">
        <option value="999">Any drive</option>
        <option value="10">10 min</option>
        <option value="15">15 min</option>
        <option value="20">20 min</option>
        <option value="30">30 min</option>
        <option value="45">45 min</option>
      </select>
      <span class="tally" id="tally"></span>
    </div>
  </div>

  <main id="view"></main>

  <footer class="legal">
    <p>Costs and hours change. Check the venue's own page before you load the car.</p>
    <p id="built"></p>
  </footer>
</div>

<script>
const D = __DATA__;
const DOW  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const FULL = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
const MON  = ["January","February","March","April","May","June","July",
              "August","September","October","November","December"];
const SLOTS = [["morning","Morning"],["midday","Midday"],
               ["afternoon","Afternoon"],["evening","Evening"],["anytime","Anytime"]];

const S = {tab:"today", free:false, dist:999, day:null};

const esc = s => String(s??"").replace(/[&<>"']/g,c=>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const mkDate = s => {const [y,m,d]=s.split("-").map(Number); return new Date(y,m-1,d);};
const dowOf = s => (mkDate(s).getDay()+6)%7;   // 0 = Monday

const realToday = iso(new Date());
const today = realToday < D.from ? D.from : (realToday > D.to ? D.to : realToday);
S.day = today;

const CHEV = `<svg class="chev" width="8" height="13" viewBox="0 0 8 13" fill="none" aria-hidden="true"><path d="M1.5 1.5 6.5 6.5 1.5 11.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

function badge(label){
  if(label==="Free")                       return ["b-ok","Free"];
  if(label==="Free for baby")              return ["b-ok","Free for baby"];
  if(label && label.startsWith("Free entry")) return ["b-ok","Free entry"];
  if(label && label.includes("first class")) return ["b-ok","1st free"];
  if(label==="Paid")                       return ["b-pay","Paid"];
  return ["b-neutral","Check"];
}
const isFree = x => {
  const l = x.label||"";
  return l==="Free" || l==="Free for baby" ||
         l.startsWith("Free entry") || l.includes("first class");
};
const passes = x => (!S.free || isFree(x)) && (x.mins||999) <= S.dist;

function row(x, opts={}){
  const [cls,txt] = badge(x.label);
  const bits = [];
  if(opts.time!==false && x.time && !/^see |^anytime$/i.test(x.time)) bits.push(esc(x.time));
  if(x.city) bits.push(esc(x.city) + (x.drive && !/see map|varies/i.test(x.drive) ? ", " + esc(x.drive) : ""));
  if(x.ages) bits.push(esc(x.ages));

  const days = opts.days && x.dows
    ? `<div class="days">${DOW.map((d,i)=>`<span class="day${x.dows.includes(i)?" on":""}">${d}</span>`).join("")}</div>`
    : "";

  const dl = [];
  if(x.cost)                  dl.push(`<dt>Cost</dt><dd>${esc(x.cost)}</dd>`);
  if(x.loc && x.loc!==x.name) dl.push(`<dt>Where</dt><dd>${esc(x.loc)}${x.city?", "+esc(x.city):""}</dd>`);
  if(x.time)                  dl.push(`<dt>When</dt><dd>${esc(x.time)}</dd>`);
  if(x.src)                   dl.push(`<dt>Source</dt><dd>${esc(x.src)}</dd>`);

  const hasDetail = x.desc || dl.length || x.url;

  return `<div class="row">
    <button class="summary" type="button" aria-expanded="false" onclick="toggleRow(this)">
      <span class="rtop">
        <span class="rtitle">${esc(x.name)}</span>
        <span class="badge ${cls}">${txt}</span>
        ${hasDetail?CHEV:""}
      </span>
      ${bits.length?`<span class="sub">${bits.map(b=>`<span>${b}</span>`).join("")}</span>`:""}
      ${days}
    </button>
    ${hasDetail?`<div class="detail">
      ${x.desc?`<p>${esc(x.desc)}</p>`:""}
      ${dl.length?`<dl>${dl.join("")}</dl>`:""}
      ${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">Open venue page</a>`:""}
    </div>`:""}
  </div>`;
}

const group = (items, opts) => `<div class="group">${items.map(x=>row(x,opts)).join("")}</div>`;
const header = (title, right="") =>
  `<div class="hdr">${title}${right?`<span class="rt">${right}</span>`:""}</div>`;
const blank = msg =>
  `<div class="blank"><b>Nothing here</b><span>${msg}</span></div>`;

function viewToday(){
  const dw = dowOf(S.day), d = mkDate(S.day);
  const evs  = D.events.filter(e => e.date===S.day && passes(e));
  const regs = D.regulars.filter(r => r.dows.includes(dw) && S.day>=r.from && S.day<=r.to && passes(r));
  const plcs = D.places.filter(p => p.dows.includes(dw) && S.day>=p.from && S.day<=p.to && passes(p));
  const on = [...evs, ...regs];
  tally(on.length + plcs.length);

  let h = `<div class="daynav">
    <h2>${S.day===today?"Today":FULL[dw]}<small>${FULL[dw]}, ${MON[d.getMonth()]} ${d.getDate()}</small></h2>
    <button class="step" onclick="shift(-1)" ${S.day<=D.from?"disabled":""} aria-label="Previous day">‹</button>
    <button class="step" onclick="shift(1)"  ${S.day>=D.to  ?"disabled":""} aria-label="Next day">›</button>
  </div>`;

  if(!on.length && !plcs.length)
    return h + `<div style="margin-top:18px">${blank("Try a longer drive, or turn off Free only.")}</div>`;

  for(const [key,name] of SLOTS){
    const inSlot = on.filter(x => (x.slot||"anytime")===key);
    if(inSlot.length) h += header(name) + group(inSlot);
  }
  if(plcs.length) h += header("Open today", `${plcs.length}`) + group(plcs,{time:false});
  return h;
}

function viewEvents(){
  const evs = D.events.filter(e => e.date>=today && passes(e));
  const tbd = D.tbd.filter(passes);
  tally(evs.length + tbd.length);

  if(!evs.length && !tbd.length)
    return `<div style="margin-top:20px">${blank("Try a longer drive, or turn off Free only.")}</div>`;

  const byDate = new Map();
  for(const e of evs){
    if(!byDate.has(e.date)) byDate.set(e.date,[]);
    byDate.get(e.date).push(e);
  }

  let h = "";
  for(const [ds,list] of byDate){
    const d = mkDate(ds);
    h += header(`${FULL[dowOf(ds)]}, ${MON[d.getMonth()].slice(0,3)} ${d.getDate()}`) + group(list);
  }
  if(tbd.length) h += header("Date not announced yet", `${tbd.length}`) + group(tbd,{time:false});
  return h;
}

function viewPlaces(){
  const ps = D.places.filter(passes);
  tally(ps.length);
  if(!ps.length) return `<div style="margin-top:20px">${blank("Try a longer drive.")}</div>`;
  return header("Sorted by drive time", `${ps.length}`) + group(ps,{days:true,time:false});
}

function viewWeekly(){
  const rs = D.regulars.filter(passes);
  tally(rs.length);
  if(!rs.length) return `<div style="margin-top:20px">${blank("Try a longer drive, or turn off Free only.")}</div>`;
  let h = "";
  for(let i=0;i<7;i++){
    const day = rs.filter(r => r.dows.includes(i));
    if(day.length) h += header(FULL[i], `${day.length}`) + group(day,{days:false});
  }
  return h;
}

function toggleRow(btn){
  const r = btn.parentElement;
  if(!r.querySelector(".detail")) return;
  const open = r.classList.toggle("open");
  btn.setAttribute("aria-expanded", open ? "true" : "false");
}
function tally(n){
  document.getElementById("tally").textContent = n === 1 ? "1 result" : n + " results";
}
function shift(n){
  const d = mkDate(S.day); d.setDate(d.getDate()+n);
  const next = iso(d);
  if(next>=D.from && next<=D.to){ S.day = next; render(); }
}
function go(tab){
  S.tab = tab;
  document.querySelectorAll(".seg button").forEach(b =>
    b.setAttribute("aria-selected", b.id === "t"+"-"+tab ? "true" : "false"));
  render();
  window.scrollTo({top:0, behavior:"smooth"});
}
function toggleFree(){
  S.free = !S.free;
  document.getElementById("f-free").setAttribute("aria-pressed", S.free?"true":"false");
  render();
}
function setDist(v){ S.dist = +v; render(); }

function render(){
  document.getElementById("view").innerHTML =
      S.tab==="today"  ? viewToday()
    : S.tab==="events" ? viewEvents()
    : S.tab==="places" ? viewPlaces()
    :                    viewWeekly();
}

const f = mkDate(D.from), t = mkDate(D.to);
document.getElementById("built").textContent =
  `${D.places.length} places, ${D.regulars.length} weekly regulars and ${D.events.length} events ` +
  `from ${MON[f.getMonth()]} ${f.getDate()} to ${MON[t.getMonth()]} ${t.getDate()}. Updated ${D.built}.`;
render();
</script>
"""


def main():
    parser = argparse.ArgumentParser(description="Build the shareable app page")
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--standalone", action="store_true",
                        help="Emit a full HTML document (for web hosting) instead of "
                             "a fragment (for the Artifact host, which supplies <head>)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV not found at {csv_path}. Run scraper.py first.")
        return

    df = pd.read_csv(csv_path).fillna("")
    out = Path(args.out)
    p = generate(df, out, standalone=args.standalone)

    kind = "standalone page" if args.standalone else "artifact fragment"
    print(f"  {kind} saved to {out}  ({out.stat().st_size/1024:.0f} KB)")
    print(f"  {len(p['places'])} places · {len(p['regulars'])} weekly · "
          f"{len(p['events'])} events · {len(p['tbd'])} TBD")


if __name__ == "__main__":
    main()
