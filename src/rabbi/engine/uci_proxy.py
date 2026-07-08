from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import subprocess
import sys
import threading


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description="UCI proxy for Rabbi Lc0 packages.")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    return run_proxy(config)


def run_proxy(config: dict[str, object]) -> int:
    lc0_path = str(config["lc0_path"])
    weights_path = str(config["weights_path"])
    command = [lc0_path, "-w", weights_path]
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    style_nodes = int(config.get("style_nodes", 1))
    analysis_mode = bool(config.get("analysis_mode", False))

    name = str(config.get("name", "Rabbi"))
    stdout_thread = threading.Thread(target=_copy_output, args=(proc.stdout, sys.stdout, name), daemon=True)
    stderr_thread = threading.Thread(target=_copy_output, args=(proc.stderr, sys.stderr), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    try:
        for line in sys.stdin:
            command = line.rstrip("\n")
            option = parse_wrapper_option(command)
            if option is not None:
                option_name, value = option
                if option_name == "StyleNodes":
                    style_nodes = int(value)
                elif option_name == "AnalysisMode":
                    analysis_mode = value.lower() in {"true", "1", "yes", "on"}
                continue
            rewritten = rewrite_go_command(command, style_nodes, analysis_mode)
            proc.stdin.write(rewritten + "\n")
            proc.stdin.flush()
            if rewritten == "quit":
                break
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
    return proc.wait()


def rewrite_go_command(line: str, style_nodes: int = 1, analysis_mode: bool = False) -> str:
    stripped = line.strip()
    if analysis_mode:
        return stripped
    if stripped == "go" or stripped.startswith("go "):
        return f"go nodes {style_nodes}"
    return stripped


def parse_wrapper_option(line: str) -> tuple[str, str] | None:
    tokens = line.strip().split()
    if len(tokens) < 5:
        return None
    if tokens[0].lower() != "setoption" or tokens[1].lower() != "name":
        return None
    if tokens[3].lower() != "value":
        return None
    name = tokens[2]
    value = " ".join(tokens[4:])
    if name in {"StyleNodes", "AnalysisMode"}:
        return name, value
    return None


def filter_engine_output(line: str, name: str) -> str:
    if line.startswith("id name "):
        return f"id name Rabbi - {name}\n"
    if line.startswith("id author "):
        return "id author Rabbi\n"
    if line.strip() == "uciok":
        return (
            "option name StyleNodes type spin default 1 min 1 max 800\n"
            "option name AnalysisMode type check default false\n"
            "uciok\n"
        )
    return line


def _copy_output(src, dest, name: str | None = None) -> None:
    for line in src:
        dest.write(filter_engine_output(line, name or "Rabbi"))
        dest.flush()


if __name__ == "__main__":
    raise SystemExit(main())
