"""Stable Video Diffusion adapter (image-only i2v).

Reference implementation — pattern for teammates adding other models.
Not loaded eagerly; `load()` is idempotent.
"""
from __future__ import annotations

from pathlib import Path

import torch

from i2v.core.base import BasePipeline
from i2v.core.registry import registry
from i2v.core.types import GenerationRequest, GenerationResult
from i2v.utils.video import save_frames_as_mp4


@registry.register("svd")
class SVDPipeline(BasePipeline):
    def __init__(
        self,
        model_id: str = "stabilityai/stable-video-diffusion-img2vid-xt",
        dtype: str = "bfloat16",
        device: str = "cuda",
    ) -> None:
        self.model_id = model_id
        self.dtype = getattr(torch, dtype)
        self.device = device
        self._pipe = None

    def load(self) -> None:
        if self._pipe is not None:
            return
        from diffusers import StableVideoDiffusionPipeline

        self._pipe = StableVideoDiffusionPipeline.from_pretrained(
            self.model_id, torch_dtype=self.dtype
        ).to(self.device)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        assert self._pipe is not None, "call .load() first"
        spec = request.spec
        image = request.image.resize((spec.width, spec.height))
        generator = (
            torch.Generator(device=self.device).manual_seed(request.seed)
            if request.seed is not None
            else None
        )
        frames = self._pipe(
            image,
            num_frames=spec.num_frames,
            num_inference_steps=request.num_inference_steps or 25,
            generator=generator,
        ).frames[0]

        out_dir = Path(request.extra.get("out_dir", "outputs"))
        out_dir.mkdir(parents=True, exist_ok=True)
        video_path = out_dir / f"svd_{request.seed or 'rand'}.mp4"
        save_frames_as_mp4(frames, video_path, fps=spec.fps)

        return GenerationResult(
            video_path=video_path,
            spec=spec,
            model_name=self.name,
            prompt=request.prompt,
            seed=request.seed,
        )

    def unload(self) -> None:
        self._pipe = None
        torch.cuda.empty_cache()
