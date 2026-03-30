"""
LLM Agent -- sends structured cost data to Groq (Llama-3) or Hugging Face
and returns optimization recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Config

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.3-70B-Instruct"
TIMEOUT_SECONDS = 120

SYSTEM_PROMPT = (
    "You are **Cost-Oracle**, an elite MLOps and FinOps cost-optimization expert.\n"
    "\n"
    "## Your Role\n"
    "Analyse cloud infrastructure cost data from a GitHub Pull Request and produce "
    "a clear, actionable optimisation report.\n"
    "\n"
    "## Instructions\n"
    "1. Summarise the overall cost impact in 3 sentences or fewer.\n"
    "2. For EVERY resource with a cost increase, evaluate whether the increase is "
    "justified or wasteful. Justify your reasoning.\n"
    "3. Suggest concrete optimisation alternatives (e.g. switch instance family, "
    "use spot/preemptible, right-size, use reserved pricing, remove orphaned "
    "resources). Include estimated savings where possible.\n"
    "4. Flag any anti-patterns: over-provisioned storage, always-on dev instances, "
    "missing auto-scaling, unattached volumes, oversized NAT gateways, etc.\n"
    "5. If the change *reduces* costs, acknowledge the win and note any risks "
    "(e.g. under-provisioning).\n"
    "6. Assign a **Confidence Score** (0-100) for your overall analysis.\n"
    "\n"
    "## Output Format (strict Markdown)\n"
    "### Cost Impact Summary\n"
    "<concise summary>\n"
    "\n"
    "### Resource Analysis\n"
    "<per-resource analysis>\n"
    "\n"
    "### Optimisation Recommendations\n"
    "<numbered list of suggestions with estimated dollar savings>\n"
    "\n"
    "### Anti-Pattern Alerts\n"
    "<list or 'None detected'>\n"
    "\n"
    "### Confidence Score\n"
    "<score>/100 -- <one-line justification>\n"
    "\n"
    "## Rules\n"
    "- Be specific: name exact instance types, SKUs, or pricing tiers.\n"
    "- Never fabricate prices. If unsure, say 'estimated' or 'verify pricing'.\n"
    "- Keep the report under 800 words.\n"
    "- Use USD for all monetary values.\n"
)


@dataclass
class LLMResponse:
    """Parsed response from the LLM."""
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


def _call_groq(prompt: str, cfg: Config) -> LLMResponse:
    """Call Groq's OpenAI-compatible chat endpoint."""
    headers = {
        "Authorization": f"Bearer {cfg.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "top_p": 0.9,
    }

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        resp = client.post(GROQ_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    usage = data.get("usage", {})

    return LLMResponse(
        content=choice["message"]["content"],
        model=data.get("model", cfg.llm_model),
        provider="groq",
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        raw=data,
    )


def _call_huggingface(prompt: str, cfg: Config) -> LLMResponse:
    """Call Hugging Face Inference API."""
    headers = {
        "Authorization": f"Bearer {cfg.hf_api_key}",
        "Content-Type": "application/json",
    }
    combined = f"[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n{prompt} [/INST]"
    payload = {
        "inputs": combined,
        "parameters": {
            "max_new_tokens": 2048,
            "temperature": 0.3,
            "top_p": 0.9,
            "return_full_text": False,
        },
    }

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        resp = client.post(HF_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        content = data[0].get("generated_text", "")
    else:
        content = data.get("generated_text", str(data))

    return LLMResponse(
        content=content,
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="huggingface",
        raw=data if isinstance(data, dict) else {"results": data},
    )


def analyse_costs(cost_context: str, cfg: Config) -> LLMResponse:
    """
    Main entry point -- send cost context to the configured LLM provider
    and return the analysis.

    Falls back from Groq -> HuggingFace on failure.
    """
    user_prompt = (
        "Below is the infrastructure cost diff from a Pull Request. "
        "Analyse it and provide your optimisation report.\n\n"
        f"{cost_context}"
    )

    providers = [
        ("groq", _call_groq),
        ("huggingface", _call_huggingface),
    ]

    # Put configured provider first
    if cfg.llm_provider == "huggingface":
        providers.reverse()

    last_error: Exception | None = None

    for name, call_fn in providers:
        try:
            logger.info("Calling LLM provider: %s", name)
            response = call_fn(user_prompt, cfg)
            logger.info(
                "LLM response received (%s tokens prompt, %s tokens completion)",
                response.prompt_tokens,
                response.completion_tokens,
            )
            return response
        except Exception as exc:
            logger.warning("Provider %s failed: %s", name, exc)
            last_error = exc
            continue

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_error}"
    ) from last_error
