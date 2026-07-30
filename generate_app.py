#!/usr/bin/env python3
"""Build the shareable web app from the activities CSV.

The calendar CSV is mostly repetition: a handful of standing venues emitted
once per open day. This regroups those rows into the three shapes a parent
actually plans around --

    places    somewhere you go; has opening days and hours
    regulars  a scheduled program that repeats on the same weekday
    events    a happening on a specific date

-- and writes a self-contained page for publishing as an Artifact. The output
has no <!doctype>/<html>/<head>/<body> wrapper; the Artifact host supplies it.

Usage:
    python generate_app.py                    # from output/activities.csv
    python generate_app.py --csv path/to.csv
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import date, datetime
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

DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


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

    span_from = dated["dt"].min().date().isoformat()
    span_to = dated["dt"].max().date().isoformat()

    return {
        "places": places, "regulars": regulars, "events": events, "tbd": tbd,
        "from": span_from, "to": span_to,
        "built": date.today().isoformat(),
    }


TITLE = "Baby Days · Peninsula"
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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{blurb}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{blurb}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#FBF8F6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#171216" media="(prefers-color-scheme: dark)">
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
:root{
  --ground:#FBF8F6; --surface:#FFFFFF; --raise:#F5EEF1;
  --ink:#2A2026; --body:#4B3F46; --muted:#7A6C74; --line:#E9DFE4;
  --accent:#8E3B62; --accent-soft:#F3E4EC;
  --free:#2E7458; --free-bg:#E4F1EA;
  --paid:#9C5C12; --paid-bg:#FBEEDC;
  --check:#6B5F67; --check-bg:#EFEAEC;
  --serif:ui-serif,"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --shadow:0 1px 2px rgba(42,32,38,.06),0 6px 20px rgba(42,32,38,.05);
}
@media (prefers-color-scheme:dark){
  :root{
    --ground:#171216; --surface:#1F181D; --raise:#271F26;
    --ink:#F4ECF0; --body:#D6C8D0; --muted:#A2919B; --line:#332A31;
    --accent:#D97BA5; --accent-soft:#38222E;
    --free:#7FCFA8; --free-bg:#163024;
    --paid:#E0A863; --paid-bg:#33240F;
    --check:#A2919B; --check-bg:#272027;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.3);
  }
}
:root[data-theme="dark"]{
  --ground:#171216; --surface:#1F181D; --raise:#271F26;
  --ink:#F4ECF0; --body:#D6C8D0; --muted:#A2919B; --line:#332A31;
  --accent:#D97BA5; --accent-soft:#38222E;
  --free:#7FCFA8; --free-bg:#163024;
  --paid:#E0A863; --paid-bg:#33240F;
  --check:#A2919B; --check-bg:#272027;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.3);
}
:root[data-theme="light"]{
  --ground:#FBF8F6; --surface:#FFFFFF; --raise:#F5EEF1;
  --ink:#2A2026; --body:#4B3F46; --muted:#7A6C74; --line:#E9DFE4;
  --accent:#8E3B62; --accent-soft:#F3E4EC;
  --free:#2E7458; --free-bg:#E4F1EA;
  --paid:#9C5C12; --paid-bg:#FBEEDC;
  --check:#6B5F67; --check-bg:#EFEAEC;
  --shadow:0 1px 2px rgba(42,32,38,.06),0 6px 20px rgba(42,32,38,.05);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--body);
  font-family:var(--sans); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:640px;margin:0 auto;padding:0 18px 72px}

/* ── Masthead ─────────────────────────── */
.mast{padding:34px 0 20px}
.mast h1{
  font-family:var(--serif); font-weight:600; font-size:33px; line-height:1.1;
  color:var(--ink); margin:0 0 8px; letter-spacing:-.015em; text-wrap:balance;
}
.mast h1 em{font-style:italic;color:var(--accent)}
.mast p{margin:0;color:var(--muted);font-size:14px;max-width:48ch}
.span{
  font-family:var(--mono); font-size:11px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); margin-top:12px;
  font-variant-numeric:tabular-nums;
}

/* ── Tabs ─────────────────────────────── */
.tabs{
  position:sticky; top:0; z-index:20; display:flex; gap:2px;
  background:var(--ground); padding:10px 0; border-bottom:1px solid var(--line);
  margin-bottom:2px;
}
.tab{
  flex:1; padding:9px 6px; border:0; border-radius:9px; cursor:pointer;
  background:transparent; color:var(--muted); font-family:var(--sans);
  font-size:13.5px; font-weight:600; transition:background .15s,color .15s;
}
.tab:hover{background:var(--raise);color:var(--body)}
.tab[aria-selected="true"]{background:var(--accent);color:var(--surface)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* ── Filters ──────────────────────────── */
.filters{
  display:flex; flex-wrap:wrap; gap:7px; align-items:center;
  padding:14px 0 6px;
}
.chip{
  border:1px solid var(--line); background:var(--surface); color:var(--body);
  border-radius:999px; padding:6px 13px; font-size:12.5px; font-weight:500;
  cursor:pointer; font-family:var(--sans); transition:.15s;
}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
select.chip{appearance:none;padding-right:26px;
  background-image:linear-gradient(45deg,transparent 50%,currentColor 50%),linear-gradient(135deg,currentColor 50%,transparent 50%);
  background-position:calc(100% - 14px) 51%,calc(100% - 9px) 51%;
  background-size:5px 5px,5px 5px;background-repeat:no-repeat}
.count{margin-left:auto;font-family:var(--mono);font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}

/* ── Day navigation ───────────────────── */
.daynav{display:flex;align-items:center;gap:8px;padding:16px 0 4px}
.daynav h2{
  flex:1; margin:0; font-family:var(--serif); font-size:23px; font-weight:600;
  color:var(--ink); letter-spacing:-.01em;
}
.daynav h2 span{display:block;font-family:var(--mono);font-size:11px;font-weight:400;
  letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-top:2px}
.arrow{
  width:34px;height:34px;flex:0 0 auto;border-radius:50%;border:1px solid var(--line);
  background:var(--surface);color:var(--body);cursor:pointer;font-size:15px;line-height:1;
}
.arrow:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
.arrow:disabled{opacity:.35;cursor:default}
.arrow:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* ── Time-of-day bands ────────────────── */
.band{margin:22px 0 0}
.band-hd{
  display:flex;align-items:baseline;gap:10px;margin-bottom:9px;
}
.band-hd b{
  font-family:var(--mono); font-size:10.5px; font-weight:700; letter-spacing:.12em;
  text-transform:uppercase; color:var(--accent);
}
.band-hd i{flex:1;height:1px;background:var(--line);font-style:normal}
.band-hd u{font-family:var(--mono);font-size:10.5px;color:var(--muted);text-decoration:none;
  font-variant-numeric:tabular-nums}

/* ── Cards ────────────────────────────── */
.list{display:flex;flex-direction:column;gap:8px}
.card{
  background:var(--surface); border:1px solid var(--line); border-radius:12px;
  padding:13px 15px; box-shadow:var(--shadow); cursor:pointer;
  transition:border-color .15s,transform .1s;
}
.card:hover{border-color:var(--accent)}
.card:active{transform:scale(.995)}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.card-top{display:flex;align-items:baseline;gap:9px}
.card h3{
  margin:0;flex:1;font-family:var(--sans);font-size:14.5px;font-weight:600;
  color:var(--ink);line-height:1.35;text-wrap:balance;
}
.tag{
  flex:0 0 auto;font-family:var(--mono);font-size:10px;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;padding:3px 7px;border-radius:5px;
}
.t-free{background:var(--free-bg);color:var(--free)}
.t-paid{background:var(--paid-bg);color:var(--paid)}
.t-check{background:var(--check-bg);color:var(--check)}
.meta{
  display:flex;flex-wrap:wrap;gap:4px 12px;margin-top:6px;
  font-family:var(--mono);font-size:11.5px;color:var(--muted);
  font-variant-numeric:tabular-nums;
}
.detail{display:none;margin-top:11px;padding-top:11px;border-top:1px solid var(--line);font-size:13.5px}
.card.open .detail{display:block}
.detail p{margin:0 0 8px}
.detail dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:12.5px}
.detail dt{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding-top:2px}
.detail dd{margin:0;color:var(--body)}
.detail a{
  display:inline-block;margin-top:10px;color:var(--accent);font-weight:600;
  font-size:13px;text-decoration:none;border-bottom:1px solid currentColor;
}
.detail a:hover{opacity:.75}
.detail a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}

/* ── Day pills (places/regulars) ──────── */
.dows{display:flex;gap:3px;margin-top:7px}
.dow{
  font-family:var(--mono);font-size:9.5px;font-weight:600;letter-spacing:.03em;
  width:23px;text-align:center;padding:2.5px 0;border-radius:4px;
  background:var(--raise);color:var(--muted);
}
.dow.on{background:var(--accent-soft);color:var(--accent)}

/* ── Section headings ─────────────────── */
.sect{margin:30px 0 0}
.sect > h2{
  font-family:var(--serif);font-size:20px;font-weight:600;color:var(--ink);
  margin:0 0 3px;letter-spacing:-.01em;
}
.sect > p{margin:0 0 13px;color:var(--muted);font-size:13px;max-width:52ch}
.datehd{
  display:flex;align-items:baseline;gap:9px;margin:22px 0 8px;
}
.datehd b{font-family:var(--serif);font-size:16px;font-weight:600;color:var(--ink)}
.datehd span{font-family:var(--mono);font-size:11px;color:var(--muted);letter-spacing:.06em;text-transform:uppercase}
.datehd i{flex:1;height:1px;background:var(--line)}

.empty{
  padding:30px 20px;text-align:center;color:var(--muted);font-size:13.5px;
  border:1px dashed var(--line);border-radius:12px;
}
.empty b{display:block;font-family:var(--serif);font-size:17px;color:var(--ink);margin-bottom:4px;font-weight:600}

.foot{
  margin-top:42px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12px;line-height:1.6;
}
.foot code{font-family:var(--mono);font-size:11.5px;color:var(--body)}

@media (max-width:520px){
  .wrap{padding:0 13px 60px}
  .mast{padding:26px 0 16px}
  .mast h1{font-size:27px}
  .daynav h2{font-size:20px}
  .tab{font-size:12.5px;padding:8px 4px}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none !important;animation:none !important}
}
</style>

<div class="wrap">
  <header class="mast">
    <h1>Somewhere to go <em>with the baby</em></h1>
    <p>Storytimes, farms, playgrounds, and free weekends within an hour of Palo Alto — filtered for babies and little kids.</p>
    <div class="span" id="span"></div>
  </header>

  <div class="tabs" role="tablist">
    <button class="tab" role="tab" id="t-today"   aria-selected="true"  onclick="go('today')">Today</button>
    <button class="tab" role="tab" id="t-events"  aria-selected="false" onclick="go('events')">What's on</button>
    <button class="tab" role="tab" id="t-places"  aria-selected="false" onclick="go('places')">Places</button>
    <button class="tab" role="tab" id="t-weekly"  aria-selected="false" onclick="go('weekly')">Every week</button>
  </div>

  <div class="filters">
    <button class="chip" id="f-free" aria-pressed="false" onclick="toggleFree()">Free only</button>
    <select class="chip" id="f-dist" onchange="setDist(this.value)" aria-label="Maximum drive time">
      <option value="999">Any drive</option>
      <option value="10">Under 10 min</option>
      <option value="15">Under 15 min</option>
      <option value="20">Under 20 min</option>
      <option value="30">Under 30 min</option>
      <option value="45">Under 45 min</option>
    </select>
    <span class="count" id="count"></span>
  </div>

  <main id="view"></main>

  <footer class="foot">
    <p>Costs and hours change — always check the venue's own page before you load the car.
    Events marked <em>date to be confirmed</em> happen every year but haven't published a 2026 date yet.</p>
    <p>Built <code id="built"></code> from public library, museum, city, and farm listings.</p>
  </footer>
</div>

<script>
const D = __DATA__;
const DOW = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const DOWFULL = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
const MON = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const SLOTS = [["morning","Morning","before 11"],["midday","Midday","11 – 2"],
               ["afternoon","Afternoon","2 – 5"],["evening","Evening","after 5"],
               ["anytime","Anytime","opening hours"]];

const S = {tab:"today", free:false, dist:999, day:null};

const esc = s => String(s??"").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const mkDate = s => {const [y,m,d]=s.split("-").map(Number); return new Date(y,m-1,d);};
const dowOf = s => (mkDate(s).getDay()+6)%7;   // 0 = Monday

// Clamp "today" into the window the data actually covers.
const realToday = iso(new Date());
const today = realToday < D.from ? D.from : (realToday > D.to ? D.to : realToday);
S.day = today;

function tagFor(label){
  if(label==="Free") return ["t-free","Free"];
  if(label==="Free for baby") return ["t-free","Free for baby"];
  if(label && label.indexOf("Free entry")===0) return ["t-free","Free entry"];
  if(label && label.indexOf("first class")>-1) return ["t-free","1st class free"];
  if(label==="Paid") return ["t-paid","Paid"];
  return ["t-check","Check site"];
}
const isFree = x => {
  const l = x.label||"";
  return l==="Free"||l==="Free for baby"||l.indexOf("Free entry")===0||l.indexOf("first class")>-1;
};
const passes = x => (!S.free || isFree(x)) && (x.mins||999) <= S.dist;

function card(x, opts={}){
  const [cls,txt] = tagFor(x.label);
  const bits = [];
  if(opts.showTime!==false && x.time && !/^see |^anytime$/i.test(x.time)) bits.push(esc(x.time));
  if(x.city) bits.push(esc(x.city) + (x.drive && !/see map|varies/i.test(x.drive) ? " · " + esc(x.drive) : ""));
  if(x.ages) bits.push(esc(x.ages));

  let dows = "";
  if(opts.dows && x.dows){
    dows = `<div class="dows">` + DOW.map((d,i) =>
      `<span class="dow${x.dows.includes(i)?" on":""}">${d}</span>`).join("") + `</div>`;
  }

  const dl = [];
  if(x.cost) dl.push(`<dt>Cost</dt><dd>${esc(x.cost)}</dd>`);
  if(x.loc && x.loc!==x.name) dl.push(`<dt>Where</dt><dd>${esc(x.loc)}${x.city?", "+esc(x.city):""}</dd>`);
  if(x.time) dl.push(`<dt>When</dt><dd>${esc(x.time)}</dd>`);
  if(x.src) dl.push(`<dt>Source</dt><dd>${esc(x.src)}</dd>`);

  return `<article class="card" tabindex="0" onclick="this.classList.toggle('open')"
     onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();this.classList.toggle('open')}">
    <div class="card-top">
      <h3>${esc(x.name)}</h3>
      <span class="tag ${cls}">${txt}</span>
    </div>
    ${bits.length?`<div class="meta">${bits.map(b=>`<span>${b}</span>`).join("")}</div>`:""}
    ${dows}
    <div class="detail">
      ${x.desc?`<p>${esc(x.desc)}</p>`:""}
      ${dl.length?`<dl>${dl.join("")}</dl>`:""}
      ${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Open venue page →</a>`:""}
    </div>
  </article>`;
}

function bands(items){
  let html = "";
  for(const [key,name,hint] of SLOTS){
    const inSlot = items.filter(x => (x.slot||"anytime")===key);
    if(!inSlot.length) continue;
    html += `<section class="band">
      <div class="band-hd"><b>${name}</b><i></i><u>${hint}</u></div>
      <div class="list">${inSlot.map(x=>card(x)).join("")}</div>
    </section>`;
  }
  return html;
}

function viewToday(){
  const d = mkDate(S.day), dw = dowOf(S.day);
  const evs = D.events.filter(e => e.date===S.day && passes(e));
  const regs = D.regulars.filter(r => r.dows.includes(dw) && S.day>=r.from && S.day<=r.to && passes(r));
  const plcs = D.places.filter(p => p.dows.includes(dw) && S.day>=p.from && S.day<=p.to && passes(p));

  const happening = [...evs, ...regs];
  setCount(happening.length + plcs.length);

  const isToday = S.day===today;
  let html = `<div class="daynav">
    <h2>${isToday?"Today":DOWFULL[dw]}<span>${DOWFULL[dw]}, ${MON[d.getMonth()]} ${d.getDate()}</span></h2>
    <button class="arrow" onclick="shift(-1)" ${S.day<=D.from?"disabled":""} aria-label="Previous day">‹</button>
    <button class="arrow" onclick="shift(1)"  ${S.day>=D.to  ?"disabled":""} aria-label="Next day">›</button>
  </div>`;

  if(!happening.length && !plcs.length){
    html += `<div class="empty"><b>Nothing matches</b>Try widening the drive time, or turning off “Free only”.</div>`;
    return html;
  }

  if(happening.length){
    html += bands(happening);
  }
  if(plcs.length){
    html += `<section class="sect">
      <h2>Open today</h2>
      <p>Places you can turn up to — no booking, no start time.</p>
      <div class="list">${plcs.map(p=>card(p,{showTime:false})).join("")}</div>
    </section>`;
  }
  return html;
}

function viewEvents(){
  const evs = D.events.filter(e => e.date >= today && passes(e));
  const tbd = D.tbd.filter(passes);
  setCount(evs.length + tbd.length);

  let html = `<section class="sect">
    <h2>What's on</h2>
    <p>One-off happenings between now and the end of October — festivals, concerts, special storytimes.</p></section>`;

  if(!evs.length && !tbd.length)
    return html + `<div class="empty"><b>Nothing matches</b>Try widening the drive time, or turning off “Free only”.</div>`;

  // One .list per date, so cards inside a day keep their gap.
  const byDate = new Map();
  for(const e of evs){
    if(!byDate.has(e.date)) byDate.set(e.date, []);
    byDate.get(e.date).push(e);
  }
  for(const [ds, list] of byDate){
    const d = mkDate(ds);
    html += `<div class="datehd"><b>${DOWFULL[dowOf(ds)]}</b>
      <span>${MON[d.getMonth()].slice(0,3)} ${d.getDate()}</span><i></i></div>
      <div class="list">${list.map(e => card(e)).join("")}</div>`;
  }

  if(tbd.length){
    html += `<section class="sect"><h2>Date to be confirmed</h2>
      <p>These run every year, but the 2026 date isn't published yet. Worth a diary note.</p>
      <div class="list">${tbd.map(t=>card(t,{showTime:false})).join("")}</div></section>`;
  }
  return html;
}

function viewPlaces(){
  const ps = D.places.filter(passes);
  setCount(ps.length);
  let html = `<section class="sect">
    <h2>Places</h2>
    <p>Somewhere to go on an open-ended morning. Highlighted days are when each one is open.</p></section>`;
  if(!ps.length) return html + `<div class="empty"><b>Nothing matches</b>Try widening the drive time.</div>`;
  return html + `<div class="list">${ps.map(p=>card(p,{dows:true,showTime:false})).join("")}</div>`;
}

function viewWeekly(){
  const rs = D.regulars.filter(passes);
  setCount(rs.length);
  let html = `<section class="sect">
    <h2>Every week</h2>
    <p>Standing dates you can build a routine around — markets, storytimes, and classes.</p></section>`;
  if(!rs.length) return html + `<div class="empty"><b>Nothing matches</b>Try widening the drive time, or turning off “Free only”.</div>`;

  for(let i=0;i<7;i++){
    const onDay = rs.filter(r => r.dows.includes(i));
    if(!onDay.length) continue;
    html += `<div class="datehd"><b>${DOWFULL[i]}</b><span>${onDay.length} regular${onDay.length>1?"s":""}</span><i></i></div>
      <div class="list">${onDay.map(r=>card(r,{dows:r.dows.length>1})).join("")}</div>`;
  }
  return html;
}

function setCount(n){
  document.getElementById("count").textContent = n + (n===1?" match":" matches");
}
function shift(n){
  const d = mkDate(S.day); d.setDate(d.getDate()+n);
  const next = iso(d);
  if(next>=D.from && next<=D.to){ S.day = next; render(); }
}
function go(tab){
  S.tab = tab;
  document.querySelectorAll(".tab").forEach(b =>
    b.setAttribute("aria-selected", b.id==="t-"+tab ? "true" : "false"));
  render();
}
function toggleFree(){
  S.free = !S.free;
  document.getElementById("f-free").setAttribute("aria-pressed", S.free?"true":"false");
  render();
}
function setDist(v){ S.dist = +v; render(); }

function render(){
  const v = document.getElementById("view");
  v.innerHTML = S.tab==="today"  ? viewToday()
              : S.tab==="events" ? viewEvents()
              : S.tab==="places" ? viewPlaces()
              :                    viewWeekly();
}

const f = mkDate(D.from), t = mkDate(D.to);
document.getElementById("span").textContent =
  `${MON[f.getMonth()].slice(0,3)} ${f.getDate()} – ${MON[t.getMonth()].slice(0,3)} ${t.getDate()} · ` +
  `${D.places.length} places · ${D.regulars.length} weekly · ${D.events.length} events`;
document.getElementById("built").textContent = D.built;
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
