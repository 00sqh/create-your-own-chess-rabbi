from pathlib import Path
import sys

from personal_maia.system.process import run_logged


def test_run_logged_writes_output(tmp_path: Path):
    log_path = tmp_path / "run.log"
    result = run_logged(
        [sys.executable, "-c", "print('hello from child')"],
        log_path=log_path,
        echo=False,
    )

    assert result.returncode == 0
    assert result.log_path == log_path
    assert "hello from child" in log_path.read_text(encoding="utf-8")


def test_run_logged_accepts_env(tmp_path: Path):
    log_path = tmp_path / "env.log"
    result = run_logged(
        [sys.executable, "-c", "import os; print(os.environ['PERSONAL_MAIA_TEST_ENV'])"],
        log_path=log_path,
        echo=False,
        env={"PERSONAL_MAIA_TEST_ENV": "ok"},
    )

    assert result.returncode == 0
    assert "ok" in log_path.read_text(encoding="utf-8")
