"""Phase 2 scaffold: user image + category selections -> LLM-generated video prompt.

Kept provider-agnostic (OpenAI or Anthropic) so the i2v pipeline doesn't care which.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from i2v.utils.config import env


@dataclass
class PromptInputs:
    """User-facing inputs that describe the desired motion for an image."""

    categories: dict[str, str] = field(default_factory=dict)  # e.g. {"style": "cinematic", "action": "slow pan"}
    user_note: str = ""
    image_caption: str = ""  # optional precomputed caption
    duration_s: float = 5.0


class PromptBuilder:
    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model

    def build(self, inputs: PromptInputs) -> str:
        system = (
            "You write concise image-to-video motion prompts for a vertical 9:16 short-form clip. "
            f"Target length: {inputs.duration_s:.0f}s. Describe camera motion, subject motion, "
            "lighting changes, and mood in one tight paragraph. No hashtags, no emojis."
        )
        user = self._format_user(inputs)

        if self.provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=env("OPENAI_API_KEY", required=True))
            model = self.model or env("OPENAI_MODEL", "gpt-5-mini")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return (resp.choices[0].message.content or "").strip()

        if self.provider == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=env("ANTHROPIC_API_KEY", required=True))
            model = self.model or env("ANTHROPIC_MODEL", "claude-sonnet-4-6")
            msg = client.messages.create(
                model=model,
                max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()

        raise ValueError(f"unknown provider: {self.provider}")

    @staticmethod
    def _format_user(inputs: PromptInputs) -> str:
        lines = []
        if inputs.image_caption:
            lines.append(f"Image: {inputs.image_caption}")
        if inputs.categories:
            lines.append("Selections:")
            for k, v in inputs.categories.items():
                lines.append(f"- {k}: {v}")
        if inputs.user_note:
            lines.append(f"Note: {inputs.user_note}")
        return "\n".join(lines) or "(no extra context)"
