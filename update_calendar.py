#!/usr/bin/env python3
"""Download the RKSV Volkel iCalendar feed and add attendance reminders."""
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from pathlib import Path
import re
import sys

SOURCE = "http://www.rksv-volkel.nl/Modules/UitslagenEnStanden/Front/ICal.ashx?id=73"
OUTPUT = Path("volkel.ics")
TEAM = "volkel"

def unescape_ical(value):
    return value.replace(r"\\n", " ").replace(r"\\,", ",").replace(r"\\;", ";").replace(r"\\:", ":")

def attendance_minutes(summary):
    # Match names are conventionally written as "Home team - Away team".
    parts = re.split(r"\s+(?:tegen|-)\s+", summary, maxsplit=1)
    if len(parts) != 2:
        return None
    home, away = (unescape_ical(x).lower() for x in parts)
    if TEAM in home or "rksv volkel" in home:
        return 45
    if TEAM in away or "rksv volkel" in away:
        return 60
    return None

def main():
    # GitHub Actions invokes this at both possible UTC equivalents of 06:00.
    # This guard makes exactly one run effective in either CET or CEST.
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduled":
        if datetime.now(ZoneInfo("Europe/Amsterdam")).hour != 6:
            print("Not 06:00 Europe/Amsterdam; skipping.")
            return

    req = Request(SOURCE, headers={"User-Agent": "VolkelAgendaBot/1.0"})
    with urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8-sig")

    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Unfold RFC 5545 continuation lines before parsing.
    unfolded = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    result = []
    in_event = False
    summary = ""
    alarm_added = False
    for line in unfolded:
        if line == "BEGIN:VEVENT":
            in_event, summary, alarm_added = True, "", False
        elif in_event and line.startswith("SUMMARY"):
            summary = line.split(":", 1)[-1]
        if in_event and line == "END:VEVENT":
            minutes = attendance_minutes(summary)
            if minutes is not None:
                result.extend([
                    "BEGIN:VALARM",
                    f"TRIGGER:-PT{minutes}M",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:Aanwezig zijn over {minutes} minuten",
                    "END:VALARM",
                ])
            in_event = False
        result.append(line)

    # Set a friendly calendar name, replacing any source calendar name.
    result = [x for x in result if not x.startswith("X-WR-CALNAME:")]
    try:
        idx = result.index("BEGIN:VCALENDAR") + 1
    except ValueError:
        raise RuntimeError("The source did not return a valid VCALENDAR.")
    result.insert(idx, "X-WR-CALNAME:Voetbal Klaas")

    text = "\r\n".join(x for x in result if x != "") + "\r\n"
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Updated {OUTPUT}; {sum(1 for x in result if x == 'BEGIN:VEVENT')} events processed.")

if __name__ == "__main__":
    main()
