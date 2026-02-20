"""Slack communication provider implementation.

This module provides a SlackCommunicationProvider that uses Slack Bolt SDK
to send messages and alerts to Slack channels.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from core.interfaces import CommunicationProvider

logger = logging.getLogger(__name__)


class SlackCommunicationProvider(CommunicationProvider):
    """Slack implementation of CommunicationProvider.
    
    Uses Slack Web API to send messages and alerts to Slack channels.
    """

    def __init__(self, bot_token: str, default_channel: Optional[str] = None):
        """Initialize the Slack communication provider.
        
        Args:
            bot_token: Slack bot token (starts with "xoxb-")
            default_channel: Default channel to send messages to (e.g., "#incidents")
        """
        self.client = WebClient(token=bot_token)
        self.default_channel = default_channel

    def send_message(
        self,
        channel: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a Slack channel.
        
        Args:
            channel: Slack channel name or ID (e.g., "#incidents" or "C1234567890")
            message: Message content to send
            metadata: Optional dictionary with additional metadata:
                - thread_ts: Thread timestamp to reply in thread
                - blocks: Slack Block Kit blocks for rich formatting
                - attachments: Legacy attachments (deprecated)
                
        Returns:
            Dictionary with response information
        """
        try:
            # Ensure channel starts with # if it's a channel name
            if not channel.startswith("#") and not channel.startswith("C"):
                channel = f"#{channel}"

            # Build message payload
            payload = {
                "channel": channel,
                "text": message,
            }

            # Add optional metadata
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
        """Send an alert/incident notification to Slack.
        
        Args:
            severity: Alert severity level (e.g., "critical", "warning", "info")
            title: Alert title
            description: Detailed alert description
            metadata: Optional dictionary with additional metadata:
                - channel: Target channel (defaults to self.default_channel)
                - incident_id: Incident identifier
                - links: List of URLs to include
                - color: Color for the alert (based on severity if not provided)
                
        Returns:
            Dictionary with response information
        """
        try:
            # Determine channel
            channel = (metadata or {}).get("channel", self.default_channel)
            if not channel:
                raise ValueError("No channel specified and no default channel set")

            # Map severity to color
            severity_colors = {
                "critical": "#FF0000",  # Red
                "high": "#FF6B00",      # Orange
                "medium": "#FFA500",    # Orange-Yellow
                "low": "#FFD700",       # Gold
                "info": "#36A2EB",      # Blue
            }
            color = (metadata or {}).get("color", severity_colors.get(severity.lower(), "#808080"))

            # Build rich message blocks
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

            # Add incident ID if provided
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

            # Add links if provided
            if metadata and "links" in metadata and metadata["links"]:
                link_text = "\n".join([f"• <{link}|{link}>" for link in metadata["links"]])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Related Links:*\n{link_text}",
                    },
                })

            # Add divider
            blocks.append({"type": "divider"})

            # Send message with blocks
            response = self.client.chat_postMessage(
                channel=channel,
                text=f"Alert: {title}",  # Fallback text
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
        """Check if Slack API is healthy and reachable.
        
        Returns:
            True if Slack API is healthy, False otherwise
        """
        try:
            # Use auth.test endpoint as a health check
            response = self.client.auth_test()
            return response["ok"]
        except Exception as e:
            logger.warning(f"Slack health check failed: {str(e)}")
            return False
