import json
import logging
from datetime import datetime

logger = logging.getLogger()

from src.notifications import NotificationProvider

class SlackWebhookProvider(NotificationProvider):
    def send_notification(self, webhook_url, notification_data):
        """Sends a formatted notification to Slack."""
        try:
            import requests
        except ImportError:
            logger.error("The 'requests' library is required for Slack notifications but is not installed.")
            return False

        if not webhook_url:
            logger.error("No Slack webhook URL provided")
            return False

        payload = self._build_payload(notification_data)
        
        try:
            response = requests.post(
                webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            if response.status_code != 200:
                logger.error(f"Failed to send Slack notification: {response.status_code} {response.text}")
                return False
            return True
        except requests.RequestException as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def _build_payload(self, data):
        """Builds the Slack Block Kit payload."""
        log_group = data.get('log_group')
        log_stream = data.get('log_stream')
        stream_type = data.get('log_stream_type')
        matched_event = data.get('matched_event', {})
        context_events = data.get('context_events', [])

        # Format timestamp
        ts = matched_event.get('timestamp', 0) / 1000
        time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S UTC')

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":rotating_light: Log Alert: {stream_type}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Log Group:*\n{log_group}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Log Stream:*\n{log_stream}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{time_str}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Matched Log Event:*\n```{matched_event.get('message', '')}```"
                }
            }
        ]

        if context_events:
            context_text = ""
            for event in context_events:
                # Format each context line
                evt_ts = datetime.fromtimestamp(event.get('timestamp', 0) / 1000).strftime('%H:%M:%S')
                context_text += f"[{evt_ts}] {event.get('message', '')}\n"
            
            # Truncate if too long (Slack block limit is 3000 chars)
            if len(context_text) > 2900:
                context_text = context_text[:2900] + "\n... (truncated)"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Context (Preceding Logs):*\n```{context_text}```"
                }
            })

        return {"blocks": blocks}
