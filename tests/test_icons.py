import os
from rtw.icons import ensure_icons, _png


def test_icons(tmp_path):
    made = ensure_icons(str(tmp_path))
    assert len(made) == 2 and all(os.path.getsize(p) > 200 for p in made)
    assert _png(192)[:8] == b"\x89PNG\r\n\x1a\n"
    assert ensure_icons(str(tmp_path)) == []
