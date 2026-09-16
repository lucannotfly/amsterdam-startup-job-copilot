## Amsterdam-startup-job-copilot

An automated pipeline that scans Amsterdam startup career pages, classifies each open role against a specific career-transition goal, and writes qualifying roles to a tracking database — built and iterated on as a personal tool for a real, ongoing job search.

## Why this exists

I built this tool to make my own startup job search more systematic. Manually checking ~400 company career pages for relevant roles doesn't scale, and generic job boards don't capture the nuances of role fit — a "Strategy Manager" title can mean anything from founder-facing commercial work to internal OKR administration. This project automates the discovery and applies a judgment layer that a keyword filter can't, to identify roles that are genuinely relevant to my career direction.

## What it does

1. **Discovers career pages** for ~400 tracked Amsterdam startups, across 6 ATS platforms (Ashby, Greenhouse, Lever, Recruitee, Workable, Personio/Hibob) plus custom company sites, with progressive URL caching so repeat runs don't re-search from scratch.
2. **Extracts live job postings** via ATS APIs where available, falling back to browser navigation and DOM scraping for non-standard career pages.
3. **Classifies every role** into Apply / Maybe / Skip against a single question: *does this role materially build the founder exposure, commercial judgment, and strategic ownership I'm looking for?* — not "is this a good startup job" in the abstract.
4. **Writes qualifying roles to Notion** (with dedup checks against existing entries) and produces a per-run coverage report.

## The classification logic (the interesting part)

The core contribution isn't the scraping — it's the judgment layer for deciding which roles are genuinely worth pursuing, and refining that judgment against real-world edge cases over multiple runs.

**Positive signals:** founder exposure, fundraising exposure, market/industry analysis, strategic or commercial judgment, ambiguous high-ownership work tied to company strategy.

**Default negative signals:** internal operations, OKR/PMO management, GTM execution, marketing, RevOps, finance-specialist work, account management, customer-facing support, pure engineering.

**The rule that mattered most in practice:** a title containing "Strategy" or "Generalist" is not enough. A role can look strategic on paper and still be mostly internal-ops execution once you read the actual job description — those default to *Maybe*, not *Apply*, until the JD proves otherwise. Company stage (Seed/Series A vs. later) acts only as a tie-breaker, never an override — a great company at a great stage doesn't rescue a role that's functionally engineering or admin, and a worse-stage company can still be an Apply if the actual work compounds founder exposure and commercial judgment.

This rubric wasn't fixed at the start — it was revised after diagnosing systematic misclassifications (e.g. strategy-titled roles that were actually PMO work) and rewritten as explicit Apply/Maybe/Skip rules with worked examples, so future runs apply the same judgment consistently rather than re-deriving it each time.

## Architecture notes

- **No blind sampling:** every run re-checks all companies with a known career URL, not a rotating batch — a role posted between runs shouldn't be missed because it fell outside a sample window.
- **Progressive caching:** career URLs, once found, are saved back to a master CSV so later runs skip re-discovery and spend their budget on new companies instead.
- **Verify before classifying:** listing-page titles are checked against the actual job posting, since listing pages and real JDs can diverge.
- **Honest reporting:** run reports only state coverage numbers that were actually tallied that run, not estimates.

## Stack

- ATS APIs, browser automation and DOM scraping for non-standard career pages
- Notion API for output and deduplication
- CSV-based state tracking for company/career-URL cache
- LLM-driven classification against a maintained rubric, refined iteratively against real-world misclassification cases

## Status

Actively running and refined on an ongoing basis as part of a live job search — the classification rubric in particular has gone through several rounds of correction as new edge cases surfaced.
