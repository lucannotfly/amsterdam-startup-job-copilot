# Company List Sources

URLs used in the weekly company refresh (amsterdam-company-refresh scheduled task).

## Source 1: startupmap.one
**URL:** `https://startupmap.one/?city=Amsterdam&stage=pre-seed,seed,series-a,series-b&size=1-10,11-50,51-200`
**API endpoint (used internally):** `https://startupmap.one/api/startups` — filter client-side for `office_city === "Amsterdam"` and stages `pre_seed / seed / series_a / series_b`.

## Source 2: iAmsterdam (startupmap.iamsterdam.com)
**URL:** `https://startupmap.iamsterdam.com/companies/f/all_regions/allof_Amsterdam%20region/company_type/not_corporate_government%20nonprofit_service%20provider/employees/anyof_1_51-200_2-10_11-50/growth_stages/not_mature/last_funding_amount_min/anyof_2000000/launch_year_min/anyof_2015/tags/not_outside%20tech`

**Filters applied:**
- Region: Amsterdam region
- Company type: excludes corporate, government/nonprofit, service provider
- Employees: 1–200 (micro / small / medium)
- Growth stage: not mature
- Min funding: €2M+
- Founded: 2015 or later
- Tags: excludes "outside tech"

Powered by Dealroom.co. Data loaded via React/Redux store after scrolling through virtual list.
