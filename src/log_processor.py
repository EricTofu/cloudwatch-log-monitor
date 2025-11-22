import re
import logging

logger = logging.getLogger()

class LogProcessor:
    def process_log_batch(self, log_group, log_stream, log_events, config):
        """
        Processes a batch of log events.
        Returns a list of matched events with their stream configuration.
        """
        matches = []
        
        stream_config = self._get_stream_config(log_stream, config)
        if not stream_config:
            logger.info(f"No configuration found for log stream: {log_stream}")
            return matches

        logger.info(f"Processing {len(log_events)} events for stream {log_stream} (Type: {stream_config.get('type')})")

        for event in log_events:
            message = event.get('message', '')
            
            if self._is_match(message, stream_config):
                matches.append({
                    'event': event,
                    'config': stream_config
                })

        return matches

    def _get_stream_config(self, log_stream, config):
        """Finds the matching configuration for a log stream."""
        stream_types = config.get('stream_types', [])
        
        for st_config in stream_types:
            pattern = st_config.get('pattern')
            if pattern and re.search(pattern, log_stream):
                return st_config
        
        return None

    def _is_match(self, message, stream_config):
        """Checks if a message matches filters and does not match whitelist."""
        filters = stream_config.get('filters', [])
        whitelist = stream_config.get('whitelist', [])

        # Check if message matches any filter keyword (case-insensitive)
        is_filtered = False
        for keyword in filters:
            if keyword.lower() in message.lower():
                is_filtered = True
                break
        
        if not is_filtered:
            return False

        # Check if message matches any whitelist pattern (regex)
        for pattern in whitelist:
            try:
                if re.search(pattern, message, re.IGNORECASE):
                    return False # Whitelisted, so ignore
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                continue

        return True
