import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger()

from src.notifications import NotificationProvider

class SlackWebhookProvider(NotificationProvider):
    def send_notification(self, webhook_url: str, notification_data: Dict[str, Any]) -> bool:
        """Sends a formatted notification to Slack."""
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

    def _build_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Builds the Slack Block Kit payload."""
        log_group = data.get('log_group')
        log_stream = data.get('log_stream')
        stream_type = data.get('log_stream_type')
        matched_event = data.get('matched_event', {})
        context_events = data.get('context_events', [])
        aws_region = data.get('aws_region', 'us-east-1')

        # Format timestamp
        ts = matched_event.get('timestamp', 0) / 1000
        time_str = matched_event.get('timestamp_jst')
        if not time_str:
            time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            time_str += " (JST)"

        # Generate CloudWatch Logs URL (compact format)
        # URL encode the log group and stream names
        import urllib.parse
        encoded_log_group = urllib.parse.quote(log_group, safe='')
        encoded_log_stream = urllib.parse.quote(log_stream, safe='')
        
        # Use compact URL format
        cloudwatch_url = (
            f"https://console.aws.amazon.com/cloudwatch/home?"
            f"region={aws_region}#logsV2:log-groups/log-group/{encoded_log_group}/"
            f"log-events/{encoded_log_stream}"
        )

        severity = data.get('severity')
        mention = data.get('mention')
        
        # Map severity to emoji
        emoji = ":rotating_light:"
        if severity:
            severity_map = {
                "CRITICAL": ":rotating_light:",
                "ERROR": ":red_circle:",
                "WARNING": ":warning:",
                "INFO": ":information_source:",
                "DEBUG": ":mag:"
            }
            emoji = severity_map.get(severity.upper(), ":rotating_light:")

        blocks = []
        
        if mention:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": mention
                }
            })

        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Log Alert: {stream_type}",
                "emoji": True
            }
        })
        blocks.append({
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
        })
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Time:*\n{time_str}"
                }
            ]
        })
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<{cloudwatch_url}|:mag: View in CloudWatch Logs>"
            }
        })
        blocks.append({
            "type": "divider"
        })
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Matched Log Event:*"
            }
        })
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{matched_event.get('message', '')}```"
            }
        })

        if context_events:
            context_text = ""
            for event in context_events:
                # Format each context line
                evt_ts = event.get('timestamp_jst')
                if not evt_ts:
                    evt_ts = datetime.fromtimestamp(event.get('timestamp', 0) / 1000).strftime('%H:%M:%S')
                
                context_text += f"[{evt_ts}] {event.get('message', '')}\n"
            
            # Truncate if too long (Slack block limit is 3000 chars)
            if len(context_text) > 2900:
                context_text = "... (truncated)\n" + context_text[-2900:]

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Context (Preceding Logs):*"
                }
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{context_text}```"
                }
            })

        return {"blocks": blocks}

