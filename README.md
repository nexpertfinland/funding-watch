# funding_watch

A minimal Python tool that collects funding opportunities from a list of URLs and saves them into a CSV file.

## Files
- `funding_watch.py` - main script
- `sources.txt` - list of source URLs (one per line)
- `requirements.txt` - required Python packages
- `funding_watch.csv` - output file created when script runs

## How it works
1. Reads URLs from `sources.txt`
2. Tries RSS/Atom parsing first
3. If RSS is not available, falls back to basic HTML parsing (page title + first link)
4. Detects if each funding item is `open`, `unknown`, or `closed`
5. Excludes `closed` items and saves only `open` + `unknown` rows
6. Writes results to `funding_watch.csv`

## Open/closed detection rules
- Exclude if text contains clear closed signals (Finnish + English), for example:
  - `haku päättynyt`, `haku on päättynyt`, `ei haettavissa`, `hakuaika päättyi`, `suljettu`
  - `closed`, `application period ended`, `no longer accepting applications`, `deadline passed`
- Exclude if an explicit closing date is found and it is before today
- Keep the item if no date/status can be detected

## Supported date formats
- `14.2.2026`
- `14.02.2026`
- `2026-02-14`

## Run step by step
1. (Optional) Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the script:
   ```bash
   python funding_watch.py
   ```
4. Open `funding_watch.csv`.

## Output columns
- `source_url`
- `title`
- `link`
- `date`
- `status` (`open` or `unknown` in output)
