#!/usr/bin/env python3
"""Drives the full Synapse troubleshooting loop through the real API."""

import argparse
import json
import os
import sys
import time

import requests

SYNAPSE_BASE_URL = os.getenv("SYNAPSE_URL", "http://localhost:8000")


def print_step(step_num: int, title: str):
    print(f"\n{'─' * 60}")
    print(f"  Step {step_num}: {title}")
    print(f"{'─' * 60}")


def check_health(base_url: str) -> bool:
    print_step(0, "Health Check")
    try:
        resp = requests.get(f"{base_url}/health", timeout=10)
        resp.raise_for_status()
        health = resp.json()
        print(f"  Status:  {health['status']}")
        print(f"  Plugins:")
        for ptype, names in health.get("plugins", {}).items():
            status = ", ".join(names) if names else "(none)"
            print(f"    {ptype:12s} → {status}")
        plugin_health = health.get("plugin_health", {})
        for pname, ok in plugin_health.items():
            icon = "✅" if ok else "❌"
            print(f"    {icon} {pname}")
        return health["status"] == "healthy"
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Cannot reach Synapse at {base_url}")
        print(f"     Start the stack: docker compose up -d")
        return False
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        return False


def list_plugins(base_url: str):
    print_step(1, "Discovered Plugins")
    try:
        resp = requests.get(f"{base_url}/plugins", timeout=10)
        resp.raise_for_status()
        plugins = resp.json()
        for ptype, names in plugins.items():
            status = ", ".join(names) if names else "(none loaded)"
            print(f"  {ptype:12s} → {status}")
    except Exception as e:
        print(f"  ⚠️  Could not list plugins: {e}")


def send_pagerduty_incident(base_url: str) -> dict:
    print_step(2, "Simulating PagerDuty Incident Webhook")

    payload = {
        "event": "incident.triggered",
        "incident": {
            "id": "PD-DEMO-42",
            "title": "High CPU on auth-api-uw2 (85% sustained)",
            "description": (
                "CPU utilization on auth-api-uw2 pods has exceeded 85% for the last "
                "10 minutes. HPA is scaling but new pods are slow to become ready. "
                "P95 latency has increased from 120ms to 890ms. "
                "Affected service: auth-api in namespace production-uw2."
            ),
            "severity": "high",
            "status": "triggered",
            "created_at": "2026-04-09T17:45:00Z",
            "service": {
                "id": "SVC-AUTH-API",
                "name": "auth-api-uw2",
            },
        },
    }

    print(f"  Alert:    {payload['incident']['title']}")
    print(f"  Severity: {payload['incident']['severity'].upper()}")
    print(f"  Service:  {payload['incident']['service']['name']}")

    try:
        print(f"\n  Sending to POST {base_url}/incident ...")
        start = time.time()
        resp = requests.post(f"{base_url}/incident", json=payload, timeout=120)
        elapsed = time.time() - start
        resp.raise_for_status()
        result = resp.json()
        print(f"  ✅ Response received in {elapsed:.1f}s")
        return result
    except requests.exceptions.Timeout:
        print(f"  ⚠️  Request timed out (LLM may need more time or a smaller model)")
        return {"status": "timeout"}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "error": str(e)}


def send_general_query(base_url: str, query: str) -> dict:
    print_step(3, "General SRE Query")
    print(f"  Query: \"{query}\"")

    try:
        start = time.time()
        resp = requests.post(
            f"{base_url}/query",
            params={"query": query},
            timeout=120,
        )
        elapsed = time.time() - start
        resp.raise_for_status()
        result = resp.json()
        print(f"  ✅ Response received in {elapsed:.1f}s")
        return result
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "error": str(e)}


def print_result(label: str, result: dict):
    print(f"\n{'═' * 60}")
    print(f"  {label}")
    print(f"{'═' * 60}")

    if "orchestrator_result" in result:
        orch = result["orchestrator_result"]
        if "response" in orch:
            print(f"\n{orch['response']}\n")
        elif "error" in orch:
            print(f"\n  ⚠️  Orchestrator error: {orch['error']}\n")
        else:
            print(json.dumps(orch, indent=2))
    elif "response" in result:
        print(f"\n{result['response']}\n")
    elif "error" in result:
        print(f"\n  ❌ {result['error']}\n")
    else:
        print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Synapse Demo Runner")
    parser.add_argument(
        "--base-url",
        default=SYNAPSE_BASE_URL,
        help="Synapse API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--skip-query",
        action="store_true",
        help="Skip the general query step (faster demo)",
    )
    args = parser.parse_args()

    print("🚀 Synapse SRE Assistant — Full Demo")
    print(f"   Target: {args.base_url}\n")

    if not check_health(args.base_url):
        sys.exit(1)

    list_plugins(args.base_url)

    incident_result = send_pagerduty_incident(args.base_url)
    print_result("Incident Analysis", incident_result)

    if not args.skip_query:
        query_result = send_general_query(
            args.base_url,
            "What runbook should I follow for database connection pool exhaustion?",
        )
        print_result("Knowledge Query", query_result)

    print(f"\n{'─' * 60}")
    print("✨ Demo complete!")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
