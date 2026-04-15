"""Wan2.1-VACE-14B adapter (unified T2V/I2V/R2V/V2V/MV2V).

L4 24GB VRAM + 16GB CPU RAM 제약으로 양자화 필수:
- transformer: GGUF (Q4_K_M 권장, ~11.6GB) — HF hub의 GGUF 파일 경로를 직접 로드
- text_encoder (T5-XXL): bnb 4bit
- VAE/scheduler/tokenizer: 원본 diffusers 리포에서 fp16 그대로

네이티브는 16fps·16:9. 9:16 576x1024는 비네이티브.
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
        gguf_repo: str = "QuantStack/Wan2.1_14B_VACE-GGUF",
        gguf_filename: str = "Wan2.1_14B_VACE-Q4_K_M.gguf",
        dtype: str = "float16",
        device: str = "cuda",
        enable_sequential_cpu_offload: bool = True,
        enable_model_cpu_offload: bool = False,
        enable_vae_slicing: bool = True,
        quantize_text_encoder_4bit: bool = True,
    ) -> None:
        self.model_id = model_id
        self.gguf_repo = gguf_repo
        self.gguf_filename = gguf_filename
        self.dtype = getattr(torch, dtype)
        self.device = device
        self.enable_sequential_cpu_offload = enable_sequential_cpu_offload
        self.enable_model_cpu_offload = enable_model_cpu_offload
        self.enable_vae_slicing = enable_vae_slicing
        self.quantize_text_encoder_4bit = quantize_text_encoder_4bit
        self._pipe = None

    def load(self) -> None:
        if self._pipe is not None:
            return
        from diffusers import GGUFQuantizationConfig, WanVACEPipeline, WanVACETransformer3DModel
        from huggingface_hub import hf_hub_download

        gguf_path = hf_hub_download(repo_id=self.gguf_repo, filename=self.gguf_filename)
        transformer = WanVACETransformer3DModel.from_single_file(
            gguf_path,
            quantization_config=GGUFQuantizationConfig(compute_dtype=self.dtype),
            torch_dtype=self.dtype,
            config=self.model_id,
            subfolder="transformer",
        )

        kwargs = dict(torch_dtype=self.dtype, transformer=transformer)
        if self.quantize_text_encoder_4bit:
            from transformers import BitsAndBytesConfig as TFBnBConfig
            from transformers import UMT5EncoderModel

            text_encoder = UMT5EncoderModel.from_pretrained(
                self.model_id,
                subfolder="text_encoder",
                quantization_config=TFBnBConfig(load_in_4bit=True, bnb_4bit_compute_dtype=self.dtype),
                torch_dtype=self.dtype,
            )
            kwargs["text_encoder"] = text_encoder

        pipe = WanVACEPipeline.from_pretrained(self.model_id, **kwargs)

        # GGUF quantized transformer is INCOMPATIBLE with enable_sequential_cpu_offload
        # (KeyError: None in GGML_QUANT_SIZES when meta tensor wrapping runs).
        # Q3/Q4 transformer fits entirely in L4 24GB VRAM alongside 4bit T5 + VAE (~11-15GB total).
        if self.enable_model_cpu_offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(self.device)
        if self.enable_vae_slicing and hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()
        self._pipe = pipe

    def generate(self, request: GenerationRequest) -> GenerationResult:
        assert self._pipe is not None, "call .load() first"
        from PIL import Image

        spec = request.spec
        W, H, n = spec.width, spec.height, spec.num_frames
        image = request.image.resize((W, H)).convert("RGB")

        mode_kwargs: dict[str, object] = {}
        if request.mode == "i2v":
            # 첫 프레임 고정 + 나머지 inpaint
            gray = Image.new("RGB", (W, H), color=(128, 128, 128))
            black = Image.new("L", (W, H), color=0)
            white = Image.new("L", (W, H), color=255)
            mode_kwargs["video"] = [image] + [gray] * (n - 1)
            mode_kwargs["mask"] = [black] + [white] * (n - 1)
        elif request.mode == "r2v":
            refs = request.reference_images or [image]
            mode_kwargs["reference_images"] = [r.resize((W, H)).convert("RGB") for r in refs]
        elif request.mode == "t2v":
            pass
        else:
            raise ValueError(f"Unsupported mode for Wan VACE: {request.mode}")

        generator = (
            torch.Generator(device="cpu").manual_seed(request.seed)
            if request.seed is not None
            else None
        )

        out = self._pipe(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or None,
            height=H,
            width=W,
            num_frames=n,
            num_inference_steps=request.num_inference_steps or 40,
            guidance_scale=request.guidance_scale if request.guidance_scale is not None else 5.0,
            generator=generator,
            **mode_kwargs,
        )
        frames = out.frames[0]

        out_dir = Path(request.extra.get("out_dir", "outputs"))
        out_dir.mkdir(parents=True, exist_ok=True)
        video_path = out_dir / f"wan21_vace_{request.mode}_{request.seed or 'rand'}.mp4"
        save_frames_as_mp4(frames, video_path, fps=spec.fps)

        return GenerationResult(
            video_path=video_path,
            spec=spec,
            model_name=self.name,
            prompt=request.prompt,
            seed=request.seed,
            meta={"native_fps": 16, "native_aspect": "16:9", "mode": request.mode},
        )

    def unload(self) -> None:
        self._pipe = None
        torch.cuda.empty_cache()
