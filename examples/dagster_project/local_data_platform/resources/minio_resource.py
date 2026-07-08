import os

import boto3
from dagster import ConfigurableResource


class MinioResource(ConfigurableResource):
    endpoint_url: str = "http://minio:9000"
    access_key: str = os.environ.get("MINIO_APP_ACCESS_KEY", "")
    secret_key: str = os.environ.get("MINIO_APP_SECRET_KEY", "")
    region: str = "us-east-1"

    def get_client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    def list_objects(self, bucket: str, prefix: str):
        client = self.get_client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                yield obj["Key"]

    def get_object_bytes(self, bucket: str, key: str) -> bytes:
        client = self.get_client()
        return client.get_object(Bucket=bucket, Key=key)["Body"].read()
