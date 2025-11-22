import json
import gzip
import base64
import logging
from src.config import ConfigLoader
from src.aws_client import AWSClient
from src.notifications.slack_webhook_provider import SlackWebhookProvider
from src.notifications.sns_provider import SNSProvider
from src.log_processor import LogProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize components (outside handler for reuse)
aws_client = AWSClient()
config_loader = ConfigLoader(aws_client)
log_processor = LogProcessor()

# Initialize Providers
slack_provider = SlackWebhookProvider()
sns_provider = SNSProvider(aws_client)

def lambda_handler(event, context):
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
        config = config_loader.load_config()
        if not config:
            logger.error("Configuration load failed, aborting.")
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

            # Prepare notification data
            notification_data = {
                'log_group': log_group,
                'log_stream': log_stream,
                'log_stream_type': stream_config.get('type', 'Unknown'),
                'matched_event': matched_event,
                'context_events': context_logs
            }

            # Send notification
            sns_topic_arn = stream_config.get('sns_topic_arn')
            webhook_url = stream_config.get('slack_webhook_url')

            if sns_topic_arn:
                logger.info(f"Sending notification via SNS to {sns_topic_arn}")
                sns_provider.send_notification(sns_topic_arn, notification_data)
            elif webhook_url:
                logger.info("Sending notification via Slack Webhook")
                slack_provider.send_notification(webhook_url, notification_data)
            else:
                logger.warning(f"No notification target configured for stream type {stream_config.get('type')}")

    except Exception as e:
        logger.error(f"Error processing logs: {e}", exc_info=True)
        raise e
