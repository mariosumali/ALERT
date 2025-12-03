import boto3
import os
from typing import Optional

# S3 client setup (optional - can use local storage instead)
_s3_client = None

def get_s3_client():
    """Initialize and return S3 client if credentials are available."""
    global _s3_client
    if _s3_client is None:
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        if aws_access_key and aws_secret_key:
            _s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
    
    return _s3_client

def upload_to_s3(file_path: str, bucket: str, s3_key: str) -> bool:
    """Upload file to S3 bucket."""
    client = get_s3_client()
    if not client:
        return False
    
    try:
        client.upload_file(file_path, bucket, s3_key)
        return True
    except Exception as e:
        print(f"S3 upload error: {str(e)}")
        return False

def download_from_s3(bucket: str, s3_key: str, local_path: str) -> bool:
    """Download file from S3 bucket."""
    client = get_s3_client()
    if not client:
        return False
    
    try:
        client.download_file(bucket, s3_key, local_path)
        return True
    except Exception as e:
        print(f"S3 download error: {str(e)}")
        return False

