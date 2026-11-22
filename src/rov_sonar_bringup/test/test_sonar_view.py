"""Check the preview against synthetic echoes with known physical positions."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("sonar_view", Path(__file__).parents[1] / "scripts/sonar_view.py")
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)


def scan():
    ranges = np.linspace(0, 10, 101)
    bearings = np.linspace(-1.1, 1.1, 45)
    return np.full((101, 45), -np.inf, np.float32), ranges, bearings


def test_echo_range_and_left_right_orientation():
    db, ranges, bearings = scan()
    db[34:37, 27:30] = -30  # 3.5 metres at positive bearing (vehicle-left).
    renderer = view.FanRenderer()
    image = renderer.render(db, ranges, bearings)
    x, y = renderer.point(3.5, .3)
    assert x < renderer.width // 2
    assert image[y, x, 0] > 200
    mirror = renderer.width - x
    assert image[y, mirror, 0] < 40


def test_gain_changes_preview_and_preserves_samples():
    db, ranges, bearings = scan()
    db[34:37, 27:30] = -50
    db[69:72, 14:17] = -20
    original = db.copy()
    renderer = view.FanRenderer()
    dim = renderer.render(db, ranges, bearings, gain=-10)
    bright = renderer.render(db, ranges, bearings, gain=10)
    x, y = renderer.point(3.5, .3)
    assert bright[y, x].sum() > dim[y, x].sum()
    np.testing.assert_array_equal(db, original)


def test_empty_scan_has_no_colored_returns():
    db, ranges, bearings = scan()
    renderer = view.FanRenderer()
    image = renderer.render(db, ranges, bearings)
    inside = image[renderer.mask]
    # Only neutral/cool annotation ink is allowed in an empty scan.
    assert not np.any((inside[:, 0].astype(int) - inside[:, 1]) > 60)
    assert renderer.reference is None


def test_invalid_geometry_is_rejected():
    db, ranges, bearings = scan()
    with pytest.raises(ValueError):
        view.FanRenderer().render(db, ranges[::-1], bearings)
    with pytest.raises(ValueError):
        view.FanRenderer().render(db[:, :-1], ranges, bearings)
