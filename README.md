# cron

Lightweight AWS CDK app that deploys scheduled (cron) Lambda jobs using EventBridge. Each job lives in `jobs/` and is packaged as a Lambda function with its own handler and optional dependencies.

**What’s included**
1. `premier_league` — Fetches today’s Premier League fixtures from API-Football and emails a summary via AWS SES.
2. `calendar_sms` — Fetches today’s Google Calendar events and sends an SMS summary via AWS SNS.
3. `example_job` — Minimal template for new jobs.

**Architecture**
1. AWS CDK (Python) defines Lambda functions and EventBridge rules.
2. Each job is a folder under `jobs/` with a `handler.py`.
3. Optional job-specific Python dependencies are vendored into the job folder before deploy.

**Requirements**
1. Python 3.12+
2. AWS CDK v2
3. AWS credentials configured locally (`aws configure` or equivalent)

**Setup**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Deploy**
```bash
cdk bootstrap
cdk synth
cdk deploy
```

**Job configuration**
Set environment variables in the Lambda console or via CDK environment overrides.

`premier_league`
1. `API_FOOTBALL_KEY` — RapidAPI key for API-Football
2. `RECIPIENT_EMAIL` — Email to receive the summary
3. `SENDER_EMAIL` — Verified SES sender email

`calendar_sms`
1. `GOOGLE_CALENDAR_ID` — Calendar ID (e.g. `primary` or full ID)
2. `GOOGLE_SERVICE_ACCOUNT_JSON_B64` — Base64-encoded service account JSON
3. `SMS_PHONE_NUMBER` — E.164 format, e.g. `+15551234567`

**Calendar SMS dependencies**
The Google auth helper depends on `PyJWT` and `cryptography`. Vendor these into the job directory before deploying:
```bash
pip install -r jobs/calendar_sms/requirements.txt -t jobs/calendar_sms
```

**Schedules (UTC)**
1. Premier League matches: `08:00` UTC (3am EST)
2. Calendar SMS: `13:00` UTC (8am EST)

**Add a new job**
1. Copy `jobs/example_job` to a new folder.
2. Implement `handler.main`.
3. Add a new `create_scheduled_lambda` entry in `cdk/cron_stack.py`.
4. If you need extra deps, add a `requirements.txt` to the job folder and vendor them into the folder before deploy.

**Useful commands**
```bash
cdk diff
cdk destroy
```

**Notes**
1. `cdk.out` is generated output and safe to delete.
2. If SES is in sandbox mode, verify sender and recipient emails in SES. << IMPORTANT >>
