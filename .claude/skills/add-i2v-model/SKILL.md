---
name: add-i2v-model
description: Scaffold a new i2v model adapter under src/i2v/models/<name>.py, register it, and create configs/models/<name>.yaml. Use when the user wants to add a new i2v pipeline (e.g. cogvideox, wan, ltx, hunyuan).
---

# Add a new i2v model adapter

## Steps
1. Ask the user for: `<name>` (slug), HF `model_id`, whether it accepts text prompts, and any special init kwargs.
2. Create `src/i2v/models/<name>.py`:
   - subclass `i2v.core.base.BasePipeline`
   - decorate with `@registry.register("<name>")`
   - implement `load()` (idempotent), `generate(request) -> GenerationResult`, and optional `unload()`
   - use `request.spec` for width/height/fps/num_frames — never hardcode
   - save output with `i2v.utils.video.save_frames_as_mp4`
3. Create `configs/models/<name>.yaml` with `name`, `class`, `init:` dict.
4. Add a minimal experiment YAML under `configs/experiments/example_<name>_5s.yaml` copying the structure of `example_svd_5s.yaml`.
5. Add a registry test in `tests/` that asserts `"<name>" in registry.list()`.

## Invariants (do not break)
- The adapter must not import from `i2v.training`, `i2v.eval`, or `i2v.serving`.
- Output must respect `VideoSpec` (9:16 default). If the model has a fixed native resolution, resize in `generate()`.
- No hardcoded paths — read `out_dir` from `request.extra`.
