"""
GitHub PR Commenter -- posts / updates the Cost-Oracle analysis comment.

Uses the GitHub REST API directly (no SDK dependency) so the action
stays lightweight.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import Config

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
COMMENT_MARKER = "<!-- cost-oracle-bot -->"
COMMENT_HEADER = (
    "## :crystal_ball: Agentic Cost-Oracle Report\n"
    f"{COMMENT_MARKER}\n\n"
)


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _find_existing_comment(
    repo: str, pr_number: int, token: str
) -> int | None:
    """Find a previous Cost-Oracle comment on the PR (by hidden marker)."""
    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    headers = _github_headers(token)

    with httpx.Client(timeout=30) as client:
        page = 1
        while True:
            resp = client.get(url, headers=headers, params={"page": page, "per_page": 100})
            resp.raise_for_status()
            comments = resp.json()
            if not comments:
                break
            for comment in comments:
                if COMMENT_MARKER in comment.get("body", ""):
                    return comment["id"]
            page += 1

    return None


def build_comment_body(
    llm_analysis: str,
    cost_summary_text: str,
    model_name: str,
    provider: str,
) -> str:
    """
    Assemble the full PR comment body with header, cost table,
    LLM analysis, and footer.
    """
    lines: list[str] = [COMMENT_HEADER]

    # Cost snapshot
    lines.append("<details>\n<summary><b>:bar_chart: Raw Cost Data</b></summary>\n")
    lines.append(f"```\n{cost_summary_text}\n```\n")
    lines.append("</details>\n\n")

    # LLM analysis
    lines.append(llm_analysis)

    # Footer
    lines.append("\n\n---")
    lines.append(
        f"*Powered by [Agentic Cost-Oracle](https://github.com/agentic-cost-oracle) "
        f"| Model: `{model_name}` via {provider} "
        f"| :zap: Automated FinOps*"
    )

    return "\n".join(lines)


def post_pr_comment(body: str, cfg: Config) -> str:
    """
    Post or update the Cost-Oracle comment on the PR.

    Returns the URL of the comment.
    """
    headers = _github_headers(cfg.github_token)
    repo = cfg.repo_full_name
    pr = cfg.pr_number

    if cfg.dry_run:
        out_path = Path("/tmp/cost-oracle-comment.md")
        out_path.write_text(body, encoding="utf-8")
        logger.info("DRY RUN: comment written to %s", out_path)
        return str(out_path)

    existing_id = _find_existing_comment(repo, pr, cfg.github_token)

    with httpx.Client(timeout=30) as client:
        if existing_id:
            # Update existing comment (avoids comment spam)
            url = f"{GITHUB_API}/repos/{repo}/issues/comments/{existing_id}"
            resp = client.patch(url, json={"body": body}, headers=headers)
            resp.raise_for_status()
            comment_url = resp.json()["html_url"]
            logger.info("Updated existing comment: %s", comment_url)
        else:
            # Create new comment
            url = f"{GITHUB_API}/repos/{repo}/issues/{pr}/comments"
            resp = client.post(url, json={"body": body}, headers=headers)
            resp.raise_for_status()
            comment_url = resp.json()["html_url"]
            logger.info("Created new comment: %s", comment_url)

    # Also save locally for artifact upload
    out_path = Path("/tmp/cost-oracle-comment.md")
    out_path.write_text(body, encoding="utf-8")

    return comment_url
