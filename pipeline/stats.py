"""Fetch recent player performance from balldontlie and rank waiver candidates.

NOTE: balldontlie has no fantasy ownership data, so "waiver candidate" here means
"strong recent production" - we can't filter by % rostered without Yahoo/ESPN data.
The endpoint usage below is untested against the live API; run with a real key once
and adjust field names if needed. Use --mock for offline development.
"""
import json, os, time, urllib.request, urllib.parse
from collections import defaultdict
from datetime import date, timedelta

BASE = "https://api.balldontlie.io/v1"

def _get(path, params):
    url = BASE + path + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"Authorization": os.environ["BALLDONTLIE_API_KEY"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def _minutes(m):
    try:
        return int(str(m).split(":")[0])
    except Exception:
        return 0

def fetch_candidates(days=10, min_games=3, min_mpg=20, top_n=12):
    end = date.today()
    start = end - timedelta(days=days)
    rows, cursor = [], None
    while True:
        p = {"start_dates[]": start.isoformat(), "end_dates[]": end.isoformat(), "per_page": 100}
        if cursor:
            p["cursor"] = cursor
        d = _get("/stats", p)
        rows += d["data"]
        cursor = d.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(1.1)  # stay under 60 req/min
    agg = defaultdict(lambda: defaultdict(float))
    names = {}
    for r in rows:
        mins = _minutes(r.get("min"))
        if mins == 0:
            continue
        pid = r["player"]["id"]
        names[pid] = f'{r["player"]["first_name"]} {r["player"]["last_name"]}'
        a = agg[pid]
        a["gp"] += 1; a["min"] += mins
        for k in ("pts", "reb", "ast", "stl", "blk", "turnover", "fg3m"):
            a[k] += r.get(k) or 0
    out = []
    for pid, a in agg.items():
        gp = a["gp"]
        if gp < min_games or a["min"] / gp < min_mpg:
            continue
        per = {k: round(a[k] / gp, 1) for k in ("min", "pts", "reb", "ast", "stl", "blk", "turnover", "fg3m")}
        score = per["pts"] + 1.2 * per["reb"] + 1.5 * per["ast"] + 3 * per["stl"] + 3 * per["blk"] - per["turnover"]
        out.append({"name": names[pid], "gp": int(gp), **per, "score": round(score, 1)})
    out.sort(key=lambda x: -x["score"])
    return out[:top_n]

def mock_candidates():
    return [
        {"name": "Sample Guard", "gp": 6, "min": 31.2, "pts": 19.5, "reb": 4.1, "ast": 7.3, "stl": 1.6, "blk": 0.3, "turnover": 2.4, "fg3m": 2.8, "score": 38.3},
        {"name": "Sample Big", "gp": 5, "min": 27.8, "pts": 12.0, "reb": 10.2, "ast": 2.1, "stl": 0.8, "blk": 2.2, "turnover": 1.5, "fg3m": 0.2, "score": 34.6},
        {"name": "Sample Wing", "gp": 7, "min": 29.5, "pts": 16.8, "reb": 5.5, "ast": 3.0, "stl": 1.4, "blk": 0.6, "turnover": 1.8, "fg3m": 2.5, "score": 31.9},
    ]
