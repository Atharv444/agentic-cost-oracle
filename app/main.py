"""
Main orchestrator for the Agentic Cost-Oracle pipeline.

Flow:
  1. Load configuration from environment
  2. Parse Infracost JSON output
  3. Format cost data for LLM consumption
  4. Send to LLM for analysis
  5. Build and post PR comment
"""

from __future__ import annotations

import logging
import sys

from app.config import load_config
from app.infracost_parser import parse_infracost_json, format_cost_context
from app.llm_agent import analyse_costs
from app.commenter import build_comment_body, post_pr_comment

# -- Logging setup -----------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cost-oracle")


def main() -> None:
    """Run the full Cost-Oracle pipeline."""

    logger.info("=== Agentic Cost-Oracle v0.1.0 ===")

    # 1. Configuration
    cfg = load_config()
    logger.info(
        "Config loaded: repo=%s, PR=#%d, provider=%s, model=%s",
        cfg.repo_full_name, cfg.pr_number, cfg.llm_provider, cfg.llm_model,
    )

    # 2. Parse Infracost output
    logger.info("Parsing Infracost diff: %s", cfg.infracost_diff_path)
    summary = parse_infracost_json(cfg.infracost_diff_path)

    if summary is None:
        # Fall back to PR breakdown if diff is missing
        logger.warning("Diff file missing, trying PR breakdown: %s", cfg.infracost_pr_path)
        summary = parse_infracost_json(cfg.infracost_pr_path)

    if summary is None:
        logger.error("No Infracost data found. Exiting.")
        sys.exit(1)

    logger.info(
        "Cost data parsed: %d resources, $%.2f -> $%.2f (delta: $%+.2f)",
        summary.resource_count,
        summary.previous_total_monthly_cost,
        summary.total_monthly_cost,
        summary.diff_total_monthly_cost,
    )

    # 3. Check if cost change exceeds threshold
    pct = summary.pct_change
    if pct is not None and abs(pct) < cfg.cost_threshold_pct:
        logger.info(
            "Cost change (%.1f%%) below threshold (%.1f%%). "
            "Posting minimal comment.",
            pct, cfg.cost_threshold_pct,
        )
        minimal_body = (
            "## :crystal_ball: Agentic Cost-Oracle Report\n"
            "<!-- cost-oracle-bot -->\n\n"
            f":white_check_mark: **No significant cost change detected** "
            f"({pct:+.1f}%, threshold: {cfg.cost_threshold_pct:.1f}%).\n\n"
            f"Monthly cost: **${summary.total_monthly_cost:,.2f}**\n\n"
            "---\n"
            "*Powered by Agentic Cost-Oracle | :zap: Automated FinOps*"
        )
        url = post_pr_comment(minimal_body, cfg)
        logger.info("Minimal comment posted: %s", url)
        return

    # 4. Format for LLM and run analysis
    cost_context = format_cost_context(summary)
    logger.info("Sending cost data to LLM for analysis...")

    try:
        llm_response = analyse_costs(cost_context, cfg)
    except RuntimeError as exc:
        logger.error("LLM analysis failed: %s", exc)
        error_body = (
            "## :crystal_ball: Agentic Cost-Oracle Report\n"
            "<!-- cost-oracle-bot -->\n\n"
            ":warning: **LLM analysis failed.** Raw cost data below.\n\n"
            f"```\n{cost_context}\n```\n\n"
            "---\n"
            "*Powered by Agentic Cost-Oracle | :zap: Automated FinOps*"
        )
        post_pr_comment(error_body, cfg)
        sys.exit(1)

    logger.info(
        "LLM analysis complete (provider=%s, model=%s, tokens=%d+%d)",
        llm_response.provider,
        llm_response.model,
        llm_response.prompt_tokens,
        llm_response.completion_tokens,
    )

    # 5. Build and post comment
    comment_body = build_comment_body(
        llm_analysis=llm_response.content,
        cost_summary_text=cost_context,
        model_name=llm_response.model,
        provider=llm_response.provider,
    )

    url = post_pr_comment(comment_body, cfg)
    logger.info("Cost-Oracle comment posted: %s", url)
    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
