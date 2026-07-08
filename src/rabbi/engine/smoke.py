from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import subprocess
import threading
import time


@dataclass(slots=True)
class EngineSmokeResult:
    engine: Path
    ok: bool
    stdout: str
    stderr: str


def smoke_test_engine(engine: Path, *, timeout: float = 10.0) -> EngineSmokeResult:
    proc = subprocess.Popen(
        [str(engine)],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_queue: queue.Queue[str] = queue.Queue()
    stdout_thread = threading.Thread(
        target=_collect_stream,
        args=(proc.stdout, stdout_lines, stdout_queue),
        daemon=True,
    )
    stderr_thread = threading.Thread(target=_collect_stream, args=(proc.stderr, stderr_lines), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    deadline = time.monotonic() + timeout

    def send(command: str) -> None:
        proc.stdin.write(command + "\n")
        proc.stdin.flush()

    def wait_for(needle: str) -> bool:
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                line = stdout_queue.get(timeout=remaining)
            except queue.Empty:
                return False
            if needle in line:
                return True
        return False

    ok = False
    try:
        send("uci")
        got_uci = wait_for("uciok")
        send("isready")
        got_ready = wait_for("readyok")
        send("position startpos moves e2e4 e7e5")
        send("go depth 1")
        got_bestmove = wait_for("bestmove ")
        ok = got_uci and got_ready and got_bestmove
        send("quit")
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

    return EngineSmokeResult(engine=engine, ok=ok, stdout="".join(stdout_lines), stderr="".join(stderr_lines))


def _collect_stream(stream, output: list[str], line_queue: queue.Queue[str] | None = None) -> None:
    for line in stream:
        output.append(line)
        if line_queue is not None:
            line_queue.put(line)
