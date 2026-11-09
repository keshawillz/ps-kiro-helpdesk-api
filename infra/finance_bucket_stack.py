"""The finance exports bucket. Owned by Finance; the API stack only writes to it."""
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from constructs import Construct


class HelpdeskFinanceBucketStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Explicit, predictable name: helpdesk-finance-exports-<account-id>.
        self.bucket_name = f"helpdesk-finance-exports-{self.account}"

        self.bucket = s3.Bucket(
            self,
            "FinanceExports",
            bucket_name=self.bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            # Sandbox settings. Never copy these into a production stack.
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        cdk.CfnOutput(self, "FinanceBucketName", value=self.bucket.bucket_name)
