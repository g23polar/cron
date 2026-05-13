# Plan: Broadway Lottery

**Status:** Approved
**Approved by:** user — 2026-05-13

---

## Goal

A Lambda function runs every Sunday at 14:00 UTC (9am EST). It authenticates
with Broadway Direct, fetches all shows currently running a lottery, picks 2 at
random, submits a 2-ticket entry for each, and emails a confirmation summary via
SES. Broadway Direct handles winner notification directly — no result checking
needed.

---

## Patterns Observed

From surveying `jobs/weekly_recipes/` and `jobs/premier_league/`:

- **Layout:** `jobs/broadway-lottery/handler.py` — self-contained folder, single entry point
- **Config:** `os.environ.get()` for all credentials; declared in CDK `environment` dict (set values in Lambda console)
- **Error handling:** Validate all env vars at top of `main()`, return `{"status": "error", "message": "..."}` dict; `print()` to stdout (CloudWatch Logs)
- **Output:** `boto3.client("ses").send_email()` — same pattern as `weekly_recipes`
- **Registration:** `create_scheduled_lambda()` in `cdk/cron_stack.py` + `iam.PolicyStatement` for `ses:SendEmail`
- **No extra deps:** `urllib` + `boto3` are sufficient — no vendoring needed

---

## Approach

- **Auth:** POST credentials to Broadway Direct's login endpoint, capture the
  session cookie from the response, carry it on all subsequent requests.
- **Discover shows:** GET the lottery listings page / API endpoint, parse the
  response to extract all shows with an active lottery (show name + entry endpoint).
- **Pick 2:** Use `random.sample()` (non-deterministic — true randomness is
  appropriate for a lottery, unlike the recipes job which uses a seeded picker
  for reproducibility).
- **Enter:** POST a 2-ticket entry request for each selected show using the
  authenticated session cookie.
- **Email:** Summarise the two shows entered (name + entry status) and send via
  SES. If either entry fails, report it clearly in the email rather than
  aborting — partial success is still useful.
- **No vendored deps:** All HTTP via `urllib`, AWS via `boto3`. No `requests`,
  no Playwright — keeps the Lambda package minimal.

Alternatives rejected:
- *Playwright/Selenium* — requires a Chrome layer, heavy Lambda package, overkill for HTTP form submission
- *Seeded random* — deterministic selection is wrong here; you want a different pair each week regardless of show list changes

---

## Changes

| File | Action | What changes and why |
|---|---|---|
| `jobs/broadway-lottery/handler.py` | Create | Full job: login, discover, pick, enter, email |
| `cdk/cron_stack.py` | Modify | Add `create_scheduled_lambda()` call for the new job + SES IAM policy |
| `README.md` | Modify | Document new job and its env vars under "Job configuration" |

---

## Risks / Open Questions

- **Broadway Direct API is undocumented.** The site is a React SPA. Login and
  entry endpoints must be confirmed by inspecting network requests in browser
  DevTools before or during implementation. The handler will be written with
  clearly named functions (`_login`, `_fetch_shows`, `_enter_lottery`) so
  endpoints can be swapped in easily once confirmed.
- **Anti-bot measures.** The site may block `urllib` requests without a realistic
  `User-Agent` or if it detects automation. Mitigation: send a browser-like
  `User-Agent` header and `Referer`. If that's insufficient, a short `time.sleep`
  between requests may help.
- **Session expiry.** Broadway Direct sessions are scoped to each Lambda
  invocation — a fresh login on every run avoids stale-cookie problems.
- **Show availability.** There may be weeks with fewer than 2 active lotteries.
  Handle gracefully: enter however many are available and report in the email.

---

## Checklist

- [x] `jobs/broadway-lottery/handler.py` created
- [x] Login, show discovery, entry, and email functions implemented and individually testable
- [ ] Broadway Direct endpoints verified against live site network traffic
- [x] `cdk/cron_stack.py` updated with new `create_scheduled_lambda()` entry
- [x] SES IAM policy added for new Lambda
- [x] All 4 env vars declared in CDK environment dict (values left blank for console)
- [x] `README.md` updated with new job and env var docs
- [x] No credentials hardcoded
- [x] `features/broadway-lottery/changes.md` written
- [x] `UML.md` and `UML.html` updated
- [x] Diff reviewed, `features/broadway-lottery/review.md` written
