# Rabbi

Rabbi is a local-first tool for building a chess engine package that imitates one player's move style.

The project is not a from-scratch chess engine. It uses:

- public or local PGN games from a target player,
- Maia Individual for personal-style transfer training,
- Lc0 as the UCI runtime/search engine,
- a small wrapper that makes the final engine easy to load in GUIs such as en-croissant.

The command-line package is named `rabbi`.

## What It Can Do

- Resolve Lichess, Chess.com, and local PGN sources.
- Download public games from Lichess or Chess.com.
- Import and filter one or more local PGN files.
- Convert the target player's games into Maia/Lc0 training chunks.
- Generate Maia Individual training configs and commands.
- Package a trained `.pb.gz` weight file with Lc0 as a local UCI engine.
- Smoke-test the packaged engine before adding it to en-croissant.

## Current Status

The pipeline is implemented through data conversion, training command generation, and engine packaging.

Verified locally:

- `pgn-extract` works.
- `trainingdata-tool` works.
- Lc0 builds and runs.
- Maia PGN conversion works.
- Engine packaging works.
- Packaged UCI engine smoke test passes.
- Test suite passes.

Real model training depends on the local TensorFlow backend. Maia Individual's current TensorFlow graph uses NCHW/channels-first `Conv2D`, so CPU-only TensorFlow may fail at graph execution. A CUDA/NVIDIA TensorFlow environment is the practical target for real training unless Maia's model is ported to CPU-friendly NHWC/channels-last execution.

## Requirements

Runtime engine packages need:

- Lc0
- a trained Maia-compatible `.pb.gz` weight file
- Python 3 for the wrapper script

Training needs more:

- Maia Individual checkout
- `pgn-extract`
- `trainingdata-tool`
- TensorFlow
- Maia Python dependencies
- preferably a TensorFlow-visible NVIDIA/CUDA GPU

## Setup

From this repository:

```bash
cd /path/to/rabbi
bash scripts/bootstrap-external.sh
export PATH="$PWD/external/bin:$PATH"
export PYTHONPATH=src
```

Check the conversion/runtime tools:

```bash
python3 -m rabbi.cli doctor \
  --maia-repo external/src/maia-individual \
  --base-model external/src/maia-individual/models/maia-1900 \
  --lc0 external/bin/lc0 \
  --python external/venv/bin/python
```

For training, use a TensorFlow-capable Python. On this Arch Linux machine, the local training venv was created with:

```bash
sudo pacman -S --needed python-tensorflow-opt tensorboard python-natsort python-humanize
python3 -m venv --system-site-packages external/train-venv
external/train-venv/bin/python -m pip install python-chess tensorboardX
```

Then check it:

```bash
python3 -m rabbi.cli doctor \
  --maia-repo external/src/maia-individual \
  --base-model external/src/maia-individual/models/maia-1900 \
  --lc0 external/bin/lc0 \
  --python external/train-venv/bin/python
```

## Basic Workflow

Create a project:

```bash
python3 -m rabbi.cli init my-style --workspace ./runs
```

Download public Lichess games:

```bash
python3 -m rabbi.cli download \
  --project ./runs/my-style \
  --source https://lichess.org/@/PlayerName \
  --max-games 5000
```

Or import local PGNs:

```bash
python3 -m rabbi.cli ingest \
  --project ./runs/my-style \
  --pgn games1.pgn games2.pgn \
  --player "Exact PGN Header Name"
```

Convert games into Maia training chunks:

```bash
python3 -m rabbi.cli convert-data \
  --project ./runs/my-style \
  --maia-repo external/src/maia-individual \
  --player "Exact PGN Header Name" \
  --python external/venv/bin/python \
  --run
```

Important Maia conversion constraints:

- `--player` must exactly match the PGN `White` or `Black` header spelling.
- The cleaned PGN must contain at least 10 games as White and 10 games as Black, because Maia's upstream 90/10 split otherwise creates empty validation chunks.

Prepare a training config:

```bash
python3 -m rabbi.cli prepare-train \
  --project ./runs/my-style \
  --maia-repo external/src/maia-individual \
  --base-model external/src/maia-individual/models/maia-1900 \
  --python external/train-venv/bin/python \
  --player "Exact PGN Header Name" \
  --skip-pgn-split
```

Run training when the TensorFlow/GPU environment is ready:

```bash
python3 -m rabbi.cli prepare-train \
  --project ./runs/my-style \
  --maia-repo external/src/maia-individual \
  --base-model external/src/maia-individual/models/maia-1900 \
  --python external/train-venv/bin/python \
  --player "Exact PGN Header Name" \
  --skip-pgn-split \
  --gpu 0 \
  --run
```

Package the newest trained weights:

```bash
python3 -m rabbi.cli package \
  --project ./runs/my-style \
  --name my-style \
  --lc0 external/bin/lc0 \
  --output ./engines/my-style
```

Or package a specific weight file:

```bash
python3 -m rabbi.cli package \
  --project ./runs/my-style \
  --name my-style \
  --lc0 external/bin/lc0 \
  --weights ./runs/my-style/models/path/to/model.pb.gz \
  --output ./engines/my-style
```

Smoke-test the engine:

```bash
python3 -m rabbi.cli smoke-test \
  --engine ./engines/my-style/rabbi-engine
```

## Using The Engine In en-croissant

Add this executable as a local UCI engine:

```text
engines/my-style/rabbi-engine
```

The wrapper launches Lc0 with the trained weights and forwards UCI traffic. It reports:

```text
id name Rabbi - <package name>
id author Rabbi
```

It also exposes:

```text
StyleNodes
AnalysisMode
```

By default, non-analysis `go ...` commands are rewritten to `go nodes <StyleNodes>` to keep play policy-like instead of deep engine analysis.

## One-Command Build

The `build` command chains project creation, source download/import, PGN ingest, conversion config, and training config.

```bash
python3 -m rabbi.cli build \
  --name my-style \
  --workspace ./runs \
  --player "Exact PGN Header Name" \
  --source https://lichess.org/@/PlayerName \
  --source local-games.pgn \
  --maia-repo external/src/maia-individual \
  --base-model external/src/maia-individual/models/maia-1900 \
  --python external/venv/bin/python \
  --max-games 5000
```

By default it writes commands/configs. Add `--run-convert`, `--run-train`, and `--package` only when all dependencies and hardware are ready.

## Development

Run tests:

```bash
PYTHONPATH=src python3 -m pytest
```

Useful project docs:

- [Implementation Plan](IMPLEMENTATION.md)
- [External Tool Setup](docs/setup-external.md)
- [Detailed Design Notes](docs/implementation/0-overview.md)

## Privacy And Use

Train on your own games or on games you have permission to use. Downloaded public games and training artifacts stay on the local machine unless you explicitly upload them elsewhere.

## License

MIT. See [LICENSE](LICENSE).
