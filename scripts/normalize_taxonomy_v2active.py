"""index.jsonl + meta.json 의 template.category/subcategory 를 v2 활성 9개 템플릿으로 재맵핑.

활성 v2 (docs/TEMPLATES.md 2026-04-16):
  category:    motion | meme | archived
  subcategory (motion): consume_product / lift_to_camera / dolly_in / orbit_pan / steam_rise / surface_shimmer
  subcategory (meme):   meme_ai_character / meme_ai_animal / meme_dance_ref
  subcategory (archived): 원본 이름 유지 (face_reveal / rim_light / silhouette / golden_hour / bokeh / rack_focus / smoke_test 등)

Usage:
    python scripts/normalize_taxonomy_v2active.py --dry-run
    python scripts/normalize_taxonomy_v2active.py            # 실제 적용 (백업 자동 생성)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


# 실험 이름 → (category, subcategory) — v2 활성 기준
#
# 근거: docs/TEMPLATES.md "기존 config → 6개 템플릿 맵핑" 표.
EXPERIMENT_MAP: dict[str, tuple[str, str]] = {
    # --- archived ---
    "smoke_wan2_1_vace_14b":                    ("archived", "smoke_test"),
    "wan_vace_beer_man_topview_face_reveal":    ("archived", "face_reveal"),
    "wan_vace_coffee_man_rim_light":            ("archived", "rim_light"),
    "wan_vace_coffee_man_silhouette":           ("archived", "silhouette"),
    "wan_vace_man_box_face_reveal":             ("archived", "face_reveal"),
    "wan_vace_man_object_face_reveal":          ("archived", "face_reveal"),
    "wan_vace_sample_ambiance_bokeh":           ("archived", "bokeh"),
    "wan_vace_sample_focus_shift":              ("archived", "rack_focus"),
    "wan_vace_sample_golden_hour":              ("archived", "golden_hour"),
    # --- motion (6 primitives) ---
    "wan_vace_beer_drink_ripple":               ("motion", "surface_shimmer"),
    "wan_vace_beer_food_glaze":                 ("motion", "surface_shimmer"),
    "wan_vace_beer_food_steam":                 ("motion", "steam_rise"),
    "wan_vace_beer_man_topview_lift":           ("motion", "lift_to_camera"),
    "wan_vace_beer_man_topview_steam":          ("motion", "steam_rise"),
    "wan_vace_beer_menu_hero":                  ("motion", "dolly_in"),
    "wan_vace_coffee_consume_drink":            ("motion", "consume_product"),
    "wan_vace_coffee_man_dolly_in":             ("motion", "dolly_in"),
    "wan_vace_coffee_man_dolly_pan":            ("motion", "orbit_pan"),
    "wan_vace_coffee_man_lift_to_camera":       ("motion", "lift_to_camera"),
    "wan_vace_coffee_man_offer_drink":          ("motion", "lift_to_camera"),
    "wan_vace_coffee_man_surface_shimmer":      ("motion", "surface_shimmer"),
    "wan_vace_man_box_dolly_in":                ("motion", "dolly_in"),
    "wan_vace_man_box_gesture_point":           ("motion", "lift_to_camera"),
    "wan_vace_man_box_lift_to_camera":          ("motion", "lift_to_camera"),
    "wan_vace_man_box_orbit_pan":               ("motion", "orbit_pan"),
    "wan_vace_man_object_dolly_in":             ("motion", "dolly_in"),
    "wan_vace_man_object_gesture_point":        ("motion", "lift_to_camera"),
    "wan_vace_man_object_lift_to_camera":       ("motion", "lift_to_camera"),
    "wan_vace_man_object_orbit_pan":            ("motion", "orbit_pan"),
    "wan_vace_man_object_surface_shimmer":      ("motion", "surface_shimmer"),
    "wan_vace_sample_consume_product":          ("motion", "consume_product"),
    "wan_vace_sample_drink_ripple":             ("motion", "surface_shimmer"),
    "wan_vace_sample_gesture_point":            ("motion", "lift_to_camera"),
    "wan_vace_sample_lift_to_camera":           ("motion", "lift_to_camera"),
    "wan_vace_sample_offer_drink":              ("motion", "lift_to_camera"),
    "wan_vace_sample_steam_rise":               ("motion", "steam_rise"),
    # --- meme (v1 → v2 retag; 기존 v1 entry 만 여기서 재분류. 이미 meme/* 는 skip) ---
    "wan_vace_beer_meme_ai_animal":             ("meme", "meme_ai_animal"),
    "wan_vace_beer_meme_ai_character":          ("meme", "meme_ai_animal"),  # 문서상 실제 외부 캐릭터 → animal
}

# subcategory → motion_template / meme_template 자동 기입
MOTION_SUBS = {"consume_product", "lift_to_camera", "dolly_in", "orbit_pan", "steam_rise", "surface_shimmer"}
MEME_SUBS = {"meme_ai_character", "meme_ai_animal", "meme_dance_ref"}


def _remap_meta(meta: dict, category: str, subcategory: str) -> bool:
    """meta.json 의 template 블록을 v2로 갱신. 변경 있을 때 True."""
    tmpl = meta.setdefault("template", {})
    old = (tmpl.get("category"), tmpl.get("subcategory"))
    if old == (category, subcategory) and tmpl.get("motion_template") is not None or tmpl.get("meme_template") is not None:
        # 이미 v2 형태이고 motion_template/meme_template 채워져 있으면 skip
        pass
    tmpl["category"] = category
    tmpl["subcategory"] = subcategory
    if subcategory in MOTION_SUBS:
        tmpl["motion_template"] = subcategory
        tmpl["meme_template"] = None
    elif subcategory in MEME_SUBS:
        tmpl["motion_template"] = None
        tmpl["meme_template"] = subcategory
    else:  # archived
        tmpl["motion_template"] = None
        tmpl["meme_template"] = None
    return True


def _remap_index_entry(entry: dict, category: str, subcategory: str) -> None:
    entry["template_category"] = category
    entry["template_subcategory"] = subcategory
    if subcategory in MOTION_SUBS:
        entry["motion_template"] = subcategory
        entry["meme_template"] = None
    elif subcategory in MEME_SUBS:
        entry["motion_template"] = None
        entry["meme_template"] = subcategory
    else:
        entry["motion_template"] = None
        entry["meme_template"] = None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    idx_path = args.outputs_root / "index.jsonl"
    if not idx_path.exists():
        sys.exit(f"no index.jsonl at {idx_path}")

    rows = []
    for line in idx_path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))

    changed_idx = 0
    meta_changed = 0
    meta_missing = 0
    skipped_already_v2 = 0
    unmapped: list[str] = []

    for entry in rows:
        exp = entry.get("experiment")
        old_cat = entry.get("template_category")
        old_sub = entry.get("template_subcategory")

        # 이미 v2 (motion/meme/archived) + 매핑이 정확하면 skip
        v2_cats = {"motion", "meme", "archived"}
        if old_cat in v2_cats and exp not in EXPERIMENT_MAP:
            skipped_already_v2 += 1
            continue

        mapping = EXPERIMENT_MAP.get(exp)
        if mapping is None:
            # 매핑 없는 실험 — v2 형태인지 확인
            if old_cat in v2_cats:
                skipped_already_v2 += 1
                continue
            unmapped.append(exp)
            continue

        category, subcategory = mapping
        if (old_cat, old_sub) != (category, subcategory) or entry.get("motion_template") is None and entry.get("meme_template") is None:
            _remap_index_entry(entry, category, subcategory)
            changed_idx += 1

        # meta.json 갱신
        run_dir = entry.get("run_dir")
        if not run_dir:
            continue
        meta_path = Path(run_dir) / "meta.json"
        if not meta_path.exists():
            meta_missing += 1
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta_missing += 1
            continue
        if _remap_meta(meta, category, subcategory):
            meta_changed += 1
            if not args.dry_run:
                bak = meta_path.with_suffix(".json.pre_v2active.bak")
                if not bak.exists():
                    shutil.copy2(meta_path, bak)
                meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"[normalize] total rows:             {len(rows)}")
    print(f"[normalize] index entries changed:  {changed_idx}")
    print(f"[normalize] meta.json files changed:{meta_changed}")
    print(f"[normalize] meta.json missing:      {meta_missing}")
    print(f"[normalize] already v2 (skipped):   {skipped_already_v2}")
    if unmapped:
        print("[normalize] UNMAPPED experiments (left unchanged):")
        for e in sorted(set(unmapped)):
            print(f"   - {e}")

    if args.dry_run:
        print("[normalize] --dry-run: index.jsonl / meta.json 원본 보존")
        return

    bak = idx_path.with_suffix(".jsonl.pre_v2active.bak")
    if not bak.exists():
        shutil.copy2(idx_path, bak)
    with idx_path.open("w") as f:
        for e in rows:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"[normalize] wrote: {idx_path}  (backup: {bak})")


if __name__ == "__main__":
    main()
