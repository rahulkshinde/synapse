#!/usr/bin/env python3
"""Synapse MVD - Minimum Viable Demo: PagerDuty Alert → Prometheus → Ollama → Slack"""

import json
import os

import ollama
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def mock_pagerduty_alert():
    """Mock a PagerDuty alert trigger."""
    return {
        "event": "incident.triggered",
        "incident": {
            "id": "PD-12345",
            "title": "High CPU on Service-A",
            "description": "CPU usage has exceeded 85% threshold",
            "service": {"name": "Service-A"},
            "severity": "high",
        },
    }


def fetch_prometheus_metrics(service_name: str = "Service-A"):
    """Fetch metrics from Prometheus with fallback to mock data."""
    query = "node_cpu_seconds_total"
    
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        # Fallback to mock data if Prometheus is unreachable
        print(f"⚠️  Prometheus unreachable at {PROMETHEUS_URL}, using mock data")
        return {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "node_cpu_seconds_total",
                            "cpu": "0",
                            "instance": "service-a-01:9100",
                            "job": "node",
                            "mode": "idle",
                        },
                        "value": [1700000000, "1234567.89"],
                    },
                    {
                        "metric": {
                            "__name__": "node_cpu_seconds_total",
                            "cpu": "0",
                            "instance": "service-a-01:9100",
                            "job": "node",
                            "mode": "user",
                        },
                        "value": [1700000000, "987654.32"],
                    },
                ],
            },
        }


def analyze_with_ai(metric_data: dict, alert: dict) -> str:
    """Analyze metric data using local Ollama model."""
    system_prompt = (
        "You are an SRE agent. Analyze this metric data for Service-A. "
        "Determine if it indicates a critical failure and suggest a resolution step."
    )
    
    user_prompt = f"""Alert: {alert['incident']['title']}
Description: {alert['incident']['description']}

Metric Data:
{json.dumps(metric_data, indent=2)}

Provide a brief analysis (2-3 sentences) and a recommended resolution step."""
    
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Error analyzing with AI: {str(e)}\nEnsure Ollama is running and model '{OLLAMA_MODEL}' is available."


def notify_slack(alert: dict, analysis: str):
    """Send analysis to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URL not set, skipping Slack notification")
        print(f"\n📊 Analysis:\n{analysis}\n")
        return
    
    payload = {
        "text": f"🚨 SRE Alert: {alert['incident']['title']}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {alert['incident']['title']}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Service:*\n{alert['incident']['service']['name']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{alert['incident']['severity'].upper()}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Analysis:*\n{analysis}",
                },
            },
        ],
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Analysis sent to Slack")
    except requests.exceptions.RequestException as e:
        print(f"❌ Slack error: {e}")
        print(f"\n📊 Analysis:\n{analysis}\n")


def main():
    """Main troubleshooting loop."""
    print("🚀 Synapse MVD - Troubleshooting Loop\n")
    print("=" * 50)
    
    # Step 1: Mock PagerDuty alert
    print("\n1️⃣  Simulating PagerDuty alert...")
    alert = mock_pagerduty_alert()
    print(f"   Alert: {alert['incident']['title']}")
    print(f"   Service: {alert['incident']['service']['name']}")
    
    # Step 2: Fetch metrics
    print(f"\n2️⃣  Fetching Prometheus metrics...")
    metrics = fetch_prometheus_metrics(alert['incident']['service']['name'])
    print("   ✅ Metrics retrieved")
    
    # Step 3: AI Analysis
    print(f"\n3️⃣  Analyzing with Ollama ({OLLAMA_MODEL})...")
    analysis = analyze_with_ai(metrics, alert)
    print("   ✅ Analysis complete")
    
    # Step 4: Notify Slack
    print(f"\n4️⃣  Sending to Slack...")
    notify_slack(alert, analysis)
    
    print("\n" + "=" * 50)
    print("✨ Troubleshooting loop complete!")


if __name__ == "__main__":
    main()
