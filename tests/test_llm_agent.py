"""
Tests for the LLM agent module.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from app.llm_agent import SYSTEM_PROMPT, LLMResponse


class TestSystemPrompt:
    """Validate the system prompt contains critical instructions."""

    def test_contains_role(self) -> None:
        assert "Cost-Oracle" in SYSTEM_PROMPT

    def test_contains_output_format(self) -> None:
        assert "Cost Impact Summary" in SYSTEM_PROMPT
        assert "Optimisation Recommendations" in SYSTEM_PROMPT
        assert "Confidence Score" in SYSTEM_PROMPT

    def test_contains_guardrails(self) -> None:
        assert "Never fabricate prices" in SYSTEM_PROMPT
        assert "800 words" in SYSTEM_PROMPT
        assert "USD" in SYSTEM_PROMPT


class TestLLMResponse:
    def test_dataclass_fields(self) -> None:
        resp = LLMResponse(
            content="Test content",
            model="llama-3",
            provider="groq",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert resp.content == "Test content"
        assert resp.model == "llama-3"
        assert resp.provider == "groq"
        assert resp.prompt_tokens == 100
        assert resp.completion_tokens == 50
        assert resp.raw == {}
