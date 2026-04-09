"""Tests for SecurityMiddleware PII/secret scrubbing."""

import pytest

from core.security import SecurityMiddleware


@pytest.fixture
def security():
    """Default SecurityMiddleware with no custom patterns."""
    return SecurityMiddleware()


@pytest.fixture
def security_custom():
    """SecurityMiddleware with a custom pattern."""
    return SecurityMiddleware(custom_patterns={"duo_internal": r"duo-internal-[a-z0-9]{8}"})


# ── AWS Credentials ────────────────────────────────────────────


class TestAWSCredentials:
    def test_scrubs_aws_access_key(self, security):
        text = "Found key AKIAIOSFODNN7EXAMPLE in config"
        result = security.scrub(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED]" in result

    def test_scrubs_aws_secret_key(self, security):
        text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = security.scrub(text)
        assert "wJalrXUtnFEMI" not in result
        assert "[REDACTED]" in result

    def test_scrubs_aws_secret_key_with_colon(self, security):
        text = "AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = security.scrub(text)
        assert "wJalrXUtnFEMI" not in result


# ── API Keys and Tokens ───────────────────────────────────────


class TestAPIKeys:
    def test_scrubs_api_key_equals(self, security):
        text = "api_key=sk_live_abc123def456ghi789jkl012mno"
        result = security.scrub(text)
        assert "sk_live_abc123" not in result

    def test_scrubs_api_key_colon(self, security):
        text = "apikey: abcdefghijklmnopqrstuvwxyz1234567890"
        result = security.scrub(text)
        assert "abcdefghijklmnopqrst" not in result

    def test_scrubs_slack_token(self, security):
        text = "Using token xoxb-123456789012-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx"
        result = security.scrub(text)
        assert "xoxb-" not in result

    def test_scrubs_jwt_token(self, security):
        text = "Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = security.scrub(text)
        assert "eyJhbGciOi" not in result


# ── PII ────────────────────────────────────────────────────────


class TestPII:
    def test_scrubs_email(self, security):
        text = "Contact admin@duo.com for access"
        result = security.scrub(text)
        assert "admin@duo.com" not in result
        assert "[REDACTED]" in result

    def test_scrubs_ssn(self, security):
        text = "SSN on file: 123-45-6789"
        result = security.scrub(text)
        assert "123-45-6789" not in result

    def test_scrubs_credit_card(self, security):
        text = "Card ending 4111-1111-1111-1111"
        result = security.scrub(text)
        assert "4111-1111-1111-1111" not in result

    def test_scrubs_password(self, security):
        text = "password=SuperSecret123!"
        result = security.scrub(text)
        assert "SuperSecret123!" not in result


# ── Network & Infrastructure ──────────────────────────────────


class TestNetwork:
    def test_scrubs_private_ip_10(self, security):
        text = "Pod running on 10.0.42.15"
        result = security.scrub(text)
        assert "10.0.42.15" not in result

    def test_scrubs_private_ip_172(self, security):
        text = "Node at 172.16.0.100"
        result = security.scrub(text)
        assert "172.16.0.100" not in result

    def test_scrubs_private_ip_192(self, security):
        text = "Service at 192.168.1.50"
        result = security.scrub(text)
        assert "192.168.1.50" not in result

    def test_scrubs_db_connection_string(self, security):
        text = "postgresql://admin:secret@db.internal:5432/mydb"
        result = security.scrub(text)
        assert "postgresql://" not in result
        assert "admin:secret" not in result

    def test_scrubs_mysql_connection(self, security):
        text = "mysql://root:pass@mysql.vpc.internal:3306/app"
        result = security.scrub(text)
        assert "mysql://" not in result

    def test_scrubs_mongodb_connection(self, security):
        text = "mongodb://user:password@mongo.cluster.local:27017/db"
        result = security.scrub(text)
        assert "mongodb://" not in result


# ── Dict / List Scrubbing ─────────────────────────────────────


class TestStructuredScrubbing:
    def test_scrubs_dict_values(self, security):
        data = {
            "host": "10.0.1.5",
            "connection": "postgresql://admin:pass@db:5432/app",
            "count": 42,
        }
        result = security.scrub_dict(data)
        assert "10.0.1.5" not in result["host"]
        assert "postgresql://" not in result["connection"]
        assert result["count"] == 42

    def test_scrubs_nested_dict(self, security):
        data = {
            "incident": {
                "description": "Alert from 10.0.1.5",
                "metadata": {"email": "admin@duo.com"},
            }
        }
        result = security.scrub_dict(data)
        assert "10.0.1.5" not in result["incident"]["description"]
        assert "admin@duo.com" not in result["incident"]["metadata"]["email"]

    def test_scrubs_list(self, security):
        data = ["Connect to 10.0.1.5", "Use password=hunter2", "OK"]
        result = security.scrub_list(data)
        assert "10.0.1.5" not in result[0]
        assert "hunter2" not in result[1]
        assert result[2] == "OK"

    def test_scrubs_list_of_dicts(self, security):
        data = [{"ip": "10.0.1.5"}, {"clean": "hello"}]
        result = security.scrub_list(data)
        assert "10.0.1.5" not in result[0]["ip"]
        assert result[1]["clean"] == "hello"


# ── Custom Patterns ───────────────────────────────────────────


class TestCustomPatterns:
    def test_custom_pattern_scrubs(self, security_custom):
        text = "Found duo-internal-a1b2c3d4 in response"
        result = security_custom.scrub(text)
        assert "duo-internal-a1b2c3d4" not in result

    def test_invalid_custom_pattern_ignored(self):
        sec = SecurityMiddleware(custom_patterns={"bad": "[invalid("})
        # Should not raise — invalid pattern is logged and skipped
        result = sec.scrub("hello world")
        assert result == "hello world"


# ── Edge Cases ────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_string(self, security):
        assert security.scrub("") == ""

    def test_non_string_passthrough(self, security):
        assert security.scrub(42) == 42
        assert security.scrub(None) is None

    def test_no_sensitive_data(self, security):
        text = "The deployment succeeded with 0 errors."
        assert security.scrub(text) == text

    def test_multiple_patterns_in_one_string(self, security):
        text = "Host 10.0.1.5 has password=secret123 and key AKIAIOSFODNN7EXAMPLE"
        result = security.scrub(text)
        assert "10.0.1.5" not in result
        assert "secret123" not in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result
