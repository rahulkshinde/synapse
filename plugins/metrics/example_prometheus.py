"""Example Prometheus metrics plugin implementation.

This plugin demonstrates how to implement the BaseMetrics interface
for querying Prometheus metrics. It can be used as a template for
creating other metrics plugins.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException

from core.base import BaseMetrics

logger = logging.getLogger(__name__)


class ExamplePrometheus(BaseMetrics):
    """Prometheus implementation of BaseMetrics.
    
    Connects to a Prometheus server via its HTTP API to query metrics.
    This plugin is automatically discovered and loaded when placed in
    the plugins/metrics/ directory.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """Initialize the Prometheus metrics plugin.
        
        Args:
            base_url: Base URL of the Prometheus server (defaults to PROMETHEUS_URL env var)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")).rstrip("/")
        self.timeout = timeout
        self.api_url = f"{self.base_url}/api/v1"

    @property
    def name(self) -> str:
        """Return the plugin name."""
        return "prometheus"

    def get_metrics(
        self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve metrics from Prometheus using PromQL.
        
        Args:
            query: PromQL query string
            start_time: Optional start time for range queries (ISO 8601 format)
            end_time: Optional end time for range queries (ISO 8601 format)
            
        Returns:
            List of metric data points
        """
        try:
            if start_time and end_time:
                return self._query_range(query, start_time, end_time)
            else:
                return self._query_instant(query)
        except Exception as e:
            logger.error(f"Error querying Prometheus: {str(e)}", exc_info=True)
            raise

    def _query_instant(self, query: str) -> List[Dict[str, Any]]:
        """Execute an instant PromQL query."""
        url = f"{self.api_url}/query"
        params = {"query": query}

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "success":
                raise ValueError(f"Prometheus query failed: {data.get('error', 'Unknown error')}")

            results = []
            result_data = data.get("data", {}).get("result", [])

            for item in result_data:
                metric = item.get("metric", {})
                value = item.get("value", [None, None])

                results.append({
                    "timestamp": datetime.fromtimestamp(value[0]).isoformat() if value[0] else datetime.utcnow().isoformat(),
                    "value": float(value[1]) if value[1] is not None else 0.0,
                    "labels": dict(metric),
                    "name": metric.get("__name__", query),
                })

            return results
        except RequestException as e:
            logger.error(f"Prometheus API request failed: {str(e)}")
            raise

    def _query_range(
        self, query: str, start_time: str, end_time: str, step: str = "15s"
    ) -> List[Dict[str, Any]]:
        """Execute a range PromQL query."""
        url = f"{self.api_url}/query_range"

        start_ts = self._iso_to_timestamp(start_time)
        end_ts = self._iso_to_timestamp(end_time)

        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": step,
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "success":
                raise ValueError(f"Prometheus query failed: {data.get('error', 'Unknown error')}")

            results = []
            result_data = data.get("data", {}).get("result", [])

            for item in result_data:
                metric = item.get("metric", {})
                values = item.get("values", [])

                for value_pair in values:
                    timestamp, value = value_pair
                    results.append({
                        "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                        "value": float(value) if value is not None else 0.0,
                        "labels": dict(metric),
                        "name": metric.get("__name__", query),
                    })

            return results
        except RequestException as e:
            logger.error(f"Prometheus API request failed: {str(e)}")
            raise

    def list_available_metrics(self) -> List[str]:
        """List all available metric names from Prometheus."""
        url = f"{self.api_url}/label/__name__/values"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "success":
                raise ValueError(f"Prometheus query failed: {data.get('error', 'Unknown error')}")

            return data.get("data", [])
        except RequestException as e:
            logger.error(f"Prometheus API request failed: {str(e)}")
            raise

    def health_check(self) -> bool:
        """Check if Prometheus is healthy and reachable."""
        try:
            url = f"{self.api_url}/status/config"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Prometheus health check failed: {str(e)}")
            return False

    @staticmethod
    def _iso_to_timestamp(iso_string: str) -> float:
        """Convert ISO 8601 timestamp to Unix timestamp."""
        try:
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            try:
                return float(iso_string)
            except ValueError:
                raise ValueError(f"Invalid timestamp format: {iso_string}")
