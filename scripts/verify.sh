#!/usr/bin/env bash
# Deployed-state checks from Module 3 clip 2. Usage: ./verify.sh [YYYY-MM-DD]
set -euo pipefail
export AWS_PROFILE="${AWS_PROFILE:-helpdesk-sandbox}"
DATE="${1:-$(date -u +%F)}"
ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="helpdesk-finance-exports-$ACCT"
POLICY=$(aws iam list-role-policies --role-name helpdesk-nightly-export-role --query 'PolicyNames[0]' --output text)
set -x
aws dynamodb describe-table --table-name helpdesk-tickets --query 'Table.GlobalSecondaryIndexes[0].IndexStatus'
aws events describe-rule --name helpdesk-nightly-export-schedule --query '{Schedule:ScheduleExpression,State:State}'
aws events list-targets-by-rule --rule helpdesk-nightly-export-schedule --query 'Targets[].Arn'
aws lambda get-function-configuration --function-name helpdesk-nightly-export --query 'Role'
aws iam get-role-policy --role-name helpdesk-nightly-export-role --policy-name "$POLICY" --query 'PolicyDocument.Statement'
aws iam list-attached-role-policies --role-name helpdesk-nightly-export-role --query 'AttachedPolicies[].PolicyName'
aws s3 ls "s3://$BUCKET/ticket-exports/"
aws s3 cp "s3://$BUCKET/ticket-exports/closed-tickets-$DATE.csv" - | head -1
aws s3 cp "s3://$BUCKET/ticket-exports/closed-tickets-$DATE.csv" - | wc -l
aws dynamodb describe-table --table-name helpdesk-tickets --query 'Table.GlobalSecondaryIndexes[].{Name:IndexName,Status:IndexStatus}'
aws iam list-role-policies --role-name helpdesk-nightly-export-role --query 'PolicyNames'
aws s3 cp "s3://$BUCKET/ticket-exports/closed-tickets-$DATE.csv" -
