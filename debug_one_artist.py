#!/usr/bin/env python3
"""
debug_one_artist.py -- prints EVERY raw event Ticketmaster returns for
one artist name, no filtering, no interpretation. Use this to see the
truth when check_ended_tours.py's summary looks wrong.

USAGE
    export TM_API_KEY="your_key"
    python3 debug_one_artist.py "Ariana Grande"
"""
import os
import sys
import json
import requests

if len(sys.argv) < 2:
    print('Usage: python3 debug_one_artist.py "Artist Name"')
    sys.exit(1)

artist = sys.argv[1]
api_key = os.environ.get("TM_API_KEY")
if not api_key:
    print('Set TM_API_KEY first: export TM_API_KEY="your_key"')
    sys.exit(1)

resp = requests.get(
    "https://app.ticketmaster.com/discovery/v2/events.json",
    params={
        "apikey": api_key,
        "keyword": artist,
        "sort": "date,asc",
        "size": 20,
        "classificationName": "music",
    },
    timeout=15,
)
resp.raise_for_status()
data = resp.json()
events = data.get("_embedded", {}).get("events", [])

print(f"\nRaw Ticketmaster results for '{artist}': {len(events)} events returned\n")
print("=" * 70)

for e in events:
    name = e.get("name", "?")
    date = e.get("dates", {}).get("start", {}).get("localDate", "?")
    time_ = e.get("dates", {}).get("start", {}).get("localTime", "?")
    status = e.get("dates", {}).get("status", {}).get("code", "?")
    venue = "?"
    venues = e.get("_embedded", {}).get("venues", [])
    if venues:
        venue = venues[0].get("name", "?")
        city = venues[0].get("city", {}).get("name", "?")
        venue = f"{venue}, {city}"
    url = e.get("url", "?")

    print(f"NAME:    {name}")
    print(f"DATE:    {date} {time_}")
    print(f"STATUS:  {status}")
    print(f"VENUE:   {venue}")
    print(f"URL:     {url}")
    print("-" * 70)

if not events:
    print("(No events at all -- Ticketmaster found nothing matching this keyword.)")
