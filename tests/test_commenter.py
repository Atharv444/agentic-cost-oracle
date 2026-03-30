"""
Tests for the PR commenter module.
"""

from __future__ import annotations

from app.commenter import COMMENT_MARKER, build_comment_body


class TestBuildCommentBody:
    def test_contains_marker(self) -> None:
        body = build_comment_body(
            llm_analysis="Test analysis",
            cost_summary_text="Cost: $100",
            model_name="llama-3",
            provider="groq",
        )
        assert COMMENT_MARKER in body

    def test_contains_analysis(self) -> None:
        body = build_comment_body(
            llm_analysis="**Reduce instance size**",
            cost_summary_text="Cost: $100",
            model_name="llama-3",
            provider="groq",
        )
        assert "**Reduce instance size**" in body

    def test_contains_raw_cost_data(self) -> None:
        body = build_comment_body(
            llm_analysis="Analysis",
            cost_summary_text="Previous: $50\nNew: $100",
            model_name="llama-3",
            provider="groq",
        )
        assert "Previous: $50" in body
        assert "Raw Cost Data" in body

    def test_contains_footer_with_model_info(self) -> None:
        body = build_comment_body(
            llm_analysis="Analysis",
            cost_summary_text="$100",
            model_name="llama-3.3-70b-versatile",
            provider="groq",
        )
        assert "llama-3.3-70b-versatile" in body
        assert "groq" in body
        assert "Agentic Cost-Oracle" in body
