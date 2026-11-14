import importlib.util
import io
import json
import sys
import types
from pathlib import Path

import pytest

BROLL = Path(__file__).resolve().parents[1] / "clipping" / "studio" / "broll.py"


def _hit(hit_id, w, h):
    return {"id": hit_id, "videos": {"large": {"url": f"https://cdn.test/{hit_id}.mp4", "width": w, "height": h}}}


@pytest.fixture
def pixabay_download(monkeypatch):
    """Extract just download_pixabay_broll so the test needs no cv2/mediapipe."""
    src = BROLL.read_text(encoding="utf-8")
    start = src.index("USED_PIXABAY_IDS = set()")
    end = src.index("def crop_center_broll")
    ns = {}
    import json as _json, os, random, shutil, urllib.parse, urllib.request
    ns.update(json=_json, os=os, random=random, shutil=shutil, urllib=urllib)
    ns["_is_vertical_ratio"] = lambda r: r in ("9:16", "3:4", "4:5")
    exec(compile(src[start:end], "broll_pixabay", "exec"), ns)
    return ns


def _fake_urlopen(search_payload):
    def _open(req, *a, **k):
        url = req.full_url
        if "pixabay.com/api/videos" in url:
            return io.BytesIO(json.dumps(search_payload).encode())
        return io.BytesIO(b"video-bytes")
    return _open


def test_picks_portrait_for_vertical_ratio(pixabay_download, tmp_path, monkeypatch):
    payload = {"hits": [_hit(1, 1920, 1080), _hit(2, 1080, 1920)]}
    monkeypatch.setattr(pixabay_download["urllib"].request, "urlopen", _fake_urlopen(payload))
    out = tmp_path / "b.mp4"
    assert pixabay_download["download_pixabay_broll"]("sea", "9:16", str(out), "key") is True
    assert out.read_bytes() == b"video-bytes"
    assert pixabay_download["USED_PIXABAY_IDS"] == {2}


def test_no_key_or_no_match_returns_false(pixabay_download, tmp_path, monkeypatch):
    assert pixabay_download["download_pixabay_broll"]("sea", "9:16", str(tmp_path / "b.mp4"), "") is False
    monkeypatch.setattr(
        pixabay_download["urllib"].request, "urlopen", _fake_urlopen({"hits": [_hit(1, 1920, 1080)]})
    )
    assert pixabay_download["download_pixabay_broll"]("sea", "9:16", str(tmp_path / "b.mp4"), "key") is False
