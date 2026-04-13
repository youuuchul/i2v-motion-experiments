from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from PIL import Image
from pydantic import BaseModel, Field, field_validator


class VideoSpec(BaseModel):
    """Output video spec. 9:16 vertical is the default target (Reels/Shorts)."""

    width: int = 576
    height: int = 1024
    fps: int = 24
    duration_s: float = 5.0
    aspect: Literal["9:16", "16:9", "1:1"] = "9:16"

    @property
    def num_frames(self) -> int:
        return max(1, int(round(self.fps * self.duration_s)))

    @field_validator("duration_s")
    @classmethod
    def _check_duration(cls, v: float) -> float:
        if not 3.0 <= v <= 15.0:
            raise ValueError("duration_s must be within [3, 15] seconds")
        return v


class GenerationRequest(BaseModel):
    """One i2v generation job, model-agnostic."""

    model_config = {"arbitrary_types_allowed": True}

    image: Image.Image
    prompt: str = ""
    negative_prompt: str = ""
    spec: VideoSpec = Field(default_factory=VideoSpec)
    seed: int | None = None
    guidance_scale: float | None = None
    num_inference_steps: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    """Result payload. `video_path` points to the saved mp4; frames optional for in-memory use."""

    model_config = {"arbitrary_types_allowed": True}

    video_path: Path
    spec: VideoSpec
    model_name: str
    prompt: str
    seed: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
