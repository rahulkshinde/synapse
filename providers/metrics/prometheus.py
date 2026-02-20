"""Prometheus metrics provider implementation.

This module provides a PrometheusMetricsProvider that connects to a Prometheus
server and implements the MetricsProvider interface.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException

from core.interfaces import MetricsProvider

logger = logging.getLogger(__name__)


class PrometheusMetricsProvider(MetricsProvider):
    """Prometheus implementation of MetricsProvider.
    
    Connects to a Prometheus server via its HTTP API to query metrics.
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the Prometheus metrics provider.
        
        Args:
            base_url: Base URL of the Prometheus server (e.g., "http://prometheus:9090")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_url = f"{self.base_url}/api/v1"

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
            # Determine if this is an instant or range query
            if start_time and end_time:
                return self._query_range(query, start_time, end_time)
            else:
                return self._query_instant(query)
        except Exception as e:
            logger.error(f"Error querying Prometheus: {str(e)}", exc_info=True)
            raise

    def _query_instant(self, query: str) -> List[Dict[str, Any]]:
        """Execute an instant PromQL query.
        
        Args:
            query: PromQL query string
            
        Returns:
            List of metric data points
        """
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
        """Execute a range PromQL query.
        
        Args:
            query: PromQL query string
            start_time: Start time (ISO 8601 format)
            end_time: End time (ISO 8601 format)
            step: Query resolution step width (e.g., "15s", "1m")
            
        Returns:
            List of metric data points
        """
        url = f"{self.api_url}/query_range"

        # Convert ISO 8601 timestamps to Unix timestamps
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
        """List all available metric names from Prometheus.
        
        Returns:
            List of metric name strings
        """
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
        """Check if Prometheus is healthy and reachable.
        
        Returns:
            True if Prometheus is healthy, False otherwise
        """
        try:
            # Use the /api/v1/status/config endpoint as a health check
            url = f"{self.api_url}/status/config"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Prometheus health check failed: {str(e)}")
            return False

    @staticmethod
    def _iso_to_timestamp(iso_string: str) -> float:
        """Convert ISO 8601 timestamp to Unix timestamp.
        
        Args:
            iso_string: ISO 8601 formatted timestamp
            
        Returns:
            Unix timestamp (seconds since epoch)
        """
        try:
            # Handle timezone-aware and naive timestamps
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            # Fallback: try parsing as Unix timestamp
            try:
                return float(iso_string)
            except ValueError:
                raise ValueError(f"Invalid timestamp format: {iso_string}")
