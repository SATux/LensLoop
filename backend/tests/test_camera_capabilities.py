import pytest
from unittest.mock import patch
from backend.services.camera import _make_capture_mode, CameraService


_NATIVE_W, _NATIVE_H = 3280, 2464

_IMX219_MODES = [
    # 8 raw modes: 4 sizes × 2 bit depths
    {"size": (640, 480),   "bit_depth": 8,  "fps_range": (0, 206), "crop_limits": (1000, 752, 1280, 960)},
    {"size": (640, 480),   "bit_depth": 10, "fps_range": (0, 120), "crop_limits": (1000, 752, 1280, 960)},
    {"size": (1640, 1232), "bit_depth": 10, "fps_range": (0, 41),  "crop_limits": (0, 0, 3280, 2464)},
    {"size": (1640, 1232), "bit_depth": 8,  "fps_range": (0, 83),  "crop_limits": (0, 0, 3280, 2464)},
    {"size": (1920, 1080), "bit_depth": 10, "fps_range": (0, 47),  "crop_limits": (680, 692, 1920, 1080)},
    {"size": (1920, 1080), "bit_depth": 8,  "fps_range": (0, 60),  "crop_limits": (680, 692, 1920, 1080)},
    {"size": (3280, 2464), "bit_depth": 10, "fps_range": (0, 21),  "crop_limits": (0, 0, 3280, 2464)},
    {"size": (3280, 2464), "bit_depth": 8,  "fps_range": (0, 28),  "crop_limits": (0, 0, 3280, 2464)},
]


def _dedup(modes):
    seen = {}
    for m in modes:
        size = tuple(m["size"])
        bd = m.get("bit_depth", 8)
        if size not in seen or bd > seen[size].get("bit_depth", 0):
            seen[size] = m
    return list(seen.values())


def test_dedup_keeps_highest_bit_depth_per_size():
    deduped = _dedup(_IMX219_MODES)
    by_size = {tuple(m["size"]): m for m in deduped}
    assert by_size[(640, 480)]["bit_depth"] == 10
    assert by_size[(1640, 1232)]["bit_depth"] == 10
    assert by_size[(1920, 1080)]["bit_depth"] == 10
    assert by_size[(3280, 2464)]["bit_depth"] == 10


def test_dedup_produces_correct_count():
    deduped = _dedup(_IMX219_MODES)
    assert len(deduped) == 4


def test_full_fov_flag_set_correctly():
    deduped = _dedup(_IMX219_MODES)
    modes = [_make_capture_mode(m, _NATIVE_W, _NATIVE_H) for m in deduped]
    by_size = {(m.width, m.height): m for m in modes}
    assert by_size[(1640, 1232)].full_fov is True
    assert by_size[(3280, 2464)].full_fov is True
    assert by_size[(640, 480)].full_fov is False
    assert by_size[(1920, 1080)].full_fov is False


def test_megapixels_rounded_to_one_dp():
    mode = {"size": (3280, 2464), "bit_depth": 10, "fps_range": (0, 21), "crop_limits": (0, 0, 3280, 2464)}
    cm = _make_capture_mode(mode, _NATIVE_W, _NATIVE_H)
    assert cm.megapixels == 8.1


def test_label_full_res():
    mode = {"size": (3280, 2464), "bit_depth": 10, "fps_range": (0, 21), "crop_limits": (0, 0, 3280, 2464)}
    cm = _make_capture_mode(mode, _NATIVE_W, _NATIVE_H)
    assert cm.label == "Full res"


def test_label_half_res():
    mode = {"size": (1640, 1232), "bit_depth": 10, "fps_range": (0, 41), "crop_limits": (0, 0, 3280, 2464)}
    cm = _make_capture_mode(mode, _NATIVE_W, _NATIVE_H)
    assert cm.label == "Half-res"


def test_label_1080p():
    mode = {"size": (1920, 1080), "bit_depth": 10, "fps_range": (0, 47), "crop_limits": (680, 692, 1920, 1080)}
    cm = _make_capture_mode(mode, _NATIVE_W, _NATIVE_H)
    assert cm.label == "1080p"


def test_label_preview():
    mode = {"size": (640, 480), "bit_depth": 10, "fps_range": (0, 120), "crop_limits": (1000, 752, 1280, 960)}
    cm = _make_capture_mode(mode, _NATIVE_W, _NATIVE_H)
    assert cm.label == "Preview"


def test_label_unknown_size():
    mode = {"size": (800, 600), "bit_depth": 8, "fps_range": (0, 30), "crop_limits": (200, 200, 800, 600)}
    cm = _make_capture_mode(mode, _NATIVE_W, _NATIVE_H)
    assert cm.label == "800×600"


def test_modes_sorted_smallest_first():
    deduped = _dedup(_IMX219_MODES)
    modes = [_make_capture_mode(m, _NATIVE_W, _NATIVE_H) for m in deduped]
    modes.sort(key=lambda m: m.width * m.height)
    pixels = [m.width * m.height for m in modes]
    assert pixels == sorted(pixels)


@pytest.mark.asyncio
async def test_camera_info_endpoint_available(test_app):
    resp = await test_app.get("/api/camera/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True


@pytest.mark.asyncio
async def test_capabilities_endpoint_returns_modes(test_app):
    resp = await test_app.get("/api/camera/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["modes"]) == 4


@pytest.mark.asyncio
async def test_start_timelapse_validates_mode(test_app):
    resp = await test_app.post("/api/timelapse/start", json={
        "interval": 5, "duration": 10, "fps": 24,
        "capture_width": 9999, "capture_height": 9999,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_timelapse_accepts_valid_mode(test_app):
    with patch("backend.services.state.asyncio.create_task"):
        resp = await test_app.post("/api/timelapse/start", json={
            "interval": 5, "duration": 10, "fps": 24,
            "capture_width": 3280, "capture_height": 2464,
        })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_capture_service_receives_correct_dimensions(test_app):
    state = test_app.app.state.state_manager
    with patch("backend.services.state.asyncio.create_task"):
        await test_app.post("/api/timelapse/start", json={
            "interval": 5, "duration": 10, "fps": 24,
            "capture_width": 1920, "capture_height": 1080,
        })
    assert state._current_run["capture_width"] == 1920
    assert state._current_run["capture_height"] == 1080
