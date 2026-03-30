"""
Tests for the Infracost JSON parser.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.infracost_parser import (
    CostSummary,
    ResourceCost,
    format_cost_context,
    parse_infracost_json,
)


# ── Fixtures ──────────────────────────────────────────────────

SAMPLE_INFRACOST_JSON = {
    "version": "0.2",
    "currency": "USD",
    "totalMonthlyCost": "350.40",
    "pastTotalMonthlyCost": "88.40",
    "projects": [
        {
            "name": "example-project",
            "breakdown": {
                "resources": [
                    {
                        "name": "aws_instance.web",
                        "resourceType": "aws_instance",
                        "provider": "aws",
                        "monthlyCost": "280.00",
                        "previousMonthlyCost": "30.00",
                        "costComponents": [
                            {
                                "name": "Instance usage (Linux/UNIX, on-demand, m5.2xlarge)",
                                "unit": "hours",
                                "monthlyCost": "280.00",
                            }
                        ],
                        "tags": {"Environment": "production"},
                    },
                    {
                        "name": "aws_db_instance.main",
                        "resourceType": "aws_db_instance",
                        "provider": "aws",
                        "monthlyCost": "70.40",
                        "previousMonthlyCost": "58.40",
                        "costComponents": [],
                        "tags": {"Environment": "production"},
                    },
                ],
            },
        }
    ],
}


@pytest.fixture
def infracost_json_path(tmp_path: Path) -> Path:
    """Write sample JSON and return its path."""
    p = tmp_path / "infracost.json"
    p.write_text(json.dumps(SAMPLE_INFRACOST_JSON), encoding="utf-8")
    return p


@pytest.fixture
def empty_json_path(tmp_path: Path) -> Path:
    """Write empty projects JSON."""
    p = tmp_path / "empty.json"
    data = {"version": "0.2", "currency": "USD", "totalMonthlyCost": "0", "pastTotalMonthlyCost": "0", "projects": []}
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── Tests ─────────────────────────────────────────────────────


class TestParseInfracostJson:
    def test_parses_valid_json(self, infracost_json_path: Path) -> None:
        result = parse_infracost_json(infracost_json_path)
        assert result is not None
        assert isinstance(result, CostSummary)
        assert result.currency == "USD"
        assert result.total_monthly_cost == 350.40
        assert result.previous_total_monthly_cost == 88.40
        assert result.resource_count == 2

    def test_resource_details(self, infracost_json_path: Path) -> None:
        result = parse_infracost_json(infracost_json_path)
        assert result is not None
        web = next(r for r in result.resources if r.name == "aws_instance.web")
        assert web.resource_type == "aws_instance"
        assert web.provider == "aws"
        assert web.monthly_cost == 280.0
        assert web.previous_cost == 30.0
        assert web.diff == 250.0

    def test_diff_calculation(self, infracost_json_path: Path) -> None:
        result = parse_infracost_json(infracost_json_path)
        assert result is not None
        assert result.diff_total_monthly_cost == pytest.approx(262.0, abs=0.01)

    def test_pct_change(self, infracost_json_path: Path) -> None:
        result = parse_infracost_json(infracost_json_path)
        assert result is not None
        assert result.pct_change is not None
        assert result.pct_change > 200  # 262/88.4 ~ 296%

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        result = parse_infracost_json(tmp_path / "nonexistent.json")
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all", encoding="utf-8")
        result = parse_infracost_json(bad)
        assert result is None

    def test_empty_projects(self, empty_json_path: Path) -> None:
        result = parse_infracost_json(empty_json_path)
        assert result is not None
        assert result.resource_count == 0


class TestResourceCost:
    def test_pct_change_with_nonzero_previous(self) -> None:
        r = ResourceCost(
            name="test", resource_type="t", provider="aws",
            monthly_cost=200, previous_cost=100, diff=100,
        )
        assert r.pct_change == 100.0

    def test_pct_change_with_zero_previous(self) -> None:
        r = ResourceCost(
            name="test", resource_type="t", provider="aws",
            monthly_cost=200, previous_cost=0, diff=200,
        )
        assert r.pct_change is None


class TestFormatCostContext:
    def test_contains_key_fields(self, infracost_json_path: Path) -> None:
        summary = parse_infracost_json(infracost_json_path)
        assert summary is not None
        text = format_cost_context(summary)
        assert "USD" in text
        assert "$350.40" in text
        assert "aws_instance.web" in text
        assert "Resource-Level Breakdown" in text

    def test_empty_resources(self) -> None:
        summary = CostSummary(
            currency="USD",
            total_monthly_cost=0.0,
            previous_total_monthly_cost=0.0,
            diff_total_monthly_cost=0.0,
            resource_count=0,
            resources=[],
        )
        text = format_cost_context(summary)
        assert "Resources affected" in text
        assert "Resource-Level Breakdown" not in text
