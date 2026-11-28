"""Download World Bank indicators used for the opportunity scores.

Writes data/wb.json:
  {"u": updated ISO time, "src": {...}, "c": {ISO2: {key: [value, year]}}}
Each value is the most recent non-empty observation (World Bank API mrnev=1).
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IND = {
    "gni": "NY.GNP.PCAP.PP.CD",   # GNI per capita, PPP (current international $)
    "gdp": "NY.GDP.MKTP.CD",      # GDP (current US$)
    "un": "SL.UEM.TOTL.ZS",       # Unemployment, total (% of labor force, modeled ILO estimate)
    "un_y": "SL.UEM.1524.ZS",     # Youth unemployment, ages 15-24 (modeled ILO estimate)
}


def get(code):
    url = (f"https://api.worldbank.org/v2/country/all/indicator/{code}"
           "?format=json&mrnev=1&per_page=500")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                meta, rows = json.load(r)
            return rows or []
        except Exception as e:
            err = e
            time.sleep(5 + attempt * 10)
    raise err


def main():
    out = {}
    for key, code in IND.items():
        rows = get(code)
        n = 0
        for row in rows:
            iso2 = (row.get("country") or {}).get("id")
            if not iso2 or row.get("value") is None or len(iso2) != 2:
                continue
            out.setdefault(iso2, {})[key] = [round(row["value"], 2), int(row["date"])]
            n += 1
        print(key, code, n)
    if len(out) < 150:
        sys.exit("too few countries, keeping the old file")
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "wb.json"), "w", encoding="utf-8") as f:
        json.dump({"u": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                   "src": IND, "c": out}, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


if __name__ == "__main__":
    main()
