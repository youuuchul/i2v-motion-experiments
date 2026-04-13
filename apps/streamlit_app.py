"""Prototype UI for i2v experiments.

Run: streamlit run apps/streamlit_app.py
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image

import i2v.models  # noqa: F401  (triggers registry)
from i2v.core.registry import registry
from i2v.core.types import GenerationRequest, VideoSpec
from i2v.prompts import PromptBuilder, PromptInputs
from i2v.utils.config import load_yaml
from i2v.utils.seed import seed_everything
from i2v.utils.video import center_crop_to_aspect

st.set_page_config(page_title="i2v motion lab", layout="wide")
st.title("i2v motion lab")

with st.sidebar:
    st.subheader("Model")
    model_name = st.selectbox("pipeline", registry.list() or ["(none registered)"])

    st.subheader("Video spec")
    preset_path = Path("configs/presets/reels_5s.yaml")
    preset = load_yaml(preset_path) if preset_path.exists() else {}
    duration = st.slider("duration (s)", 3.0, 15.0, float(preset.get("duration_s", 5.0)), 0.5)
    fps = st.number_input("fps", 8, 60, int(preset.get("fps", 24)))
    width = st.number_input("width", 256, 2048, int(preset.get("width", 576)), step=16)
    height = st.number_input("height", 256, 2048, int(preset.get("height", 1024)), step=16)

    st.subheader("Run")
    seed = st.number_input("seed", value=42, step=1)
    steps = st.number_input("inference steps", 1, 100, 25)

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Input image")
    up = st.file_uploader("image", type=["jpg", "jpeg", "png", "webp"])
    image: Image.Image | None = None
    if up is not None:
        image = Image.open(BytesIO(up.read())).convert("RGB")
        st.image(image, caption="original", use_column_width=True)

    st.subheader("Prompt")
    tab_manual, tab_auto = st.tabs(["manual", "auto (LLM)"])
    with tab_manual:
        prompt = st.text_area("prompt", height=100)
        negative = st.text_area("negative prompt", height=60)
    with tab_auto:
        style = st.text_input("style", "cinematic")
        action = st.text_input("action", "slow dolly-in")
        mood = st.text_input("mood", "warm, golden hour")
        note = st.text_area("user note")
        provider = st.selectbox("LLM provider", ["openai", "anthropic"])
        if st.button("generate prompt"):
            pb = PromptBuilder(provider=provider)
            prompt_out = pb.build(
                PromptInputs(
                    categories={"style": style, "action": action, "mood": mood},
                    user_note=note,
                    duration_s=duration,
                )
            )
            st.session_state["auto_prompt"] = prompt_out
        prompt_auto = st.text_area("generated prompt", value=st.session_state.get("auto_prompt", ""), height=120)
        use_auto = st.checkbox("use generated prompt for run")
        if use_auto and prompt_auto:
            prompt = prompt_auto

with col_r:
    st.subheader("Generate")
    if st.button("run", type="primary", disabled=image is None):
        seed_everything(int(seed))
        spec = VideoSpec(width=int(width), height=int(height), fps=int(fps), duration_s=float(duration))
        prepared = center_crop_to_aspect(image, spec.width, spec.height)
        pipe_cls = registry.get(model_name)
        model_cfg = load_yaml(Path("configs/models") / f"{model_name}.yaml")
        pipe = pipe_cls(**model_cfg.get("init", {}))
        with st.spinner("loading model..."):
            pipe.load()
        req = GenerationRequest(
            image=prepared,
            prompt=prompt or "",
            negative_prompt=negative if "negative" in dir() else "",
            spec=spec,
            seed=int(seed),
            num_inference_steps=int(steps),
            extra={"out_dir": f"outputs/streamlit/{model_name}"},
        )
        with st.spinner("generating..."):
            result = pipe.generate(req)
        st.success(f"done: {result.video_path}")
        st.video(str(result.video_path))
