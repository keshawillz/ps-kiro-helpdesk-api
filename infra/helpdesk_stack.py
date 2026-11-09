"""helpdesk-api: a DynamoDB table, four Lambda handlers, and a REST API."""
import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

TABLE_NAME = "helpdesk-tickets"


class HelpdeskApiStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        finance_bucket_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # One table. Partition key ticketId. Items carry status, createdAt,
        # closedAt (only once closed), priority, requester, subject, assignee.
        self.table = dynamodb.Table(
            self,
            "Tickets",
            table_name=TABLE_NAME,
            partition_key=dynamodb.Attribute(
                name="ticketId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),
            # Sandbox setting. Never copy into a production stack.
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        code = lambda_.Code.from_asset("src")
        common_env = {"TABLE_NAME": self.table.table_name}

        def handler(name: str, module: str) -> lambda_.Function:
            fn = lambda_.Function(
                self,
                f"{module.title().replace('_', '')}Fn",
                function_name=f"helpdesk-api-{name}",
                runtime=lambda_.Runtime.PYTHON_3_12,
                handler=f"api.{module}.handler",
                code=code,
                environment=common_env,
                timeout=cdk.Duration.seconds(10),
                memory_size=256,
            )
            self.table.grant_read_write_data(fn)
            return fn

        create_fn = handler("create-ticket", "create_ticket")
        get_fn = handler("get-ticket", "get_ticket")
        update_fn = handler("update-ticket", "update_ticket")
        close_fn = handler("close-ticket", "close_ticket")

        api = apigw.RestApi(
            self,
            "HelpdeskApi",
            rest_api_name="helpdesk-api",
            deploy_options=apigw.StageOptions(stage_name="v1"),
        )
        tickets = api.root.add_resource("tickets")
        tickets.add_method("POST", apigw.LambdaIntegration(create_fn))

        ticket = tickets.add_resource("{ticketId}")
        ticket.add_method("GET", apigw.LambdaIntegration(get_fn))
        ticket.add_method("PATCH", apigw.LambdaIntegration(update_fn))

        close = ticket.add_resource("close")
        close.add_method("POST", apigw.LambdaIntegration(close_fn))

        cdk.CfnOutput(self, "ApiUrl", value=api.url)
        cdk.CfnOutput(self, "TableName", value=self.table.table_name)
        cdk.CfnOutput(self, "FinanceBucketName", value=finance_bucket_name)
