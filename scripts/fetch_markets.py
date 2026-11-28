"""Collect the latest level of each country's main stock index.

Reads scripts/markets.json ([country code, Yahoo symbol, Korean name]) and writes
markets.json at the site root:
  {"u": updated ISO time, "q": [{"c", "n", "y", "p", "ch", "t"}]}
y is the Yahoo Finance symbol, used to link to the index page.
p is the latest price, ch the change in percent against the previous session,
t the time of the latest price. Indexes that fail are left out; if every index
fails, the previous markets.json is kept.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def chart(sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym)
           + "?range=5d&interval=1d")
    err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as r:
                return json.load(r)["chart"]["result"][0]
        except Exception as e:
            err = e
            time.sleep(2 + attempt * 3)
    raise err


def quote_yf(sym):
    """Use the yfinance library when it is installed; it handles Yahoo's cookies."""
    import yfinance as yf
    h = yf.Ticker(sym).history(period="7d", interval="1d", auto_adjust=False)
    closes = [float(x) for x in h["Close"].dropna().tolist()]
    if len(closes) < 2:
        raise ValueError("no price data")
    price, prev = closes[-1], closes[-2]
    t = h["Close"].dropna().index[-1].to_pydatetime().astimezone(timezone.utc)
    return {"p": round(price, 2), "ch": round((price - prev) / prev * 100, 2),
            "t": t.isoformat(timespec="minutes")}


def quote(sym):
    try:
        return quote_yf(sym)
    except ImportError:
        pass
    res = chart(sym)
    meta = res.get("meta", {})
    closes = [x for x in (res.get("indicators", {}).get("quote", [{}])[0].get("close") or []) if x is not None]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    if price is None or len(closes) < 2:
        raise ValueError("no price data")
    prev = closes[-2]
    t = meta.get("regularMarketTime")
    return {
        "p": round(price, 2),
        "ch": round((price - prev) / prev * 100, 2) if prev else 0,
        "t": datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="minutes") if t else "",
    }


def main():
    rows, fails = [], []
    for code, sym, name in json.load(open(os.path.join(ROOT, "scripts", "markets.json"), encoding="utf-8")):
        try:
            rows.append({"c": code, "n": name, "y": sym, **quote(sym)})
        except Exception as e:
            fails.append(f"{sym}: {e}")
        time.sleep(0.4)
    for f in fails:
        print("failed", f, file=sys.stderr)
    print(f"updated {len(rows)}, failed {len(fails)}")
    if not rows:
        sys.exit(1)
    out = {"u": datetime.now(timezone.utc).isoformat(timespec="minutes"), "q": rows}
    with open(os.path.join(ROOT, "markets.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
