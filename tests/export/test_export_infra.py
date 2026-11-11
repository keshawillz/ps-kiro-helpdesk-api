"""Nightly export infrastructure: CDK template assertions (no AWS calls)."""
import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "infra")
)

from helpdesk_stack import HelpdeskApiStack  # noqa: E402

BUCKET = "helpdesk-finance-exports-123456789012"
ROLE_NAME = "helpdesk-nightly-export-role"
FUNCTION_NAME = "helpdesk-nightly-export"
INDEX_NAME = "helpdesk-tickets-status-closedat"


@pytest.fixture(scope="module")
def template():
    app = cdk.App()
    stack = HelpdeskApiStack(app, "TestStack", finance_bucket_name=BUCKET)
    return Template.from_stack(stack)


@pytest.fixture(scope="module")
def statements(template):
    roles = template.find_resources(
        "AWS::IAM::Role",
        {"Properties": {"RoleName": ROLE_NAME}},
    )
    assert len(roles) == 1
    role = next(iter(roles.values()))
    policies = role["Properties"]["Policies"]
    assert len(policies) == 1
    return policies[0]["PolicyDocument"]["Statement"]


def _as_list(value):
    return value if isinstance(value, list) else [value]


def _statement_for(statements, action):
    matches = [s for s in statements if action in _as_list(s["Action"])]
    assert len(matches) == 1
    return matches[0]


def test_function_has_explicit_name(template):
    template.has_resource_properties(
        "AWS::Lambda::Function", {"FunctionName": FUNCTION_NAME}
    )


def test_role_has_explicit_name(template):
    template.has_resource_properties(
        "AWS::IAM::Role", {"RoleName": ROLE_NAME}
    )


def test_schedule_rule_runs_at_0600_utc(template):
    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "Name": "helpdesk-nightly-export-schedule",
            "ScheduleExpression": "cron(0 6 * * ? *)",
        },
    )


def test_schedule_rule_targets_the_function(template):
    fn_ids = list(
        template.find_resources(
            "AWS::Lambda::Function",
            {"Properties": {"FunctionName": FUNCTION_NAME}},
        )
    )
    assert len(fn_ids) == 1
    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "Name": "helpdesk-nightly-export-schedule",
            "Targets": [
                Match.object_like({"Arn": {"Fn::GetAtt": [fn_ids[0], "Arn"]}})
            ],
        },
    )


def test_function_uses_the_export_role(template):
    role_ids = list(
        template.find_resources(
            "AWS::IAM::Role", {"Properties": {"RoleName": ROLE_NAME}}
        )
    )
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "FunctionName": FUNCTION_NAME,
            "Role": {"Fn::GetAtt": [role_ids[0], "Arn"]},
        },
    )


def test_role_has_no_managed_policies(template):
    template.has_resource_properties(
        "AWS::IAM::Role",
        {"RoleName": ROLE_NAME, "ManagedPolicyArns": Match.absent()},
    )


def test_table_has_status_closedat_index(template):
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "GlobalSecondaryIndexes": Match.array_with(
                [
                    Match.object_like(
                        {
                            "IndexName": INDEX_NAME,
                            "KeySchema": [
                                {"AttributeName": "status", "KeyType": "HASH"},
                                {"AttributeName": "closedAt", "KeyType": "RANGE"},
                            ],
                        }
                    )
                ]
            )
        },
    )


def test_table_key_schema_is_unchanged(template):
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {"KeySchema": [{"AttributeName": "ticketId", "KeyType": "HASH"}]},
    )


def test_role_queries_the_index_arn_only(template, statements):
    table_ids = list(template.find_resources("AWS::DynamoDB::Table"))
    assert len(table_ids) == 1
    stmt = _statement_for(statements, "dynamodb:Query")
    assert stmt["Effect"] == "Allow"
    assert stmt["Resource"] == {
        "Fn::Join": [
            "",
            [
                {"Fn::GetAtt": [table_ids[0], "Arn"]},
                f"/index/{INDEX_NAME}",
            ],
        ]
    }


def test_log_group_retention_is_30_days(template):
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": f"/aws/lambda/{FUNCTION_NAME}",
            "RetentionInDays": 30,
        },
    )


def test_function_environment_has_index_name(template):
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "FunctionName": FUNCTION_NAME,
            "Environment": {
                "Variables": Match.object_like({"INDEX_NAME": INDEX_NAME})
            },
        },
    )


def test_role_puts_objects_under_export_prefix_only(statements):
    stmt = _statement_for(statements, "s3:PutObject")
    assert stmt["Effect"] == "Allow"
    assert stmt["Resource"] == f"arn:aws:s3:::{BUCKET}/ticket-exports/*"


def test_role_logs_to_its_own_log_group(template, statements):
    log_group_ids = list(
        template.find_resources(
            "AWS::Logs::LogGroup",
            {"Properties": {"LogGroupName": f"/aws/lambda/{FUNCTION_NAME}"}},
        )
    )
    assert len(log_group_ids) == 1
    stmt = _statement_for(statements, "logs:PutLogEvents")
    assert sorted(_as_list(stmt["Action"])) == [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    ]
    assert stmt["Resource"] == {"Fn::GetAtt": [log_group_ids[0], "Arn"]}


def test_role_has_no_wildcard_resource(statements):
    for stmt in statements:
        for resource in _as_list(stmt["Resource"]):
            assert resource != "*"


def test_role_has_only_query_on_dynamodb(statements):
    allowed = {a for s in statements for a in _as_list(s["Action"])}
    dynamodb_actions = {a for a in allowed if a.startswith("dynamodb:")}
    assert dynamodb_actions == {"dynamodb:Query"}
    assert "dynamodb:Scan" not in allowed


def test_role_has_no_s3_action_other_than_put_object(statements):
    allowed = {a for s in statements for a in _as_list(s["Action"])}
    s3_actions = {a for a in allowed if a.startswith("s3:")}
    assert s3_actions == {"s3:PutObject"}
