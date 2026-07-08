from pathlib import Path

from rabbi.engine.smoke import smoke_test_engine


def test_smoke_test_engine_with_fake_uci(tmp_path: Path):
    engine = tmp_path / "fake-engine"
    engine.write_text(
        """#!/usr/bin/env python3
import sys
for line in sys.stdin:
    cmd = line.strip()
    if cmd == "uci":
        print("id name fake", flush=True)
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
    engine.chmod(0o755)

    result = smoke_test_engine(engine, timeout=2)

    assert result.ok
    assert "bestmove e2e4" in result.stdout

