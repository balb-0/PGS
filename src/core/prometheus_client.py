from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os

import requests


@dataclass
class PrometheusQueryResult:
    ok: bool
    data: List[Dict[str, Any]]
    error: Optional[str] = None


class PrometheusClient:
    """Small adapter for Prometheus HTTP API with safe fallbacks."""

    def __init__(self, base_url: Optional[str] = None, timeout_seconds: float = 1.2) -> None:
        self.base_url = (base_url or os.getenv("PROMETHEUS_BASE_URL") or "http://localhost:9090").rstrip("/")
        self.timeout_seconds = timeout_seconds

    def query(self, promql: str) -> PrometheusQueryResult:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": promql},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "success":
                return PrometheusQueryResult(ok=False, data=[], error="query_unsuccessful")
            result_data = payload.get("data", {}).get("result", [])
            return PrometheusQueryResult(ok=True, data=result_data)
        except Exception as exc:  # pragma: no cover - defensive path
            return PrometheusQueryResult(ok=False, data=[], error=str(exc))

    def query_range(self, promql: str, start: str, end: str, step: str) -> PrometheusQueryResult:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query_range",
                params={"query": promql, "start": start, "end": end, "step": step},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "success":
                return PrometheusQueryResult(ok=False, data=[], error="query_range_unsuccessful")
            result_data = payload.get("data", {}).get("result", [])
            return PrometheusQueryResult(ok=True, data=result_data)
        except Exception as exc:  # pragma: no cover - defensive path
            return PrometheusQueryResult(ok=False, data=[], error=str(exc))
