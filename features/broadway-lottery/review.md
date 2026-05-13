# Review: Broadway Lottery

**Reviewed:** 2026-05-13
**Plan:** [plan.md](./plan.md)
**Changes:** [changes.md](./changes.md)

---

## Checklist Verification

| Item | Status | Notes |
|---|---|---|
| Feature files follow existing layout | ✅ | `jobs/broadway-lottery/handler.py` matches pattern of all other jobs |
| Registered in CDK stack | ✅ | `create_scheduled_lambda()` + SES IAM policy added to `cron_stack.py` |
| Env vars documented | ✅ | All 4 vars in CDK environment dict, README, and feature README |
| Dependencies documented | ✅ | No extra deps — stdlib `urllib` + Lambda-native `boto3` only |
| Error handling matches pattern | ✅ | Env var guard at top of `main()`, `{"status": "error", "message": ...}` returns, `print()` to CloudWatch throughout |
| No hardcoded secrets | ✅ | All credentials via `os.environ.get()` |
| `changes.md` written | ✅ | |
| `UML.md` + `UML.html` updated | ✅ | New Lambda + EventBridge node added to diagram, Last activity updated |

---

## Findings

### 🔴 Must Fix

None.

### 🟡 Should Fix

- **`jobs/broadway-lottery/handler.py` — API endpoints unverified.** All three endpoint constants (`LOGIN_URL`, `LOTTERIES_URL`, `ENTRY_URL_TEMPLATE`) and all response field names are marked with `# VERIFY:` and cannot be confirmed without inspecting live Broadway Direct network traffic. The job will not work until these are verified and corrected. This is a known, documented risk — not a code defect — but it is a required pre-deploy step. The `# VERIFY:` comments and the README callout make this visible.

- **`_enter_lottery()` — HTTP status code not checked.** A 4xx response (e.g. already entered, lottery closed) will return a parsed body but the function only inspects `response["status"]`. If the API signals failure via HTTP status rather than a body field, the entry will be silently misreported as failed with "Unknown response". Mitigation: after verifying endpoints, add HTTP status code checking if needed.

### 🟢 Nice to Have

- Consider logging the full show list (not just selected) at `DEBUG` level for easier troubleshooting when entries fail.
- Once endpoints are verified and stable, the `# VERIFY:` comments can be replaced with confirmed values and the explanatory docstrings trimmed.
- A `requirements.txt` stub (even empty) in `jobs/broadway-lottery/` would match the pattern of other job folders that have one.

---

## Verdict

`Approved with fixes`

Implementation is structurally sound and matches all existing patterns. The `# VERIFY:` scaffolding is the right approach for an undocumented API — the code is deliberately designed to be corrected after inspecting live network traffic. No 🔴 items. The two 🟡 items are expected pre-deploy tasks, not defects. The job is ready to deploy once Broadway Direct endpoints are confirmed.
