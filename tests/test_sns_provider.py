import unittest
from unittest.mock import Mock, MagicMock
from src.notifications.sns_provider import SNSProvider

class TestSNSProvider(unittest.TestCase):
    def setUp(self):
        self.mock_aws_client = Mock()
        self.provider = SNSProvider(self.mock_aws_client)
        self.notification_data = {
            'log_group': '/aws/lambda/test',
            'log_stream': 'api-server-123',
            'log_stream_type': 'api',
            'matched_event': {
                'timestamp': 1600000000000,
                'message': '[ERROR] Test error'
            },
            'context_events': [
                {'timestamp': 1599999990000, 'message': '[INFO] Context 1'}
            ]
        }

    def test_send_notification_success(self):
        self.mock_aws_client.publish_sns_message.return_value = None
        
        # Should not raise
        self.provider.send_notification('arn:aws:sns:us-east-1:123456789012:test', self.notification_data)
        
        self.assertTrue(self.mock_aws_client.publish_sns_message.called)

    def test_send_notification_no_arn(self):
        with self.assertRaises(ValueError):
            self.provider.send_notification('', self.notification_data)

    def test_build_chatbot_payload(self):
        payload = self.provider._build_chatbot_payload(self.notification_data)
        
        self.assertEqual(payload['version'], '1.0')
        self.assertEqual(payload['source'], 'custom')
        self.assertIn('content', payload)
        self.assertIn('title', payload['content'])
        self.assertIn('description', payload['content'])

if __name__ == '__main__':
    unittest.main()
