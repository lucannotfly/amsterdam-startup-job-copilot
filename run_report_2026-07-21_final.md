**Amsterdam Startup Jobs — Run Report 2026-07-21 (Full Coverage)**

**Coverage**
- Companies with cached career URL (start of run): 339 / 410
- ATS hits this run (Step 2): all Ashby/Greenhouse/Lever/Recruitee/Workable/hibob companies swept via batched API/DOM calls, including a supplemental sweep of 54 companies that were missed by the original override-list logic (see Trends)
- Career pages navigated this run (Step 3): 259/259 custom (non-ATS) career pages checked, plus 1 stale override corrected (Qogita: jobs.qogita.com → qogita.careers.hibob.com/jobs)
- Companies still without career URL: 70 (unchanged this run — Step 3 fallback for NOT_FOUND companies was not attempted this run, per Wen's request to prioritize full live-URL coverage first)
- Full live-career_url coverage confirmed: 340/340, with 3 exceptions that failed to load on repeated attempts this session — Vandersat (DNS/timeout on both /careers and homepage), Honeypot.io (timeout x2), and Productpine (career_url resolves to a 404/storefront page, not a real career page). These are flagged for retry, not marked NOT_FOUND.

**New Roles Added to Notion**
(Notion connector unavailable again this run — written to `pending_notion_roles_2026-07-21.csv` instead)
- [Apply] Monumental — BizOps/Special Projects
- [Apply] Reson8 — Chief of Staff — direct founding-team exposure, "part operator, part strategist, part sparring partner," shapes commercial strategy. Found in the supplemental ATS-gap sweep after Wen flagged it was missing.
- [Maybe] Qogita — Strategy & Operations Analyst
- [Maybe] Carbon Equity — Investor Relations Manager
- [Maybe] Aquablu — Program Manager
- [Maybe] OMRT — Commercial Project Manager — client-delivery PM bridging technical output and commercial outcomes; Project Manager signal but execution-focused, not founder-facing. Found in the supplemental ATS-gap sweep.

Evaluated and correctly classified Skip: Wonderful.ai "Deployment Strategist" (known execution-heavy title trap) and Workwize "Partnerships Lead" (JD explicitly ties the role to owning ARR/pipeline targets — channel/BD partnerships, not strategic, despite the title).

No additional Apply/Maybe candidates surfaced in the rest of the custom-page sweep (indices 32–259). Most companies either had no open roles, or only engineering/sales/support/marketing postings that fall under the rubric's default-Skip categories.

**Trends**
Full-coverage sweeps continue to show a low hit rate for VC-transferable roles — most Amsterdam startups' open strategic-sounding titles turn out to be GTM, customer support, or engineering roles once the actual JD is checked. The generic-name slug-sweep for NOT_FOUND companies (Equip, Propel, Struck) continues to be unreliable and yielded zero genuine recoveries this run.

**Process fix this run:** Wen caught that Reson8's Chief of Staff posting was missing from the report. Investigation found a structural gap in the amsterdam-startup-jobs skill: the ATS sweep (Step 2) only re-queried a ~15-company hardcoded override list plus companies with no cached career_url — any company that had already been resolved to an ATS URL in a past run (54 found, e.g. Reson8, Ankorstore, Bitvavo, TestGorilla, Weaviate, plus ~25 Recruitee companies) was silently never re-checked again. Ran a one-off supplemental sweep of all 54 to close today's gap (surfaced Reson8 and OMRT above), and updated the skill's Step 2/Step 4 so future runs derive the full ATS re-fetch list directly from master_companies.csv every time instead of relying on the static override list. This should prevent the gap from recurring in future runs.
