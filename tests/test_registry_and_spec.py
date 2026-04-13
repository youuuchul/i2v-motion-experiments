import pytest

from i2v.core.registry import registry
from i2v.core.types import VideoSpec


def test_video_spec_num_frames():
    spec = VideoSpec(fps=24, duration_s=5.0)
    assert spec.num_frames == 120


def test_video_spec_duration_bounds():
    with pytest.raises(ValueError):
        VideoSpec(duration_s=1.0)
    with pytest.raises(ValueError):
        VideoSpec(duration_s=20.0)


def test_registry_list():
    import i2v.models  # noqa: F401  (import triggers registration)

    names = registry.list()
    assert "svd" in names
    assert "wan2_1_vace_14b" in names
