#!/usr/bin/env python3
"""Build separate, automatically refreshed RKSV Volkel team calendars."""
from datetime import datetime
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

def make_alarm(minutes):
    return [
        "BEGIN:VALARM",
        f"TRIGGER:-PT{minutes}M",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Aanwezig zijn over {minutes} minuten",
        "END:VALARM",
    ]

def process_event(lines, config):
    summary_line = next((line for line in lines if line.startswith("SUMMARY")), "")
    summary = unescape_ical(summary_line.split(":", 1)[-1]) if ":" in summary_line else ""
    # RKSV Volkel may be written with or without the club prefix.
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

    # Remove any source alarm so the configured team-specific reminder is authoritative.
    cleaned = []
    in_alarm = False
    for line in lines:
        if line == "BEGIN:VALARM":
            in_alarm = True
        elif line == "END:VALARM":
            in_alarm = False
        elif not in_alarm:
            cleaned.append(line)
    end_index = cleaned.index("END:VEVENT")
    cleaned[end_index:end_index] = make_alarm(minutes)
    return cleaned

def build_calendar(key, config):
    request = Request(config["source"], headers={"User-Agent": "VolkelFamilieAgenda/2.0"})
    with urlopen(request, timeout=45) as response:
        raw = response.read().decode("utf-8-sig")
    lines = unfold_ical(raw)
    if "BEGIN:VCALENDAR" not in lines or "END:VCALENDAR" not in lines:
        raise RuntimeError(f"{key}: de bron leverde geen geldige iCalendar-feed.")

    output = []
    event = None
    event_count = 0
    for line in lines:
        if line == "BEGIN:VEVENT":
            event = [line]
        elif event is not None:
            event.append(line)
            if line == "END:VEVENT":
                output.extend(process_event(event, config))
                event_count += 1
                event = None
        elif not line.startswith("X-WR-CALNAME:"):
            output.append(line)

    if event is not None:
        raise RuntimeError(f"{key}: onvolledig wedstrijdonderdeel in de feed.")
    if event_count == 0:
        raise RuntimeError(f"{key}: er zijn geen wedstrijden gevonden; bestaand bestand blijft behouden.")

    output.insert(output.index("BEGIN:VCALENDAR") + 1, f"X-WR-CALNAME:{config['name']}")
    text = "\r\n".join(output) + "\r\n"
    Path(f"{key}.ics").write_text(text, encoding="utf-8")
    print(f"{key}.ics bijgewerkt: {event_count} wedstrijden.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduled":
        if datetime.now(ZoneInfo("Europe/Amsterdam")).hour != 6:
            print("Niet 06:00 in Nederland; geplande run overgeslagen.")
            return
    for key, config in TEAMS.items():
        build_calendar(key, config)
    # Keep the old URL working as a JO12 compatibility link.
    Path("volkel.ics").write_text(Path("jo12.ics").read_text(encoding="utf-8"), encoding="utf-8")
    print("Ook de oude volkel.ics-link is bijgewerkt als JO12-kopie.")

if __name__ == "__main__":
    main()
