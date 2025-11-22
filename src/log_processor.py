import re
import logging
from typing import List, Dict, Any, Optional, Pattern

logger = logging.getLogger()

class LogProcessor:
    def __init__(self):
        self._pattern_cache: Dict[str, Pattern] = {}

    def process_log_batch(self, log_group: str, log_stream: str, log_events: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes a batch of log events.
        Returns a list of matched events with their stream configuration.
        """
        matches: List[Dict[str, Any]] = []
        
        stream_config = self._get_stream_config(log_stream, config)
        if not stream_config:
            logger.info(f"No configuration found for log stream: {log_stream}")
            return matches

        logger.info(f"Processing {len(log_events)} events for stream {log_stream} (Type: {stream_config.get('type')})")

        # Pre-compile whitelist patterns for this stream config
        whitelist_patterns = self._compile_patterns(stream_config.get('whitelist', []))

        for event in log_events:
            message = event.get('message', '')
            
            if self._is_match(message, stream_config, whitelist_patterns):
                matches.append({
                    'event': event,
                    'config': stream_config
                })

        return matches

    def _get_stream_config(self, log_stream: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Finds the matching configuration for a log stream."""
        stream_types = config.get('stream_types', [])
        
        for st_config in stream_types:
            pattern_str = st_config.get('pattern')
            if not pattern_str:
                continue
                
            # Cache the compiled pattern for the stream type
            if pattern_str not in self._pattern_cache:
                try:
                    self._pattern_cache[pattern_str] = re.compile(pattern_str)
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{pattern_str}': {e}")
                    continue
            
            if self._pattern_cache[pattern_str].search(log_stream):
                return st_config
        
        return None

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

    def _is_match(self, message: str, stream_config: Dict[str, Any], whitelist_patterns: List[Pattern]) -> bool:
        """Checks if a message matches filters and does not match whitelist."""
        filters = stream_config.get('filters', [])

        # Check if message matches any filter keyword (case-insensitive)
        # Note: Filters are simple keywords, not regex, per original implementation.
        # If they were regex, we should compile them too. 
        # Requirement 4 says "filter keywords", implying substrings.
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
