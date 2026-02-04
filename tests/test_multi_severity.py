import unittest
from src.log_processor import LogProcessor

class TestMultiSeverity(unittest.TestCase):
    def setUp(self):
        self.processor = LogProcessor()
        self.config = {
            "stream_types": [
                {
                    "type": "api-critical",
                    "pattern": "api-.*",
                    "filters": ["CRITICAL"],
                    "severity": "CRITICAL"
                },
                {
                    "type": "api-error",
                    "pattern": "api-.*",
                    "filters": ["ERROR"],
                    "severity": "ERROR"
                }
            ]
        }

    def test_multi_severity_match(self):
        # 1. Test CRITICAL match (should match first config)
        events = [{'message': 'Something CRITICAL happened'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['config']['severity'], 'CRITICAL')
        self.assertEqual(matches[0]['config']['type'], 'api-critical')

        # 2. Test ERROR match (should match second config because first doesn't match filter)
        events = [{'message': 'An ERROR occurred'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['config']['severity'], 'ERROR')
        self.assertEqual(matches[0]['config']['type'], 'api-error')

        # 3. Test both in one batch (should match appropriate configs for each)
        events = [
            {'message': 'Something CRITICAL happened', 'id': 'e1'},
            {'message': 'An ERROR occurred', 'id': 'e2'}
        ]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 2)
        
        # Order should follow log event order
        self.assertEqual(matches[0]['config']['severity'], 'CRITICAL')
        self.assertEqual(matches[1]['config']['severity'], 'ERROR')

    def test_priority_order(self):
        # If both patterns match filters, first config wins
        events = [{'message': 'CRITICAL ERROR'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['config']['severity'], 'CRITICAL')

if __name__ == '__main__':
    unittest.main()
