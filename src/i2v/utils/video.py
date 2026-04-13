from __future__ import annotations

from pathlib import Path
from typing import Iterable

import imageio.v3 as iio
import numpy as np
from PIL import Image


def save_frames_as_mp4(frames: Iterable[Image.Image | np.ndarray], path: Path, fps: int = 24) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.stack([np.asarray(f) if not isinstance(f, np.ndarray) else f for f in frames])
    iio.imwrite(path, arr, fps=fps, codec="libx264", macro_block_size=1)
    return path


def center_crop_to_aspect(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop to the target aspect ratio (cover), then resize to exact size."""
    src_w, src_h = image.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        off = (src_w - new_w) // 2
        image = image.crop((off, 0, off + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        off = (src_h - new_h) // 2
        image = image.crop((0, off, src_w, off + new_h))
    return image.resize((target_w, target_h), Image.LANCZOS)
