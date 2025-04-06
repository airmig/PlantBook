import os
import boto3
from botocore.config import Config

# Configure boto3 client
s3_config = Config(
    s3={
        'addressing_style': 'virtual',
        'signature_version': 's3v4',
        'payload_signing_enabled': False,
        'checksum_algorithm': None,
    }
)

# Create a session
session = boto3.Session()

# Create an S3 client with the custom config
s3_client = session.client(
    's3',
    aws_access_key_id=os.getenv('B2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('B2_SECRET_KEY'),
    endpoint_url=os.getenv('B2_ENDPOINT_URL'),
    region_name='us-east-005',
    config=s3_config
) 