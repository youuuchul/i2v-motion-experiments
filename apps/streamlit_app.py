"""i2v motion lab — 실험 결과 분석 대시보드 (v2 schema).

Run:
    streamlit run apps/streamlit_app.py

탭 구성:
  - Gallery: outputs/index.jsonl (v2 flat) 읽어 필터·상세·비교
  - Generate: 단일 실행 UI (기존)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

# 저장은 VM UTC, 표시는 KST. 배치 끝나고 저장 포맷도 TZ 명시로 바꿀 예정.
DISPLAY_TZ = timezone(timedelta(hours=9), name="KST")


def _parse_ts(ts: str | None) -> datetime | None:
    """ISO 8601 + legacy "YYYYMMDD-HHMMSS" 양쪽 지원. UTC 가정."""
    if not ts or not isinstance(ts, str):
        return None
    # legacy: "20260414-031829" → "2026-04-14T03:18:29"
    s = ts.replace("Z", "")
    if len(s) == 15 and s[8] == "-" and s[:8].isdigit() and s[9:].isdigit():
        s = f"{s[:4]}-{s[4:6]}-{s[6:8]}T{s[9:11]}:{s[11:13]}:{s[13:15]}"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def utc_naive_to_kst(ts: str | None) -> str | None:
    """naive ISO8601 (UTC 가정) → KST 표시 문자열."""
    dt = _parse_ts(ts)
    if dt is None:
        return ts
    return dt.astimezone(DISPLAY_TZ).strftime("%Y-%m-%d %H:%M:%S")

import i2v.models  # noqa: F401  (triggers registry)
from i2v.core.registry import registry
from i2v.core.types import GenerationRequest, VideoSpec
from i2v.prompts import PromptBuilder, PromptInputs
from i2v.utils.config import load_yaml
from i2v.utils.seed import seed_everything
from i2v.utils.video import center_crop_to_aspect

st.set_page_config(page_title="i2v motion lab", layout="wide")
st.title("i2v motion lab")

OUTPUTS_ROOT = Path("outputs")
INDEX_PATH = OUTPUTS_ROOT / "index.jsonl"

# v2 canonical taxonomy (docs/TEMPLATES.md). 사이드바 필터 순서 고정용.
CANONICAL_CATEGORIES = ["motion", "meme", "archived"]
CANONICAL_MOTION_SUBS = [
    "consume_product", "lift_to_camera",
    "dolly_in", "orbit_pan",
    "steam_rise", "surface_shimmer",
]
CANONICAL_MEME_SUBS = ["meme_ai_character", "meme_ai_animal", "meme_dance_ref"]
SUB_BY_CATEGORY = {
    "motion": CANONICAL_MOTION_SUBS,
    "meme": CANONICAL_MEME_SUBS,
}


@st.cache_data(ttl=5)
def load_index(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # tags 는 list — 필터에선 string 으로 flatten
    if "tags" in df.columns:
        df["tags_str"] = df["tags"].apply(
            lambda v: ",".join(v) if isinstance(v, list) else (v or "")
        )
    # 정렬 키 = parse 된 datetime (legacy 포맷 + ISO 둘 다 수용)
    if "started_at" in df.columns:
        df["_started_dt"] = df["started_at"].apply(_parse_ts)
        # 시간 오름차순으로 한 번 정렬 → run_num 부여 → 다시 내림차순 (표시)
        df = df.sort_values("_started_dt", ascending=True, na_position="last").reset_index(drop=True)
        df["run_num"] = range(1, len(df) + 1)

        # version: (experiment, config_hash) 그룹 내 first-seen 순서
        if "config_hash" in df.columns:
            df["version"] = (
                df.groupby(["experiment", "config_hash"], dropna=False)["run_num"]
                .rank(method="dense").astype("Int64")
            )
            # 각 (experiment, config_hash) 의 첫 등장 시점 기준 version 부여
            order = (
                df.groupby("experiment")["config_hash"]
                .transform(lambda s: pd.factorize(s)[0] + 1)
            )
            df["version"] = order.astype("Int64")
        else:
            df["version"] = pd.NA

        df = df.sort_values(
            "_started_dt", ascending=False, na_position="last"
        ).drop(columns=["_started_dt"]).reset_index(drop=True)
    # 표시용 KST 컬럼 추가
    for col in ("started_at", "finished_at"):
        if col in df.columns:
            df[f"{col}_kst"] = df[col].apply(utc_naive_to_kst)

    # input_type: mode + 이미지 소스를 한눈에 보이는 컬럼
    # t2v → "텍스트 생성", i2v → 이미지 파일명, r2v → "레퍼런스"
    def _input_type(row):
        def _s(v):
            return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
        mode = _s(row.get("mode"))
        img = _s(row.get("image_path"))
        ref_url = _s(row.get("source_ref_url"))
        if mode == "t2v":
            return "텍스트 생성"
        elif mode == "r2v":
            return "레퍼런스"
        elif img:
            name = Path(img).name
            if ref_url:
                return f"{name} (ref)"
            return name
        return mode or "?"
    df["input_type"] = df.apply(_input_type, axis=1)

    return df


@st.cache_data(ttl=5)
def load_meta(run_dir: str) -> dict:
    p = Path(run_dir) / "meta.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


TABLE_COLUMNS = [
    "run_num",
    "version",
    "started_at_kst",
    "experiment",
    "template_category",
    "template_subcategory",
    "template_secondary",
    "intent",
    "tags_str",
    "mode",
    "input_type",
    "model",
    "quant",
    "resolution_tier",
    "steps",
    "cfg",
    "seed",
    "wall_sec",
    "load_sec",
    "inference_sec",
    "steps_per_sec",
    "vram_peak_mib",
    "status",
    "archived",
    "legacy",
]


def _resolution_str(meta: dict) -> str:
    gen = meta.get("generation") or {}
    w = gen.get("width") or "?"
    h = gen.get("height") or "?"
    return f"{w}×{h}"


def _duration_str(meta: dict) -> str:
    gen = meta.get("generation") or {}
    d = gen.get("duration_s")
    fps = gen.get("fps")
    return f"{d}s @ {fps}fps" if d and fps else "?"


def _prompt_of(meta: dict, fallback_entry: dict) -> str:
    inp = meta.get("input") or {}
    return inp.get("prompt") or fallback_entry.get("prompt") or ""


def _negative_of(meta: dict, fallback_entry: dict) -> str:
    inp = meta.get("input") or {}
    return inp.get("negative_prompt") or fallback_entry.get("negative_prompt") or ""


def render_detail(entry: dict) -> None:
    run_dir = entry.get("run_dir", "")
    video_path = entry.get("video_path")
    meta = load_meta(run_dir)
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("source image")
        _render_source_image(meta, entry, compact=False)

        st.subheader("video")
        if video_path and Path(video_path).exists():
            st.video(video_path)
        elif entry.get("archived"):
            st.info(
                f"📦 archived to Drive — local video 삭제됨\n\n"
                f"`{entry.get('drive_path')}`\n\n"
                f"복원: `rclone copy {entry.get('drive_path')} {Path(video_path).parent}`"
            )
        else:
            st.warning(f"video not found: {video_path}")

    with c2:
        st.subheader("summary")
        mdl = meta.get("model") or {}
        quant_blk = mdl.get("quantization") or {}
        st.write(
            {
                "experiment": entry.get("experiment"),
                "run_num": entry.get("run_num"),
                "version": entry.get("version"),
                "config_hash": entry.get("config_hash"),
                "template": f"{entry.get('template_category')}/{entry.get('template_subcategory')}",
                "secondary": entry.get("template_secondary"),
                "intent": entry.get("intent"),
                "tags": entry.get("tags"),
                "started_at (KST)": utc_naive_to_kst(entry.get("started_at")),
                "finished_at (KST)": utc_naive_to_kst(entry.get("finished_at")),
                "mode": entry.get("mode"),
                "input_image": (meta.get("input") or {}).get("image_path"),
                "source_reference": (meta.get("input") or {}).get("source_reference"),
                "model": entry.get("model"),
                "quant_transformer": quant_blk.get("transformer"),
                "quant_text_encoder": quant_blk.get("text_encoder"),
                "offload": mdl.get("offload"),
                "resolution": _resolution_str(meta),
                "duration": _duration_str(meta),
                "steps": entry.get("steps"),
                "cfg": entry.get("cfg"),
                "seed": entry.get("seed"),
                "wall_sec": entry.get("wall_sec"),
                "load_sec": entry.get("load_sec"),
                "inference_sec": entry.get("inference_sec"),
                "steps_per_sec": entry.get("steps_per_sec"),
                "vram_peak_mib": entry.get("vram_peak_mib"),
                "status": entry.get("status"),
                "archived": entry.get("archived"),
            }
        )
        st.markdown("**prompt**")
        with st.container(border=True):
            st.markdown(_prompt_of(meta, entry) or "_(none)_")
        neg = _negative_of(meta, entry)
        if neg:
            st.markdown("**negative prompt**")
            with st.container(border=True):
                st.markdown(neg)
        if entry.get("error"):
            st.error(entry["error"])

    with st.expander("config snapshot"):
        snap = Path(run_dir) / "config.snapshot.yaml"
        if snap.exists():
            st.code(snap.read_text(), language="yaml")
        else:
            st.info("no config snapshot (legacy run)")
    with st.expander("meta.json (full)"):
        if meta:
            st.json(meta)
        else:
            st.info("no meta.json")
    with st.expander("run.log (tail 200)"):
        log = Path(run_dir) / "run.log"
        if log.exists():
            lines = log.read_text().splitlines()[-200:]
            st.code("\n".join(lines))
        else:
            st.info("no run.log (legacy run)")


def _render_source_image(meta: dict, entry: dict, *, compact: bool) -> None:
    """compare/detail 공용 — 원본 입력 이미지 썸네일을 표시."""
    inp = meta.get("input") or {}
    img_path = inp.get("image_path") or entry.get("image_path")
    mode = entry.get("mode") or inp.get("mode") or ""
    if not img_path:
        if mode == "t2v":
            st.caption("source: (t2v — no input image)")
        else:
            st.caption("source: (none)")
        return
    p = Path(img_path)
    cap = f"source: {p.name}"
    if p.exists():
        st.image(str(p), caption=cap, width=220 if compact else 360)
    else:
        st.caption(f"{cap} — _file missing_")


def _compare_card(entry: dict) -> None:
    run_dir = entry.get("run_dir", "")
    meta = load_meta(run_dir)
    st.caption(
        f"{entry.get('experiment')} · "
        f"{entry.get('template_category')}/{entry.get('template_subcategory')} · "
        f"{utc_naive_to_kst(entry.get('started_at'))} KST"
    )
    _render_source_image(meta, entry, compact=True)
    vp = entry.get("video_path")
    if vp and Path(vp).exists():
        st.video(vp)
    elif entry.get("archived"):
        st.info("📦 archived")
    st.write(
        {
            "quant": entry.get("quant"),
            "steps": entry.get("steps"),
            "cfg": entry.get("cfg"),
            "seed": entry.get("seed"),
            "resolution_tier": entry.get("resolution_tier"),
            "wall_sec": entry.get("wall_sec"),
            "vram_peak_mib": entry.get("vram_peak_mib"),
            "tags": entry.get("tags"),
        }
    )
    # 비교 관점에서 프롬프트가 중요 → 항상 노출 (자동 줄바꿈)
    st.markdown("**prompt**")
    with st.container(border=True):
        st.markdown(_prompt_of(meta, entry) or "_(none)_")
    neg = _negative_of(meta, entry)
    if neg:
        with st.expander("negative prompt"):
            st.markdown(neg)


def _unique_sorted(df: pd.DataFrame, col: str) -> list:
    if col not in df.columns:
        return []
    return sorted({v for v in df[col].dropna().tolist() if v != ""})


def gallery_tab() -> None:
    df = load_index(INDEX_PATH)
    if df.empty:
        st.info(f"no runs indexed yet. run one experiment then reload.\n\nindex: `{INDEX_PATH}`")
        return

    with st.sidebar:
        st.subheader("template filters (v2)")

        # category: 정규 순서 + 데이터에 있는 것만 노출
        available_cats = set(_unique_sorted(df, "template_category"))
        cat_options = [c for c in CANONICAL_CATEGORIES if c in available_cats]
        # v2 외 잔여값은 뒤에 (이론상 0, 방어용)
        cat_options += sorted(available_cats - set(CANONICAL_CATEGORIES))
        cats = st.multiselect(
            "category", cat_options,
            help="motion = 활성 6개 모션 프리미티브 / meme = 활성 3개 밈 / archived = 폐기된 legacy",
        )

        # subcategory: 선택된 category 따라 동적 제안, 선택 없으면 전체
        if cats:
            suggested: list[str] = []
            for c in cats:
                suggested += SUB_BY_CATEGORY.get(c, [])
            if "archived" in cats:
                suggested += sorted({
                    s for c_, s in zip(df["template_category"], df["template_subcategory"])
                    if c_ == "archived" and isinstance(s, str)
                })
        else:
            suggested = CANONICAL_MOTION_SUBS + CANONICAL_MEME_SUBS
            suggested += sorted({
                s for c_, s in zip(df["template_category"], df["template_subcategory"])
                if c_ == "archived" and isinstance(s, str)
            })
        # 중복 제거, 데이터에 존재하는 값만
        present = set(_unique_sorted(df, "template_subcategory"))
        sub_options: list[str] = []
        for s in suggested:
            if s in present and s not in sub_options:
                sub_options.append(s)
        subs = st.multiselect("subcategory", sub_options)

        intents = st.multiselect("intent", _unique_sorted(df, "intent"))

        # secondary: "camera_move/dolly_in" 포맷의 any-match
        all_sec = sorted({
            s for row in df.get("template_secondary", [])
            if isinstance(row, list) for s in row
        })
        if all_sec:
            secondary_pick = st.multiselect(
                "secondary (any-match, primary OR secondary 에 있으면)", all_sec
            )
        else:
            secondary_pick = []

        st.divider()
        st.subheader("run filters")
        exps = st.multiselect("experiment", _unique_sorted(df, "experiment"))
        modes = st.multiselect("mode", _unique_sorted(df, "mode"))
        tiers = st.multiselect("resolution_tier", _unique_sorted(df, "resolution_tier"))
        quants = st.multiselect("quant", _unique_sorted(df, "quant"))

        st.divider()
        statuses = st.multiselect("status", _unique_sorted(df, "status"))

        all_tags = sorted({t for ts in df.get("tags", []) if isinstance(ts, list) for t in ts})
        tag_pick = st.multiselect("tags (any-match)", all_tags)

        legacy_mode = st.radio("legacy", ["all", "exclude legacy", "only legacy"], index=0)
        archived_mode = st.radio("archived (drive)", ["all", "local only", "archived only"], index=0)

        st.divider()
        search = st.text_input("search (experiment contains)", "")

    f = df
    if cats: f = f[f["template_category"].isin(cats)]
    if subs: f = f[f["template_subcategory"].isin(subs)]
    if secondary_pick:
        def _hit_secondary(row):
            prim = f"{row.get('template_category')}/{row.get('template_subcategory')}"
            sec = row.get("template_secondary") or []
            return prim in secondary_pick or any(s in secondary_pick for s in sec)
        f = f[f.apply(_hit_secondary, axis=1)]
    if intents: f = f[f["intent"].isin(intents)]
    if exps: f = f[f["experiment"].isin(exps)]
    if modes: f = f[f["mode"].isin(modes)]
    if tiers: f = f[f["resolution_tier"].isin(tiers)]
    if quants: f = f[f["quant"].isin(quants)]
    if statuses: f = f[f["status"].isin(statuses)]
    if tag_pick:
        f = f[f["tags"].apply(
            lambda ts: isinstance(ts, list) and any(t in ts for t in tag_pick)
        )]
    if legacy_mode == "exclude legacy" and "legacy" in f.columns:
        f = f[~f["legacy"].fillna(False).astype(bool)]
    elif legacy_mode == "only legacy" and "legacy" in f.columns:
        f = f[f["legacy"].fillna(False).astype(bool)]
    if archived_mode == "local only" and "archived" in f.columns:
        f = f[~f["archived"].fillna(False).astype(bool)]
    elif archived_mode == "archived only" and "archived" in f.columns:
        f = f[f["archived"].fillna(False).astype(bool)]
    if search:
        f = f[f["experiment"].astype(str).str.contains(search, case=False, na=False)]

    # 집계 카드
    total = len(f)
    ok = int((f.get("status") == "ok").sum()) if "status" in f else 0
    err = int((f.get("status") == "error").sum()) if "status" in f else 0
    avg_wall = f["wall_sec"].dropna().mean() if "wall_sec" in f else None
    avg_vram = f["vram_peak_mib"].dropna().mean() if "vram_peak_mib" in f else None

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("runs", total)
    m2.metric("ok / err", f"{ok} / {err}")
    m3.metric("avg wall (s)", f"{avg_wall:.0f}" if avg_wall is not None and not pd.isna(avg_wall) else "-")
    m4.metric("avg VRAM (MiB)", f"{avg_vram:.0f}" if avg_vram is not None and not pd.isna(avg_vram) else "-")

    display_cols = [c for c in TABLE_COLUMNS if c in f.columns]
    st.dataframe(
        f[display_cols] if display_cols else f,
        use_container_width=True,
        hide_index=False,
        column_config={
            "run_num": st.column_config.NumberColumn("#", width="small", help="전역 실행 일련번호 (시간순 1..N)"),
            "version": st.column_config.NumberColumn("v", width="small", help="experiment 내 설정(config_hash) 버전"),
            "started_at_kst": st.column_config.TextColumn("started (KST)", width="medium"),
            "wall_sec": st.column_config.NumberColumn("wall_s", format="%.0f", help="전체 실행시간 (로드 + 생성)"),
            "load_sec": st.column_config.NumberColumn("load_s", format="%.0f", help="모델 로드 시간 (배치 그룹 첫 실행만)"),
            "inference_sec": st.column_config.NumberColumn("infer_s", format="%.0f", help="생성(diffusion) 순수 시간"),
            "steps_per_sec": st.column_config.NumberColumn("steps/s", format="%.3f"),
            "vram_peak_mib": st.column_config.NumberColumn("vram_MiB", format="%.0f"),
            "archived": st.column_config.CheckboxColumn("archived"),
            "legacy": st.column_config.CheckboxColumn("legacy"),
        },
    )

    st.divider()
    st.subheader("detail / compare (최대 4개 선택)")

    def _label(i: int, r: dict) -> str:
        cat = r.get("template_category") or "-"
        sub = r.get("template_subcategory") or "-"
        rn = r.get("run_num")
        ver = r.get("version")
        tag = f"#{rn}"
        if ver and not pd.isna(ver):
            tag += f" v{int(ver)}"
        return (
            f"{i} [{tag}]: {r.get('experiment')} · {cat}/{sub} · "
            f"seed={r.get('seed')} · {r.get('started_at_kst') or r.get('started_at')}"
        )

    fr = f.reset_index(drop=True)
    options = [_label(i, r.to_dict()) for i, r in fr.iterrows()]
    picked = st.multiselect("select 1~4 run(s)", options, max_selections=4)
    if not picked:
        st.info("위에서 하나 이상 선택. 2개 이상 고르면 프롬프트까지 나란히 비교.")
        return

    picked_idx = [int(s.split(" ", 1)[0]) for s in picked]
    entries = [fr.iloc[i].to_dict() for i in picked_idx]

    if len(entries) == 1:
        render_detail(entries[0])
    else:
        cols = st.columns(len(entries))
        for col, entry in zip(cols, entries):
            with col:
                _compare_card(entry)


def generate_tab() -> None:
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
        mode = st.selectbox("mode", ["i2v", "r2v", "t2v"])
        seed = st.number_input("seed", value=42, step=1)
        steps = st.number_input("inference steps", 1, 100, 25)

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Input image")
        up = st.file_uploader("image", type=["jpg", "jpeg", "png", "webp"])
        image: Image.Image | None = None
        if up is not None:
            image = ImageOps.exif_transpose(Image.open(BytesIO(up.read()))).convert("RGB")
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
            prompt_auto = st.text_area(
                "generated prompt", value=st.session_state.get("auto_prompt", ""), height=120
            )
            if st.checkbox("use generated prompt for run") and prompt_auto:
                prompt = prompt_auto

    with col_r:
        st.subheader("Generate")
        if st.button("run", type="primary", disabled=image is None):
            seed_everything(int(seed))
            spec = VideoSpec(
                width=int(width), height=int(height), fps=int(fps), duration_s=float(duration)
            )
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
                mode=mode,
                spec=spec,
                seed=int(seed),
                num_inference_steps=int(steps),
                extra={"out_dir": f"outputs/streamlit/{model_name}"},
            )
            with st.spinner("generating..."):
                result = pipe.generate(req)
            st.success(f"done: {result.video_path}")
            st.video(str(result.video_path))


tab_gallery, tab_gen = st.tabs(["Gallery", "Generate"])
with tab_gallery:
    gallery_tab()
with tab_gen:
    generate_tab()
