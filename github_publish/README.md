# Amsterdam Startup Job Copilot

An automated pipeline that scans Amsterdam startup career pages, classifies each open role against a specific career-transition goal, and writes qualifying roles to a tracking database. Built and iterated on as a personal tool for a real, ongoing job search.

## Why this exists

Manually checking hundreds of company career pages for relevant roles doesn't scale, and generic job boards don't capture role fit. A "Strategy Manager" title can mean founder-facing commercial work or internal OKR administration. This project automates discovery and adds a judgment layer a keyword filter can't.

## A real result

In a scheduled run on 2026-10-16 the copilot surfaced **Minimal AI's Founder's Associate (Amsterdam, YC-backed)** and rated it **Apply**: direct founder exposure, commercial and strategic ownership. In the same run it read the full JD of eight other "strategy / associate / partnerships" roles and skipped all of them: quota-carrying BD, a BDR under a softer title, customer implementation. A title filter would have surfaced most of those.

See [`sample_run_report_2026-10-16.md`](sample_run_report_2026-10-16.md) for the full (lightly anonymised) report.

## What it does

1. **Discovers career pages** for ~600 tracked Amsterdam startups, across Ashby, Greenhouse, Lever, Recruitee, Workable, Personio/Hibob/Homerun and custom sites. Found URLs are cached in `master_companies.csv` (currently ~290 live, the rest empty or marked `NOT_FOUND:<date>` and re-checked after 60 days).
2. **Extracts live job postings** via ATS JSON APIs where available, falling back to browser navigation and DOM scraping for custom pages.
3. **Classifies every role** into Apply / Maybe / Skip against a single question: *does this role materially build the founder exposure, commercial judgment, and strategic ownership I'm looking for?*
4. **Writes qualifying roles to Notion** (with dedup checks) and produces a per-run coverage report.

## The classification logic

The core contribution isn't the scraping. It's the judgment layer, refined against real misclassifications.

- **Positive signals:** founder exposure, fundraising exposure, market/industry analysis, strategic or commercial judgment, ambiguous high-ownership work tied to company strategy.
- **Default negatives:** internal operations, OKR/PMO, GTM execution, marketing, RevOps, finance-specialist work, account management, support, pure engineering.
- **The rule that mattered most:** a title containing "Strategy" or "Generalist" is not enough. Read the JD; if the work is mostly internal-ops execution it defaults to *Maybe*, not *Apply*. Company stage is only a tie-breaker, never an override.

## Lessons learned (what broke, and the fix)

**1. The first version, a Python script, never worked.** Post-mortem: across 353 "processed" companies it resolved **zero** career pages. Three causes: DuckDuckGo's HTML endpoint blocks scripted queries; it ignored the career URLs already stored in the CSV; and `requests` + BeautifulSoup can't see jobs on JS-rendered pages (Ashby, Recruitee, custom React sites), failing silently with "0 jobs". The fix was to move to an agent-driven workflow that calls ATS JSON APIs and renders pages in a real browser.

**2. Two tools editing the same files drift apart.** The pipeline runs in both Claude Code and Claude Cowork. Over time the installed skill, the project copy and per-session uploads diverged. One session had silently overwritten another's edits, and a previously valid career URL was overwritten with `NOT_FOUND`. Fixes:
- **Single source of truth:** the installed skill is now a tiny pointer ([`skill_stub/`](skill_stub/SKILL.md)) that tells the agent to read the project's `SKILL.md`.
- **[`csv_guard.py`](csv_guard.py):** snapshot the CSV before a run, diff after. It flags any resolved URL replaced by `NOT_FOUND` and any removed row, and lists every changed row for review.
- **Git history** for `SKILL.md` and the CSV, so any session can see what changed.

**3. A 200 response is not proof.** Single-page sites return 200 for any path, and generic names collide with unrelated companies. A career URL is now only written after an *identity check* (company name on the page plus a Netherlands signal).

**4. URL guessing has sharp edges.** Names that look like domains (`Effect.AI` → `effect.ai`), names whose last word is the TLD (`Yasu Cloud` → `yasu.cloud`), uncommon TLDs (`.sh`), and duplicate rows for one company under two names all caused false `NOT_FOUND`s. Each is now a rule in `SKILL.md` Step 3b.

## Architecture notes

- **No blind sampling:** every run re-checks every company with a known career URL.
- **Progressive caching:** career URLs found once are saved to the master CSV.
- **Verify before classifying:** listing-page titles are checked against the real posting.
- **Honest reporting:** run reports state only numbers actually tallied, and list pages that failed to load as "not confirmed", never as covered.

## Repo layout

| File | Purpose |
|---|---|
| `SKILL.md` | The full agent instructions (steps 0-8, rubric, report template). Paths and IDs are placeholders. |
| `skill_stub/SKILL.md` | The pointer skill to install, so there is only one copy of the real instructions |
| `master_companies.csv` | Tracked companies and their cached career URLs |
| `csv_guard.py` | Snapshot/diff guard for the CSV |
| `CLAUDE.md` | Working agreements for Claude Code / Cowork |
| `sources_config.md` | Where the company list comes from |
| `sample_run_report_2026-10-16.md` | Example run report |

## Status

Actively running as part of a live job search. The rubric and the URL-discovery rules keep getting corrected as new edge cases appear.
