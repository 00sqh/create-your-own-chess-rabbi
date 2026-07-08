# 0. Overview

## Goal

Build a local-first tool that turns one or more public chess profiles or PGN files into a locally usable personal-style chess engine package.

The first target GUI is en-croissant, so the output must be usable as a normal local UCI engine: the user should be able to add one executable path in en-croissant and play/analyze against the personalized engine.

The tool should not train on a remote server by default. Downloading public games, dependencies, base Maia weights, and helper binaries may use the network, but training and final engine execution should happen on the user's machine.

## Product Shape

Use a TUI as the main interface, with a CLI beneath it.

The TUI should guide the user through:

1. Creating a project profile.
2. Adding one or more sources:
   - Lichess profile URL.
   - Chess.com profile URL.
   - Lichess study/game URL if feasible.
   - Local PGN file or directory.
3. Choosing which side/player to imitate when PGNs contain many players.
4. Filtering games by time control, date range, color, rated/casual, variant, and result.
5. Selecting a base Maia model, normally nearest estimated level.
6. Running local preprocessing and training.
7. Exporting a final engine package.
8. Showing the exact path to add in en-croissant.

The CLI should support the same workflow non-interactively:

```bash
rabbi build \
  --name example-style \
  --source https://lichess.org/@/example \
  --source https://www.chess.com/member/example \
  --player example \
  --maia-repo ../maia-individual \
  --base-model ./weights/maia-1900
```

## High-Level Architecture

```text
TUI / CLI
-> source resolver
-> game downloader / PGN importer
-> player identity matcher
-> PGN cleaner and filter
-> Maia/Lc0 training-data converter
-> base weight manager
-> local trainer
-> model exporter
-> UCI engine packager
-> en-croissant instructions
```

The final engine package should look like this:

```text
example-style/
  rabbi-engine       # executable UCI wrapper
  lc0/                       # bundled or referenced Lc0 binary
  weights/
    example-style.pb.gz      # trained network
    base-maia.pb.gz          # optional, for provenance/recovery
  config/
    engine.json
    training.json
    sources.json
  data/
    raw/
    cleaned/
    training/
  logs/
  README.md
```

In en-croissant, the user adds:

```text
example-style/rabbi-engine
```

The wrapper launches Lc0 with the trained weights and fixed Maia-style runtime settings.
