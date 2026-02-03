import unittest
from unittest.mock import Mock, patch, MagicMock
from src.notifications.slack_webhook_provider import SlackWebhookProvider

class TestSlackWebhookProvider(unittest.TestCase):
    def setUp(self):
        self.provider = SlackWebhookProvider()
        self.notification_data = {
            'log_group': '/aws/lambda/test',
            'log_stream': 'api-server-123',
            'log_stream_type': 'api',
            'matched_event': {
                'timestamp': 1600000000000,
                'message': '[ERROR] Test error'
            },
            'context_events': [
                {'timestamp': 1599999990000, 'message': '[INFO] Context 1'},
                {'timestamp': 1599999995000, 'message': '[INFO] Context 2'}
            ]
        }

    @patch('src.notifications.slack_webhook_provider.requests.post')
    def test_send_notification_success(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        
        result = self.provider.send_notification('https://hooks.slack.com/test', self.notification_data)
        
        self.assertTrue(result)
        self.assertTrue(mock_post.called)
        
    @patch('src.notifications.slack_webhook_provider.requests.post')
    def test_send_notification_failure(self, mock_post):
        mock_post.return_value = Mock(status_code=500, text='Server Error')
        
        result = self.provider.send_notification('https://hooks.slack.com/test', self.notification_data)
        
        self.assertFalse(result)

    def test_send_notification_no_url(self):
        result = self.provider.send_notification('', self.notification_data)
        self.assertFalse(result)

    def test_build_payload(self):
        payload = self.provider._build_payload(self.notification_data)
        
        self.assertIn('blocks', payload)
        self.assertIsInstance(payload['blocks'], list)
        self.assertGreater(len(payload['blocks']), 0)

    def test_build_payload_with_severity_and_mention(self):
        self.notification_data['severity'] = 'ERROR'
        self.notification_data['mention'] = '<@channel>'
        
        payload = self.provider._build_payload(self.notification_data)
        
        blocks = payload['blocks']
        
        # Check mention block
        mention_block = next((b for b in blocks if b['type'] == 'section' and '<@channel>' in b['text']['text']), None)
        self.assertIsNotNone(mention_block)
        
        # Check header emoji
        header_block = next((b for b in blocks if b['type'] == 'header'), None)
        self.assertIsNotNone(header_block)
        self.assertIn(':red_circle:', header_block['text']['text'])

if __name__ == '__main__':
    unittest.main()
