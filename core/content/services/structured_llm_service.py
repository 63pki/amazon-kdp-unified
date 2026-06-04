"""Stub for youngReader StructuredBookPlanningService — replaced by direct Anthropic calls."""
import anthropic
import json
import os
from typing import Optional


class StructuredBookPlanningService:
    """Thin wrapper around the Anthropic SDK for structured book planning."""

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or os.getenv("LLM_MODEL", "claude-opus-4-5")
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def plan_book(self, prompt: str, schema: Optional[dict] = None) -> dict:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    def generate(self, system: str, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
