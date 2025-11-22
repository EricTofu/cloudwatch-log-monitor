import unittest
import json
from unittest.mock import MagicMock
from src.config import ConfigLoader

class TestConfigMerge(unittest.TestCase):
    def setUp(self):
        # Mock AWSClient to avoid Boto3 region errors
        self.mock_aws = MagicMock()
        self.loader = ConfigLoader(aws_client=self.mock_aws)

    def test_merge_json_chunks(self):
        chunk1 = json.dumps({
            "stream_types": [{"type": "api", "pattern": "api.*"}]
        })
        chunk2 = json.dumps({
            "stream_types": [{"type": "db", "pattern": "db.*"}]
        })
        
        merged = self.loader._merge_configs([chunk1, chunk2])
        self.assertEqual(len(merged['stream_types']), 2)
        types = [s['type'] for s in merged['stream_types']]
        self.assertIn('api', types)
        self.assertIn('db', types)

    def test_merge_yaml_lists(self):
        chunk1 = """
stream_types:
  - type: api
    pattern: api.*
"""
        chunk2 = """
stream_types:
  - type: db
    pattern: db.*
"""
        merged = self.loader._merge_configs([chunk1, chunk2])
        self.assertEqual(len(merged['stream_types']), 2)

    def test_mixed_content(self):
        # One valid, one invalid
        chunk1 = json.dumps({"stream_types": [{"type": "valid"}]})
        chunk2 = "INVALID_JSON_OR_YAML"
        
        merged = self.loader._merge_configs([chunk1, chunk2])
        self.assertEqual(len(merged['stream_types']), 1)
        self.assertEqual(merged['stream_types'][0]['type'], 'valid')

if __name__ == '__main__':
    unittest.main()
