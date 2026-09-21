"""Generate today's waiver-wire debate and write docs/data/latest.json.

Usage:  python pipeline/run_daily.py [--mock]
  --mock  no API calls: canned stats + canned dialogue (for UI/dev work)
"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm, stats, ownership

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config" / "agents.json").read_text())
MOCK = "--mock" in sys.argv

def pick_candidates():
    w = CFG["waiver"]
    info = {"available": False, "season": None, "max_owned_pct": w["max_owned_pct"], "unmatched": [], "error": None}
    if MOCK:
        pool, own = stats.mock_candidates(), ownership.mock_ownership(); info["season"] = "mock"
    else:
        pool = stats.fetch_candidates(w["days"], w["min_games"], w["min_mpg"])
        try:
            own, info["season"] = ownership.fetch_ownership(w["espn_season"])
        except Exception as e:
            info["error"] = str(e); own = None
    if own is None:  # graceful fallback: production only, no ownership filter
        return pool[: w["top_n"]], info
    matched, info["unmatched"] = ownership.attach(pool, own)
    info["available"] = True
    return [p for p in matched if p["owned_pct"] < w["max_owned_pct"]][: w["top_n"]], info

def system_prompt(agent, players, others, own_info):
    return (f"You are {agent['name']}, one of three fantasy basketball analysts on a daily show, debating the best "
            f"waiver-wire pickups. Personality: {agent['persona']} Co-hosts: {', '.join(others)}. "
            f"Speak in first person, at most {CFG['max_words_per_turn']} words per turn, no stage directions, no markdown. "
            f"Only discuss players from this list (recent per-game averages):\n" + json.dumps(players) +
            (f"\nEvery player is owned in under {own_info['max_owned_pct']}% of ESPN leagues (owned_pct = % rostered), so they are realistic waiver adds."
             if own_info["available"] else "\nOwnership data is unavailable today, so do not claim anything about how widely rostered these players are.") +
            "\nReact to what the others just said. Never invent stats that are not in the list.")

def run():
    players, own_info = pick_candidates()
    if not players:
        raise SystemExit("No waiver candidates found; not overwriting existing data.")
    agents = CFG["agents"]
    spent = {a["id"]: 0.0 for a in agents}
    usage = {a["id"]: {"in": 0, "out": 0} for a in agents}
    lines = []
    for rnd in range(CFG["rounds"]):
        for a in agents:
            if spent[a["id"]] >= CFG["daily_cap_usd_per_agent"]:
                continue
            others = [x["name"] for x in agents if x["id"] != a["id"]]
            history = "\n".join(f'{l["name"]}: {l["text"]}' for l in lines) or "(you speak first - open the show)"
            prompt = "Conversation so far:\n" + history + f"\n\nYour turn, {a['name']}."
            if MOCK:
                text, ti, to = f"[mock line {rnd + 1}] Talking about {players[rnd % len(players)]['name']}.", 0, 0
            else:
                text, ti, to = llm.call(a["provider"], a["model"], system_prompt(a, players, others, own_info), prompt, 120)
            spent[a["id"]] += (ti * a["price_in"] + to * a["price_out"]) / 1e6
            usage[a["id"]]["in"] += ti; usage[a["id"]]["out"] += to
            lines.append({"agent": a["id"], "name": a["name"], "text": text})
    now = datetime.now(timezone.utc)
    out = {
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(timespec="seconds"),
        "agents": [{"id": a["id"], "name": a["name"], "provider": a["provider"], "model": a["model"]} for a in agents],
        "candidates": players,
        "ownership": {"source": "ESPN", "available": own_info["available"], "season": own_info["season"], "max_owned_pct": own_info["max_owned_pct"], "unmatched": own_info["unmatched"], "error": own_info["error"]},
        "lines": lines,
        "cost_usd": {k: round(v, 5) for k, v in spent.items()},
        "usage": usage,
        "mock": MOCK,
    }
    data = ROOT / "docs" / "data"
    (data / "archive").mkdir(parents=True, exist_ok=True)
    (data / "latest.json").write_text(json.dumps(out, indent=2))
    (data / "archive" / f"{out['date']}.json").write_text(json.dumps(out, indent=2))
    print("wrote", out["date"], "lines:", len(lines), "cost:", out["cost_usd"])

if __name__ == "__main__":
    run()
