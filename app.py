#!/usr/bin/env python3
import aws_cdk as cdk

from cdk.cron_stack import CronStack

app = cdk.App()
CronStack(app, "CronStack")

app.synth()
