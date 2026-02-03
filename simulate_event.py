import os
import sys
import json
import gzip
import base64
import logging
from unittest.mock import MagicMock, patch

# Mock environment variables
os.environ['CONFIG_SOURCE'] = 'ENV'
os.environ['STREAM_CONFIG'] = json.dumps({
    "stream_types": [
        {
            "type": "api-server",
            "pattern": "api-.*",
            "filters": ["ERROR", "Exception"],
            "severity": "ERROR",
            "mention": "@channel",
            "whitelist": ["HealthCheck"],
            "sns_topic_arn": "arn:aws:sns:us-east-1:123456789012:chatbot-topic"
        }
    ]
})

# Mock missing dependencies
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()
sys.modules['yaml'] = MagicMock()

# Setup mock for ClientError
class MockClientError(Exception):
    pass
sys.modules['botocore.exceptions'].ClientError = MockClientError

# Import modules to ensure they are loaded before patching
# Now that we mocked boto3 and yaml, these imports should succeed
import src.aws_client
import src.notifications.slack_webhook_provider
from src.lambda_function import lambda_handler

# Mock AWS Client behavior
with patch('src.aws_client.boto3') as mock_boto3:
    # Mock Logs client
    mock_logs = MagicMock()
    mock_sns = MagicMock()
    
    def mock_client(service_name):
        if service_name == 'logs': return mock_logs
        if service_name == 'sns': return mock_sns
        return MagicMock()

    mock_boto3.client.side_effect = mock_client
    
    # Mock get_log_events response (Context logs)
    mock_logs.get_log_events.return_value = {
        'events': [
            {'timestamp': 1600000000000, 'message': '[INFO] Previous log 1'},
            {'timestamp': 1600000001000, 'message': '[INFO] Previous log 2'}
        ]
    }

    # Create a sample event
    log_data = {
        "messageType": "DATA_MESSAGE",
        "owner": "123456789012",
        "logGroup": "/aws/lambda/test-group",
        "logStream": "api-server-12345",
        "subscriptionFilters": ["testFilter"],
        "logEvents": [
            {
                "id": "eventId1",
                "timestamp": 1600000005000,
                "message": "[INFO] Normal operation"
            },
            {
                "id": "eventId2",
                "timestamp": 1600000006000,
                "message": "[ERROR] Something went wrong!"
            },
            {
                "id": "eventId3",
                "timestamp": 1600000007000,
                "message": "[ERROR] Ignore this HealthCheck error"
            }
        ]
    }

    # Compress and encode
    json_data = json.dumps(log_data).encode('utf-8')
    compressed_data = gzip.compress(json_data)
    b64_data = base64.b64encode(compressed_data).decode('utf-8')

    event = {'awslogs': {'data': b64_data}}

    print("Running Lambda Handler Simulation...")
    try:
        lambda_handler(event, None)
        print("\nSimulation Complete.")
    except Exception as e:
        print(f"\nSimulation Failed with error: {e}")

    # Verify SNS call
    if mock_sns.publish.called:
        print("\nSNS Notification Sent!")
        args, kwargs = mock_sns.publish.call_args
        print(f"Topic: {kwargs.get('TopicArn')}")
        payload = json.loads(kwargs.get('Message', '{}'))
        print(json.dumps(payload, indent=2))
    else:
        print("\nNo SNS Notification Sent.")
