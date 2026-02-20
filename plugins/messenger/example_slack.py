"""Example Slack messenger plugin implementation.

This plugin demonstrates how to implement the BaseMessenger interface
for sending messages and alerts via Slack Bolt. It can be used as a
template for creating other messenger plugins.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from core.base import BaseMessenger

logger = logging.getLogger(__name__)


class ExampleSlack(BaseMessenger):
    """Slack implementation of BaseMessenger.
    
    Uses Slack Web API to send messages and alerts to Slack channels.
    This plugin is automatically discovered and loaded when placed in
    the plugins/messenger/ directory.
    """

    def __init__(self, bot_token: Optional[str] = None, default_channel: Optional[str] = None):
        """Initialize the Slack messenger plugin.
        
        Args:
            bot_token: Slack bot token (defaults to SLACK_BOT_TOKEN env var)
            default_channel: Default channel (defaults to SLACK_DEFAULT_CHANNEL env var)
        """
        token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        if not token:
            raise ValueError("SLACK_BOT_TOKEN environment variable is required")

        self.client = WebClient(token=token)
        self.default_channel = default_channel or os.getenv("SLACK_DEFAULT_CHANNEL", "#incidents")

    @property
    def name(self) -> str:
        """Return the plugin name."""
        return "slack"

    def send_message(
        self,
        channel: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a Slack channel."""
        try:
            if not channel.startswith("#") and not channel.startswith("C"):
                channel = f"#{channel}"

            payload = {
                "channel": channel,
                "text": message,
            }

            if metadata:
                if "thread_ts" in metadata:
                    payload["thread_ts"] = metadata["thread_ts"]
                if "blocks" in metadata:
                    payload["blocks"] = metadata["blocks"]

            response = self.client.chat_postMessage(**payload)

            return {
                "message_id": response["ts"],
                "status": "sent",
                "timestamp": datetime.utcnow().isoformat(),
                "channel": response["channel"],
            }
        except SlackApiError as e:
            logger.error(f"Slack API error: {str(e)}")
            return {
                "message_id": None,
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error sending Slack message: {str(e)}", exc_info=True)
            return {
                "message_id": None,
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def send_alert(
        self,
        severity: str,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send an alert/incident notification to Slack."""
        try:
            channel = (metadata or {}).get("channel", self.default_channel)
            if not channel:
                raise ValueError("No channel specified and no default channel set")

            severity_colors = {
                "critical": "#FF0000",
                "high": "#FF6B00",
                "medium": "#FFA500",
                "low": "#FFD700",
                "info": "#36A2EB",
            }
            color = (metadata or {}).get("color", severity_colors.get(severity.lower(), "#808080"))

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {title}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{severity.upper()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{description}",
                    },
                },
            ]

            if metadata and "incident_id" in metadata:
                blocks.append({
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n{metadata['incident_id']}",
                        },
                    ],
                })

            if metadata and "links" in metadata and metadata["links"]:
                link_text = "\n".join([f"• <{link}|{link}>" for link in metadata["links"]])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Related Links:*\n{link_text}",
                    },
                })

            blocks.append({"type": "divider"})

            response = self.client.chat_postMessage(
                channel=channel,
                text=f"Alert: {title}",
                blocks=blocks,
            )

            return {
                "alert_id": response["ts"],
                "status": "sent",
                "timestamp": datetime.utcnow().isoformat(),
                "channel": response["channel"],
            }
        except SlackApiError as e:
            logger.error(f"Slack API error: {str(e)}")
            return {
                "alert_id": None,
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}", exc_info=True)
            return {
                "alert_id": None,
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def health_check(self) -> bool:
        """Check if Slack API is healthy and reachable."""
        try:
            response = self.client.auth_test()
            return response["ok"]
        except Exception as e:
            logger.warning(f"Slack health check failed: {str(e)}")
            return False
