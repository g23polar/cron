# Changes: Broadway Lottery

**Implemented:** 2026-05-13
**Plan:** [plan.md](./plan.md)

---

## Files Created

| File | Description |
|---|---|
| `jobs/broadway-lottery/handler.py` | Full job handler: `_build_opener`, `_login`, `_fetch_active_lotteries`, `_enter_lottery`, `_format_email`, `_send_error_email`, `send_email`, `main` |
| `features/broadway-lottery/README.md` | Feature spec (this feature) |
| `features/broadway-lottery/plan.md` | Technical implementation plan |
| `features/broadway-lottery/changes.md` | This file |
| `features/README.md` | Features index (created for first feature) |

## Files Modified

| File | What changed | Why |
|---|---|---|
| `cdk/cron_stack.py` | Added `broadway-lottery` `create_scheduled_lambda()` block + SES IAM policy | Register the new Lambda and EventBridge Sunday 14:00 UTC schedule |
| `README.md` | Added job to "What's included", "Schedules", and "Job configuration" sections | Keep project docs current |

---

## Deviations from Plan

None.

---

## Implementation Decisions

- **`http.cookiejar.CookieJar` for session management** — Broadway Direct likely sets cookies on login in addition to (or instead of) returning a token. Using a cookie-aware opener ensures both mechanisms are handled without extra code.
- **Dual token extraction paths** — `_login()` tries `response["token"]`, `response["auth_token"]`, and `response["data"]["token"]` so the handler works regardless of the exact response shape, which can only be confirmed against the live site.
- **Dual response unwrapping in `_fetch_active_lotteries()`** — tries bare list, `data`, `lotteries`, and `results` keys for the same reason.
- **`# VERIFY:` comments throughout** — all endpoint constants and response field names are clearly flagged for confirmation via browser DevTools before first deploy. This is the key risk in the plan.
- **Partial-success model** — if one entry fails the other is still reported and the email is always sent. Aborting on the first failure would lose the second entry unnecessarily.
- **`random.sample()` without seed** — true randomness (unlike `weekly_recipes` which uses a seeded picker for reproducibility). A lottery should pick differently each week.

---

## Post-fix Updates

| Fix | File | Description |
|---|---|---|
| 🟡 | `jobs/broadway-lottery/handler.py` | Added 5 new env vars confirmed from DevTools screenshot: `ENTRANT_FIRST_NAME`, `ENTRANT_LAST_NAME`, `ENTRANT_DATE_OF_BIRTH`, `ENTRANT_COUNTRY`, `ENTRANT_ZIP`; bundled into `entrant` dict passed to `_enter_lottery` |
| 🟡 | `cdk/cron_stack.py` | Added all 5 new env var slots to the Lambda environment block |
| 🟡 | `README.md` | Updated `broadway-lottery` env var list from 4 to 9 entries |
