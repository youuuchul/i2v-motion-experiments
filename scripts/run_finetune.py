"""Fine-tuning entry point — scaffold only.

Implement per-model LoRA / full-finetune loops under src/i2v/training/
and dispatch from here using the experiment YAML.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()
    raise NotImplementedError(
        f"finetune pipeline not implemented yet. config={args.config}"
    )


if __name__ == "__main__":
    main()
