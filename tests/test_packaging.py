from pathlib import Path
import json
import os

from rabbi.engine import EnginePackageConfig, create_engine_package, rewrite_go_command
from rabbi.engine.uci_proxy import filter_engine_output, parse_wrapper_option


def test_rewrite_go_command_defaults_to_style_nodes():
    assert rewrite_go_command("go depth 12", style_nodes=1, analysis_mode=False) == "go nodes 1"
    assert rewrite_go_command("isready", style_nodes=1, analysis_mode=False) == "isready"
    assert rewrite_go_command("go depth 12", style_nodes=1, analysis_mode=True) == "go depth 12"


def test_wrapper_options_and_output_filtering():
    assert parse_wrapper_option("setoption name StyleNodes value 7") == ("StyleNodes", "7")
    assert parse_wrapper_option("setoption name Unknown value 7") is None
    assert filter_engine_output("id name Lc0\n", "alice") == "id name Rabbi - alice\n"
    assert "StyleNodes" in filter_engine_output("uciok\n", "alice")


def test_create_engine_package(tmp_path: Path):
    output = tmp_path / "engine"
    wrapper = create_engine_package(
        EnginePackageConfig(
            name="alice-style",
            lc0_path=tmp_path / "lc0",
            weights_path=tmp_path / "alice.pb.gz",
            output_dir=output,
        )
    )
    assert wrapper.exists()
    assert os.access(wrapper, os.X_OK)
    config = json.loads((output / "engine.json").read_text(encoding="utf-8"))
    assert config["name"] == "alice-style"
    assert config["lc0_path"] == str((tmp_path / "lc0").resolve())
    assert config["weights_path"] == str((tmp_path / "alice.pb.gz").resolve())
    assert config["style_nodes"] == 1
