"""
Tests for configuration loading and validation.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from app.config import Config, load_config


class TestConfig:
    def test_default_values(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.llm_provider == "groq"
            assert cfg.llm_model == "llama-3.3-70b-versatile"
            assert cfg.cost_threshold_pct == 5.0
            assert cfg.dry_run is False

    def test_validates_missing_token(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            errors = cfg.validate()
            assert any("GITHUB_TOKEN" in e for e in errors)

    def test_validates_missing_repo(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "t"}, clear=True):
            cfg = Config()
            errors = cfg.validate()
            assert any("REPO_FULL_NAME" in e for e in errors)

    def test_valid_config(self) -> None:
        env = {
            "GITHUB_TOKEN": "ghp_test",
            "REPO_FULL_NAME": "owner/repo",
            "PR_NUMBER": "42",
            "GROQ_API_KEY": "gsk_test",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Config()
            errors = cfg.validate()
            assert errors == []
            assert cfg.pr_number == 42

    def test_llm_api_key_groq(self) -> None:
        env = {
            "GROQ_API_KEY": "gsk_test",
            "LLM_PROVIDER": "groq",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Config()
            assert cfg.llm_api_key == "gsk_test"

    def test_llm_api_key_huggingface(self) -> None:
        env = {
            "HF_API_KEY": "hf_test",
            "LLM_PROVIDER": "huggingface",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Config()
            assert cfg.llm_api_key == "hf_test"

    def test_dry_run_parsing(self) -> None:
        with mock.patch.dict(os.environ, {"DRY_RUN": "true"}, clear=True):
            cfg = Config()
            assert cfg.dry_run is True

        with mock.patch.dict(os.environ, {"DRY_RUN": "TRUE"}, clear=True):
            cfg = Config()
            assert cfg.dry_run is True

        with mock.patch.dict(os.environ, {"DRY_RUN": "false"}, clear=True):
            cfg = Config()
            assert cfg.dry_run is False
