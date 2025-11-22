import unittest
from src.log_processor import LogProcessor

class TestLogProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = LogProcessor()
        self.config = {
            "stream_types": [
                {
                    "type": "api",
                    "pattern": "api-.*",
                    "filters": ["ERROR", "Exception"],
                    "whitelist": ["HealthCheck", "IgnoredError"]
                },
                {
                    "type": "db",
                    "pattern": "db-.*",
                    "filters": ["FATAL"],
                    "whitelist": []
                }
            ]
        }

    def test_match_error(self):
        events = [{'message': 'Something went wrong ERROR'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['config']['type'], 'api')

    def test_whitelist(self):
        events = [{'message': 'This is an ERROR but it is a HealthCheck failure'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 0)

    def test_no_match(self):
        events = [{'message': 'Just info'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 0)

    def test_wrong_stream_type(self):
        # 'db-1' matches 'db' type, which only looks for FATAL
        events = [{'message': 'An ERROR occurred'}]
        matches = self.processor.process_log_batch('group', 'db-1', events, self.config)
        self.assertEqual(len(matches), 0)

        events = [{'message': 'A FATAL error'}]
        matches = self.processor.process_log_batch('group', 'db-1', events, self.config)
        self.assertEqual(len(matches), 1)

    def test_case_insensitive(self):
        events = [{'message': 'error occurred'}]
        matches = self.processor.process_log_batch('group', 'api-1', events, self.config)
        self.assertEqual(len(matches), 1)

if __name__ == '__main__':
    unittest.main()
