# External Tool Setup

Rabbi separates two phases:

```text
training time: Maia Individual + pgn-extract + trainingdata-tool + ML dependencies
runtime:       Lc0 + trained .pb.gz weights + Rabbi wrapper
```

For development, install external tools under this project:

```bash
cd /path/to/rabbi
bash scripts/bootstrap-external.sh
export PATH="$PWD/external/bin:$PATH"
```

The pgn-extract checkout keeps its Makefile in `external/src/pgn-extract/src`, so manual rebuild is:

```bash
make -C external/src/pgn-extract/src
cp external/src/pgn-extract/src/pgn-extract external/bin/pgn-extract
```

`trainingdata-tool` requires Boost headers. On Arch Linux:

```bash
sudo pacman -S --needed boost
git -C external/src/trainingdata-tool submodule update --init --recursive --depth 1
cmake -S external/src/trainingdata-tool -B external/build/trainingdata-tool -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="$PWD/external/bin" \
  -DCMAKE_CXX_FLAGS="-include cstdint" \
  -DCMAKE_C_FLAGS="-include unistd.h"
cmake --build external/build/trainingdata-tool --target trainingdata-tool
```

Maia Individual's conversion script uses `screen` to run conversions in detached sessions. The bootstrap script creates a project-local `external/bin/screen` shim that runs those commands synchronously, so you do not need to install GNU screen for this workflow.

The conversion scripts also need a small Python environment. The bootstrap script creates `external/venv` and installs:

```text
python-chess PyYAML numpy pandas pytz
```

Use that interpreter when converting:

```bash
PYTHONPATH=src python3 -m rabbi.cli convert-data \
  --project ./runs/my-style \
  --maia-repo external/src/maia-individual \
  --player "Exact PGN Header Name" \
  --python external/venv/bin/python \
  --run
```

`--player` must exactly match the PGN `White` or `Black` header spelling. Maia Individual's fixed per-color 90/10 split also needs at least 10 games as White and 10 games as Black after filtering, otherwise validation data is empty.

Actual training is separate from conversion. It needs a Python environment with TensorFlow and Maia's ML dependencies, and Maia Individual defaults to GPU index `0`. The project bootstrap does not install TensorFlow because the correct package depends on CPU/GPU hardware and the local Python version.

On this Arch Linux machine, a TensorFlow-capable training venv can be created with system packages plus a few pip packages:

```bash
sudo pacman -S --needed python-tensorflow-opt tensorboard python-natsort python-humanize
python3 -m venv --system-site-packages external/train-venv
external/train-venv/bin/python -m pip install python-chess tensorboardX
```

Then use `--python external/train-venv/bin/python` for `prepare-train`. This verifies TensorFlow import, but CPU-only TensorFlow is not enough for unmodified Maia training: Maia builds `Conv2D` layers in NCHW/channels-first format, and the current CPU TensorFlow backend rejects that graph. A CUDA/NVIDIA TensorFlow environment is the practical path for real local training unless the Maia network is ported to channels-last CPU execution.

Lc0 requires Meson, Ninja, and a neural-network backend. For the local CPU build used here:

```bash
sudo pacman -S --needed meson ninja openblas
meson setup external/src/lc0/build/release external/src/lc0 --wipe \
  --buildtype release \
  --prefix "$PWD/external" \
  -Dgtest=false \
  -Dopenblas=true \
  -Dblas=true \
  -Dopenblas_include=/usr/include/openblas \
  -Dopenblas_libdirs=/usr/lib
meson compile -C external/src/lc0/build/release
cp external/src/lc0/build/release/lc0 external/bin/lc0
```

Then check:

```bash
PYTHONPATH=src python3 -m rabbi.cli doctor \
  --maia-repo external/src/maia-individual \
  --lc0 external/bin/lc0 \
  --base-model external/src/maia-individual/models/maia-1900 \
  --python external/venv/bin/python
```

## Arch Linux Shortcut

On Arch Linux, if you are willing to install system packages:

```bash
sudo pacman -S lc0 pgn-extract
```

Then use:

```bash
PYTHONPATH=src python3 -m rabbi.cli doctor \
  --maia-repo external/src/maia-individual \
  --lc0 /usr/bin/lc0 \
  --base-model external/src/maia-individual/models/maia-1900 \
  --python external/venv/bin/python
```

## What Normal Users Should See Later

Normal users should not have to understand these tools. The final product should provide a dependency installer/checker that handles downloads or gives one clear command. The current project is still in developer setup mode.
