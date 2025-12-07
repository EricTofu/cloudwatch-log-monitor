import unittest
from unittest.mock import MagicMock, patch
import json
import logging
import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import ConfigLoader
from src.notifications.slack_webhook_provider import SlackWebhookProvider
from src.notifications.sns_provider import SNSProvider
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)

class TestVerification(unittest.TestCase):

    def setUp(self):
        self.mock_aws_client = MagicMock()
        self.config_loader = ConfigLoader(self.mock_aws_client)
        
        # Reset config cache
        ConfigLoader._config_cache = None
        ConfigLoader._cache_timestamp = 0

    def test_cache_strategy_ttl(self):
        print("\nTesting TTL Cache Strategy...")
        os.environ['CONFIG_SOURCE'] = 'S3'
        os.environ['S3_BUCKET'] = 'test-bucket'
        os.environ['S3_KEY'] = 'config.json'

        # 1. Initial Load - Should fetch content
        self.mock_aws_client.get_s3_object.return_value = '{"stream_types": []}'
        
        config = self.config_loader.load_config()
        self.assertIsNotNone(config)
        self.mock_aws_client.get_s3_object.assert_called_with('test-bucket', 'config.json')
        
        # Reset mock
        self.mock_aws_client.get_s3_object.reset_mock()

        # 2. Immediate Second Load - Should be cached
        print("  Testing Cached Load...")
        config2 = self.config_loader.load_config()
        self.assertIs(config, config2) # Same object
        self.mock_aws_client.get_s3_object.assert_not_called()

        # 3. Load after TTL expiry
        print("  Testing Expired Cache Load...")
        # Artificially age the cache
        ConfigLoader._cache_timestamp = time.time() - 301 # 5 minutes + 1s ago
        
        config3 = self.config_loader.load_config()
        # Should be a new fetch
        self.mock_aws_client.get_s3_object.assert_called_once()
        
    def test_log_truncation_slack(self):
        print("\nTesting Slack Log Truncation...")
        provider = SlackWebhookProvider()
        
        # Create a context string longer than 2900 chars
        # 30 lines of 100 chars = 3000 chars
        long_context = []
        for i in range(30):
            long_context.append({
                'timestamp_jst': '2023-01-01 12:00:00',
                'message': f"Line {i}: " + "x" * 90
            })
            
        data = {
            'log_group': 'test-group',
            'log_stream': 'test-stream',
            'context_events': long_context
        }
        
        payload = provider._build_payload(data)
        context_block = payload['blocks'][-1]['text']['text']
        
        # Should start with truncated message and end with the last line
        print(f"  Context start: {context_block[:50]}...")
        print(f"  Context end: ...{context_block[-50:]}")
        
        self.assertTrue(context_block.startswith("```... (truncated)\n"))
        self.assertTrue("Line 29" in context_block)
        self.assertFalse("Line 0" in context_block) # Oldest should be gone

    def test_log_truncation_sns(self):
        print("\nTesting SNS Log Truncation...")
        provider = SNSProvider(self.mock_aws_client)
        
        # Create a context string longer than 2000 chars
        long_context = []
        for i in range(25):
            long_context.append({
                'timestamp_jst': '2023-01-01 12:00:00',
                'message': f"Line {i}: " + "x" * 90
            })
            
        data = {
            'log_group': 'test-group',
            'log_stream': 'test-stream',
            'context_events': long_context
        }
        
        payload = provider._build_chatbot_payload(data)
        description = payload['content']['description']
        
        # Extract context part
        context_text = description.split('*Context:*\n```\n')[1].rstrip('```')
        
        print(f"  Context start: {context_text[:50]}...")
        print(f"  Context end: ...{context_text[-50:]}")
        
        self.assertTrue(context_text.startswith("... (truncated)\n"))
        self.assertTrue("Line 24" in context_text)
        self.assertFalse("Line 0" in context_text)

if __name__ == '__main__':
    unittest.main()
