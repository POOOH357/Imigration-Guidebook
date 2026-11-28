"""Collect recent Korean-language headlines per country from Google News RSS.

Writes news/<CODE>.json for each country in scripts/countries.json:
  {"u": updated ISO time, "a": [main headlines], "m": [immigration headlines]}
Each headline is {"t": title, "s": source, "d": ISO date, "l": link}.
If a fetch fails, the previous file for that country is kept as is.
"""
import json, os, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "news")
N = 6
IMM = "(이민 OR 비자 OR 영주권 OR 취업)"
UA = "Mozilla/5.0 (compatible; immigration-guidebook-news/1.0)"


def rss(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return ET.fromstring(r.read())
        except Exception as e:  # network or parse error: retry, then give up
            err = e
            time.sleep(2 + attempt * 3)
    raise err


def items(query):
    root = rss(query)
    out, seen = [], set()
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src = (it.findtext("source") or "").strip()
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3].strip()
        try:
            d = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc).isoformat()
        except Exception:
            d = ""
        key = title[:40]
        if not title or not link.startswith("https://") or key in seen:
            continue
        seen.add(key)
        out.append({"t": title, "s": src, "d": d, "l": link})
    out.sort(key=lambda x: x["d"], reverse=True)
    return out[:N]


def main():
    os.makedirs(OUT, exist_ok=True)
    countries = json.load(open(os.path.join(ROOT, "scripts", "countries.json"), encoding="utf-8"))
    only = set(sys.argv[1:])
    ok = fail = 0
    for code, q, _en in countries:
        if only and code not in only:
            continue
        try:
            a = items(q + " when:14d") or items(q)
            time.sleep(0.6)
            m = items(f"{q} {IMM} when:180d") or items(f"{q} {IMM}")
            time.sleep(0.6)
        except Exception as e:
            fail += 1
            print(f"{code}: failed ({e})", file=sys.stderr)
            continue
        data = {"u": datetime.now(timezone.utc).isoformat(timespec="minutes"), "a": a, "m": m}
        with open(os.path.join(OUT, f"{code}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        ok += 1
    print(f"updated {ok}, failed {fail}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
