from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_ENV_LOADED = False


def load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    _ENV_LOADED = True


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    load_env()
    v = os.environ.get(name, default)
    if required and not v:
        raise RuntimeError(f"env var {name} is required but not set")
    return v
