from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from pathlib import Path
import os
import subprocess
import sys


@dataclass(slots=True)
class LoggedProcessResult:
    command: list[str]
    returncode: int
    log_path: Path


def run_logged(
    command: list[str],
    *,
    cwd: Path | None = None,
    log_path: Path,
    echo: bool = True,
    env: Mapping[str, str] | None = None,
) -> LoggedProcessResult:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"$ {' '.join(command)}\n\n")
        log.flush()
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            if echo:
                sys.stdout.write(line)
                sys.stdout.flush()
        returncode = proc.wait()

    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, command)
    return LoggedProcessResult(command=command, returncode=returncode, log_path=log_path)
