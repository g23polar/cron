from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
)
from constructs import Construct
from pathlib import Path


class CronStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        jobs_dir = Path(__file__).parent.parent / "jobs"

        # Premier League daily matches - 3am EST = 8am UTC
        pl_job = self.create_scheduled_lambda(
            name="premier-league-matches",
            description="Fetches daily Premier League matches and emails summary",
            code_path=str(jobs_dir / "premier_league"),
            handler="handler.main",
            schedule=events.Schedule.cron(hour="8", minute="0"),
            timeout_minutes=2,
            memory_mb=128,
            environment={
                "API_FOOTBALL_KEY": "",  # Set in console or via secrets
                "RECIPIENT_EMAIL": "",   # Set in console
                "SENDER_EMAIL": "",      # Set in console, must be verified in SES
            },
        )
        # Grant SES send permission
        pl_job.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            )
        )

        # Google Calendar SMS - 8am EST = 1pm UTC
        # Note: Run `pip install -r requirements.txt -t .` in jobs/calendar_sms before deploying
        calendar_job = self.create_scheduled_lambda(
            name="calendar-sms",
            description="Fetches today's Google Calendar events and sends SMS summary",
            code_path=str(jobs_dir / "calendar_sms"),
            handler="handler.main",
            schedule=events.Schedule.cron(hour="13", minute="0"),
            timeout_minutes=2,
            memory_mb=256,
            environment={
                "GOOGLE_CALENDAR_ID": "",  # Set in console
                "GOOGLE_SERVICE_ACCOUNT_JSON_B64": "",  # Set in console
                "SMS_PHONE_NUMBER": "",  # E.164 format, e.g. +15551234567
            },
        )
        # Grant SNS publish permission for SMS
        calendar_job.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=["*"],
            )
        )

        # Weekly vegan recipes - 8am EST Sunday = 1pm UTC Sunday
        recipes_job = self.create_scheduled_lambda(
            name="weekly-vegan-recipes",
            description="Fetches weekly vegan recipes and emails recommendations",
            code_path=str(jobs_dir / "weekly_recipes"),
            handler="handler.main",
            schedule=events.Schedule.cron(hour="13", minute="0", week_day="SUN"),
            timeout_minutes=2,
            memory_mb=128,
            environment={
                "RECIPIENT_EMAIL": "",  # Set in console
                "SENDER_EMAIL": "",  # Set in console, must be verified in SES
            },
        )
        # Grant SES send permission
        recipes_job.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            )
        )

    def create_scheduled_lambda(
        self,
        name: str,
        description: str,
        code_path: str,
        handler: str,
        schedule: events.Schedule,
        timeout_minutes: int = 5,
        memory_mb: int = 256,
        environment: dict = None,
    ) -> lambda_.Function:
        """Create a Lambda function with an EventBridge schedule trigger."""

        fn = lambda_.Function(
            self,
            f"{name}-fn",
            function_name=name,
            description=description,
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler=handler,
            code=lambda_.Code.from_asset(code_path),
            timeout=Duration.minutes(timeout_minutes),
            memory_size=memory_mb,
            environment=environment or {},
        )

        # Create EventBridge rule to trigger on schedule
        rule = events.Rule(
            self,
            f"{name}-rule",
            rule_name=f"{name}-schedule",
            description=f"Schedule for {name}",
            schedule=schedule,
        )
        rule.add_target(targets.LambdaFunction(fn))

        return fn
