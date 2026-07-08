from pathlib import Path

from rabbi.config import init_project, load_project


def test_init_project_creates_workspace(tmp_path: Path):
    paths = init_project("Alice Style", tmp_path)
    assert paths.project_config.exists()
    assert paths.raw_dir.exists()
    assert load_project(paths.root).name == "Alice Style"

