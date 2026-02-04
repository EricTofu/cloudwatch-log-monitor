import re
import logging
from typing import List, Dict, Any, Optional, Pattern

logger = logging.getLogger()

class LogProcessor:
    def __init__(self) -> None:
        self._pattern_cache: Dict[str, Pattern] = {}

    def process_log_batch(self, log_group: str, log_stream: str, log_events: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes a batch of log events.
        Returns a list of matched events with their stream configuration.
        """
        matches: List[Dict[str, Any]] = []
        
        matching_configs = self._get_matching_configs(log_group, log_stream, config)
        if not matching_configs:
            logger.info(f"No configuration found for log stream: {log_stream} in group: {log_group}")
            return matches

        logger.info(f"Processing {len(log_events)} events for stream {log_stream} ({len(matching_configs)} matching configs)")

        # Pre-compile whitelist patterns and filters for each matching config
        prepared_configs = []
        for st_config in matching_configs:
            prepared_configs.append({
                'config': st_config,
                'whitelist_patterns': self._compile_patterns(st_config.get('whitelist', [])),
                'filters': st_config.get('filters', [])
            })

        for event in log_events:
            message = event.get('message', '')
            
            # Check against each matching configuration in order
            for prepared in prepared_configs:
                if self._is_match(message, prepared['filters'], prepared['whitelist_patterns']):
                    matches.append({
                        'event': event,
                        'config': prepared['config']
                    })
                    break # Stop at first matching configuration for this event

        return matches

    def _get_matching_configs(self, log_group: str, log_stream: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Finds all matching configurations for a log stream."""
        stream_types = config.get('stream_types', [])
        matches = []
        
        for st_config in stream_types:
            # Check log group pattern if present
            log_group_pattern = st_config.get('log_group_pattern')
            if log_group_pattern:
                if log_group_pattern not in self._pattern_cache:
                    try:
                        self._pattern_cache[log_group_pattern] = re.compile(log_group_pattern)
                    except re.error as e:
                        logger.error(f"Invalid regex pattern '{log_group_pattern}': {e}")
                        continue
                
                if not self._pattern_cache[log_group_pattern].search(log_group):
                    continue

            pattern_str = st_config.get('pattern')
            if pattern_str:
                # Cache the compiled pattern for the stream type
                if pattern_str not in self._pattern_cache:
                    try:
                        self._pattern_cache[pattern_str] = re.compile(pattern_str)
                    except re.error as e:
                        logger.error(f"Invalid regex pattern '{pattern_str}': {e}")
                        continue
                
                if not self._pattern_cache[pattern_str].search(log_stream):
                    continue
            elif not log_group_pattern:
                # If neither pattern nor log_group_pattern is specified, skip to avoid matching everything by accident
                continue
            
            matches.append(st_config)
        
        return matches

    def _compile_patterns(self, patterns: List[str]) -> List[Pattern]:
        """Compiles a list of regex strings into pattern objects."""
        compiled = []
        for p in patterns:
            if p not in self._pattern_cache:
                try:
                    self._pattern_cache[p] = re.compile(p, re.IGNORECASE)
                except re.error as e:
                    logger.error(f"Invalid whitelist regex pattern '{p}': {e}")
                    continue
            compiled.append(self._pattern_cache[p])
        return compiled

    def _is_match(self, message: str, filters: List[str], whitelist_patterns: List[Pattern]) -> bool:
        """Checks if a message matches filters and does not match whitelist."""
        # Check if message matches any filter keyword (case-insensitive)
        is_filtered = False
        message_lower = message.lower()
        
        for keyword in filters:
            if keyword.lower() in message_lower:
                is_filtered = True
                break
        
        if not is_filtered:
            return False

        # Check if message matches any whitelist pattern (regex)
        for pattern in whitelist_patterns:
            if pattern.search(message):
                return False # Whitelisted, so ignore

        return True
