from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from personal_maia.engine import EnginePackageConfig, create_engine_package


def test_packaged_wrapper_speaks_uci_with_fake_lc0(tmp_path: Path):
    fake_lc0 = tmp_path / "fake-lc0.py"
    fake_lc0.write_text(
        """#!/usr/bin/env python3
import sys

for line in sys.stdin:
    cmd = line.strip()
    if cmd == "uci":
        print("id name Fake Lc0", flush=True)
        print("id author Fake", flush=True)
        print("uciok", flush=True)
    elif cmd == "isready":
        print("readyok", flush=True)
    elif cmd.startswith("go "):
        print("bestmove e2e4", flush=True)
    elif cmd == "quit":
        break
""",
        encoding="utf-8",
    )
    fake_lc0.chmod(0o755)
    weights = tmp_path / "weights.pb.gz"
    weights.write_text("fake", encoding="utf-8")
    wrapper = create_engine_package(
        EnginePackageConfig(
            name="fake-style",
            lc0_path=fake_lc0,
            weights_path=weights,
            output_dir=tmp_path / "engine",
        )
    )

    proc = subprocess.run(
        [sys.executable, str(wrapper)],
        input="uci\nisready\nposition startpos\ngo depth 12\nquit\n",
        text=True,
        capture_output=True,
        timeout=5,
        check=True,
    )

    assert "uciok" in proc.stdout
    assert "id name Personal Maia - fake-style" in proc.stdout
    assert "option name StyleNodes" in proc.stdout
    assert "readyok" in proc.stdout
    assert "bestmove e2e4" in proc.stdout
