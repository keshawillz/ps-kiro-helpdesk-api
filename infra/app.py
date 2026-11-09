#!/usr/bin/env python3
"""CDK app entry point for helpdesk-api."""
import os
import sys

import aws_cdk as cdk

sys.path.insert(0, os.path.dirname(__file__))

from finance_bucket_stack import HelpdeskFinanceBucketStack  # noqa: E402
from helpdesk_stack import HelpdeskApiStack  # noqa: E402

app = cdk.App()
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

# Finance owns this bucket. It lives in its own stack so the API stack can
# treat it as an external dependency, which is how it would look in real life.
finance = HelpdeskFinanceBucketStack(app, "HelpdeskFinanceBucketStack", env=env)

HelpdeskApiStack(
    app,
    "HelpdeskApiStack",
    finance_bucket_name=finance.bucket_name,
    env=env,
)

app.synth()
