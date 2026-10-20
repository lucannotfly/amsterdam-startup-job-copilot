# Amsterdam Startup Job Copilot

The active pipeline is the `amsterdam-startup-jobs` skill (see [SKILL.md](SKILL.md)), run via Claude + Chrome browser tools. It reads/writes `career_url` in `master_companies.csv` and writes Apply/Maybe roles to Notion directly.

A retired standalone Python script (requests + BeautifulSoup + DuckDuckGo) is not included; why it failed is written up in the README under "Lessons learned".

## Working across Claude Code and Cowork

- **Source of truth:** this folder's [SKILL.md](SKILL.md). The installed `amsterdam-startup-jobs` skill is a copy; after editing SKILL.md, re-sync the installed copy by hand. Read SKILL.md fresh before editing it, since another session may have changed it.
- **History:** this folder is a git repo. Commit after meaningful changes to SKILL.md or master_companies.csv so any session can see what changed.
- **CSV guard:** `python3 csv_guard.py snapshot` before a scan, `python3 csv_guard.py diff` after. It flags resolved URLs replaced by NOT_FOUND and removed rows. Snapshots live in `snapshots/` (not in git).
- **Never write a career_url without an identity check** (company name on the page + NL signal); see SKILL.md Step 3b.
