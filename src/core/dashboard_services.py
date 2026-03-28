from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from .prometheus_client import PrometheusClient


@dataclass
class DashboardFilters:
    interval: str = "1h"
    step: str = "5m"
    endpoint: str = "all"
    source: str = "all"
    account: str = "all"
    dn: str = "all"


@dataclass
class DashboardDependencies:
    health_checker: Any
    circuit_breaker: Any
    rate_limiter: Any
    process_store: Any
    audit_log: Any
    idempotency_store: Any
    transaction_history: Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _interval_start(interval: str) -> datetime:
    unit = interval[-1:].lower()
    value_str = interval[:-1]
    try:
        value = int(value_str)
    except ValueError:
        value = 1

    if unit == "m":
        return datetime.now(timezone.utc) - timedelta(minutes=value)
    if unit == "h":
        return datetime.now(timezone.utc) - timedelta(hours=value)
    if unit == "d":
        return datetime.now(timezone.utc) - timedelta(days=value)
    return datetime.now(timezone.utc) - timedelta(hours=1)


def _prom_status(source: str) -> str:
    return "degraded" if source == "unavailable" else "ok"


def _read_float(result_data: List[Dict[str, Any]], default: float = 0.0) -> float:
    if not result_data:
        return default
    value = result_data[0].get("value")
    if not value or len(value) < 2:
        return default
    try:
        return float(value[1])
    except (TypeError, ValueError):
        return default


def _read_series(result_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    series: List[Dict[str, Any]] = []
    for item in result_data:
        metric = item.get("metric", {})
        points: List[Dict[str, Any]] = []
        for pair in item.get("values", []):
            if len(pair) != 2:
                continue
            ts, raw_value = pair
            try:
                numeric = float(raw_value)
            except (TypeError, ValueError):
                continue
            points.append({"t": ts, "v": numeric})
        series.append({"metric": metric, "points": points})
    return series


class DashboardServiceBase:
    def __init__(self, deps: DashboardDependencies, prom_client: Optional[PrometheusClient] = None) -> None:
        self.deps = deps
        self.prom_client = prom_client or PrometheusClient()
        self.repo_root = Path(__file__).resolve().parents[2]

    def _query(self, promql: str) -> Dict[str, Any]:
        response = self.prom_client.query(promql)
        return {
            "ok": response.ok,
            "data": response.data,
            "error": response.error,
        }

    def _query_range(self, promql: str, interval: str, step: str) -> Dict[str, Any]:
        end = datetime.now(timezone.utc)
        start = _interval_start(interval)
        response = self.prom_client.query_range(
            promql=promql,
            start=start.isoformat(),
            end=end.isoformat(),
            step=step,
        )
        return {
            "ok": response.ok,
            "data": response.data,
            "error": response.error,
        }


class BusinessDashboardService(DashboardServiceBase):
    def build(self, filters: DashboardFilters) -> Dict[str, Any]:
        health = self.deps.health_checker.get_status()
        total_requests = int(health.get("total_requests", 0))
        total_errors = int(health.get("total_errors", 0))
        success_rate = ((total_requests - total_errors) / total_requests * 100.0) if total_requests else 0.0

        p90_query = self._query(
            'histogram_quantile(0.9, sum(rate(asis_request_duration_seconds_bucket[5m])) by (le))'
        )
        throughput_query = self._query('sum(rate(asis_requests_total[5m]))')
        source_breakdown_query = self._query('sum(rate(asis_requests_total[5m])) by (source)')

        p90_seconds = _read_float(p90_query["data"], default=0.0)
        p90_ms = p90_seconds * 1000.0
        throughput_rps = _read_float(throughput_query["data"], default=0.0)

        if p90_ms > 650:
            sla_status = "critical"
        elif p90_ms > 500:
            sla_status = "warning"
        else:
            sla_status = "healthy"

        trend_query = self._query_range(
            'histogram_quantile(0.9, sum(rate(asis_request_duration_seconds_bucket[5m])) by (le))',
            filters.interval,
            filters.step,
        )

        source_breakdown: List[Dict[str, Any]] = []
        for item in source_breakdown_query["data"]:
            source = item.get("metric", {}).get("source", "unknown")
            source_breakdown.append({"source": source, "rps": _read_float([item], 0.0)})

        return {
            "dashboard": "business",
            "generated_at": _iso_now(),
            "filters": filters.__dict__,
            "degradation": {
                "prometheus": _prom_status("unavailable" if not p90_query["ok"] else "ok"),
                "details": p90_query["error"] or throughput_query["error"] or source_breakdown_query["error"],
            },
            "summary": {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "success_rate_percent": round(success_rate, 2),
                "p90_latency_ms": round(p90_ms, 2),
                "throughput_rps": round(throughput_rps, 3),
                "sla_status": sla_status,
                "process_store_size": self.deps.process_store.size(),
            },
            "breakdown": {
                "source_rps": source_breakdown,
                "quality_signals": {
                    "validation_errors_current": int(_read_float(self._query('sum(asis_validation_errors_total)')["data"], 0.0)),
                    "audit_entries_total": self.deps.audit_log.size(),
                },
            },
            "trends": {
                "p90_latency": _read_series(trend_query["data"]),
            },
        }


class SystemHealthDashboardService(DashboardServiceBase):
    def build(self, filters: DashboardFilters) -> Dict[str, Any]:
        health = self.deps.health_checker.get_status()
        error_rate = float(health.get("error_rate_percent", 0.0))
        circuit_state = self.deps.circuit_breaker.state.value
        rate_remaining = self.deps.rate_limiter.get_remaining_for_all_accounts()

        health_score = max(0.0, 100.0 - error_rate)
        if circuit_state == "OPEN":
            health_score = min(health_score, 30.0)

        error_trend = self._query_range('avg(asis_health_error_rate_percent)', filters.interval, filters.step)
        req_trend = self._query_range('sum(rate(asis_requests_total[1m]))', filters.interval, filters.step)
        alerts_query = self._query('count(ALERTS{alertstate="firing"})')

        top_accounts = sorted(rate_remaining.items(), key=lambda item: item[1])[:10]
        account_pressure = [
            {"account_key_hash": key_hash, "remaining": remaining}
            for key_hash, remaining in top_accounts
        ]

        return {
            "dashboard": "system-health",
            "generated_at": _iso_now(),
            "filters": filters.__dict__,
            "degradation": {
                "prometheus": _prom_status("unavailable" if not req_trend["ok"] else "ok"),
                "details": req_trend["error"] or error_trend["error"] or alerts_query["error"],
            },
            "summary": {
                "status": health.get("status", "unknown"),
                "health_score": round(health_score, 2),
                "error_rate_percent": round(error_rate, 2),
                "uptime_seconds": health.get("uptime_seconds", 0),
                "circuit_breaker_state": circuit_state,
                "firing_alerts": int(_read_float(alerts_query["data"], 0.0)),
            },
            "breakdown": {
                "rate_limit_pressure": account_pressure,
                "stores": {
                    "process_store_size": self.deps.process_store.size(),
                    "audit_log_size": self.deps.audit_log.size(),
                    "idempotency_store_size": self.deps.idempotency_store.size(),
                    "transaction_history_size": self.deps.transaction_history.size(),
                },
            },
            "trends": {
                "error_rate": _read_series(error_trend["data"]),
                "throughput": _read_series(req_trend["data"]),
            },
        }


class TestingGapDashboardService(DashboardServiceBase):
    def _load_pytest_report(self) -> Dict[str, int]:
        report_file = self.repo_root / "pytest-report.xml"
        if not report_file.exists():
            return {"total": 0, "passed": 0, "failed": 0}

        tree = ET.parse(report_file)
        root = tree.getroot()
        tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))
        passed = max(tests - failures - errors - skipped, 0)
        return {"total": tests, "passed": passed, "failed": failures + errors}

    def _load_coverage(self) -> Dict[str, float]:
        coverage_file = self.repo_root / "coverage.xml"
        if not coverage_file.exists():
            return {"line_rate_percent": 0.0, "branch_rate_percent": 0.0}

        tree = ET.parse(coverage_file)
        root = tree.getroot()
        line_rate = float(root.attrib.get("line-rate", 0.0))
        branch_rate = float(root.attrib.get("branch-rate", 0.0))
        return {
            "line_rate_percent": round(line_rate * 100.0, 2),
            "branch_rate_percent": round(branch_rate * 100.0, 2),
        }

    def build(self, filters: DashboardFilters) -> Dict[str, Any]:
        report = self._load_pytest_report()
        coverage = self._load_coverage()
        total = report["total"]
        passed = report["passed"]
        failed = report["failed"]
        pending = max(total - passed, 0)

        pass_rate = (passed / total * 100.0) if total else 0.0
        risk_level = "high" if failed > 20 else "moderate" if failed > 5 else "low"

        prom_pass_rate = self._query('100 * (pytest_tests_passed / clamp_min(pytest_tests_total, 1))')
        validation_trend = self._query_range('sum(rate(asis_validation_errors_total[5m]))', filters.interval, filters.step)

        area_progress = [
            {"area": "DN2", "priority": "critical", "status": "pending" if failed else "stable"},
            {"area": "RF1", "priority": "high", "status": "pending" if failed else "stable"},
            {"area": "RNF1", "priority": "high", "status": "pending" if failed else "stable"},
            {"area": "INT3", "priority": "medium", "status": "in_analysis"},
            {"area": "INT5", "priority": "medium", "status": "in_analysis"},
        ]

        return {
            "dashboard": "testing-gap",
            "generated_at": _iso_now(),
            "filters": filters.__dict__,
            "degradation": {
                "prometheus": _prom_status("unavailable" if not prom_pass_rate["ok"] else "ok"),
                "details": prom_pass_rate["error"] or validation_trend["error"],
            },
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "pending_tests": pending,
                "pass_rate_percent": round(pass_rate, 2),
                "prometheus_pass_rate_percent": round(_read_float(prom_pass_rate["data"], pass_rate), 2),
                "risk_level": risk_level,
            },
            "coverage": coverage,
            "breakdown": {
                "areas": area_progress,
            },
            "trends": {
                "validation_errors": _read_series(validation_trend["data"]),
            },
        }


def build_dashboard_metadata() -> Dict[str, Any]:
    return {
        "generated_at": _iso_now(),
        "dashboards": ["business", "system-health", "testing-gap"],
        "filters": {
            "interval": ["30m", "1h", "6h", "24h", "7d"],
            "step": ["30s", "1m", "5m", "15m"],
            "source": ["all", "real", "mock"],
            "dn": ["all", "DN1", "DN2", "DN3", "DN4", "RF1", "RF2", "RNF1", "RNF2", "INT3", "INT5"],
        },
    }
