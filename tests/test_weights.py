from pathlib import Path
import time

import pytest

from personal_maia.maia.weights import find_latest_weights


def test_find_latest_weights(tmp_path: Path):
    old = tmp_path / "old.pb.gz"
    new = tmp_path / "nested" / "new.pb.gz"
    new.parent.mkdir()
    old.write_text("old", encoding="utf-8")
    time.sleep(0.01)
    new.write_text("new", encoding="utf-8")
    assert find_latest_weights(tmp_path) == new


def test_find_latest_weights_raises_for_empty_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        find_latest_weights(tmp_path)
