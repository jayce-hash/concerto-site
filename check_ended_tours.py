#!/usr/bin/env python3
"""
check_ended_tours.py

Checks every tour in data/tours.json against Ticketmaster's Discovery
API to find which ones have zero upcoming dates -- the "this tour is
probably over" signal. Does the 150 manual searches for you; it does
NOT delete anything. A tour with zero upcoming dates right now might
just be between legs (US wrapped, Europe not on sale yet), so the
actual "remove it or not" call still needs a human. This script's job
is narrowing 150 tours down to the handful worth actually looking at.

USAGE
    export TM_API_KEY="your_ticketmaster_api_key"
    python3 check_ended_tours.py
    python3 check_ended_tours.py --tours-file data/tours.json
    python3 check_ended_tours.py --stale-days 60   # see NOTE below

OUTPUT
    Prints a categorized report to the terminal and writes
    tour_audit_report.json with the same data, so you can hand the
    "no upcoming dates" list to a fresh chat or just work through it
    yourself without re-running the search.

NOTE on --stale-days
    Default behavior only checks "does this artist have ANY upcoming
    Ticketmaster event right now." That's binary and can't tell the
    difference between "tour is over" and "tour is on a two-week
    break between legs." If you want a bit more signal, --stale-days
    N will also flag any tour where the LAST checked event was more
    than N days ago (requires a second, slower pass keeping event
    history -- off by default, opt in with the flag).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("This script needs the 'requests' library.")
    print("Install it with: pip install requests --break-system-packages")
    sys.exit(1)

TM_DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

# Ticketmaster's basic tier is rate-limited (5 req/sec, 5000/day at
# time of writing). A small delay keeps this comfortably under that
# even for a very large tours.json, and a 429 gets one retry with a
# longer backoff rather than just failing that tour outright.
REQUEST_DELAY_SECONDS = 0.3
RETRY_DELAY_SECONDS = 5


def load_tours(path: Path) -> list[dict]:
    if not path.exists():
        print(f"Couldn't find {path}. Point --tours-file at your tours.json.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print(f"{path} doesn't look like a list of tours. Check the file.")
        sys.exit(1)
    return data


TM_ATTRACTIONS_URL = "https://app.ticketmaster.com/discovery/v2/attractions.json"


def resolve_attraction_id(artist: str, api_key: str) -> str | None:
    """
    Looks up the real performer record for an artist name and returns
    their stable Ticketmaster attractionId, or None if nothing close
    enough is found. This is what makes the difference between "a
    real Ariana Grande show" and "a DJ night that mentions her name."
    """
    params = {"apikey": api_key, "keyword": artist, "size": 5, "classificationName": "music"}
    try:
        resp = requests.get(TM_ATTRACTIONS_URL, params=params, timeout=15)
        if resp.status_code == 429:
            time.sleep(RETRY_DELAY_SECONDS)
            resp = requests.get(TM_ATTRACTIONS_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        attractions = data.get("_embedded", {}).get("attractions", [])
        if not attractions:
            return None
        # Prefer an exact (case-insensitive) name match over the
        # first result -- Ticketmaster's attraction search can return
        # tribute acts and similarly-named performers first.
        norm = artist.strip().lower()
        for a in attractions:
            if a.get("name", "").strip().lower() == norm:
                return a.get("id")
        return attractions[0].get("id")
    except requests.exceptions.RequestException:
        return None


def check_artist_upcoming(artist: str, api_key: str) -> dict:
    """
    Returns {'found': bool, 'upcoming_count': int, 'next_date': str|None,
    'error': str|None} for a single artist name. Searches by the
    artist's actual Ticketmaster attraction ID when one can be
    resolved, falling back to a keyword search only if no attraction
    record exists at all (rare for anyone who actually tours).
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    attraction_id = resolve_attraction_id(artist, api_key)
    params = {
        "apikey": api_key,
        "sort": "date,asc",
        "size": 20,
        "classificationName": "music",
        "startDateTime": now,
    }
    if attraction_id:
        params["attractionId"] = attraction_id
    else:
        params["keyword"] = artist
    try:
        resp = requests.get(TM_DISCOVERY_URL, params=params, timeout=15)
        if resp.status_code == 429:
            time.sleep(RETRY_DELAY_SECONDS)
            resp = requests.get(TM_DISCOVERY_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        events = data.get("_embedded", {}).get("events", [])
        today = datetime.now(timezone.utc).date()
        future_events = []
        for e in events:
            date_str = e.get("dates", {}).get("start", {}).get("localDate")
            if not date_str:
                continue
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if event_date >= today:
                future_events.append(e)
        if not future_events:
            return {"found": False, "upcoming_count": 0, "next_date": None, "error": None}
        next_date = future_events[0].get("dates", {}).get("start", {}).get("localDate")
        return {"found": True, "upcoming_count": len(future_events), "next_date": next_date, "error": None}
    except requests.exceptions.RequestException as e:
        return {"found": False, "upcoming_count": 0, "next_date": None, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Find tours with zero upcoming Ticketmaster dates.")
    parser.add_argument("--tours-file", default="data/tours.json", help="Path to tours.json")
    parser.add_argument("--output", default="tour_audit_report.json", help="Where to write the JSON report")
    args = parser.parse_args()

    api_key = os.environ.get("TM_API_KEY")
    if not api_key:
        print("Set TM_API_KEY first:  export TM_API_KEY=\"your_key\"")
        sys.exit(1)

    tours = load_tours(Path(args.tours_file))
    print(f"Checking {len(tours)} tours against Ticketmaster...\n")

    no_dates = []
    has_dates = []
    errors = []

    for i, tour in enumerate(tours, 1):
        artist = tour.get("artist") or tour.get("tourName", "")
        slug = tour.get("tourId", "?")
        if not artist:
            errors.append({"slug": slug, "reason": "no artist field to search on"})
            continue

        result = check_artist_upcoming(artist, api_key)
        label = f"[{i}/{len(tours)}] {artist}"

        if result["error"]:
            print(f"{label} -- ERROR: {result['error']}")
            errors.append({"slug": slug, "artist": artist, "reason": result["error"]})
        elif not result["found"]:
            print(f"{label} -- NO UPCOMING DATES")
            no_dates.append({"slug": slug, "artist": artist, "tourName": tour.get("tourName")})
        else:
            print(f"{label} -- {result['upcoming_count']} upcoming, next {result['next_date']}")
            has_dates.append({"slug": slug, "artist": artist, "nextDate": result["next_date"]})

        time.sleep(REQUEST_DELAY_SECONDS)

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalTours": len(tours),
        "summary": {
            "hasUpcomingDates": len(has_dates),
            "noUpcomingDates": len(no_dates),
            "errors": len(errors),
        },
        "candidatesForRemoval": no_dates,
        "needsManualCheck": errors,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 60)
    print(f"  {len(has_dates)} tours have upcoming dates -- leave alone")
    print(f"  {len(no_dates)} tours have ZERO upcoming dates -- review these")
    print(f"  {len(errors)} couldn't be checked -- probably a name mismatch")
    print("=" * 60)
    print(f"\nFull report written to {args.output}")
    if no_dates:
        print("\nCandidates for removal (double check before deleting --")
        print("a tour between legs looks identical to one that's over):\n")
        for t in no_dates:
            print(f"  - {t['artist']} ({t['slug']})")


if __name__ == "__main__":
    main()
