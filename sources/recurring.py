"""Recurring and seasonal events that don't need scraping.

These are hand-curated events with known schedules. The script generates
concrete dated entries across the window requested by the caller
(weeks_ahead), which scraper.py derives from WINDOW_END.
"""

from datetime import date, datetime, timedelta


# Farmers markets - (name, city, day_of_week, time, drive_time)
# day_of_week: 0=Monday, 6=Sunday
FARMERS_MARKETS = [
    ("California Ave Farmers' Market", "Palo Alto", 6, "9:00 AM - 1:00 PM", "5 min",
     "https://www.cityofpaloalto.org/Departments/Community-Services/Arts-Sciences/Farmers-Market"),
    ("Downtown Palo Alto Farmers' Market", "Palo Alto", 5, "8:00 AM - 12:00 PM", "5 min",
     "https://www.cityofpaloalto.org/Departments/Community-Services/Arts-Sciences/Farmers-Market"),
    ("Mountain View Farmers' Market", "Mountain View", 6, "9:00 AM - 1:00 PM", "10 min",
     "https://www.mountainview.gov/our-city/departments/community-services/farmers-market"),
    ("Menlo Park Farmers' Market", "Menlo Park", 6, "9:00 AM - 1:00 PM", "10 min", ""),
    ("San Mateo Farmers' Market", "San Mateo", 5, "9:00 AM - 1:00 PM", "20 min", ""),
    ("Redwood City Farmers' Market", "Redwood City", 5, "9:00 AM - 1:00 PM", "15 min", ""),
    ("Sunnyvale Farmers' Market", "Sunnyvale", 5, "9:00 AM - 1:00 PM", "15 min", ""),
    ("Los Altos Farmers' Market", "Los Altos", 3, "4:00 PM - 8:00 PM", "10 min", ""),
    ("San Jose Downtown Farmers' Market", "San Jose", 4, "10:00 AM - 2:00 PM", "25 min", ""),
    ("Half Moon Bay Farmers' Market", "Half Moon Bay", 5, "9:00 AM - 1:00 PM", "35 min", ""),
]

# Free museum days
# Note: CDM and BADM free days are now only ~2x/year (March & September for BADM),
# not monthly — removed from auto-generating events. Check websites for current dates.
FREE_MUSEUM_DAYS = []

# Seasonal activities (berry/fruit picking)
SEASONAL_ACTIVITIES = [
    {
        "event_name": "Strawberry/Olallieberry Picking at Swanton Berry Farm",
        "location": "Swanton Berry Farm",
        "city": "Davenport",
        "drive_time": "55 min",
        "months": [6, 7, 8],  # Olallieberries Jul-Aug; strawberries iffy mid-July+
        "day_of_week": [5, 6],  # Weekends - Sat, Sun
        "time": "9:00 AM - 5:00 PM",
        "cost": "No entry fee / $8/lb",
        "description": "Organic olallieberry/strawberry U-pick. Call ahead: 831-889-0850 or check Instagram for crop availability — changes weekly. Coastal — bring layers for baby! Baby carrier recommended.",
        "url": "https://www.swantonberryfarm.com",
        "age_range": "All ages",
    },
    {
        "event_name": "U-Pick at Webb Ranch",
        "location": "Webb Ranch",
        "city": "Portola Valley",
        "drive_time": "15 min",
        "months": [6, 7, 8, 9],
        "day_of_week": [5],  # SATURDAYS ONLY — 8am-10am window, arrive early!
        "time": "8:00 AM - 10:00 AM",
        "cost": "$4 adults / free under 2 / + $7/lb berries",
        "description": "Organic blackberries/olallieberries U-pick. Baby under 2 free! SATURDAYS ONLY 8-10am — arrive early, sell out fast. Use baby carrier (uneven terrain). Call 650-854-5417 to confirm crop. Cash/card accepted.",
        "url": "https://www.webbranchinc.com/u-pick-berries.html",
        "age_range": "All ages",
    },
    # Gizdich Ranch berry U-pick is CLOSED for 2026 (reopens apple picking Sept 2026)
    # {
    #     "event_name": "Berry Picking at Gizdich Ranch",
    # },
    {
        "event_name": "Visit Deer Hollow Farm",
        "location": "Deer Hollow Farm",
        "city": "Cupertino",
        "drive_time": "10 min",
        "months": list(range(1, 13)),  # Year-round
        "day_of_week": [1, 2, 3, 4, 5, 6],  # Tue-Sun (Mon closed; Wed closes 1pm)
        "time": "8:00 AM - 4:00 PM",
        "cost": "Free",
        "description": "Free working farm with goats, chickens, pigs, cows. Tue/Thu-Sun 8am-4pm. Wednesday 8am-1pm only. Closed Monday. Arrive after 9am to see animals out.",
        "url": "https://www.deerhollowfarm.org",
        "age_range": "All ages",
    },
    {
        "event_name": "Hidden Villa Farm Visit",
        "location": "Hidden Villa",
        "city": "Los Altos Hills",
        "drive_time": "15 min",
        "months": [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6],  # Closed through Aug 3; reopens Aug 4
        "day_of_week": [1, 2, 3, 4, 5, 6],  # Tues-Sun
        "time": "9:00 AM - 5:00 PM",
        "cost": "$10 parking",
        "description": "1,600-acre organic farm, animals, and trails. REOPENS August 4. Tue-Sun 9am-5pm. Mostly flat near farm buildings; stroller-accessible on paved paths.",
        "url": "https://www.hiddenvilla.org/visit/",
        "age_range": "All ages",
    },
    {
        "event_name": "Lemos Farm Visit",
        "location": "Lemos Farm",
        "city": "Half Moon Bay",
        "drive_time": "35 min",
        "months": list(range(1, 13)),
        "day_of_week": [5, 6],  # Weekends
        "time": "10:00 AM - 5:00 PM",
        "cost": "$29-$34 kids / $17 adults / free under 14 months",
        "description": "Train ride, petting zoo, hay rides. Free for babies under 14 months! Stroller-friendly.",
        "url": "https://www.lemosfarm.com",
        "age_range": "All ages",
    },
    {
        "event_name": "Pumpkin Patch at Webb Ranch",
        "location": "Webb Ranch",
        "city": "Portola Valley",
        "drive_time": "15 min",
        "months": [9, 10],
        "day_of_week": [0, 1, 2, 3, 4, 5, 6],  # Open daily once the patch opens
        "start_date": "2026-09-26",  # Opens the last full weekend of September
        "end_date": "2026-10-31",
        "time": "10:00 AM - 6:00 PM",
        "cost": "No entry fee / activities ticketed",
        "description": "Pumpkin patch with corn maze, hay rides, and farm animals. Activities close at 5pm; weekend activity passes need a reservation. CONFIRM 2026 dates — 650-854-6334. Stroller-tricky on dirt; carrier is easier.",
        "url": "https://www.webbranchinc.com/pumpkin-patch.html",
        "age_range": "All ages",
    },
]

# Great parks for baby picnics & walks
PARKS_PICNIC_SPOTS = [
    {
        "event_name": "Picnic at Mitchell Park",
        "location": "Mitchell Park",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Playground, large grass areas, picnic tables. Baby swings available. Adjacent to library.",
        "url": "",
        "cost": "Free",
    },
    {
        "event_name": "Walk at Baylands Nature Preserve",
        "location": "Baylands Nature Preserve",
        "city": "Palo Alto",
        "drive_time": "10 min",
        "description": "Flat stroller-friendly trails along the bay. Great for bird watching with baby.",
        "url": "",
        "cost": "Free",
    },
    {
        "event_name": "Picnic at Rinconada Park",
        "location": "Rinconada Park",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Shaded picnic area, playground, pool nearby. Quiet neighborhood park.",
        "url": "",
        "cost": "Free",
    },
    {
        "event_name": "Explore Stanford Dish Trail",
        "location": "The Dish",
        "city": "Stanford",
        "drive_time": "5 min",
        "description": "3.7 mile loop with beautiful views. Stroller-friendly paved trail. Go early for cooler temps.",
        "url": "",
        "cost": "Free",
    },
    {
        "event_name": "Visit Shoreline Park & Lake",
        "location": "Shoreline Park",
        "city": "Mountain View",
        "drive_time": "10 min",
        "description": "Lake, walking paths, playground, picnic areas. Watch the Google geese!",
        "url": "",
        "cost": "Free",
    },
    {
        "event_name": "Explore Half Moon Bay State Beach",
        "location": "Half Moon Bay State Beach",
        "city": "Half Moon Bay",
        "drive_time": "35 min",
        "description": "Beautiful coastal trails and beach. Great for a morning stroller walk.",
        "url": "",
        "cost": "$10 parking",
    },
    {
        "event_name": "Visit San Francisco Zoo",
        "location": "San Francisco Zoo",
        "city": "San Francisco",
        "drive_time": "45 min",
        "description": "Great for babies - animals, carousel, playground. Free for under 2.",
        "url": "https://www.sfzoo.org",
        "cost": "$29-$31 adults (weekday/weekend) / free under 2",
        "time": "10:00 AM - 5:00 PM",
    },
    {
        "event_name": "Palo Alto Junior Museum & Zoo",
        "location": "Palo Alto Junior Museum & Zoo",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Hands-on science exhibits, live animals, outdoor play. Great for babies! Tue-Sun 10am-5pm.",
        "url": "https://www.paloaltozoo.org",
        "cost": "$14 (weekday AM/weekends) / $10 (weekday PM) / free under 12 months",
        "time": "10:00 AM - 5:00 PM",
    },
    {
        "event_name": "Visit CuriOdyssey",
        "location": "CuriOdyssey",
        "city": "San Mateo",
        "drive_time": "20 min",
        "description": "Science playground + small zoo with ~100 live animals at Coyote Point. Free for under 18 months.",
        "url": "https://curiodyssey.org",
        "cost": "$15 adults / free under 18mo",
        "time": "10:00 AM - 5:00 PM",
    },
    {
        "event_name": "Magical Bridge Playground",
        "location": "Magical Bridge Playground (Mitchell Park)",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "All-inclusive playground with baby swings, sensory areas, music features. Beautifully designed for all abilities.",
        "url": "https://www.magicalbridge.org",
        "cost": "Free",
        "time": "Anytime",
    },
    {
        "event_name": "Palo Alto Art Center - Family Drop-In",
        "location": "Palo Alto Art Center",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Free art center with rotating exhibits. Family Days with art-making activities for kids.",
        "url": "https://www.cityofpaloalto.org/Departments/Community-Services/Arts-Sciences/Palo-Alto-Art-Center",
        "cost": "Free",
        "time": "10:00 AM - 5:00 PM",
    },
    {
        "event_name": "Visit Children's Fairyland",
        "location": "Children's Fairyland",
        "city": "Oakland",
        "drive_time": "45 min",
        "description": "Storybook theme park for ages 0-8. Puppet shows, petting zoo, train ride, gentle rides.",
        "url": "https://fairyland.org",
        "cost": "$19 adults / $17 children (1-17) / free under 1",
        "time": "10:00 AM - 5:00 PM",
    },
    {
        "event_name": "Emma Prusch Farm Park",
        "location": "Emma Prusch Farm Park",
        "city": "San Jose",
        "drive_time": "25 min",
        "description": "Free historic farm park with 4-H livestock, rare fruit orchard, community gardens, and huge grass fields. Stroller-friendly and uncrowded. Great hidden gem!",
        "url": "https://pruschfarmpark.org/",
        "cost": "Free",
        "time": "8:30 AM - 8:30 PM",
    },
    {
        "event_name": "Ardenwood Historic Farm",
        "location": "Ardenwood Historic Farm",
        "city": "Fremont",
        "drive_time": "30 min",
        "description": "Historic working farm with drop-in programs (Toddler Time, butter making, animal meet-and-greets). Baby under 4 is free! Tue-Sun 10am-4pm. Cashless payment only.",
        "url": "https://www.ebparks.org/parks/ardenwood",
        "cost": "$2-4 children / $4-6 adults / free under 4",
        "time": "10:00 AM - 4:00 PM",
    },
]

# One-time summer events (specific dates) — added to calendar individually
ONE_TIME_SUMMER_EVENTS = [
    # Mountain View Free Outdoor Movie Nights (Fridays at neighborhood parks)
    {
        "event_name": "Free Outdoor Movie: SpongeBob: The Search for SquarePants",
        "date": "2026-07-17", "day": "Friday", "time": "8:30 PM",
        "location": "Sylvan Park", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/special-events/summer-outdoor-movie-night-series",
        "description": "Free outdoor movie night. Bring a blanket or lawn chair. Flat grass park — stroller-friendly. Food truck may be on site. | Source: City of Mountain View",
        "category": "Community Events",
    },
    {
        "event_name": "Free Outdoor Movie: Hoppers",
        "date": "2026-07-24", "day": "Friday", "time": "8:30 PM",
        "location": "Stevenson Park", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/special-events/summer-outdoor-movie-night-series",
        "description": "Free outdoor movie night. Bring a blanket or lawn chair. Flat grass park — stroller-friendly. | Source: City of Mountain View",
        "category": "Community Events",
    },
    {
        "event_name": "Free Outdoor Movie: Super Mario Galaxy",
        "date": "2026-07-31", "day": "Friday", "time": "8:30 PM",
        "location": "Whisman Park", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/special-events/summer-outdoor-movie-night-series",
        "description": "Free outdoor movie night. Bring a blanket or lawn chair. Flat grass park — stroller-friendly. | Source: City of Mountain View",
        "category": "Community Events",
    },
    {
        "event_name": "Free Outdoor Movie: Lilo & Stitch (live action)",
        "date": "2026-08-14", "day": "Friday", "time": "8:30 PM",
        "location": "Rengstorff Park", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/special-events/summer-outdoor-movie-night-series",
        "description": "Free outdoor movie night. Bring a blanket or lawn chair. Flat grass park — stroller-friendly. | Source: City of Mountain View",
        "category": "Community Events",
    },
    # Filoli Art Walk - kids 0-14 free with adult admission
    {
        "event_name": "Filoli Art Walk (Kids Go Free!)",
        "date": "2026-07-25", "day": "Saturday", "time": "10:00 AM - 7:00 PM",
        "location": "Filoli Historic House & Garden", "city": "Woodside", "drive_time": "20 min",
        "cost": "Kids 0-14 FREE / Adults: see website (members free)",
        "age_range": "All ages",
        "url": "https://filoli.org/events/",
        "description": "Artisans market in the gardens with children's art activity area, local vendors, and food trucks. Kids under 14 FREE with paying adult. Stroller-friendly paved paths. | Source: Filoli",
        "category": "Special Events",
    },
    {
        "event_name": "Filoli Art Walk (Kids Go Free!)",
        "date": "2026-07-26", "day": "Sunday", "time": "10:00 AM - 5:00 PM",
        "location": "Filoli Historic House & Garden", "city": "Woodside", "drive_time": "20 min",
        "cost": "Kids 0-14 FREE / Adults: see website (members free)",
        "age_range": "All ages",
        "url": "https://filoli.org/events/",
        "description": "Artisans market in the gardens with children's art activity area, local vendors, and food trucks. Kids under 14 FREE with paying adult. Stroller-friendly paved paths. | Source: Filoli",
        "category": "Special Events",
    },
    # ── PALO ALTO EVENTS ───────────────────────────────────────────
    {
        "event_name": "Palo Alto Twilight Concert: Fleetwood Mask (Fleetwood Mac tribute)",
        "date": "2026-07-18", "day": "Saturday", "time": "6:30 PM - 9:00 PM",
        "location": "Rinconada Park", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloalto.gov/Departments/Community-Services/Arts-Sciences/Palo-Alto-Childrens-Theatre/Twilight-Concert-Series",
        "description": "Free outdoor concert at Rinconada Park. Bring a blanket, food trucks on site. Very stroller-friendly. | Source: City of Palo Alto",
        "category": "Community Events",
    },
    {
        "event_name": "Palo Alto Twilight Concert: Legally Blue (blues ensemble)",
        "date": "2026-08-08", "day": "Saturday", "time": "6:30 PM - 9:00 PM",
        "location": "Rinconada Park", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloalto.gov/Departments/Community-Services/Arts-Sciences/Palo-Alto-Childrens-Theatre/Twilight-Concert-Series",
        "description": "Free outdoor blues concert at Rinconada Park. Bring a blanket, food trucks on site. Very stroller-friendly. | Source: City of Palo Alto",
        "category": "Community Events",
    },
    {
        "event_name": "Music in the Park: Carnatic Flute Concert",
        "date": "2026-07-25", "day": "Saturday", "time": "4:00 PM - 5:30 PM",
        "location": "Mitchell Park", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.eventbrite.com/e/music-in-the-park-series-carnatic-violin-concert-tickets-1989798577108",
        "description": "Free classical Indian music in the park. Calm afternoon concert — great for babies. Flat grass, stroller-friendly. | Source: Palo Alto Parks",
        "category": "Community Events",
    },
    {
        "event_name": "Music in the Park: Hindustani Sarangi Concert",
        "date": "2026-08-22", "day": "Saturday", "time": "4:00 PM - 5:30 PM",
        "location": "Mitchell Park", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.eventbrite.com/e/music-in-the-park-series-hindustani-sarangi-concert-tickets-1989799252127",
        "description": "Free classical Indian music in the park. Calm afternoon concert — great for babies. Flat grass, stroller-friendly. | Source: Palo Alto Parks",
        "category": "Community Events",
    },
    {
        "event_name": "Palo Alto Family Movie Night: GOAT",
        "date": "2026-07-17", "day": "Friday", "time": "7:30 PM",
        "location": "Mitchell Park Athletics Fields", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloalto.gov",
        "description": "Free outdoor family movie night. Gates open 7pm, movie at sunset ~7:30pm. Bring blanket/chairs. Flat grass. | Source: City of Palo Alto",
        "category": "Community Events",
    },
    {
        "event_name": "Palo Alto Family Movie Night: Hoppers",
        "date": "2026-07-31", "day": "Friday", "time": "7:30 PM",
        "location": "Mitchell Park Athletics Fields", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloalto.gov",
        "description": "Free outdoor family movie night. Gates open 7pm, movie at sunset ~7:30pm. Bring blanket/chairs. Flat grass. | Source: City of Palo Alto",
        "category": "Community Events",
    },
    {
        "event_name": "Palo Alto Family Movie Night: Super Mario Galaxy Movie",
        "date": "2026-08-14", "day": "Friday", "time": "7:30 PM",
        "location": "Mitchell Park Athletics Fields", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloalto.gov",
        "description": "Free outdoor family movie night. Gates open 7pm, movie at sunset ~7:30pm. Bring blanket/chairs. Flat grass. | Source: City of Palo Alto",
        "category": "Community Events",
    },
    {
        "event_name": "Palo Alto Festival of the Arts",
        "date": "2026-08-22", "day": "Saturday", "time": "10:00 AM - 6:00 PM",
        "location": "University Avenue", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloaltochamber.com/festival-of-the-arts/",
        "description": "250+ artists on University Ave, live music stages, Kids' Chalk-a-Lot activity area, food vendors. Wide boulevard, very stroller-friendly. Free admission and parking. | Source: Palo Alto Chamber",
        "category": "Special Events",
    },
    {
        "event_name": "Palo Alto Festival of the Arts",
        "date": "2026-08-23", "day": "Sunday", "time": "10:00 AM - 6:00 PM",
        "location": "University Avenue", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloaltochamber.com/festival-of-the-arts/",
        "description": "250+ artists on University Ave, live music stages, Kids' Chalk-a-Lot activity area, food vendors. Wide boulevard, very stroller-friendly. Free admission and parking. | Source: Palo Alto Chamber",
        "category": "Special Events",
    },
    # ── MOUNTAIN VIEW EVENTS ────────────────────────────────────────
    *[{
        "event_name": "Mountain View Concerts on the Plaza",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM - 7:30 PM",
        "location": "Civic Center Plaza", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/special-events/concerts-on-the-plaza",
        "description": "Free weekly outdoor concert at Civic Center Plaza. Food trucks and beer/wine available. Very stroller-friendly paved plaza. | Source: City of Mountain View",
        "category": "Community Events",
    } for d in ["2026-07-17","2026-07-24","2026-07-31","2026-08-07","2026-08-14","2026-08-21","2026-08-28","2026-09-04"]],
    *[{
        "event_name": "Mountain View Music on Castro (Free Weekly)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "5:00 PM - 6:45 PM",
        "location": "200 Block Castro Street", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/music-on-castro",
        "description": "Free live music on the pedestrian street. Walkable, flat, great for strollers. | Source: City of Mountain View",
        "category": "Community Events",
    } for d in ["2026-07-15","2026-07-22","2026-07-29","2026-08-05","2026-08-12","2026-08-19","2026-08-26","2026-09-02"]],
    # ── LOS ALTOS EVENTS ────────────────────────────────────────────
    *[{
        "event_name": f"Los Altos Summer Concert (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:30 PM - 8:00 PM",
        "location": "Hillview Park", "city": "Los Altos", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.losaltosca.gov/766/2026-Summer-Concert-Series",
        "description": "Free summer concert in the park. Bring a blanket. Grassy field, stroller-friendly. | Source: City of Los Altos",
        "category": "Community Events",
    } for d in ["2026-07-16","2026-07-23","2026-07-30"]],
    # ── MENLO PARK EVENTS ───────────────────────────────────────────
    *[{
        "event_name": f"Menlo Park Summer Concert (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM - 8:00 PM",
        "location": "Fremont Park", "city": "Menlo Park", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.menlopark.gov/Government/Departments/Library-and-Community-Services/Events/Community-events/Summer-Concert-Series",
        "description": "Free live concert in the park. Relaxed vibe, great for families with babies. Bring a blanket. | Source: City of Menlo Park",
        "category": "Community Events",
    } for d in ["2026-07-15","2026-07-22","2026-07-29","2026-07-31","2026-08-05","2026-08-07","2026-08-12"]],
    # ── REDWOOD CITY EVENTS ─────────────────────────────────────────
    *[{
        "event_name": "Redwood City Music on the Square (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM - 8:00 PM",
        "location": "Courthouse Square", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.redwoodcity.org/residents/redwood-city-events/music",
        "description": "Free outdoor concert at Courthouse Square. Flat open plaza, very stroller-friendly. | Source: City of Redwood City",
        "category": "Community Events",
    } for d in ["2026-07-17","2026-07-24","2026-07-31","2026-08-07","2026-08-14","2026-08-21","2026-08-28","2026-09-04"]],
    *[{
        "event_name": "Redwood City Music in the Park (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM - 8:00 PM",
        "location": "Stafford Park", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.redwoodcity.org/musicinthepark",
        "description": "Free weekly live music in the park. Bring lawn chairs. | Source: City of Redwood City",
        "category": "Community Events",
    } for d in ["2026-07-15","2026-07-22","2026-07-29","2026-08-05","2026-08-12","2026-08-19"]],
    *[{
        "event_name": "Redwood City Kids Movie (FREE 6pm kids film)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM",
        "location": "Courthouse Square", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.redwoodcity.org/residents/redwood-city-events/movies",
        "description": "Free outdoor kids movie double-bill night. Kids film at 6pm (feature at 8:30pm). Bring blanket/chairs. Open plaza. | Source: City of Redwood City",
        "category": "Community Events",
    } for d in ["2026-07-16","2026-07-23","2026-07-30","2026-08-06","2026-08-13","2026-08-20","2026-08-27"]],
    {
        "event_name": "Redwood City Kids Rock! Morning Concert (Free)",
        "date": "2026-07-18", "day": "Saturday", "time": "10:00 AM - 12:00 PM",
        "location": "Courthouse Square", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.redwoodcity.org",
        "description": "Saturday morning kids concert series! Perfect timing for babies. Flat open plaza, very stroller-friendly. | Source: City of Redwood City",
        "category": "Community Events",
    },
    {
        "event_name": "Redwood City Kids Rock! Morning Concert (Free)",
        "date": "2026-08-08", "day": "Saturday", "time": "10:00 AM - 12:00 PM",
        "location": "Courthouse Square", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.redwoodcity.org",
        "description": "Saturday morning kids concert series! Perfect timing for babies. Flat open plaza, very stroller-friendly. | Source: City of Redwood City",
        "category": "Community Events",
    },
    {
        "event_name": "Shakespeare in the Park: Antony & Cleopatra (Free)",
        "date": "2026-08-15", "day": "Saturday", "time": "6:00 PM - 7:30 PM",
        "location": "Red Morton Park Amphitheater", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.eventbrite.com/e/free-shakespeare-in-the-parks-antony-and-cleopatra-in-red-morton-park-tickets-1991008316471",
        "description": "Free outdoor Shakespeare. ~90 min, no intermission. Flat grassy lawn, stroller-friendly. No reservations needed. | Source: Shakespeare in the Park",
        "category": "Community Events",
    },
    *[{
        "event_name": "Shakespeare in the Park: Antony & Cleopatra (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM - 7:30 PM",
        "location": "Red Morton Park Amphitheater", "city": "Redwood City", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.eventbrite.com/e/free-shakespeare-in-the-parks-antony-and-cleopatra-in-red-morton-park-tickets-1991008316471",
        "description": "Free outdoor Shakespeare. ~90 min, no intermission. Flat grassy lawn, stroller-friendly. | Source: Shakespeare in the Park",
        "category": "Community Events",
    } for d in ["2026-08-16","2026-08-22","2026-08-23","2026-08-29","2026-08-30"]],
    # ── SUNNYVALE EVENTS ────────────────────────────────────────────
    *[{
        "event_name": "Sunnyvale Downtown Summer Concert (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:00 PM - 8:30 PM",
        "location": "Historic Murphy Avenue", "city": "Sunnyvale", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://sunnyvaledowntown.org/events",
        "description": "Free live music on Sunnyvale's pedestrian street. Great stroller-friendly walkable area. | Source: Sunnyvale Downtown",
        "category": "Community Events",
    } for d in ["2026-07-15","2026-07-22","2026-07-29","2026-08-05","2026-08-12","2026-08-19","2026-08-26"]],
    *[{
        "event_name": f"Sunnyvale Sunset Movie (Free Outdoor)",
        "date": d["date"], "day": d["day"], "time": "7:40 PM",
        "location": d["loc"], "city": "Sunnyvale", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.sunnyvale.ca.gov/recreation-and-community/special-events",
        "description": f"Free outdoor movie: {d['film']}. Bring blanket/chairs. Flat park. | Source: City of Sunnyvale",
        "category": "Community Events",
    } for d in [
        {"date":"2026-08-07","day":"Friday","film":"The Wild Robot","loc":"Serra Park"},
        {"date":"2026-08-14","day":"Friday","film":"Super Mario Galaxy Movie","loc":"Columbia Park"},
        {"date":"2026-08-21","day":"Friday","film":"A Minecraft Movie","loc":"Murphy Park"},
        {"date":"2026-08-28","day":"Friday","film":"Elio","loc":"Sunnyvale Community Center"},
    ]],
    # ── CAMPBELL & OTHER ────────────────────────────────────────────
    *[{
        "event_name": "Campbell Summer Concert: Orchard City Green (Free)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:30 PM - 8:00 PM",
        "location": "Orchard City Green", "city": "Campbell", "drive_time": "25 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.campbellca.gov/280/Summer-Concert-Series",
        "description": "Free Thursday concert series in downtown Campbell's open green space. | Source: City of Campbell",
        "category": "Community Events",
    } for d in ["2026-07-16","2026-07-23","2026-07-30","2026-08-06","2026-08-13","2026-08-20","2026-08-27"]],
    # ── OFJCC REMAINING EVENTS ──────────────────────────────────────
    *[{
        "event_name": "LIBI Play Space at OFJCC (Free Drop-In)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "9:30 AM - 12:00 PM",
        "location": "Oshman Family JCC", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free (no membership required)", "age_range": "0-3 years",
        "url": "https://paloaltojcc.org/libi-play-space-weekly",
        "description": "Drop-in morning play for parents with babies and toddlers. No RSVP, walk-ins welcome. Jeff Center for Families. | Source: OFJCC",
        "category": "Special Events",
    } for d in ["2026-07-22","2026-07-29","2026-08-12","2026-08-19","2026-08-26","2026-09-02"]],
    {
        "event_name": "Infant First Aid & CPR Class at OFJCC",
        "date": "2026-08-09", "day": "Sunday", "time": "9:30 AM - 12:00 PM",
        "location": "Oshman Family JCC", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "See website (registration required)", "age_range": "New parents",
        "url": "https://paloaltojcc.org/youth-family-upcoming-events/",
        "description": "Infant First Aid & CPR class at OFJCC. Essential for new parents. Registration required. | Source: OFJCC",
        "category": "Classes & Groups",
    },
    # ── BIGGER FESTIVALS ────────────────────────────────────────────
    {
        "event_name": "PV Palooza Summer Music Festival (Free)",
        "date": "2026-08-29", "day": "Saturday", "time": "10:30 AM - 8:30 PM",
        "location": "Portola Valley Town Center", "city": "Portola Valley", "drive_time": "15 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.pvpalooza.com/",
        "description": "All-day free music festival with 20 local bands on 4 stages. Family-friendly community event. | Source: PV Palooza",
        "category": "Community Events",
    },
    {
        "event_name": "Coyote Point Summerfest (Free)",
        "date": "2026-08-15", "day": "Saturday", "time": "12:00 PM - 4:00 PM",
        "location": "Coyote Point Recreation Area", "city": "San Mateo", "drive_time": "20 min",
        "cost": "Free admission / $6 parking", "age_range": "All ages",
        "url": "https://www.smcgov.org/parks/coyote-point-summerfest-community-celebration",
        "description": "Giant kites, taiko drumming, Ballet Folklorico, train rides, food trucks. Flat waterfront park, very baby-friendly! | Source: San Mateo County Parks",
        "category": "Community Events",
    },
    # ── MOUNTAIN VIEW LIBRARY (dynamically loaded — curated manually) ──
    *[{
        "event_name": "MV Library Baby Storytime (0-18mo) + Stay & Play",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:15 AM",
        "location": "Mountain View Public Library", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "0-18 months",
        "url": "https://mountainview.libcal.com/calendar",
        "description": "Musical storytime with books, bounces, and dancing. Stay & Play afterward. Great for babies! | Source: Mountain View Public Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-15","2026-07-22","2026-07-29","2026-08-05","2026-08-12","2026-08-19","2026-08-26","2026-09-02"]],
    *[{
        "event_name": "MV Library Outdoor Storytime at Pioneer Park",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:00 AM",
        "location": "Pioneer Park (outdoors)", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://mountainview.libcal.com/calendar",
        "description": "Outdoor storytime at Pioneer Park. No registration needed, weather permitting. Stroller-friendly grassy park! | Source: Mountain View Public Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-14","2026-07-21","2026-07-28","2026-08-04","2026-08-11","2026-08-18","2026-08-25"]],
    *[{
        "event_name": "MV Library Lullaby Storytime (Evening for Babies)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:30 PM - 7:00 PM",
        "location": "Mountain View Public Library", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "0-18 months",
        "url": "https://mountainview.libcal.com/calendar",
        "description": "Evening baby storytime — perfect for working parents! Calm, soothing songs and stories for babies. | Source: Mountain View Public Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-20","2026-07-27","2026-08-03","2026-08-10","2026-08-17","2026-08-24","2026-08-31"]],
    # ── SUNNYVALE LIBRARY (specific confirmed dates) ─────────────────
    *[{
        "event_name": "Sunnyvale Baby Lapsit & Playtime (0-12mo)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 12:00 PM",
        "location": "Sunnyvale Public Library", "city": "Sunnyvale", "drive_time": "15 min",
        "cost": "Free", "age_range": "0-12 months",
        "url": "https://www.library.sunnyvale.ca.gov/events",
        "description": "Baby lapsit storytime followed by open stay-and-play time. Specifically for babies 0-12 months. | Source: Sunnyvale Public Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-16","2026-07-23","2026-07-30","2026-08-06","2026-08-13","2026-08-20","2026-08-27"]],
    {
        "event_name": "Sunnyvale Japanese Storytime (0-5 years)",
        "date": "2026-07-18", "day": "Saturday", "time": "11:00 AM - 12:00 PM",
        "location": "Sunnyvale Public Library", "city": "Sunnyvale", "drive_time": "15 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://www.library.sunnyvale.ca.gov/events",
        "description": "Japanese storytime for young children by Poponta Children's Cultural Society. | Source: Sunnyvale Public Library",
        "category": "Library & Storytimes",
    },
    {
        "event_name": "Sunnyvale Early Learning Playtime (Drop-In, 0-5yr)",
        "date": "2026-07-25", "day": "Saturday", "time": "3:00 PM - 5:00 PM",
        "location": "Sunnyvale Public Library", "city": "Sunnyvale", "drive_time": "15 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://www.library.sunnyvale.ca.gov/events",
        "description": "Drop-in early learning play session at the library. Fun for babies and toddlers! | Source: Sunnyvale Public Library",
        "category": "Library & Storytimes",
    },
    # ── PALO ALTO LIBRARY SUMMER SPECIAL EVENTS ──────────────────────
    # Note: Regular storytimes (Family Storytime, Little Ones, Bilingual, Music & Movement)
    # are on BREAK all of August and resume week of Sept 1.
    {
        "event_name": "PA Library: Happy Birds Performance",
        "date": "2026-07-18", "day": "Saturday", "time": "1:30 PM - 2:30 PM",
        "location": "Mitchell Park Community Center", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Bird performance — fun for babies and young kids! Summer Reading Program event. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    },
    {
        "event_name": "PA Library: Disco Bubbles with Daisy",
        "date": "2026-08-01", "day": "Saturday", "time": "3:00 PM - 4:00 PM",
        "location": "Children's Library (Secret Garden)", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Disco bubbles performance in the Secret Garden outdoor space! Perfect for babies. Summer Reading finale event. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    },
    {
        "event_name": "PA Library: Music & Puppets with Mr. Elephant",
        "date": "2026-08-01", "day": "Saturday", "time": "4:30 PM - 5:30 PM",
        "location": "Children's Library (Secret Garden)", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Music and puppet show in the Secret Garden. Great for babies and toddlers! Summer Reading finale. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    },
    {
        "event_name": "PA Library: Marc Griffiths Ventriloquy Show",
        "date": "2026-08-08", "day": "Saturday", "time": "4:00 PM - 5:00 PM",
        "location": "Mitchell Park Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Ventriloquism show — fun for babies and young children! | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    },
    # ── PALO ALTO LIBRARY RECURRING STORYTIMES (curated — BiblioCommons only shows current week)
    # Storytimes run July 14–31, BREAK all August, resume Sept 1 week.
    # Tuesday Family Storytime — Children's Library, 1276 Harriet St
    *[{
        "event_name": "PA Library: Family Storytime (Tue – Children's Library)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:00 AM",
        "location": "Children's Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Family storytime with songs, rhymes, and stories. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-21","2026-07-28","2026-09-01"]],
    # Wednesday Little Ones Storytime — Children's Library
    *[{
        "event_name": "PA Library: Little Ones Storytime (Wed – Children's Library)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:00 AM",
        "location": "Children's Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-3 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Storytime for babies and toddlers with songs, rhymes, and movement activities. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-22","2026-07-29","2026-09-02"]],
    # Wednesday Music & Movement — Mitchell Park Library
    *[{
        "event_name": "PA Library: Music & Movement (Wed evening – Mitchell Park)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "6:30 PM - 7:15 PM",
        "location": "Mitchell Park Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Build early literacy through movement, songs, and dance. Evening option great for working parents! | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-22","2026-07-29","2026-09-02"]],
    # Thursday Bilingual Family Storytime — College Terrace Library
    *[{
        "event_name": "PA Library: Bilingual Storytime Spanish/English (Thu – College Terrace)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:00 AM",
        "location": "College Terrace Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Bilingual storytime in Spanish and English with songs, rhymes, and movement. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-23","2026-07-30","2026-09-03"]],
    # Friday Family Storytime — Downtown Library
    *[{
        "event_name": "PA Library: Family Storytime (Fri – Downtown Library)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:00 AM",
        "location": "Downtown Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Family storytime with songs, rhymes, and stories. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-24","2026-07-31","2026-09-04"]],
    # Saturday Family Storytime — Mitchell Park Library (continues through August)
    *[{
        "event_name": "PA Library: Saturday Family Storytime (Mitchell Park)",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:30 AM - 11:00 AM",
        "location": "Mitchell Park Library", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "0-5 years",
        "url": "https://paloalto.bibliocommons.com/v2/events",
        "description": "Saturday morning family storytime. Songs, rhymes, and stories. Continues through August. | Source: Palo Alto City Library",
        "category": "Library & Storytimes",
    } for d in ["2026-07-18","2026-07-25","2026-08-01","2026-08-08","2026-08-15","2026-08-22","2026-08-29","2026-09-05"]],

    # ── Fall 2026 — dates confirmed against official sources ──
    *[{
        "event_name": "The Great Glass Pumpkin Patch",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "10:00 AM - 5:00 PM",
        "location": "Palo Alto Art Center", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.paloalto.gov/Departments/Community-Services/Arts-Sciences/Palo-Alto-Art-Center/Special-Events/Pumpkins",
        "description": "Thousands of hand-blown glass pumpkins on the Art Center lawn with live glassblowing demos. Free admission. Outdoors and stroller-friendly — glass is on low tables, so keep baby carried or strapped in. | Source: City of Palo Alto",
        "category": "Special Events",
    } for d in ["2026-09-26", "2026-09-27"]],
    *[{
        "event_name": "Half Moon Bay Art & Pumpkin Festival",
        "date": d, "day": date.fromisoformat(d).strftime("%A"), "time": "9:00 AM - 5:00 PM",
        "location": "Main Street (Miramontes to Spruce)", "city": "Half Moon Bay", "drive_time": "35 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://hmbpumpkinfest.com/",
        "description": "Free street festival with a Family Fun Zone at 620 Main Street — non-competitive pumpkin carving, pie-eating contests, and a diaper changing/family rest station. Giant champion pumpkins on display. Very crowded; carrier beats stroller. Coastal fog — bring layers. | Source: HMB Art & Pumpkin Festival",
        "category": "Special Events",
    } for d in ["2026-10-17", "2026-10-18"]],
]

# Annual fall events whose 2026 dates aren't published yet.
# Listed as TBD so they show up as a reminder instead of asserting a wrong date.
FALL_EVENTS_TBD = [
    {
        "event_name": "Halloween Hoopla Parade & Trick-or-Treat",
        "location": "Fremont Park & Downtown Menlo Park", "city": "Menlo Park", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.menlopark.gov/Citywide-calendar",
        "description": "Costume parade to Fremont Park, then trick-or-treating at downtown shops, plus carnival games, crafts, and a magic show. Usually the Saturday before Halloween — confirm the 2026 date on the city calendar.",
        "category": "Community Events",
    },
    {
        "event_name": "Halloween on Castro Street",
        "location": "Downtown Castro Street", "city": "Mountain View", "drive_time": "10 min",
        "cost": "Free", "age_range": "All ages",
        "url": "https://www.mountainview.gov/our-city/departments/community-services/special-events",
        "description": "Decorated storefronts and trick-or-treating along downtown Castro Street, with discounts for anyone in costume. Flat, walkable, stroller-friendly. Confirm the 2026 date with the city.",
        "category": "Community Events",
    },
    {
        "event_name": "Halloween at the Junior Museum & Zoo",
        "location": "Palo Alto Junior Museum & Zoo", "city": "Palo Alto", "drive_time": "5 min",
        "cost": "See website / free under 12 months", "age_range": "0-9 years",
        # Distinct from the zoo homepage on purpose — deduplicate() drops a TBD row
        # whose URL already appears on a dated row.
        "url": "https://www.paloaltozoo.org/Programs/Family-Programs",
        "description": "Annual Halloween party — trick-or-treating through the zoo plus animal encounters. Tickets sell out early; confirm the 2026 date and on-sale time.",
        "category": "Special Events",
    },
    {
        "event_name": "Apple U-Pick at Gizdich Ranch",
        "location": "Gizdich Ranch", "city": "Watsonville", "drive_time": "1 hr",
        "cost": "Pay per pound", "age_range": "All ages",
        "url": "https://www.gizdich-ranch.com/u-pick",
        "description": "Apple picking opens in late September and runs into fall. Card only — no cash at U-pick. Call 831-722-1056 for exact opening dates and current varieties. Flat orchard rows; stroller works on dry ground.",
        "category": "Outdoor & Nature",
    },
]

# Indoor play spaces (weekday and weekend entries)
INDOOR_PLAY_SPACES = [
    {
        "event_name": "Open Play at La Petite Playhouse",
        "location": "La Petite Playhouse",
        "city": "Redwood City",
        "drive_time": "15 min",
        "description": "10,000 sq ft indoor playground with separate baby/toddler area. Great for rainy days! Non-walkers (babies) only $8. Up to 2 adults FREE per child. Walk-ins welcome.",
        "url": "https://lapetiteplay.com",
        "cost": "$8 non-walkers (babies) / $18 walkers / adults free",
        "age_range": "0-5 years",
        "day_of_week": [0, 1, 2, 3, 4, 5, 6],
        "time": "9:00 AM - 5:00 PM",
    },
]

# Baby classes with known recurring schedules
BABY_CLASSES = [
    {
        "event_name": "My Gym - Little Bundles & Tiny Tykes",
        "location": "My Gym Palo Alto",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Little Bundles (6wk-6mo), Tiny Tykes (3-12mo). Music, movement, and play. $29 trial week available. ~$110/month after.",
        "url": "https://www.mygym.com/paloalto",
        "cost": "~$110/month (try 1 week for $29)",
        "age_range": "6 weeks - 21 months",
        "category": "Classes & Groups",
    },
    {
        "event_name": "Music Together - Baby & Family Music",
        "location": "Music Together Menlo Park",
        "city": "Menlo Park",
        "drive_time": "10 min",
        "description": "Early childhood music classes. Babies class (0-8mo) and mixed-age (birth-5yr). Singing, instruments, movement. Free demo class available — call 650-799-1624.",
        "url": "https://www.mt-mp.com/schedule.html",
        "cost": "$305/semester (10 weeks) — free demo class available",
        "age_range": "0-8 months (babies) / 0-5 years (mixed)",
        "category": "Classes & Groups",
    },
    {
        "event_name": "The Little Gym - Bugs Class",
        "location": "The Little Gym",
        "city": "Mountain View",
        "drive_time": "10 min",
        "description": "Parent-child gym classes. Bugs (4-10mo): tummy time, crawling, sensory play, songs. Free introductory visit available — call to schedule.",
        "url": "https://www.thelittlegym.com/california-mountain-view/classes/",
        "cost": "~$76/month — free intro visit available",
        "age_range": "4 months - 2.5 years",
        "category": "Classes & Groups",
    },
    {
        "event_name": "British Swim School - Tadpole Program",
        "location": "British Swim School",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Gentle water acclimation swim lessons. 3-36 months with parent in the water. Warm pool, small classes. Free trial lesson (Smart Start Guarantee).",
        "url": "https://britishswimschool.com/palo-alto/programs/",
        "cost": "~$250/month + $50 registration — free trial lesson",
        "age_range": "3-36 months",
        "category": "Classes & Groups",
    },
    {
        "event_name": "FIT4MOM Stroller Strides",
        "location": "FIT4MOM SF Peninsula",
        "city": "Palo Alto",
        "drive_time": "5 min",
        "description": "Outdoor stroller fitness class for moms with babies. Strength, cardio, community. Start ~6 weeks postpartum. First class is always free!",
        "url": "https://sfpeninsula.fit4mom.com",
        "cost": "Paid monthly (first class FREE)",
        "age_range": "6 weeks+ (in stroller)",
        "category": "Classes & Groups",
    },
    {
        "event_name": "Gymboree Play & Music",
        "location": "Gymboree",
        "city": "San Mateo",
        "drive_time": "20 min",
        "description": "Play, music, and art classes for babies and toddlers. Age-appropriate developmental activities. First class free — try before committing.",
        "url": "https://www.gymboreeclasses.com/en/locations/CA/San-Mateo/",
        "cost": "Monthly membership (first class FREE)",
        "age_range": "0-5 years",
        "category": "Classes & Groups",
    },
]


def get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a month.
    weekday: 0=Monday, 6=Sunday
    n: 1-based (1=first, 2=second, etc.)
    """
    first_day = date(year, month, 1)
    # Find first occurrence of the weekday
    days_ahead = weekday - first_day.weekday()
    if days_ahead < 0:
        days_ahead += 7
    first_occurrence = first_day + timedelta(days=days_ahead)
    return first_occurrence + timedelta(weeks=n - 1)


def generate_recurring_events(weeks_ahead: int = 4) -> list[dict]:
    """Generate concrete dated entries for all recurring events."""
    events = []
    today = date.today()
    cutoff = today + timedelta(weeks=weeks_ahead)

    # Farmers markets
    for name, city, dow, time_str, drive_time, url in FARMERS_MARKETS:
        current = today
        while current <= cutoff:
            if current.weekday() == dow:
                events.append({
                    "date": current.isoformat(),
                    "day": current.strftime("%A"),
                    "time": time_str,
                    "event_name": name,
                    "category": "Community Events",
                    "location": name,
                    "city": city,
                    "drive_time": drive_time,
                    "cost": "Free entry",
                    "age_range": "All ages",
                    "url": url,
                    "description": "Weekly farmers market. Great stroller walk, fresh produce, and samples!",
                })
            current += timedelta(days=1)

    # Free museum days
    for museum in FREE_MUSEUM_DAYS:
        current_month = today.month
        current_year = today.year
        for _ in range(2):  # Check this month and next
            if museum["rule"] == "first_wednesday":
                event_date = get_nth_weekday(current_year, current_month, 2, 1)
            elif museum["rule"] == "second_tuesday":
                event_date = get_nth_weekday(current_year, current_month, 1, 2)
            elif museum["rule"] == "first_saturday":
                event_date = get_nth_weekday(current_year, current_month, 5, 1)
            else:
                continue

            if today <= event_date <= cutoff:
                events.append({
                    "date": event_date.isoformat(),
                    "day": event_date.strftime("%A"),
                    "time": museum["time"],
                    "event_name": museum["event_name"],
                    "category": "Special Events",
                    "location": museum["location"],
                    "city": museum["city"],
                    "drive_time": museum["drive_time"],
                    "cost": "Free",
                    "age_range": museum["age_range"],
                    "url": museum["url"],
                    "description": museum["description"],
                })

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

    # Seasonal activities
    for activity in SEASONAL_ACTIVITIES:
        # Optional hard bounds for seasons that don't align to whole months
        season_start = activity.get("start_date")
        season_end = activity.get("end_date")
        season_start = date.fromisoformat(season_start) if season_start else None
        season_end = date.fromisoformat(season_end) if season_end else None

        current = today
        while current <= cutoff:
            if ((season_start is None or current >= season_start)
                    and (season_end is None or current <= season_end)
                    and current.month in activity["months"]
                    and current.weekday() in activity["day_of_week"]):
                events.append({
                    "date": current.isoformat(),
                    "day": current.strftime("%A"),
                    "time": activity["time"],
                    "event_name": activity["event_name"],
                    "category": "Outdoor & Nature",
                    "location": activity["location"],
                    "city": activity["city"],
                    "drive_time": activity["drive_time"],
                    "cost": activity.get("cost", "See website"),
                    "age_range": activity.get("age_range", "All ages"),
                    "url": activity.get("url", ""),
                    "description": activity["description"],
                })
            current += timedelta(days=1)

    # Parks - generate weekend entries only
    for park in PARKS_PICNIC_SPOTS:
        current = today
        while current <= cutoff:
            if current.weekday() in [5, 6]:  # Weekends
                events.append({
                    "date": current.isoformat(),
                    "day": current.strftime("%A"),
                    "time": park.get("time", "Anytime"),
                    "event_name": park["event_name"],
                    "category": "Outdoor & Nature",
                    "location": park["location"],
                    "city": park["city"],
                    "drive_time": park["drive_time"],
                    "cost": park.get("cost", "Free"),
                    "age_range": "All ages",
                    "url": park.get("url", ""),
                    "description": park["description"],
                })
            current += timedelta(days=1)

    # Indoor play spaces - generate daily entries
    for space in INDOOR_PLAY_SPACES:
        current = today
        while current <= cutoff:
            if current.weekday() in space["day_of_week"]:
                events.append({
                    "date": current.isoformat(),
                    "day": current.strftime("%A"),
                    "time": space["time"],
                    "event_name": space["event_name"],
                    "category": "Classes & Groups",
                    "location": space["location"],
                    "city": space["city"],
                    "drive_time": space["drive_time"],
                    "cost": space.get("cost", "See website"),
                    "age_range": space.get("age_range", "All ages"),
                    "url": space.get("url", ""),
                    "description": space["description"],
                })
            current += timedelta(days=1)

    # Baby classes - generate one entry per week (weekdays)
    for cls in BABY_CLASSES:
        current = today
        week_added = set()
        while current <= cutoff:
            week_num = current.isocalendar()[1]
            if current.weekday() < 5 and week_num not in week_added:  # One weekday per week
                week_added.add(week_num)
                events.append({
                    "date": current.isoformat(),
                    "day": current.strftime("%A"),
                    "time": "See schedule",
                    "event_name": cls["event_name"],
                    "category": cls.get("category", "Classes & Groups"),
                    "location": cls["location"],
                    "city": cls["city"],
                    "drive_time": cls["drive_time"],
                    "cost": cls.get("cost", "See website"),
                    "age_range": cls.get("age_range", "0-12 months"),
                    "url": cls.get("url", ""),
                    "description": cls["description"],
                })
            current += timedelta(days=1)

    # One-time summer events (specific dates)
    from datetime import datetime as dt
    for event in ONE_TIME_SUMMER_EVENTS:
        try:
            event_date = date.fromisoformat(event["date"])
        except (ValueError, KeyError):
            continue
        if today <= event_date <= cutoff:
            events.append({
                "date": event["date"],
                "day": event["day"],
                "time": event.get("time", "See website"),
                "event_name": event["event_name"],
                "category": event.get("category", "Community Events"),
                "location": event["location"],
                "city": event["city"],
                "drive_time": event["drive_time"],
                "cost": event.get("cost", "Free"),
                "age_range": event.get("age_range", "All ages"),
                "url": event.get("url", ""),
                "description": event.get("description", ""),
            })

    # Annual fall events with no published 2026 date yet
    for event in FALL_EVENTS_TBD:
        events.append({
            "date": "TBD",
            "day": "",
            "time": event.get("time", "See website"),
            "event_name": event["event_name"],
            "category": event.get("category", "Community Events"),
            "location": event["location"],
            "city": event["city"],
            "drive_time": event["drive_time"],
            "cost": event.get("cost", "See website"),
            "age_range": event.get("age_range", "All ages"),
            "url": event.get("url", ""),
            "description": event.get("description", ""),
        })

    return events


def scrape_all(weeks_ahead: int = 8) -> list[dict]:
    """Generate all recurring/static events."""
    events = generate_recurring_events(weeks_ahead=weeks_ahead)
    # Add source attribution to all curated events
    for event in events:
        desc = event.get("description", "")
        source = "Source: Curated (hand-picked)"
        event["description"] = f"{desc} | {source}" if desc else source
    print(f"  Generated {len(events)} recurring/seasonal events")
    return events
