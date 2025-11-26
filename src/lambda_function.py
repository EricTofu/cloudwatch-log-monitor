import json
import gzip
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

JST = timezone(timedelta(hours=9))
from src.config import ConfigLoader
from src.aws_client import AWSClient
from src.notifications.slack_webhook_provider import SlackWebhookProvider
from src.notifications.sns_provider import SNSProvider
from src.log_processor import LogProcessor

# Configure logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]
logger.setLevel(logging.INFO)

# Initialize components (outside handler for reuse)
aws_client = AWSClient()
config_loader = ConfigLoader(aws_client)
log_processor = LogProcessor()

# Initialize Providers
slack_provider = SlackWebhookProvider()
sns_provider = SNSProvider(aws_client)

def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    """
    Main Lambda entry point.
    """
    try:
        # 1. Decode and decompress log data
        cw_data = event['awslogs']['data']
        compressed_payload = base64.b64decode(cw_data)
        uncompressed_payload = gzip.decompress(compressed_payload)
        payload = json.loads(uncompressed_payload)

        log_group = payload['logGroup']
        log_stream = payload['logStream']
        log_events = payload['logEvents']

        logger.info(f"Received {len(log_events)} events from {log_group}/{log_stream}")

        # 2. Load Configuration
        try:
            config = config_loader.load_config()
        except Exception as e:
            logger.error(f"Configuration load failed: {e}")
            return

        if not config:
            logger.error("Configuration is empty, aborting.")
            return

        # 3. Process Logs
        matches = log_processor.process_log_batch(log_group, log_stream, log_events, config)
        
        if not matches:
            logger.info("No matching events found.")
            return

        logger.info(f"Found {len(matches)} matching events.")

        # 4. Handle Matches
        for match in matches:
            matched_event = match['event']
            stream_config = match['config']
            
            # Fetch context
            context_logs = aws_client.get_context_logs(
                log_group, 
                log_stream, 
                matched_event['timestamp']
            )

            # Convert timestamps to JST
            def to_jst_str(timestamp_ms):
                dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                return dt.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S')

            matched_event_jst = matched_event.copy()
            matched_event_jst['timestamp_jst'] = to_jst_str(matched_event['timestamp'])
            
            context_logs_jst = []
            for log in context_logs:
                log_copy = log.copy()
                log_copy['timestamp_jst'] = to_jst_str(log['timestamp'])
                context_logs_jst.append(log_copy)

            # Prepare notification data
            notification_data = {
                'log_group': log_group,
                'log_stream': log_stream,
                'log_stream_type': stream_config.get('type', 'Unknown'),
                'matched_event': matched_event_jst,
                'context_events': context_logs_jst
            }

            # Send notification
            sns_topic_arn = stream_config.get('sns_topic_arn')
            webhook_url = stream_config.get('slack_webhook_url')

            try:
                if sns_topic_arn:
                    logger.info(f"Sending notification via SNS to {sns_topic_arn}")
                    sns_provider.send_notification(sns_topic_arn, notification_data)
                elif webhook_url:
                    logger.info("Sending notification via Slack Webhook")
                    slack_provider.send_notification(webhook_url, notification_data)
                else:
                    logger.warning(f"No notification target configured for stream type {stream_config.get('type')}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    except Exception as e:
        logger.error(f"Error processing logs: {e}", exc_info=True)
        raise e
