# RKSV Volkel – Familie voetbalagenda

Automatische iCalendar-feeds voor twee teams:

- `jo12.ics`: RKSV Volkel JO12-1 (thuis: agenda start 45 minuten vóór aftrap, uit: 60 minuten vooraf)
- `jo13.ics`: RKSV Volkel JO13-1 (thuis: agenda start 60 minuten vóór aftrap, uit: 75 minuten vooraf)

Bronnen (officiële RKSV Volkel iCalendar-feeds):
- JO12: `https://www.rksv-volkel.nl/Modules/UitslagenEnStanden/Front/ICal.ashx?id=73`
- JO13: `https://www.rksv-volkel.nl/Modules/UitslagenEnStanden/Front/ICal.ashx?id=229`

De GitHub Actions-workflow haalt beide programma's dagelijks op en bewaart de bestaande agenda als een bestand wanneer een bron niet geldig is. De oude `volkel.ics`-URL blijft bestaan als kopie van JO12.

## Instellingen aanpassen

Pas bovenaan `update_calendar.py` de waarden `home_minutes` en `away_minutes` aan voor het gewenste team. De workflow publiceert de bijgewerkte feeds via GitHub Pages.

## Google Agenda

Voeg beide ICS-links afzonderlijk toe via **Andere agenda's → Via URL**. Geef de JO12-agenda blauw en JO13 groen. Deel beide agenda's met gezinsleden. De kleur wordt in Google Agenda ingesteld, niet in het ICS-bestand.
