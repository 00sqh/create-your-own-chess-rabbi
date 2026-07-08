from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os

from rabbi.config import write_json


@dataclass(slots=True)
class EnginePackageConfig:
    name: str
    lc0_path: Path
    weights_path: Path
    output_dir: Path
    style_nodes: int = 1
    analysis_mode: bool = False


def create_engine_package(config: EnginePackageConfig) -> Path:
    output_dir = config.output_dir.resolve()
    lc0_path = config.lc0_path.resolve()
    weights_path = config.weights_path.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_config = {
        "name": config.name,
        "lc0_path": str(lc0_path),
        "weights_path": str(weights_path),
        "style_nodes": config.style_nodes,
        "analysis_mode": config.analysis_mode,
    }
    write_json(output_dir / "engine.json", package_config)
    write_json(output_dir / "manifest.json", asdict(config) | {
        "lc0_path": str(lc0_path),
        "weights_path": str(weights_path),
        "output_dir": str(output_dir),
    })

    wrapper = output_dir / "rabbi-engine"
    wrapper.write_text(_wrapper_script(), encoding="utf-8")
    wrapper.chmod(wrapper.stat().st_mode | 0o755)

    readme = output_dir / "README.md"
    readme.write_text(
        _package_readme(
            EnginePackageConfig(
                name=config.name,
                lc0_path=lc0_path,
                weights_path=weights_path,
                output_dir=output_dir,
                style_nodes=config.style_nodes,
                analysis_mode=config.analysis_mode,
            )
        ),
        encoding="utf-8",
    )
    return wrapper


def _wrapper_script() -> str:
    return """#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
import json
import subprocess
import sys
import threading


def rewrite_go_command(line, style_nodes=1, analysis_mode=False):
    stripped = line.strip()
    if analysis_mode:
        return stripped
    if stripped == "go" or stripped.startswith("go "):
        return f"go nodes {style_nodes}"
    return stripped


def parse_wrapper_option(line):
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


def filter_engine_output(line, name):
    if line.startswith("id name "):
        return f"id name Rabbi - {name}\\n"
    if line.startswith("id author "):
        return "id author Rabbi\\n"
    if line.strip() == "uciok":
        return (
            "option name StyleNodes type spin default 1 min 1 max 800\\n"
            "option name AnalysisMode type check default false\\n"
            "uciok\\n"
        )
    return line


def copy_output(src, dest, name):
    for line in src:
        dest.write(filter_engine_output(line, name))
        dest.flush()


def run_proxy(config):
    lc0_path = str(config["lc0_path"])
    weights_path = str(config["weights_path"])
    proc = subprocess.Popen(
        [lc0_path, "-w", weights_path],
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

    threading.Thread(target=copy_output, args=(proc.stdout, sys.stdout, name), daemon=True).start()
    threading.Thread(target=copy_output, args=(proc.stderr, sys.stderr, name), daemon=True).start()

    try:
        for line in sys.stdin:
            command = line.rstrip("\\n")
            option = parse_wrapper_option(command)
            if option is not None:
                option_name, value = option
                if option_name == "StyleNodes":
                    style_nodes = int(value)
                elif option_name == "AnalysisMode":
                    analysis_mode = value.lower() in {"true", "1", "yes", "on"}
                continue
            rewritten = rewrite_go_command(command, style_nodes, analysis_mode)
            proc.stdin.write(rewritten + "\\n")
            proc.stdin.flush()
            if rewritten == "quit":
                break
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
    return proc.wait()


def main(argv=None):
    parser = ArgumentParser(description="Rabbi UCI proxy.")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().with_name("engine.json"))
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    return run_proxy(config)


if __name__ == "__main__":
    raise SystemExit(main())
"""


def _package_readme(config: EnginePackageConfig) -> str:
    return f"""# {config.name}

This is a Rabbi engine package.

Add this executable as a local UCI engine in en-croissant:

```text
{os.fspath(config.output_dir / "rabbi-engine")}
```

Runtime:

```text
Lc0: {config.lc0_path}
Weights: {config.weights_path}
Style nodes: {config.style_nodes}
Analysis mode: {config.analysis_mode}
```
"""
