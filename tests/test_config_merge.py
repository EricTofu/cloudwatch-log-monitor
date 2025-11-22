import unittest
import json
import sys
from unittest.mock import MagicMock
from src.config import ConfigLoader

# Check if yaml is mocked
is_yaml_mocked = isinstance(sys.modules.get('yaml'), MagicMock)

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
        # If yaml is mocked, we need to configure it to return expected data
        if is_yaml_mocked:
            import yaml
            # Define side effect to return dict based on input
            def safe_load_side_effect(content):
                if "type: api" in content:
                    return {"stream_types": [{"type": "api", "pattern": "api.*"}]}
                if "type: db" in content:
                    return {"stream_types": [{"type": "db", "pattern": "db.*"}]}
                return None
            
            yaml.safe_load.side_effect = safe_load_side_effect

        merged = self.loader._merge_configs([chunk1, chunk2])
        self.assertEqual(len(merged['stream_types']), 2)

    def test_mixed_content(self):
        # One valid, one invalid
        chunk1 = json.dumps({"stream_types": [{"type": "valid"}]})
        chunk2 = "INVALID_JSON_OR_YAML"
        
        # If yaml is mocked, safe_load might return a Mock for invalid input, which _merge_configs might log as invalid structure
        # We want it to return None or raise YAMLError
        if is_yaml_mocked:
            import yaml
            # Reset side effect for this test or handle it
            # If we set side effect in previous test, it persists?
            # Yes, if it's the same mock object.
            # Let's ensure it raises YAMLError or returns None for invalid input
            original_side_effect = yaml.safe_load.side_effect
            
            def mixed_side_effect(content):
                if content == chunk2:
                    # Simulate YAMLError
                    raise yaml.YAMLError("Invalid YAML")
                return original_side_effect(content) if original_side_effect else None

            yaml.safe_load.side_effect = mixed_side_effect

        merged = self.loader._merge_configs([chunk1, chunk2])
        self.assertEqual(len(merged['stream_types']), 1)
        self.assertEqual(merged['stream_types'][0]['type'], 'valid')

if __name__ == '__main__':
    unittest.main()
