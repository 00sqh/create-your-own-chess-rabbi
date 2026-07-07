#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL="$ROOT/external"
SRC="$EXTERNAL/src"
BIN="$EXTERNAL/bin"
DOWNLOADS="$EXTERNAL/downloads"

mkdir -p "$SRC" "$BIN" "$DOWNLOADS"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

clone_or_update() {
  local repo="$1"
  local dir="$2"
  if [ -d "$dir/.git" ]; then
    git -C "$dir" pull --ff-only
  else
    git clone --depth 1 "$repo" "$dir"
  fi
}

need git
need curl

echo "Installing external project assets under: $EXTERNAL"

echo
echo "1. Maia Individual"
clone_or_update "https://github.com/CSSLab/maia-individual.git" "$SRC/maia-individual"

echo
echo "2. Lc0 source"
clone_or_update "https://github.com/LeelaChessZero/lc0.git" "$SRC/lc0"

echo
echo "3. pgn-extract source"
clone_or_update "https://github.com/MichaelB7/pgn-extract.git" "$SRC/pgn-extract"

if command -v make >/dev/null 2>&1; then
  echo
  echo "Building pgn-extract"
  make -C "$SRC/pgn-extract/src"
  cp "$SRC/pgn-extract/src/pgn-extract" "$BIN/pgn-extract"
else
  echo "make not found; skipping pgn-extract build" >&2
fi

echo
echo "4. trainingdata-tool source"
clone_or_update "https://github.com/DanielUranga/trainingdata-tool.git" "$SRC/trainingdata-tool"
git -C "$SRC/trainingdata-tool" submodule update --init --recursive --depth 1

if [ -d /usr/include/boost ]; then
  echo
  echo "Building trainingdata-tool"
  cmake -S "$SRC/trainingdata-tool" -B "$EXTERNAL/build/trainingdata-tool" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="$BIN" \
    -DCMAKE_CXX_FLAGS="-include cstdint" \
    -DCMAKE_C_FLAGS="-include unistd.h"
  cmake --build "$EXTERNAL/build/trainingdata-tool" --target trainingdata-tool
else
  echo "Boost headers not found; skipping trainingdata-tool build." >&2
  echo "On Arch Linux, install them with: sudo pacman -S --needed boost" >&2
fi

echo
echo "5. screen compatibility shim"
cat > "$BIN/screen" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "-S" ]; then
  shift 2
fi
if [ "${1:-}" = "-dm" ]; then
  shift
fi
exec "$@"
EOF
chmod +x "$BIN/screen"

echo
echo "6. Lc0 build"
if command -v meson >/dev/null 2>&1 && command -v ninja >/dev/null 2>&1 && [ -f /usr/lib/libopenblas.so ]; then
  meson setup "$SRC/lc0/build/release" "$SRC/lc0" --wipe \
    --buildtype release \
    --prefix "$EXTERNAL" \
    -Dgtest=false \
    -Dopenblas=true \
    -Dblas=true \
    -Dopenblas_include=/usr/include/openblas \
    -Dopenblas_libdirs=/usr/lib
  meson compile -C "$SRC/lc0/build/release"
  cp "$SRC/lc0/build/release/lc0" "$BIN/lc0"
else
  cat <<'EOF'
Skipping Lc0 build. Required local dependencies:

  meson ninja openblas

On Arch Linux:

  sudo pacman -S --needed meson ninja openblas

Then rerun this script.
EOF
fi

echo
echo "7. Maia Python conversion venv"
if command -v python3 >/dev/null 2>&1; then
  python3 -m venv "$EXTERNAL/venv"
  if "$EXTERNAL/venv/bin/python" -m pip install python-chess PyYAML numpy pandas pytz; then
    echo "Created conversion venv: $EXTERNAL/venv"
  else
    cat <<EOF >&2
Python package install failed. Conversion needs these packages in the Python
used with --python:

  python-chess PyYAML numpy pandas pytz

You can retry manually with:

  $EXTERNAL/venv/bin/python -m pip install python-chess PyYAML numpy pandas pytz
EOF
  fi
else
  echo "python3 not found; skipping Maia Python conversion venv." >&2
fi

echo
echo "8. trainingdata-tool note"
cat <<'EOF'
Maia Individual expects Leela/Lc0 training-data tooling. This script clones
DanielUranga/trainingdata-tool and builds it when Boost headers are available.
Run:

  PYTHONPATH=src python3 -m personal_maia.cli doctor --maia-repo external/src/maia-individual --lc0 external/bin/lc0 --python external/venv/bin/python

If trainingdata-tool is still missing, install Boost and rerun this script.

For conversion, pass the local venv explicitly:

  --python external/venv/bin/python

Actual model training also needs a TensorFlow install compatible with Maia
Individual plus a base Maia weight directory.
EOF

echo
echo "Done. Add this to PATH for project-local tools:"
echo "  export PATH=\"$BIN:\$PATH\""
