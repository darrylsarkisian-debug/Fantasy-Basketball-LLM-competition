"""ESPN fantasy ownership (% rostered). Unofficial, no-login endpoint - may change without notice.

Verified shape (season 2026 responded): {"players":[{"id":..,"fullName":"..","ownership":{"percentOwned":41.47}}]}
percentOwned is already a percentage (41.47 = 41.47%), not a 0-1 fraction.
ESPN's basketball season id is the year the season ENDS (2026-27 season -> 2027).
"""
import json, re, unicodedata, urllib.request
from datetime import date
from pathlib import Path

URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/players?scoringPeriodId=0&view=players_wl"
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

def normalize(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    return " ".join(w for w in s.split() if w not in SUFFIXES)

def default_season(today=None):
    t = today or date.today()
    return t.year + 1 if t.month >= 8 else t.year

def _load(season):
    req = urllib.request.Request(URL.format(season=season), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def fetch_ownership(season=None):
    """Returns {normalized_name: pct_owned}. Tries the current season, then the previous one."""
    season = season or default_season()
    last_err = None
    for s in (season, season - 1):
        try:
            data = _load(s)
            players = data if isinstance(data, list) else data.get("players", [])
            out = {}
            for p in players:
                pct = (p.get("ownership") or {}).get("percentOwned")
                name = p.get("fullName")
                if name and pct is not None:
                    out[normalize(name)] = float(pct)
            if out:
                return out, s
        except Exception as e:  # network, JSON, etc.
            last_err = e
    raise RuntimeError(f"ESPN ownership unavailable: {last_err}")

def load_aliases():
    p = Path(__file__).resolve().parent.parent / "config" / "name_aliases.json"
    return json.loads(p.read_text()) if p.exists() else {}

def attach(players, ownership):
    """Adds owned_pct to each player. Returns (matched, unmatched_names)."""
    aliases = {normalize(k): normalize(v) for k, v in load_aliases().items()}
    matched, unmatched = [], []
    for p in players:
        key = normalize(p["name"])
        key = aliases.get(key, key)
        if key in ownership:
            matched.append({**p, "owned_pct": round(ownership[key], 1)})
        else:
            unmatched.append(p["name"])
    return matched, unmatched

def mock_ownership():
    return {normalize("Sample Guard"): 12.0, normalize("Sample Big"): 31.5, normalize("Sample Wing"): 4.2}
