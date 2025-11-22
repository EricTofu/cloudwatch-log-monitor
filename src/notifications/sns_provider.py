import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from src.notifications import NotificationProvider
from src.aws_client import AWSClient

logger = logging.getLogger()

class SNSProvider(NotificationProvider):
    def __init__(self, aws_client: Optional[AWSClient] = None) -> None:
        self.aws_client = aws_client or AWSClient()

    def send_notification(self, target_arn: str, data: Dict[str, Any]) -> None:
        """
        Sends an AWS Chatbot compatible message to SNS.
        Raises ClientError on failure.
        """
        if not target_arn:
            logger.error("No SNS Topic ARN provided")
            raise ValueError("No SNS Topic ARN provided")

        message = self._build_chatbot_payload(data)
        self.aws_client.publish_sns_message(target_arn, json.dumps(message))

    def _build_chatbot_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Builds the AWS Chatbot Custom Notification payload."""
        log_group = data.get('log_group')
        log_stream = data.get('log_stream')
        stream_type = data.get('log_stream_type')
        matched_event = data.get('matched_event', {})
        context_events = data.get('context_events', [])

        ts = matched_event.get('timestamp', 0) / 1000
        time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Markdown content for Chatbot
        description = f"**Log Group:** {log_group}\n**Log Stream:** {log_stream}\n**Time:** {time_str}\n\n"
        description += f"**Matched Event:**\n```\n{matched_event.get('message', '')}\n```\n\n"

        if context_events:
            context_text = ""
            for event in context_events:
                evt_ts = datetime.fromtimestamp(event.get('timestamp', 0) / 1000).strftime('%H:%M:%S')
                context_text += f"[{evt_ts}] {event.get('message', '')}\n"
            
            if len(context_text) > 2000:
                context_text = context_text[:2000] + "\n... (truncated)"
            
            description += f"**Context:**\n```\n{context_text}\n```"

        return {
            "version": "1.0",
            "source": "custom",
            "content": {
                "textType": "client-markdown",
                "title": f":rotating_light: Log Alert: {stream_type}",
                "description": description
            }
        }
