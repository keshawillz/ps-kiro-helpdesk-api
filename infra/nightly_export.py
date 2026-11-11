"""Nightly export of closed tickets: a scheduled Lambda with a least-access role."""
import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

FUNCTION_NAME = "helpdesk-nightly-export"
EXPORT_PREFIX = "ticket-exports/"
# Shared by the table definition, the role policy, and the INDEX_NAME env var.
INDEX_NAME = "helpdesk-tickets-status-closedat"


class NightlyExport(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: dynamodb.ITable,
        finance_bucket_name: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # Created first so its ARN can be named in the role's policy.
        log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"/aws/lambda/{FUNCTION_NAME}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # No managed policies. Read the one table, write one prefix, log to
        # the function's own log group.
        role = iam.Role(
            self,
            "Role",
            role_name="helpdesk-nightly-export-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "export": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["dynamodb:Query"],
                            resources=[f"{table.table_arn}/index/{INDEX_NAME}"],
                        ),
                        iam.PolicyStatement(
                            actions=["s3:PutObject"],
                            resources=[
                                f"arn:aws:s3:::{finance_bucket_name}/{EXPORT_PREFIX}*"
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[log_group.log_group_arn],
                        ),
                    ]
                )
            },
        )

        fn = lambda_.Function(
            self,
            "Fn",
            function_name=FUNCTION_NAME,
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="export.nightly_export.handler",
            code=lambda_.Code.from_asset("src"),
            role=role,
            log_group=log_group,
            environment={
                "TABLE_NAME": table.table_name,
                "INDEX_NAME": INDEX_NAME,
                "BUCKET_NAME": finance_bucket_name,
            },
            timeout=cdk.Duration.seconds(120),
            memory_size=256,
        )

        # EventBridge cron is UTC: 06:00 UTC is before 3 AM Eastern year-round.
        events.Rule(
            self,
            "Schedule",
            rule_name="helpdesk-nightly-export-schedule",
            schedule=events.Schedule.cron(minute="0", hour="6"),
            targets=[targets.LambdaFunction(fn)],
        )
