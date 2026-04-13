"""Run one experiment YAML end-to-end.

Usage:
    python scripts/run_inference.py --config configs/experiments/example_svd_5s.yaml
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from PIL import Image

import i2v.models  # noqa: F401  (trigger registry)
from i2v.core.registry import registry
from i2v.core.types import GenerationRequest, VideoSpec
from i2v.utils.config import load_yaml
from i2v.utils.seed import seed_everything
from i2v.utils.video import center_crop_to_aspect


def _build_pipeline(model_cfg: dict):
    cls_path = model_cfg["class"]
    module_name, cls_name = cls_path.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_name), cls_name)
    pipe = cls(**model_cfg.get("init", {}))
    pipe.load()
    return pipe


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    model_cfg = load_yaml(cfg["model_config"])
    preset = load_yaml(cfg["preset"])
    run = cfg["run"]

    if (seed := run.get("seed")) is not None:
        seed_everything(seed)

    spec = VideoSpec(**preset)
    image = Image.open(cfg["input"]["image"]).convert("RGB")
    image = center_crop_to_aspect(image, spec.width, spec.height)

    _ = registry  # keeps import used
    pipe = _build_pipeline(model_cfg)

    request = GenerationRequest(
        image=image,
        prompt=cfg["input"].get("prompt", ""),
        negative_prompt=cfg["input"].get("negative_prompt", ""),
        spec=spec,
        seed=seed,
        guidance_scale=run.get("guidance_scale"),
        num_inference_steps=run.get("num_inference_steps"),
        extra={"out_dir": run.get("out_dir", "outputs")},
    )
    result = pipe.generate(request)
    print(f"saved -> {result.video_path}")


if __name__ == "__main__":
    main()
