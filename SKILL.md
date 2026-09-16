---
name: amsterdam-startup-jobs
description: Scan Amsterdam startup career pages (6 ATS platforms + direct navigation), cache career URLs progressively, classify Apply/Maybe/Skip, write to Notion
---

You are running the Amsterdam Startup Job Copilot. Scan career pages of Amsterdam startups, classify new roles for Wen's VC-transition goal, write Apply/Maybe roles to Notion, and output a run report.

---

## PRIMARY GOAL

Wen's goal is to transition into early-stage generalist VC investing within 1-2 years. Classify every role to optimize for that outcome.

---

## FILES

Master company list: `/Users/wenqianlu/Claude/Projects/Amsterdam Startup Job Copilot/master_companies.csv`
Columns: `name,source,career_url`

---

## STEP 1: LOAD COMPANIES

Read master_companies.csv into memory using the Read tool or bash. Note which rows already have `career_url` populated and which are empty or `NOT_FOUND`.

**`NOT_FOUND` entries are dated, not permanent.** They're written as `NOT_FOUND:YYYY-MM-DD` (the date Step 3 gave up on them). Treat a `NOT_FOUND:DATE` row as eligible for retry in Step 3 once 60+ days have passed since DATE; a bare `NOT_FOUND` with no date (from before this convention) is always eligible for retry. This exists because the domain-guessing heuristic misses real, live companies — e.g. "Effect.AI" was guessed as `effectai.com` and marked NOT_FOUND when the real site is `effect.ai` — so a permanent skip compounds heuristic misses forever.

**NOTE: Do NOT attempt to query the Notion Jobs DB via SQL — it requires a Business plan and will always fail. Instead, use `notion-search` per-role to check for duplicates just before writing each entry (Step 6).**

---

## STEP 2: ATS API SWEEP — ALL COMPANIES (Chrome JS Promise.all)

**IMPORTANT: Do NOT use bash/Python for HTTP requests. The bash sandbox has no outbound network access. All ATS fetching must go through the Chrome browser.**

### 2a. Navigate Chrome to a neutral page first
Use `mcp__Claude_in_Chrome__navigate` to go to `https://example.com`. This gives a clean CORS context.

### 2b. Re-fetch ALL companies with a cached career_url on a known ATS (CSV-driven — do this every run, not just for new companies)

Read master_companies.csv. For every row with a non-empty, non-`NOT_FOUND` `career_url`, check if it matches one of these five URL patterns. If it does, extract the slug directly from the URL (not by guessing from the company name) and add it to the batch sweep below:

```javascript
function classifyFromUrl(url) {
  let m;
  if (m = url.match(/ashbyhq\.com\/([^\/?#]+)/i)) return {ats: 'ashby', slug: m[1]};
  if (m = url.match(/greenhouse\.io\/([^\/?#]+)/i) || url.match(/greenhouse\.io\/embed\/job_board\?for=([^&]+)/i)) return {ats: 'greenhouse', slug: m[1]};
  if (m = url.match(/lever\.co\/([^\/?#]+)/i)) return {ats: 'lever', slug: m[1]};
  if (m = url.match(/^https?:\/\/([a-z0-9-]+)\.recruitee\.com/i)) return {ats: 'recruitee', slug: m[1]};
  if (m = url.match(/workable\.com\/([a-z0-9-]+)/i)) return {ats: 'workable', slug: m[1]};
  return null; // not a standard-ATS URL — leave for 2c (non-standard) or Step 3/4 (custom pages)
}
```

This list will typically be 50-80+ companies (it grows every time a company graduates from "uncached" to "cached" via 2d below) — **this is the majority of the ATS sweep's work, every run.** Do not skip a company just because it already has a career_url; that's the exact bug this replaces (see [[feedback_cached_ats_url_gap]]).

Batch these through the same `sweepBatch`-style Promise.all fetcher used below, 30 at a time, using the slug extracted from the URL rather than derived from the company name.

### 2c. Non-standard ATS overrides (hibob / personio / homerun / custom — not covered by the fetch-based sweep in 2b/2d)

These platforms don't expose a public JSON API the same way, or the company's URL doesn't cleanly match a standard pattern. Navigate directly and DOM-scrape (see [[feedback_hibob_scan]]):

```
tiqets           → homerun     → https://tiqets.homerun.co/
otrium           → hibob       → https://careers.otrium.com/
qogita           → hibob       → https://qogita.careers.hibob.com/jobs   (verify this hasn't gone stale — see [[feedback_qogita_override_stale]])
happeo           → personio    → https://happeo.jobs.personio.com/
silverflow       → personio    → https://silverflow.jobs.personio.com/
bunq             → custom      → https://www.bunq.com/jobs
adyen            → custom      → https://careers.adyen.com/ (large — skip most roles)
booking.com      → skip entirely
```

If you find other companies whose career_url is on hibob/personio/homerun during Step 2b's CSV scan, add them here too rather than silently dropping them.

### 2d. Slug-guessing sweep for companies with NO cached career_url at all

Use `mcp__Claude_in_Chrome__javascript_tool` to run Promise.all batches of **30 companies at a time**. Keep batches small to avoid Chrome extension timeouts. This step is for *discovering* new career URLs only — companies already covered by 2b should NOT be re-included here.

Derive slug:
```javascript
const slug = name.toLowerCase().replace(/[^a-z0-9\s-]/g,'').replace(/\s+/g,'-').replace(/-+/g,'-').trim();
```

For each batch, run this JS on `example.com`:
```javascript
async function sweepBatch(companies) {
  const results = {};
  await Promise.all(companies.map(async ({name, slug}) => {
    // Try Ashby
    try {
      const r = await fetch(`https://api.ashbyhq.com/posting-api/job-board/${slug}`, {signal: AbortSignal.timeout(6000)});
      const d = await r.json();
      const jobs = d.jobs || d.jobPostings || []; // NOTE: Ashby returns 'jobs' key, not 'jobPostings'
      if (jobs.length > 0) { results[name] = {ats:'ashby', slug, jobs: jobs.map(j=>({title:j.title,url:j.jobUrl,location:j.location}))}; return; }
    } catch(e) {}
    // Try Greenhouse
    try {
      const r = await fetch(`https://boards-api.greenhouse.io/v1/boards/${slug}/jobs?content=false`, {signal: AbortSignal.timeout(6000)});
      const d = await r.json();
      if (d.jobs?.length > 0) { results[name] = {ats:'greenhouse', slug, jobs: d.jobs.map(j=>({title:j.title,url:j.absolute_url,location:j.location?.name}))}; return; }
    } catch(e) {}
    // Try Lever
    try {
      const r = await fetch(`https://api.lever.co/v0/postings/${slug}?mode=json`, {signal: AbortSignal.timeout(6000)});
      const d = await r.json();
      if (Array.isArray(d) && d.length > 0) { results[name] = {ats:'lever', slug, jobs: d.map(j=>({title:j.text,url:j.hostedUrl,location:j.categories?.location}))}; return; }
    } catch(e) {}
    // Try Recruitee
    try {
      const r = await fetch(`https://${slug}.recruitee.com/api/offers/`, {signal: AbortSignal.timeout(6000)});
      const d = await r.json();
      if (d.offers?.length > 0) { results[name] = {ats:'recruitee', slug, jobs: d.offers.map(o=>({title:o.title,url:o.urls?.ad||`https://${slug}.recruitee.com/o/${o.slug}`,location:o.city}))}; return; }
    } catch(e) {}
    // Try Workable
    try {
      const r = await fetch(`https://apply.workable.com/api/v1/widget/accounts/${slug}/jobs`, {signal: AbortSignal.timeout(6000)});
      const d = await r.json();
      if (d.results?.length > 0) { results[name] = {ats:'workable', slug, jobs: d.results.map(j=>({title:j.title,url:`https://apply.workable.com/${slug}/j/${j.shortcode}`,location:j.location}))}; return; }
    } catch(e) {}
    // No ATS hit → mark for Step 3
    results[name] = null;
  }));
  return results;
}

// Call with current batch, e.g.:
sweepBatch([{name:'Accel Club',slug:'accel-club'}, ...]).then(r => JSON.stringify(r));
```

Process the company list in batches of 30. For each batch:
- Run the JS, collect results
- Companies with a hit → record career_url, collect jobs for Step 4
- Companies with null → add to Step 3 queue (needs browser navigation)
- Save career_url updates to CSV after each batch

---

## Note for STEP 4 (unchanged step number, updated first bullet):

- **ATS companies (Step 2b, 2c, and 2d hits):** Jobs are already in memory from the API/DOM responses. Use them directly.
- **Non-ATS career pages (Step 3 finds):** Navigate to the career_url, extract job listings from the page text.
- **Skip:** Companies with `career_url = NOT_FOUND`, empty, or still unknown after Step 3.

---

## STEP 3: NAVIGATE TO FIND CAREER URLS (fallback — capped at 50 per run)

Many Amsterdam startups do NOT use standard ATS platforms and have custom career pages. After the ATS sweep, navigate to company websites for all companies that:
- Got null/no hit from every ATS in Step 2, AND
- Have no `career_url` cached in CSV (or career_url is empty, or `NOT_FOUND` older than 60 days per Step 1)

Take up to 50 of these per run in CSV order (prioritize companies earlier in the list that haven't been visited yet, then companies whose `NOT_FOUND` date is oldest).

For each company, use Chrome navigation:
0. **If the company name itself looks like a domain** (two alphanumeric segments joined by a single dot, e.g. "Effect.AI", "Orq.ai", "Ver.iD") → try that literal lowercased name as a domain FIRST (`effect.ai`, `orq.ai`, `ver.id`), before the slug-based guesses below. The plain slug derivation strips dots and will guess the wrong domain for these (`effectai.com` instead of `effect.ai`).
1. Try `https://${slug}.com`, then `.io`, then `.nl`
2. On the homepage, look for a link containing: "careers", "jobs", "werken", "vacatures", "join us", "join the team", "team"
3. If found → navigate to that link, record the final URL as `career_url`
4. If not found on homepage → try `https://${slug}.com/careers` and `https://${slug}.com/jobs` directly
5. If still nothing → record `NOT_FOUND:{today's date, YYYY-MM-DD}` in the CSV (eligible for retry after 60 days, per Step 1)

Write each result back to master_companies.csv immediately after processing (use bash/Python to update the CSV row).

For companies found via Step 3: navigate to the career_url and extract visible job listings (title + link) for Step 4.

---

## STEP 4: EXTRACT JOBS FROM ALL KNOWN CAREER URLS

- **ATS companies (Step 2 hits):** Jobs are already in memory from the API responses. Use them directly.
- **Non-ATS career pages (Step 3 finds):** Navigate to the career_url, extract job listings from the page text.
- **Skip:** Companies with `career_url = NOT_FOUND`, empty, or still unknown after Step 3.

---

## STEP 5: CLASSIFY ROLES

### ALWAYS SKIP (title alone sufficient)
- Executive assistant / EA / personal assistant
- GTM prefix roles (GTM Engineer, GTM Strategy, etc.)
- Head of Growth
- BDR / SDR / Business Development Representative
- Internship / working student / stage / stagiaire
- Account Executive / Account Manager / Technical Account Manager
- Customer Success / Customer Support
- Marketing Manager / Product Marketing / Growth Marketing
- RevOps / Sales Operations
- Software Engineer / Backend / Frontend / Infrastructure / ML / AI Researcher
- Office Manager / Facilities / HR
- Finance Controller / Accountant / Bookkeeper
- Recruiter / Talent Acquisition
- Data Analyst / Data Engineer (unless explicitly "for strategy")

### APPLY signals (strong direct bridge to VC)
- Chief of Staff / CoS
- Special Projects / Strategic Projects
- Deployment Strategist
- Strategy / Strategic (NOT "Strategic Account Executive")
- CEO Office / Founder's Office
- Head of Strategy / Head of Commercial / Head of Business
- Market Research / Market Intelligence / Market Mapping
- Partnerships (business/corporate context, not sales)
- Venture / Investment (any role)
- General Manager (seed/series A stage)

### MAYBE signals
- Business Operations Manager / Biz Ops
- Operations Manager / Head of Operations
- Program Manager / Project Manager / PMO
- Strategy & Operations
- Generalist (without CEO office context)

### Rules
- Dutch-only job postings → Skip
- Company stage as tiebreaker only (Seed/Series A/B = positive signal, does not override role mismatch)

---

## STEP 6: WRITE TO NOTION

For each Apply/Maybe role found:
1. **Dedup check:** Use `notion-search` with query `"[Job Title] [Company]"` and `data_source_url: collection://3794ee23-1b53-8050-9508-000b0cf32128`. If an exact title+company match is found, skip it.
2. **Write:** Create a new page in the Jobs DB (data_source_id: `3794ee23-1b53-8050-9508-000b0cf32128`) with:
   - `Job Title`: role title
   - `Company`: company name
   - `Link`: direct application URL
   - `Wen Rating`: "Apply" or "Maybe"
   - `Archetype`: "Generalist" (default)
   - `Applied Date`: leave empty
   - `Outcome`: leave empty

---

## STEP 7: SAVE CSV UPDATES

Write all career_url updates back to master_companies.csv using Python (via bash), preserving all existing rows and columns.

---

## STEP 8: RUN REPORT

**Amsterdam Startup Jobs — Run Report [DATE]**

**Coverage**
- Companies with cached career URL (start of run): X / 409
- ATS hits this run (Step 2): X new companies
- Career pages navigated this run (Step 3): X (Y found, Z → NOT_FOUND)
- Companies still without career URL: X (will be covered in future runs)

**New Roles Added to Notion**
[Apply/Maybe] Company — Role Title — one sentence VC-fit reason

**Trends**
2–3 sentences on patterns observed.
