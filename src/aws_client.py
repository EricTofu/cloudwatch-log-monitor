import boto3
import json
import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AWSClient:
    def __init__(self) -> None:
        self.ssm = boto3.client('ssm')
        self.s3 = boto3.client('s3')
        self.logs = boto3.client('logs')
        self.sns = boto3.client('sns')

    def publish_sns_message(self, topic_arn: str, message: str) -> None:
        """Publishes a message to an SNS topic. Raises ClientError on failure."""
        try:
            self.sns.publish(
                TopicArn=topic_arn,
                Message=message
            )
        except ClientError as e:
            logger.error(f"Error publishing to SNS {topic_arn}: {e}")
            raise

    def get_ssm_parameter(self, name: str) -> str:
        """Retrieves a parameter from SSM Parameter Store. Raises ClientError on failure."""
        try:
            response = self.ssm.get_parameter(Name=name, WithDecryption=True)
            return response['Parameter']['Value']
        except ClientError as e:
            logger.error(f"Error getting SSM parameter {name}: {e}")
            raise

    def get_ssm_parameters_by_path(self, path: str) -> List[str]:
        """Retrieves all parameters under a path from SSM Parameter Store. Raises ClientError on failure."""
        try:
            parameters = []
            paginator = self.ssm.get_paginator('get_parameters_by_path')
            page_iterator = paginator.paginate(
                Path=path,
                Recursive=True,
                WithDecryption=True
            )

            for page in page_iterator:
                for param in page.get('Parameters', []):
                    parameters.append(param['Value'])
            
            return parameters
        except ClientError as e:
            logger.error(f"Error getting SSM parameters by path {path}: {e}")
            raise

    def get_s3_object(self, bucket: str, key: str) -> str:
        """Retrieves an object from S3. Raises ClientError on failure."""
        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            logger.error(f"Error getting S3 object {bucket}/{key}: {e}")
            raise

    def get_context_logs(self, log_group: str, log_stream: str, end_time: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves preceding logs for context.
        end_time: The timestamp of the matched event (in milliseconds).
        
        Strategy: Fetch the last 'limit' events before 'end_time' by querying backwards
        from the event timestamp. startFromHead=False ensures we get the most recent events.
        """
        try:
            response = self.logs.get_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                endTime=end_time,
                limit=limit,
                startFromHead=False
            )
            return response.get('events', [])
        except ClientError as e:
            logger.error(f"Error getting logs from {log_group}/{log_stream}: {e}")
            # For context logs, it might be acceptable to return empty list rather than failing the whole process
            # But let's log it clearly.
            return []
