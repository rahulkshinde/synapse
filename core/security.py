"""PII and secret scrubbing. All data passes through here before reaching the LLM."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    PATTERNS = {
        "api_key": re.compile(
            r"(?i)(api[_-]?key|apikey)\s*[:=]\s*([a-zA-Z0-9_\-]{20,})", re.MULTILINE
        ),
        "bearer_token": re.compile(
            r"(?i)(bearer\s+)?([a-zA-Z0-9_\-\.]{40,})", re.MULTILINE
        ),
        "slack_token": re.compile(r"(?i)(xox[baprs]-[0-9a-zA-Z\-]{10,})", re.MULTILINE),
        "aws_access_key": re.compile(r"(?i)(AKIA[0-9A-Z]{16})", re.MULTILINE),
        "aws_secret_key": re.compile(
            r"(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*([a-zA-Z0-9/+=]{40})",
            re.MULTILINE,
        ),
        "email": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.MULTILINE
        ),
        "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", re.MULTILINE),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b", re.MULTILINE),
        "private_ip": re.compile(
            r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b",
            re.MULTILINE,
        ),
        "password": re.compile(
            r"(?i)(password|passwd|pwd)\s*[:=]\s*([^\s]{6,})", re.MULTILINE
        ),
        "db_connection": re.compile(
            r"(?i)(postgresql|mysql|mongodb)://[^\s]+", re.MULTILINE
        ),
        "jwt": re.compile(
            r"eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
            re.MULTILINE,
        ),
    }

    custom_patterns: Dict[str, re.Pattern] = {}

    def __init__(self, custom_patterns: Optional[Dict[str, str]] = None):
        if custom_patterns:
            for name, pattern_str in custom_patterns.items():
                try:
                    self.custom_patterns[name] = re.compile(
                        pattern_str, re.MULTILINE | re.IGNORECASE
                    )
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{name}': {e}")

    def scrub(self, text: str, replacement: str = "[REDACTED]") -> str:
        if not isinstance(text, str):
            return text

        scrubbed = text

        for pattern_name, pattern in self.PATTERNS.items():
            matches = pattern.findall(scrubbed)
            if matches:
                logger.debug(
                    f"Found {len(matches)} matches for pattern '{pattern_name}'"
                )
                if isinstance(matches[0], tuple):
                    scrubbed = pattern.sub(replacement, scrubbed)
                else:
                    scrubbed = pattern.sub(replacement, scrubbed)

        for pattern_name, pattern in self.custom_patterns.items():
            matches = pattern.findall(scrubbed)
            if matches:
                logger.debug(
                    f"Found {len(matches)} matches for custom pattern '{pattern_name}'"
                )
                scrubbed = pattern.sub(replacement, scrubbed)

        return scrubbed

    def scrub_dict(
        self, data: Dict[str, Any], replacement: str = "[REDACTED]"
    ) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return self.scrub(str(data), replacement) if isinstance(data, str) else data

        scrubbed = {}
        for key, value in data.items():
            if isinstance(value, dict):
                scrubbed[key] = self.scrub_dict(value, replacement)
            elif isinstance(value, list):
                scrubbed[key] = [
                    (
                        self.scrub_dict(item, replacement)
                        if isinstance(item, dict)
                        else (
                            self.scrub(str(item), replacement)
                            if isinstance(item, str)
                            else item
                        )
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                scrubbed[key] = self.scrub(value, replacement)
            else:
                scrubbed[key] = value

        return scrubbed

    def scrub_list(self, data: List[Any], replacement: str = "[REDACTED]") -> List[Any]:
        scrubbed = []
        for item in data:
            if isinstance(item, dict):
                scrubbed.append(self.scrub_dict(item, replacement))
            elif isinstance(item, list):
                scrubbed.append(self.scrub_list(item, replacement))
            elif isinstance(item, str):
                scrubbed.append(self.scrub(item, replacement))
            else:
                scrubbed.append(item)
        return scrubbed
