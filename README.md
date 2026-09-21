# Fantasy Basketball LLM Competition

Three LLM agents (Claude, ChatGPT, Gemini), each with a distinct personality, debate the best
waiver-wire pickups every day at 3pm PT during the NBA season. Static site + scheduled pipeline.

## Layout
- `config/agents.json` - personas, models, prices, per-agent daily cap ($0.03)
- `pipeline/` - stdlib-only Python: `stats.py` (balldontlie), `llm.py` (provider clients), `run_daily.py`
- `docs/` - the site (GitHub Pages: Settings > Pages > Deploy from branch `main`, folder `/docs`)
- `docs/data/latest.json` - today's debate, played back client-side over ~3 minutes
- `.github/workflows/daily.yml` - daily generation; needs repo secrets BALLDONTLIE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY

## Dev
    python pipeline/run_daily.py --mock     # no keys needed
    python -m http.server -d docs           # then open localhost:8000

## Known gaps / to verify
- Model IDs and prices in agents.json are placeholders.
- balldontlie calls are untested against the live API.
- Ownership comes from ESPN's unofficial no-login endpoint (`pipeline/ownership.py`); candidates are players under `waiver.max_owned_pct` (25%) in `config/agents.json`. If ESPN fails, the pipeline falls back to production-only and the site says so. Players ESPN can't name-match are listed in `latest.json` under `ownership.unmatched`; fix them in `config/name_aliases.json`.
- Yahoo API access needs an approved application; not used for now.
- Module 4 is a placeholder (Waiver Board table).
