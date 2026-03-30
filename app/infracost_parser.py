"""
Infracost JSON → structured Python objects.

Handles both `breakdown` and `diff` JSON formats, extracting the
fields the LLM agent needs without leaking raw JSON into the prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Data Models ───────────────────────────────────────────────

@dataclass
class ResourceCost:
    """A single cloud resource and its cost impact."""
    name: str
    resource_type: str
    provider: str
    monthly_cost: float
    previous_cost: float
    diff: float
    cost_components: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def pct_change(self) -> float | None:
        if self.previous_cost == 0:
            return None
        return round((self.diff / self.previous_cost) * 100, 2)


@dataclass
class CostSummary:
    """Aggregated cost summary across all resources."""
    currency: str
    total_monthly_cost: float
    previous_total_monthly_cost: float
    diff_total_monthly_cost: float
    resource_count: int
    resources: list[ResourceCost] = field(default_factory=list)

    @property
    def pct_change(self) -> float | None:
        if self.previous_total_monthly_cost == 0:
            return None
        return round(
            (self.diff_total_monthly_cost / self.previous_total_monthly_cost) * 100, 2
        )


# ── Parser ────────────────────────────────────────────────────

def _safe_float(val: Any) -> float:
    """Coerce value to float, defaulting to 0.0."""
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_resource(raw: dict[str, Any]) -> ResourceCost:
    """Convert a single Infracost resource dict to a ResourceCost."""
    monthly = _safe_float(raw.get("monthlyCost"))
    previous = _safe_float(raw.get("previousMonthlyCost", raw.get("monthlyCost")))
    return ResourceCost(
        name=raw.get("name", "unknown"),
        resource_type=raw.get("resourceType", "unknown"),
        provider=raw.get("provider", "unknown"),
        monthly_cost=monthly,
        previous_cost=previous,
        diff=round(monthly - previous, 4),
        cost_components=raw.get("costComponents", []),
        tags=raw.get("tags", {}),
    )


def parse_infracost_json(path: Path) -> CostSummary | None:
    """
    Parse an Infracost JSON file (breakdown or diff format).

    Returns None if the file does not exist or is unparseable.
    """
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Infracost wraps projects in a top-level list
    projects = data.get("projects", [])
    resources: list[ResourceCost] = []

    for project in projects:
        breakdown = project.get("breakdown", project.get("diff", {}))
        for raw_res in breakdown.get("resources", []):
            resources.append(_parse_resource(raw_res))

    total = _safe_float(data.get("totalMonthlyCost"))
    previous = _safe_float(data.get("pastTotalMonthlyCost"))

    return CostSummary(
        currency=data.get("currency", "USD"),
        total_monthly_cost=total,
        previous_total_monthly_cost=previous,
        diff_total_monthly_cost=round(total - previous, 4),
        resource_count=len(resources),
        resources=resources,
    )


def format_cost_context(summary: CostSummary) -> str:
    """
    Build a concise, LLM-friendly text representation of the cost data.
    """
    lines: list[str] = []
    lines.append(f"Currency: {summary.currency}")
    lines.append(f"Previous monthly cost : ${summary.previous_total_monthly_cost:,.2f}")
    lines.append(f"New monthly cost      : ${summary.total_monthly_cost:,.2f}")
    lines.append(f"Monthly cost change   : ${summary.diff_total_monthly_cost:+,.2f}")
    if summary.pct_change is not None:
        lines.append(f"Percentage change     : {summary.pct_change:+.1f}%")
    lines.append(f"Resources affected    : {summary.resource_count}")
    lines.append("")

    if summary.resources:
        lines.append("### Resource-Level Breakdown")
        lines.append("| Resource | Type | Provider | Previous | New | Δ |")
        lines.append("|----------|------|----------|----------|-----|---|")
        for r in sorted(summary.resources, key=lambda x: abs(x.diff), reverse=True):
            lines.append(
                f"| {r.name} | {r.resource_type} | {r.provider} "
                f"| ${r.previous_cost:,.2f} | ${r.monthly_cost:,.2f} "
                f"| ${r.diff:+,.2f} |"
            )

    return "\n".join(lines)
