"""Wan2.1-VACE-14B adapter (unified T2V/I2V/R2V/V2V/MV2V).

L4 24GB 환경 제약: model offload / t5 CPU / fp16 필수 영역.
네이티브는 16fps·16:9 (480P 832x480, 720P 1280x720). 9:16 576x1024는 비네이티브.
"""
from __future__ import annotations

from pathlib import Path

import torch

from i2v.core.base import BasePipeline
from i2v.core.registry import registry
from i2v.core.types import GenerationRequest, GenerationResult
from i2v.utils.video import save_frames_as_mp4


@registry.register("wan2_1_vace_14b")
class Wan21VACE14BPipeline(BasePipeline):
    def __init__(
        self,
        model_id: str = "Wan-AI/Wan2.1-VACE-14B-diffusers",
        dtype: str = "float16",
        device: str = "cuda",
        enable_model_cpu_offload: bool = True,
        enable_vae_slicing: bool = True,
    ) -> None:
        self.model_id = model_id
        self.dtype = getattr(torch, dtype)
        self.device = device
        self.enable_model_cpu_offload = enable_model_cpu_offload
        self.enable_vae_slicing = enable_vae_slicing
        self._pipe = None

    def load(self) -> None:
        if self._pipe is not None:
            return
        from diffusers import WanVACEPipeline

        pipe = WanVACEPipeline.from_pretrained(self.model_id, torch_dtype=self.dtype)
        if self.enable_model_cpu_offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(self.device)
        if self.enable_vae_slicing and hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
        self._pipe = pipe

    def generate(self, request: GenerationRequest) -> GenerationResult:
        assert self._pipe is not None, "call .load() first"
        spec = request.spec
        image = request.image.resize((spec.width, spec.height))

        generator = (
            torch.Generator(device="cpu").manual_seed(request.seed)
            if request.seed is not None
            else None
        )

        # VACE는 native 16fps. spec.fps(24)로 맞추려면 생성은 16fps 길이로 뽑고 저장만 24로 리샘플해도 되지만,
        # 여기서는 단순화를 위해 spec.num_frames를 그대로 요청하고 저장 fps만 spec에 맞춘다.
        out = self._pipe(
            image=image,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or None,
            height=spec.height,
            width=spec.width,
            num_frames=spec.num_frames,
            num_inference_steps=request.num_inference_steps or 40,
            guidance_scale=request.guidance_scale if request.guidance_scale is not None else 5.0,
            generator=generator,
        )
        frames = out.frames[0]

        out_dir = Path(request.extra.get("out_dir", "outputs"))
        out_dir.mkdir(parents=True, exist_ok=True)
        video_path = out_dir / f"wan21_vace_{request.seed or 'rand'}.mp4"
        save_frames_as_mp4(frames, video_path, fps=spec.fps)

        return GenerationResult(
            video_path=video_path,
            spec=spec,
            model_name=self.name,
            prompt=request.prompt,
            seed=request.seed,
            meta={"native_fps": 16, "native_aspect": "16:9"},
        )

    def unload(self) -> None:
        self._pipe = None
        torch.cuda.empty_cache()
