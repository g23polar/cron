# Broadway Lottery

**Status:** Complete
**Slug:** broadway-lottery
**Created:** 2026-05-13
**Last updated:** 2026-05-13 — implementation complete, pending endpoint verification

---

## Summary

Weekly Sunday Lambda job that discovers all active Broadway Direct lotteries, picks 2 shows at random, enters each for 2 tickets, and emails a confirmation summary via SES.

---

## Goal

Every Sunday morning the job runs automatically, enters 2 randomly selected Broadway Direct lotteries for 2 tickets each, and sends an email confirming which shows were entered. No manual action required.

---

## Requirements

- Runs every Sunday
- Targets Broadway Direct (https://lottery.broadwaydirect.com/)
- Discovers all shows currently running a lottery
- Picks 2 at random
- Enters each for 2 tickets
- Sends email confirmation via SES (which shows were entered, entry status)
- Broadway Direct emails winners directly — no result-checking needed

---

## Acceptance Criteria

- [ ] Job runs on a Sunday EventBridge schedule
- [ ] Successfully authenticates with Broadway Direct using stored credentials
- [ ] Discovers all shows with active lotteries
- [ ] Selects exactly 2 shows at random
- [ ] Submits a 2-ticket entry for each selected show
- [ ] Sends an SES email listing the shows entered and confirmation status
- [ ] Returns `{"status": "success", "entered": [...]}` on success
- [ ] Returns `{"status": "error", "message": "..."}` on failure with descriptive message
- [ ] No credentials hardcoded anywhere

---

## External Dependencies

| Dependency | Purpose | Auth method |
|---|---|---|
| Broadway Direct (lottery.broadwaydirect.com) | Discover shows, submit lottery entries | Email + password login (session cookie) |
| AWS SES | Send confirmation email | IAM role (ses:SendEmail) |

---

## Environment Variables

| Variable | Description | Example / format |
|---|---|---|
| `BROADWAY_DIRECT_EMAIL` | Broadway Direct account email | `you@example.com` |
| `BROADWAY_DIRECT_PASSWORD` | Broadway Direct account password | (plaintext, set in Lambda console) |
| `ENTRANT_FIRST_NAME` | First name on entry form | `Gautam` |
| `ENTRANT_LAST_NAME` | Last name on entry form | `Nair` |
| `ENTRANT_DATE_OF_BIRTH` | Date of birth on entry form | `02/01/2000` |
| `ENTRANT_COUNTRY` | Country of residence (default: `USA`) | `USA` |
| `ENTRANT_ZIP` | ZIP code on entry form | `10016` |
| `RECIPIENT_EMAIL` | Address to receive confirmation email | `you@example.com` |
| `SENDER_EMAIL` | Verified SES sender address | `alerts@example.com` |

---

## Patterns Followed

Surveyed `jobs/weekly_recipes/` (closest match: Sunday schedule, web scraping, random selection, SES email) and `jobs/premier_league/` (SES email pattern).

- **Layout / naming:** `jobs/broadway-lottery/handler.py` — self-contained folder, single `handler.py`
- **Dependency management:** No extra deps needed — `urllib` for HTTP, `boto3` for SES, both in Lambda runtime
- **Configuration:** `os.environ.get()` for all secrets; env vars declared in CDK `environment` dict
- **Error handling:** Validate env vars at top of `main()`, return `{"status": "error", "message": "..."}` on failure; `print()` all errors (CloudWatch)
- **Output:** `boto3.client("ses").send_email()` — identical pattern to `weekly_recipes` and `premier_league`
- **Registration:** One `create_scheduled_lambda()` call in `cdk/cron_stack.py` + `iam.PolicyStatement` for `ses:SendEmail`

---

## Related Files

- [x] [plan.md](./plan.md)
- [x] [changes.md](./changes.md)
- [x] [review.md](./review.md)
