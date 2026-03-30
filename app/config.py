"""
Centralised configuration — read once from environment, validate early.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration populated from environment variables."""

    # ── GitHub context ──────────────────────────────────────
    github_token: str = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN", ""))
    repo_full_name: str = field(default_factory=lambda: os.environ.get("REPO_FULL_NAME", ""))
    pr_number: int = field(default_factory=lambda: int(os.environ.get("PR_NUMBER", "0")))

    # ── LLM provider ───────────────────────────────────────
    groq_api_key: str = field(default_factory=lambda: os.environ.get("GROQ_API_KEY", ""))
    hf_api_key: str = field(default_factory=lambda: os.environ.get("HF_API_KEY", ""))
    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "groq"))
    llm_model: str = field(
        default_factory=lambda: os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
    )

    # ── Infracost paths ────────────────────────────────────
    infracost_diff_path: Path = field(
        default_factory=lambda: Path(os.environ.get("INFRACOST_DIFF_PATH", "/tmp/infracost-diff.json"))
    )
    infracost_pr_path: Path = field(
        default_factory=lambda: Path(os.environ.get("INFRACOST_PR_PATH", "/tmp/infracost-pr.json"))
    )
    infracost_base_path: Path = field(
        default_factory=lambda: Path(os.environ.get("INFRACOST_BASE_PATH", "/tmp/infracost-base.json"))
    )

    # ── Behaviour ──────────────────────────────────────────
    cost_threshold_pct: float = field(
        default_factory=lambda: float(os.environ.get("COST_THRESHOLD_PCT", "5.0"))
    )
    dry_run: bool = field(
        default_factory=lambda: os.environ.get("DRY_RUN", "false").lower() == "true"
    )

    # ── Derived ────────────────────────────────────────────
    @property
    def llm_api_key(self) -> str:
        if self.llm_provider == "groq":
            return self.groq_api_key
        return self.hf_api_key

    def validate(self) -> list[str]:
        """Return a list of configuration errors (empty = valid)."""
        errors: list[str] = []
        if not self.github_token:
            errors.append("GITHUB_TOKEN is required")
        if not self.repo_full_name:
            errors.append("REPO_FULL_NAME is required")
        if self.pr_number <= 0:
            errors.append("PR_NUMBER must be a positive integer")
        if not self.llm_api_key:
            errors.append(f"API key for LLM provider '{self.llm_provider}' is missing")
        return errors


def load_config() -> Config:
    """Create, validate, and return configuration. Exits on fatal errors."""
    cfg = Config()
    errors = cfg.validate()
    if errors:
        for err in errors:
            print(f"❌ Config error: {err}", file=sys.stderr)
        if not cfg.dry_run:
            sys.exit(1)
    return cfg
