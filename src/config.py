import os
import json
import yaml
import logging
from src.aws_client import AWSClient

logger = logging.getLogger()

class ConfigLoader:
    _config_cache = None

    def __init__(self, aws_client=None):
        self.aws_client = aws_client or AWSClient()

    def load_config(self):
        """Loads configuration from the configured source (Env, SSM, or S3)."""
        if ConfigLoader._config_cache:
            return ConfigLoader._config_cache

        config_source = os.environ.get('CONFIG_SOURCE', 'ENV').upper()
        config_data = None

        logger.info(f"Loading configuration from {config_source}")

        if config_source == 'SSM':
            param_name = os.environ.get('SSM_PARAMETER_NAME')
            if not param_name:
                raise ValueError("SSM_PARAMETER_NAME environment variable is required for SSM config source")
            
            if param_name.endswith('/'):
                # It's a path, fetch all parameters under it
                logger.info(f"Fetching configuration from SSM path: {param_name}")
                param_values = self.aws_client.get_ssm_parameters_by_path(param_name)
                config_data = self._merge_configs(param_values)
            else:
                # It's a single parameter
                config_content = self.aws_client.get_ssm_parameter(param_name)
                if config_content:
                    config_data = self._parse_content(config_content)

        elif config_source == 'S3':
            bucket = os.environ.get('S3_BUCKET')
            key = os.environ.get('S3_KEY')
            if not bucket or not key:
                raise ValueError("S3_BUCKET and S3_KEY environment variables are required for S3 config source")
            config_content = self.aws_client.get_s3_object(bucket, key)
            if config_content:
                config_data = self._parse_content(config_content)

        else: # Default to ENV
            # Expecting a JSON string in STREAM_CONFIG env var
            config_content = os.environ.get('STREAM_CONFIG')
            if config_content:
                config_data = self._parse_content(config_content)
            else:
                logger.warning("STREAM_CONFIG environment variable is empty")

        if not config_data:
            logger.error("Failed to load configuration or configuration is empty")
            return {}

        ConfigLoader._config_cache = config_data
        return config_data

    def _parse_content(self, content):
        """Parses JSON or YAML content."""
        try:
            # Try JSON first
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                # Try YAML
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse config content: {e}")
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse config content: {e}")
                return None

    def _merge_configs(self, config_contents):
        """Merges multiple configuration strings into a single config object."""
        merged_config = {"stream_types": []}
        
        for content in config_contents:
            parsed = self._parse_content(content)
            if not parsed:
                continue
            
            # If the chunk has 'stream_types', extend the main list
            if 'stream_types' in parsed:
                merged_config['stream_types'].extend(parsed['stream_types'])
            # If the chunk IS a list (YAML list), assume it's a list of stream types
            elif isinstance(parsed, list):
                merged_config['stream_types'].extend(parsed)
            # If it's a single dict but not wrapped in stream_types, maybe add it?
            # Let's stick to the structure: {stream_types: [...]} or just [...]
        
        return merged_config
