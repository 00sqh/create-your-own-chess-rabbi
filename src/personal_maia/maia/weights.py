from __future__ import annotations

from pathlib import Path


def find_latest_weights(models_dir: Path) -> Path:
    candidates = sorted(
        [path for path in models_dir.rglob("*.pb.gz") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No .pb.gz weight files found under {models_dir}")
    return candidates[0]

