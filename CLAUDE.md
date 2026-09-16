# Amsterdam Startup Job Copilot

The active pipeline is the `amsterdam-startup-jobs` skill (see [SKILL.md](SKILL.md)), run via Claude + Chrome browser tools. It reads/writes `career_url` in `master_companies.csv` and writes Apply/Maybe roles to Notion directly.

`archive/pipeline.py` is a retired standalone Python script (requests + BeautifulSoup + DuckDuckGo search). It never worked in practice — 0 career pages were ever resolved across 353 "processed" companies (see `archive/pipeline_state.json`), because:
- DuckDuckGo's HTML endpoint blocks scripted queries (returns a bot-check page, not results).
- It never read the `career_url` already resolved in `master_companies.csv`.
- Static `requests.get()` + BeautifulSoup can't see job listings on JS-rendered career pages (Ashby, Recruitee, custom React sites, etc.) — the skill solves this by fetching ATS JSON APIs / DOM through Chrome instead.

Kept for reference only; not part of the active workflow.
