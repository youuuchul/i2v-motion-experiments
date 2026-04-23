"""meta.json v2 빌더 + index.jsonl flat 엔트리 변환.

스키마 상세: docs/SCHEMA.md

사용 예:
    meta = build_meta_v2(
        run_id=..., run_dir=..., cfg=..., preset=..., model_cfg=...,
        started_at=..., finished_at=..., status="ok", error=None,
        video_path=..., wall_sec=..., vram_peak_mib=...,
    )
    write_meta(run_dir, meta)
    append_index(outputs_root, to_index_entry(meta))
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2


def _file_sha256(path: str | Path, chunk: int = 1 << 20) -> str | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return f"sha256:{h.hexdigest()}"


def _video_size_mb(path: str | Path | None) -> float | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return round(p.stat().st_size / (1024 * 1024), 2)


def _resolution_tier(width: int, height: int) -> str:
    short = min(width, height)
    if short <= 480:
        return "smoke"
    if short <= 720:
        return "hd"
    if short <= 1080:
        return "fhd"
    return "2k"


def _probe_gpu() -> dict:
    """nvidia-smi 로 GPU 이름/VRAM 수집. 실패 시 null 값."""
    out = {"gpu": None, "vram_total_gib": None, "driver": None}
    if not shutil.which("nvidia-smi"):
        return out
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            first = res.stdout.strip().splitlines()[0]
            parts = [x.strip() for x in first.split(",")]
            if len(parts) >= 3:
                name, mem_mib, drv = parts[0], parts[1], parts[2]
                out["gpu"] = name.replace("NVIDIA ", "").strip() or None
                try:
                    out["vram_total_gib"] = round(float(mem_mib) / 1024, 1)
                except ValueError:
                    pass
                out["driver"] = drv or None
    except Exception:
        pass
    return out


def _probe_library_versions() -> dict:
    out = {"torch": None, "diffusers": None}
    try:
        import torch  # noqa: F401
        out["torch"] = torch.__version__
    except Exception:
        pass
    try:
        import diffusers  # noqa: F401
        out["diffusers"] = diffusers.__version__
    except Exception:
        pass
    return out


def _infer_quantization(model_cfg: dict) -> dict:
    init = model_cfg.get("init", {}) or {}
    gguf_filename = init.get("gguf_filename")
    q = {
        "transformer": None,
        "gguf_repo": init.get("gguf_repo"),
        "gguf_filename": gguf_filename,
        "text_encoder": None,
    }
    if gguf_filename:
        low = gguf_filename.lower()
        # "Wan2.1_14B_VACE-Q4_K_M.gguf" -> "gguf_q4_k_m"
        if "q2_k" in low: q["transformer"] = "gguf_q2_k"
        elif "q3_k_s" in low: q["transformer"] = "gguf_q3_k_s"
        elif "q3_k_m" in low: q["transformer"] = "gguf_q3_k_m"
        elif "q4_k_s" in low: q["transformer"] = "gguf_q4_k_s"
        elif "q4_k_m" in low: q["transformer"] = "gguf_q4_k_m"
        elif "q5_k_s" in low: q["transformer"] = "gguf_q5_k_s"
        elif "q5_k_m" in low: q["transformer"] = "gguf_q5_k_m"
        elif "q6_k" in low: q["transformer"] = "gguf_q6_k"
        elif "q8_0" in low: q["transformer"] = "gguf_q8_0"
        else: q["transformer"] = f"gguf_{Path(gguf_filename).stem.lower()}"
    else:
        q["transformer"] = init.get("dtype") or "fp16"

    if init.get("quantize_text_encoder_4bit"):
        q["text_encoder"] = "bnb_nf4"
    else:
        q["text_encoder"] = "fp16"
    return q


def _infer_offload(model_cfg: dict) -> str:
    init = model_cfg.get("init", {}) or {}
    if init.get("enable_sequential_cpu_offload"):
        return "sequential_cpu_offload"
    if init.get("enable_model_cpu_offload"):
        return "model_cpu_offload"
    return "none"


def compute_config_hash(meta: dict) -> str:
    """실험 재현성 기준 필드로 sha1 짧은 해시.

    같은 해시 = 같은 version (prompt/seed/steps/cfg/model/quant/image 동일).
    run_id / 시간 / 경로 / 결과는 제외.
    """
    inp = meta.get("input") or {}
    gen = meta.get("generation") or {}
    mdl = meta.get("model") or {}
    qnt = mdl.get("quantization") or {}
    payload = {
        "mode": inp.get("mode"),
        "image_path": inp.get("image_path"),
        "prompt": (inp.get("prompt") or "").strip(),
        "negative_prompt": (inp.get("negative_prompt") or "").strip(),
        "seed": gen.get("seed"),
        "steps": gen.get("num_inference_steps"),
        "cfg": gen.get("guidance_scale"),
        "width": gen.get("width"),
        "height": gen.get("height"),
        "fps": gen.get("fps"),
        "duration_s": gen.get("duration_s"),
        "model_name": mdl.get("name"),
        "quant_transformer": qnt.get("transformer"),
        "quant_text_encoder": qnt.get("text_encoder"),
        "offload": mdl.get("offload"),
        "lora": mdl.get("lora") or [],
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return "sha1:" + hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def build_meta_v2(
    *,
    run_id: str,
    run_dir: Path,
    config_path: Path,
    cfg: dict,
    preset: dict,
    model_cfg: dict,
    started_at: str,
    finished_at: str,
    status: str,
    error: str | None,
    video_path: Path | None,
    wall_sec: float | None,
    vram_peak_mib: float | None,
    load_sec: float | None = None,
    inference_sec: float | None = None,
    host: str | None = None,
) -> dict[str, Any]:
    inp = cfg.get("input", {}) or {}
    run_block = cfg.get("run", {}) or {}
    tmpl = cfg.get("template", {}) or {}
    width = int(preset.get("width", 0))
    height = int(preset.get("height", 0))
    fps = int(preset.get("fps", 0))
    duration_s = float(preset.get("duration_s", 0.0) or 0.0)
    num_frames = int(round(fps * duration_s)) if fps and duration_s else None

    libs = _probe_library_versions()
    gpu_info = _probe_gpu()

    steps = run_block.get("num_inference_steps")
    steps_per_sec = None
    if steps and inference_sec:
        try:
            steps_per_sec = round(float(steps) / float(inference_sec), 3)
        except Exception:
            steps_per_sec = None

    image_path = inp.get("image")

    meta = {
        "schema_version": SCHEMA_VERSION,
        "legacy": False,
        "run": {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "config_path": str(config_path),
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "error": error,
        },
        "experiment": {
            "name": cfg.get("experiment") or config_path.stem,
            "notes": cfg.get("notes"),
            "tags": list(cfg.get("tags", []) or []),
        },
        "template": {
            "template_id": tmpl.get("template_id"),
            "motion_template": tmpl.get("motion_template"),
            "meme_template": tmpl.get("meme_template"),
            "category": tmpl.get("category"),
            "subcategory": tmpl.get("subcategory"),
            "intent": tmpl.get("intent"),
            "secondary": list(tmpl.get("secondary", []) or []),
            "promoted_at": tmpl.get("promoted_at"),
        },
        "input": {
            "mode": inp.get("mode", "i2v"),
            "image_path": image_path,
            "image_hash": _file_sha256(image_path) if image_path else None,
            "reference_images": list(inp.get("reference_images", []) or []),
            "source_reference": inp.get("source_reference"),
            "prompt": inp.get("prompt", ""),
            "negative_prompt": inp.get("negative_prompt", ""),
        },
        "model": {
            "name": model_cfg.get("name"),
            "class": model_cfg.get("class"),
            "version": f"diffusers-{libs['diffusers']}" if libs["diffusers"] else None,
            "quantization": _infer_quantization(model_cfg),
            "offload": _infer_offload(model_cfg),
            "lora": list(model_cfg.get("lora", []) or []),
        },
        "generation": {
            "seed": run_block.get("seed"),
            "num_inference_steps": steps,
            "guidance_scale": run_block.get("guidance_scale"),
            "width": width,
            "height": height,
            "fps": fps,
            "num_frames": num_frames,
            "duration_s": duration_s,
            "aspect": preset.get("aspect"),
            "resolution_tier": _resolution_tier(width, height) if width and height else None,
        },
        "output": {
            "video_path": str(video_path) if video_path else None,
            "video_size_mb": _video_size_mb(video_path),
            "archived": False,
            "drive_path": None,
            "archived_at": None,
        },
        "metrics": {
            "wall_sec": wall_sec,
            "load_sec": load_sec,
            "inference_sec": inference_sec,
            "vram_peak_mib": vram_peak_mib,
            "ram_peak_mib": None,
            "steps_per_sec": steps_per_sec,
        },
        "environment": {
            "gpu": gpu_info["gpu"],
            "vram_total_gib": gpu_info["vram_total_gib"],
            "host": host or os.environ.get("HOST_LABEL") or "unknown",
            "driver": gpu_info["driver"],
            "torch": libs["torch"],
            "diffusers": libs["diffusers"],
        },
    }
    meta["run"]["config_hash"] = compute_config_hash(meta)
    return meta


def to_index_entry(meta: dict) -> dict:
    """meta.json → index.jsonl flat 엔트리."""
    run = meta.get("run", {})
    exp = meta.get("experiment", {})
    tmpl = meta.get("template", {})
    inp = meta.get("input", {})
    mdl = meta.get("model", {})
    gen = meta.get("generation", {})
    out = meta.get("output", {})
    met = meta.get("metrics", {})
    return {
        "schema_version": meta.get("schema_version"),
        "run_id": run.get("run_id"),
        "config_hash": run.get("config_hash"),
        "experiment": exp.get("name"),
        "tags": exp.get("tags", []),
        "template_id": tmpl.get("template_id"),
        "motion_template": tmpl.get("motion_template"),
        "meme_template": tmpl.get("meme_template"),
        "template_category": tmpl.get("category"),
        "template_subcategory": tmpl.get("subcategory"),
        "template_secondary": [
            f"{s.get('category')}/{s.get('subcategory')}"
            for s in (tmpl.get("secondary") or [])
            if isinstance(s, dict)
        ],
        "intent": tmpl.get("intent"),
        "model": mdl.get("name"),
        "quant": (mdl.get("quantization") or {}).get("transformer"),
        "mode": inp.get("mode"),
        "image_path": inp.get("image_path"),
        "source_ref_url": (inp.get("source_reference") or {}).get("url"),
        "seed": gen.get("seed"),
        "steps": gen.get("num_inference_steps"),
        "cfg": gen.get("guidance_scale"),
        "width": gen.get("width"),
        "height": gen.get("height"),
        "fps": gen.get("fps"),
        "resolution_tier": gen.get("resolution_tier"),
        "wall_sec": met.get("wall_sec"),
        "load_sec": met.get("load_sec"),
        "inference_sec": met.get("inference_sec"),
        "steps_per_sec": met.get("steps_per_sec"),
        "vram_peak_mib": met.get("vram_peak_mib"),
        "status": run.get("status"),
        "error": run.get("error"),
        "archived": out.get("archived", False),
        "drive_path": out.get("drive_path"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "video_path": out.get("video_path"),
        "run_dir": run.get("run_dir"),
        "legacy": meta.get("legacy", False),
    }


def build_run_id(experiment: str, started_at: str, seed: int | None) -> str:
    """run_id = {experiment}_{YYYYMMDDTHHMMSS}_seed{N}"""
    ts = started_at.replace("-", "").replace(":", "").replace("T", "T")
    seed_part = f"seed{seed}" if seed is not None else "seedrand"
    return f"{experiment}_{ts}_{seed_part}"
