"""Generate today's waiver-wire debate and write docs/data/latest.json.

Usage:  python pipeline/run_daily.py [--mock]
  --mock  no API calls: canned stats + canned dialogue (for UI/dev work)
"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm, stats

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config" / "agents.json").read_text())
MOCK = "--mock" in sys.argv

def system_prompt(agent, players, others):
    return (f"You are {agent['name']}, one of three fantasy basketball analysts on a daily show, debating the best "
            f"waiver-wire pickups. Personality: {agent['persona']} Co-hosts: {', '.join(others)}. "
            f"Speak in first person, at most {CFG['max_words_per_turn']} words per turn, no stage directions, no markdown. "
            f"Only discuss players from this list (recent per-game averages):\n" + json.dumps(players) +
            "\nReact to what the others just said. Never invent stats that are not in the list.")

def run():
    players = stats.mock_candidates() if MOCK else stats.fetch_candidates()
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
                text, ti, to = llm.call(a["provider"], a["model"], system_prompt(a, players, others), prompt, 120)
            spent[a["id"]] += (ti * a["price_in"] + to * a["price_out"]) / 1e6
            usage[a["id"]]["in"] += ti; usage[a["id"]]["out"] += to
            lines.append({"agent": a["id"], "name": a["name"], "text": text})
    now = datetime.now(timezone.utc)
    out = {
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(timespec="seconds"),
        "agents": [{"id": a["id"], "name": a["name"], "provider": a["provider"], "model": a["model"]} for a in agents],
        "candidates": players,
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
