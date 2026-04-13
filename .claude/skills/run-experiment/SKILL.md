---
name: run-experiment
description: Launch an experiment from a YAML under configs/experiments/. Use when the user says "run <exp>" or wants to reproduce/compare runs.
---

# Run an experiment

1. Verify `.env` exists and has `HF_TOKEN` (required for most gated i2v weights). If missing, tell the user to copy from `.env.example`.
2. Locate the YAML at `configs/experiments/<name>.yaml`.
3. Run: `python scripts/run_inference.py --config configs/experiments/<name>.yaml`
4. After completion, print the `outputs/<name>/*.mp4` path and surface any OOM / dtype warnings.
5. Never commit anything under `outputs/` — it is gitignored on purpose.
