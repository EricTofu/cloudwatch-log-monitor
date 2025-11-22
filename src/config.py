import os
import json
import yaml
import logging
from typing import List, Dict, Any, Optional, Union
from src.aws_client import AWSClient

logger = logging.getLogger()

class ConfigLoader:
    _config_cache: Optional[Dict[str, Any]] = None

    def __init__(self, aws_client: Optional[AWSClient] = None):
        self.aws_client = aws_client or AWSClient()

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from the configured source (Env, SSM, or S3)."""
        if ConfigLoader._config_cache:
            return ConfigLoader._config_cache

        config_source = os.environ.get('CONFIG_SOURCE', 'ENV').upper()
        config_data: Optional[Dict[str, Any]] = None

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

        # Validate structure
        if 'stream_types' not in config_data or not isinstance(config_data['stream_types'], list):
             logger.error("Invalid configuration structure: missing 'stream_types' list")
             return {}

        ConfigLoader._config_cache = config_data
        return config_data

    def _parse_content(self, content: str) -> Optional[Dict[str, Any]]:
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
                return None

    def _merge_configs(self, config_contents: List[str]) -> Dict[str, Any]:
        """Merges multiple configuration strings into a single config object."""
        merged_config: Dict[str, List[Any]] = {"stream_types": []}
        
        for content in config_contents:
            parsed = self._parse_content(content)
            if not parsed:
                continue
            
            # If the chunk has 'stream_types', extend the main list
            if isinstance(parsed, dict) and 'stream_types' in parsed and isinstance(parsed['stream_types'], list):
                merged_config['stream_types'].extend(parsed['stream_types'])
            # If the chunk IS a list (YAML list), assume it's a list of stream types
            elif isinstance(parsed, list):
                merged_config['stream_types'].extend(parsed)
            else:
                logger.warning(f"Skipping invalid config chunk structure: {type(parsed)}")
        
        return merged_config
