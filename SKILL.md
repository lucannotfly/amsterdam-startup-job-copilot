---
name: amsterdam-startup-jobs
description: Scan ALL live Amsterdam startup career pages every run (ATS APIs + custom pages), discover missing career URLs, read full JDs, classify Apply/Maybe/Skip for the user's career-transition goal, write to Notion (or pending CSV fallback), and output a run report. Use whenever the user asks to run the job scan, the Amsterdam job copilot, or the scheduled job-scan task.
---

You are running the Amsterdam Startup Job Copilot. Every run: refresh every company with a live career page, read the actual JD of every candidate role, classify against the user's VC-transition goal, write Apply/Maybe roles to Notion (or the pending CSV), and output the run report.

---

## PRIMARY GOAL

The user's goal is to transition into an early-stage generalist VC investing role within 1-2 years. Classify every role by one question: **how much does this role materially improve the user's odds of entering early-stage generalist VC within 1-2 years?** Do not optimise for general startup-operator fit in the abstract.

---

## NON-NEGOTIABLE RULES

1. **Full coverage every run.** Every company whose `career_url` does not start with `NOT_FOUND` (and is not empty) is re-scanned every run: ATS and custom pages alike. No rotation, no sampling, no caps, no "remaining companies next run". If a run is interrupted, continue in the same session. Only stop early if genuinely blocked (e.g. Chrome disconnected with no recovery), and then say so.
2. **Full sweep first, JD reading second.** Complete the full sweep of every company with a live career_url (Steps 2–4) before starting JD reading. Full coverage takes priority. If a candidate's JD can't be read, keep the role with "JD not verified" in the report rather than cutting scan coverage.
3. **Read the JD for every candidate title.** Roles with a candidate title (Step 5) must be classified from the full JD of the individual posting, not the careers listing page, title, teaser, or API title. Listing pages can misrepresent the role (title and content can differ). Non-candidate titles are classified by title alone (Step 5a).
4. **Location filter before classification.** Keep only roles located in Amsterdam / Netherlands / NL / Remote / unspecified. Discard roles with an explicit non-NL location.
5. **Honest metrics.** Only report numbers that were actually tallied from collected data. If a method only captures keyword matches, say so. List companies that failed to load as "not confirmed this run", never silently as covered or dead.
6. **Report template verbatim.** Use the exact Step 8 template below.

---

## FILES

- Master company list: `<PROJECT_DIR>/master_companies.csv` (columns: `name,source,career_url`)
- Pending Notion fallback: `<PROJECT_DIR>/pending_notion_roles_{YYYY-MM-DD}.csv`

---

## STEP 0: PREFLIGHT CHECKS (do these first, before any planning)

0. **Snapshot the CSV:** run `python3 csv_guard.py snapshot` in the project folder (no network needed). The matching post-run check is in Step 7.
1. **Chrome:** call `tabs_context_mcp` once. If Chrome is not connected, wait briefly and retry once. If still unavailable, the run is blocked: skip to Step 8 and report honestly that no scan happened. Do NOT attempt workarounds via bash (no outbound network) or web_fetch.
2. **Notion:** one quick tool search for Notion tools. If unavailable, plan to use the pending CSV fallback in Step 6 and flag this at the TOP of the run report.
3. **Already applied:** load the list of roles the user has already applied to (Notion Jobs DB `Applied Date` field and/or prior pending CSVs). Examples are kept in Notion, not in this file. Do not re-surface these as new unless the posting itself has changed.

---

## STEP 1: LOAD COMPANIES (with a script, never by eye)

Read master_companies.csv with Python via bash and bucket every row programmatically:

- **ATS (API-fetchable):** `career_url` matches `ashbyhq.com`, `greenhouse.io`, `lever.co`, `recruitee.com`, `workable.com`. Extract the slug directly from the URL.
- **ATS (browser-only):** `career_url` matches `hibob.com`, `personio.com`, `homerun.co`.
- **Custom pages:** any other non-empty `career_url` that does not start with `NOT_FOUND`.
- **Uncached:** empty `career_url`.
- **NOT_FOUND:** `NOT_FOUND` or `NOT_FOUND:YYYY-MM-DD`. Skipped in the scan; retry rules in Step 3d.

Print the count of each bucket. These counts are the denominators for the run report. Never build these lists by manually transcribing a CSV dump: manual transcription of 60+ rows has already caused a missed company.

**Do NOT query the Notion Jobs DB via SQL** (requires a Business plan, always fails). Use `notion-search` per role for dedup in Step 6.

---

## STEP 2: ATS API SWEEP — EVERY ATS COMPANY, EVERY RUN

**Do NOT use bash/Python for HTTP requests (no outbound network). All fetching goes through Chrome.**

### 2a. Neutral page
Navigate Chrome to `https://example.com` for a clean CORS context.

### 2b. Re-fetch ALL cached API-fetchable ATS companies
Using the slugs extracted in Step 1 (not slug guessing, not a hardcoded list), call each company's own ATS API endpoint:

```javascript
async function fetchOne({name, ats, slug}) {
  const t = {signal: AbortSignal.timeout(8000)};
  try {
    if (ats === 'ashby') {
      const d = await (await fetch(`https://api.ashbyhq.com/posting-api/job-board/${slug}`, t)).json();
      const jobs = d.jobs || d.jobPostings || []; // Ashby returns 'jobs'
      return jobs.map(j => ({title: j.title, url: j.jobUrl, location: j.location}));
    }
    if (ats === 'greenhouse') {
      const d = await (await fetch(`https://boards-api.greenhouse.io/v1/boards/${slug}/jobs?content=false`, t)).json();
      return (d.jobs || []).map(j => ({id: j.id, title: j.title, url: j.absolute_url, location: j.location?.name}));
    }
    if (ats === 'lever') {
      const d = await (await fetch(`https://api.lever.co/v0/postings/${slug}?mode=json`, t)).json();
      return (Array.isArray(d) ? d : []).map(j => ({title: j.text, url: j.hostedUrl, location: j.categories?.location}));
    }
    if (ats === 'recruitee') {
      const d = await (await fetch(`https://${slug}.recruitee.com/api/offers/`, t)).json();
      return (d.offers || []).map(o => ({title: o.title, url: o.careers_url || o.urls?.ad || `https://${slug}.recruitee.com/o/${o.slug}`, location: o.city}));
    }
    if (ats === 'workable') {
      const d = await (await fetch(`https://apply.workable.com/api/v1/widget/accounts/${slug}/jobs`, t)).json();
      return (d.results || d.jobs || []).map(j => ({title: j.title, url: `https://apply.workable.com/${slug}/j/${j.shortcode}`, location: j.location?.city || j.city || j.location}));
    }
  } catch (e) { return 'ERROR'; }
  return 'ERROR';
}
```

**Batching and output rules (important):**
- **10-15 companies per `javascript_tool` call**, not 30. Larger outputs get silently truncated in the tool display, and roles late in the array get missed with no error.
- **Return compact output only:** for every company, its total job count, plus only the jobs that (a) pass the location filter and (b) are not ALWAYS SKIP titles. Do not return full job lists.
- **Verify completeness:** every input company name must appear in the output (with a count or `ERROR`). If the output ends abruptly or any name is missing, re-run that batch in halves before moving on.
- If a batch returns `[BLOCKED: Cookie/query string data]`, just retry the same batch, or run it as a sequential for-loop instead of Promise.all. Don't hunt for a "bad" company. If one domain blocks repeatedly, use `get_page_text` on that page instead.
- If an ATS endpoint errors or returns 0 jobs where there used to be jobs, check the company homepage for a moved careers link before changing anything (see Step 3 fallback rules).

### 2c. Browser-only ATS companies (hibob / personio / homerun)
Navigate to each cached URL; do not fetch via CORS.
- **Hibob:** navigate to the `*.careers.hibob.com` URL, wait ~3s, click "View all", scroll to bottom, parse titles from `document.body.innerText` (a line is a title if the next line contains "·" and "contract"/"Permanent"). Hibob job detail views often have no real per-job href; record the listing URL and open the job by clicking it to read the JD.
- **Personio / Homerun:** navigate and extract with the compact extractor in Step 4.

Known current URLs (verify, don't trust blindly): Qogita → `https://qogita.careers.hibob.com/jobs` (the old `jobs.qogita.com` is dead). If any known URL fails, go to the company homepage `/careers` and follow the live link before marking anything.

### 2d. Special cases
- **adyen:** custom page `https://careers.adyen.com/` — large; scan titles, most roles will be ALWAYS SKIP.
- **bunq:** custom page `https://www.bunq.com/jobs`.
- **booking.com:** skip entirely.
- **Honeypot.io:** known unreachable (renderer timeouts across 3+ runs). Skip on sight, list as "known unreachable, skipped" in the report. Do not mark NOT_FOUND (the URL is valid).

---

## STEP 3: DISCOVER CAREER URLS FOR UNCACHED COMPANIES

Applies only to companies with an **empty** `career_url`.

### 3a. Slug-based ATS sweep
Derive slug: `name.toLowerCase().replace(/[^a-z0-9\s-]/g,'').replace(/\s+/g,'-').replace(/-+/g,'-').trim()` and try Ashby → Greenhouse → Lever → Recruitee → Workable (same endpoints as 2b), 10-15 companies per call.

**False-positive check (mandatory):** generic one-word names collide with unrelated companies on the same ATS (previous false hits: Equip, Propel, Struck, Proof, Rise, Stable). Only accept a hit if at least some returned jobs are in Amsterdam/Netherlands/Europe and the company identity matches. Otherwise discard it.

### 3b. Navigation fallback
For companies with no valid ATS hit, navigate (up to 50 per run, CSV order):
1. Find the real domain. **If the company name itself looks like a domain** (e.g. "Effect.AI", "Orq.ai", "Ver.iD", "eevi.ai"), try that literal lowercased name first (`effect.ai`); the slug derivation strips dots and guesses the wrong domain. Also try the name's last word as the TLD ("Yasu Cloud" → `yasu.cloud`, "Florence Finance" → `florence.finance`, "Send AI" → `send.ai`), and try less common TLDs (`.sh`, `.cloud`, `.dev`, `.health`) before concluding the domain is unknown. Otherwise try `.com`, `.io`, `.nl`, `.ai`, `.co`; if none resolves, do a quick web search for the company.
2. On the homepage, look for links containing "careers", "career", "jobs", "werken", "vacatures", "join us", "join the team".
3. If not found, probe in this order: `jobs.{domain}`, `{domain}/careers`, `{domain}/career`, `{domain}/jobs`, `{domain}/vacatures`, `careers.{domain}`.
4. If a third-party ATS URL (e.g. from startupmap) is known but shows no jobs, check the company's own site for the real careers page.
5. **Identity check before writing (mandatory):** the page must show the company name in its title or body AND have an Amsterdam/Netherlands/NL signal (address, `.nl`, Dutch text, Dutch-located jobs). A page that returns 200 is not proof: single-page sites return 200 for any path, and generic names collide with unrelated companies (e.g. Origin → ea.com, Relevate → randstad.com). If identity can't be confirmed, do NOT write the URL; list it as "unconfirmed candidate" in the report.
6. Record the final URL as `career_url` and write it to the CSV immediately. Extract its jobs in Step 4 this run.

### 3c. When to mark NOT_FOUND
Only mark `NOT_FOUND` if: the company's real live site (checked across TLDs / web search) has no careers link anywhere, or the company is genuinely gone. A parked/for-sale page on one domain is NOT sufficient (e.g. Dexter Energy's `.com` was parked, the real site was `.ai`). A single timeout is NOT sufficient: list it as "not confirmed this run" and retry next run.

**Never overwrite a resolved `career_url` with `NOT_FOUND`.** If a previously working URL now fails (e.g. Airweave's Ashby board returned 404), keep the existing URL in the CSV and list the company as "board currently down / not confirmed this run". Only empty or already-NOT_FOUND rows may be written as NOT_FOUND. Write new NOT_FOUND marks as `NOT_FOUND:{YYYY-MM-DD}`.

**Same rule applies to cached URLs that break during Steps 2 or 4:** before writing NOT_FOUND, go to the root domain and look for a renamed/moved careers link (e.g. `/careers` → `/career`).

### 3d. NOT_FOUND re-checks
Re-check a `NOT_FOUND:DATE` row via homepage navigation (3b) once DATE is 60+ days old; a bare `NOT_FOUND` with no date is always eligible, and gets a date after its re-check. Count these within the 50-per-run navigation cap, oldest first. The standard-ATS slug sweep against NOT_FOUND companies has already been done with zero genuine recoveries, so do not repeat it.

---

## STEP 4: EXTRACT JOBS FROM EVERY CUSTOM CAREER PAGE, EVERY RUN

Re-scan **every** company in the Custom bucket from Step 1, plus any newly found in Step 3. Not just this run's discoveries.

Use `browser_batch` with navigate + `javascript_tool` pairs, 4-10 companies per call, with this compact extractor (do NOT use `get_page_text` as the default, it is too token-heavy):

```javascript
await new Promise(r=>setTimeout(r,900));
const bad=/^(about|contact|home|privacy|terms|login|sign in|blog|news|products?|solutions?|company|careers?|jobs?|faq|cookie|accept|decline|customize|read more|learn more|view all|apply now|apply|share|back to jobs|all jobs|resources|pricing|support|our team|linkedin|instagram|twitter|facebook|youtube|open positions?|department|location|job type|get in touch|contact us|sign up|log in|menu)$/i;
const seen=new Set(); const out=[];
document.querySelectorAll('a, li, h1,h2,h3,h4').forEach(el=>{
  const t=el.innerText&&el.innerText.trim().replace(/\s+/g,' ');
  if(!t||t.length<6||t.length>90) return;
  if(bad.test(t)) return;
  if(seen.has(t)) return;
  seen.add(t); out.push(t);
});
out.slice(0,35).join(' | ');
```

Notes:
- JS state does not persist across `navigate`; do each page's extraction in one call.
- If Chrome drops mid-run ("not connected"), pause and retry `tabs_context_mcp`; the same tab usually keeps working. Continue the sweep, don't restart or abandon it.
- Expect a low hit rate; that is normal.
- Track per company: loaded / failed. Failed companies go into the report as "not confirmed this run".

---

## STEP 5: CLASSIFY ROLES

### 5a. Pipeline (in this order — only after the full sweep in Steps 2–4 is done)
1. **Location filter:** drop non-NL roles.
2. **Already applied / already in Notion:** drop (see Step 0).
3. **Three-tier title triage:**
   - **ALWAYS SKIP titles** (list below) → Skip by title alone.
   - **Titles in neither list** (e.g. Product Manager, Designer, Legal Counsel) → Skip by title alone. If a title looks borderline-relevant but isn't listed (e.g. "Business Analyst, Corporate Development"), treat it as a candidate and read the JD.
   - **Candidate titles** (list below) → read the full JD, then classify with the rubric in 5b. A candidate title is never an automatic rating.
4. **Where to get the JD (fastest source first):**
   - **ATS roles:** fetch the description via the ATS API for candidate roles only, in a separate small call after the sweep (keep descriptions out of the sweep output to avoid truncation): Ashby job-board response (`descriptionPlain` / `descriptionHtml`); Greenhouse `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{id}` (`content`); Lever posting (`descriptionPlain` + `lists`); Recruitee offer (`description` + `requirements`). If the field is missing or empty, navigate to the job URL instead. Workable / hibob / personio / homerun: navigate to the job page.
   - **Custom-page roles:** navigate to the individual job posting page (not the listing page) and read it with `get_page_text`.
5. If the JD can't be read, follow 5d.

### ALWAYS SKIP (title alone sufficient)
- Executive assistant / EA / personal assistant
- GTM-prefixed roles (GTM Engineer, GTM Strategy, Founding GTM, etc.)
- Head of Growth
- BDR / SDR / Business Development Representative
- Internship / working student / stage / stagiaire
- Account Executive / Account Manager / Technical Account Manager
- Customer Success / Customer Support
- Marketing Manager / Product Marketing / Growth Marketing
- RevOps / Sales Operations
- Software Engineer / Backend / Frontend / Infrastructure / ML Engineer / AI Researcher
- Office Manager / Facilities / HR
- Finance Controller / Accountant / Bookkeeper
- Recruiter / Talent Acquisition
- Data Analyst / Data Engineer (unless explicitly "for strategy" — then read the JD)

### Candidate titles (read the JD; title is NOT the rating)
Chief of Staff, Special Projects / Strategic Projects, Strategy / Strategic (not "Strategic Account Executive"), CEO Office / Founder's Office / Founder's Associate, Head of Strategy / Commercial / Business, Market Research / Market Intelligence / Market Mapping, Venture / Investment / Investor Relations, General Manager, Deployment Strategist, Partnerships, Business Operations / Biz Ops, Operations Manager / Head of Operations, Strategy & Operations, Program / Project Manager, Generalist.

### 5b. Rubric (apply to JD content)

**Primary positive signals:**
- Founder exposure (works directly with / reports to founders or CEO on strategic calls)
- Fundraising exposure (investor materials, investor relations, board prep)
- Market analysis, industry mapping, competitive landscape work
- Strategic / commercial judgment (owns or shapes real decisions: market entry, pricing, roadmap direction, resourcing, deal terms)
- High-context cross-functional decision support tied to company strategy
- Ambiguous, high-ownership work tied to company direction

**Default negative signals:**
- Internal operations, OKR management, program / project management, PMO
- GTM execution, marketing, revops
- Finance specialist work
- Account management, customer-facing implementation / support, "forward deployed" work
- Quota / ARR ownership
- Pure engineering or research
- **Required language mismatch:** a JD that requires fluent/native Dutch (or another language the user doesn't have at working level) is a default negative signal, and a Dutch-only posting is Skip.

**Decision-authority lens:** does the role own/influence actual decisions, or execute against a predefined playbook? Language like "escalation resolution", "measured on customer P&L", "resolve within SLAs", "forward deployed", "own partnership ARR targets", "reports into Revenue/Sales" → execution, Skip. Language like "recommend where to invest/deprioritise", "shape the roadmap", "set go-to-market strategy", "work directly with founders on strategic decisions" → Apply candidate.

**Ratings:**
- **Apply:** strong, direct bridge to VC. The JD clearly shows several primary positive signals.
- **Maybe:** superficially strategic/generalist, but the actual work may be mainly internal ops / OKR / PMO / execution-heavy. Default Maybe is the fallback for ambiguous strategy/generalist roles whose JD is mainly internal ops / OKR / PMO.
- **Skip:** limited direct transfer value to early-stage generalist VC.

**Company stage is a tie-breaker only** (Seed / Series A / B = mild positive). It never overrides a role-content mismatch.

**Known title traps (verified in past runs):**
- "Deployment Strategist" is often forward-deployed customer implementation/support → Skip unless the JD shows real strategy/founder decision work.
- "Partnerships Lead/Manager" is often quota-carrying channel BD → Skip unless the JD is genuinely corporate/ecosystem strategy with no quota.
- "Founder's Associate" on a listing page can turn out to be "Founding GTM" on the actual job page → always open the job page.
- "Strategy Director" at agencies/consultancies can be client-service work → check the JD.

### 5c. Validation test cases (the rubric must produce these outcomes)
1. "Strategy" in the title but mostly OKR / internal ops / PMO → **Maybe**, not Apply.
2. GTM / marketing / revops at a strong startup without investing-relevant judgment → **Skip**.
3. Worse company stage, but the work strongly compounds founder exposure, commercial judgment, and market insight → can still be **Apply**.
4. Great Seed / Series A company, but the role is functionally engineering, support, or admin → **Skip**.

### 5d. If a JD can't be read
If the job page won't load or is too sparse, say so. Fall back to title/archetype/stage as a proxy only as a last resort, rate no higher than **Maybe**, and mark it "JD not verified" in the report.

---

## STEP 6: WRITE TO NOTION (or pending CSV)

For each Apply/Maybe role:
1. **Dedup:** `notion-search` with query `"[Job Title] [Company]"` and `data_source_url: collection://<NOTION_JOBS_DB_ID>`. Skip exact title+company matches.
2. **Write** a new page in the Jobs DB (data_source_id `<NOTION_JOBS_DB_ID>`):
   - `Job Title`: title as shown on the actual job page
   - `Company`
   - `Link`: direct URL to the individual job posting
   - `the user Rating`: "Apply" or "Maybe"
   - `Archetype`: "Generalist" (default)
   - `Applied Date`, `Outcome`: leave empty
   - Page content: 1-3 sentences of rationale citing specific JD responsibilities (or "JD not verified").

**If Notion is unavailable:** write the same fields to `pending_notion_roles_{YYYY-MM-DD}.csv` in the project folder. Merge forward unconfirmed entries from earlier pending CSVs, marked "carried over, verify before adding". Preserve any `Applied Date` already recorded there. When Notion is back, write pending entries (including Applied Dates) to Notion.

---

## STEP 7: SAVE CSV UPDATES

Write all `career_url` changes (new finds, corrected URLs, NOT_FOUND) back to master_companies.csv with Python, preserving all rows and columns.

Then run `python3 csv_guard.py diff`. Include its CHANGED and PROBLEMS lists in the run report. If it reports a PROBLEM (a resolved URL lost, or a row removed), restore that row from the latest file in `snapshots/` before finishing.

---

## STEP 8: RUN REPORT (use this template verbatim)

**Amsterdam Startup Jobs — Run Report [DATE]**

[If Notion or Chrome was unavailable, state it here first, with what the user needs to do.]

**Coverage**
- Companies in master list: X (live career_url: X · empty: X · NOT_FOUND: X)
- ATS companies re-fetched (Step 2): X / X (errors: list)
- Custom career pages scanned (Step 4): X / X (keyword/title scan; total postings on these pages not counted)
- Not confirmed this run: X (list names + reason)
- New career URLs found this run (Step 3): X (list) · newly marked NOT_FOUND: X (list)
- Candidate roles whose full JD was read: X

**New Roles Added to Notion** (or pending CSV)
[Apply/Maybe] Company — Role Title — one-sentence VC-fit reason based on the JD
[Mark "JD not verified" where applicable]

**Trends**
2–3 sentences on patterns observed.

Every number above must come from an actual tally in this run. Do not estimate.

**Notifications:** if nothing new was added to Notion, do not send a push notification; only notify on new Apply roles or if the run failed to execute.
