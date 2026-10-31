#!/usr/bin/env python3
"""Build separate, automatically refreshed RKSV Volkel team calendars."""
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import re
import sys

TEAMS = {
    "jo12": {
        "source": "https://www.rksv-volkel.nl/Modules/UitslagenEnStanden/Front/ICal.ashx?id=73",
        "name": "RKSV Volkel JO12-1",
        "home_minutes": 45,
        "away_minutes": 60,
    },
    "jo13": {
        "source": "https://www.rksv-volkel.nl/Modules/UitslagenEnStanden/Front/ICal.ashx?id=229",
        "name": "RKSV Volkel JO13-1",
        "home_minutes": 60,
        "away_minutes": 75,
    },
}

def unfold_ical(raw):
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return [line for line in unfolded if line]

def unescape_ical(value):
    return (value.replace(r"\\n", " ").replace(r"\\,", ",")
                 .replace(r"\\;", ";").replace(r"\\:", ":"))

def set_attendance_start(lines, minutes):
    """Move the calendar event start to arrival time; retain kickoff in description."""
    index = next((i for i, line in enumerate(lines) if line.startswith("DTSTART")), None)
    if index is None:
        raise RuntimeError("Wedstrijd heeft geen DTSTART (aanvangstijd).")
    line = lines[index]
    prop, value = line.split(":", 1)
    has_seconds = len(value.rstrip("Z")) == 15
    fmt = "%Y%m%dT%H%M%S" if has_seconds else "%Y%m%dT%H%M"
    suffix = "Z" if value.endswith("Z") else ""
    kickoff = datetime.strptime(value.rstrip("Z"), fmt)
    arrival = kickoff - timedelta(minutes=minutes)
    lines[index] = f"{prop}:{arrival.strftime(fmt)}{suffix}"

    kickoff_text = kickoff.strftime("%H:%M")
    arrival_text = arrival.strftime("%H:%M")
    description = f"Aanwezig vanaf {arrival_text}. Aanvang wedstrijd: {kickoff_text}."
    desc_index = next((i for i, item in enumerate(lines) if item.startswith("DESCRIPTION")), None)
    if desc_index is None:
        lines.insert(index + 1, f"DESCRIPTION:{description}")
    else:
        old = lines[desc_index].split(":", 1)[1]
        lines[desc_index] = f"DESCRIPTION:{old}\\n{description}"
    return lines

def process_event(lines, config):
    summary_line = next((line for line in lines if line.startswith("SUMMARY")), "")
    summary = unescape_ical(summary_line.split(":", 1)[-1]) if ":" in summary_line else ""
    parts = re.split(r"\s+(?:tegen|-)\s+", summary, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        raise RuntimeError(f"Kan thuis/uit niet bepalen uit wedstrijdnaam: {summary!r}")
    home, away = (part.lower() for part in parts)
    if "volkel" in home:
        minutes = config["home_minutes"]
    elif "volkel" in away:
        minutes = config["away_minutes"]
    else:
        raise RuntimeError(f"Wedstrijd hoort niet bij Volkel: {summary!r}")
    # The event begins at the required arrival time. Kickoff remains in its description.
    return set_attendance_start(lines, minutes)

