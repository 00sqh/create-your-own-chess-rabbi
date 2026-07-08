# 5. Packaging And GUI

## Packaging

The packager should create a self-contained engine directory when possible.

Package contents:

- UCI wrapper executable.
- Lc0 executable for the user's OS/architecture, or a path reference if bundling is disabled.
- Trained weights.
- Runtime config.
- Training metadata.
- Human-readable README.
- Optional opening book created from the target player's games.

The wrapper should expose a UCI name similar to:

```text
id name Rabbi - example
id author Rabbi
```

It should also expose useful UCI options:

```text
option name StyleNodes type spin default 1 min 1 max 800
option name UseOwnOpeningBook type check default true
option name AnalysisMode type check default false
option name Temperature type spin default 0 min 0 max 100
```

## en-croissant Compatibility

en-croissant supports local UCI engines. It spawns an executable, sends `uci`, waits for `uciok`, sends `isready`, waits for `readyok`, then sends normal `position` and `go` commands.

Therefore the package must include one executable path that:

1. Starts reliably without shell-specific setup.
2. Responds to `uci`.
3. Responds to `isready`.
4. Returns `bestmove ...` after `go`.
5. Exits on `quit`.

The TUI should finish with:

```text
Engine package created:
  /path/to/example-style/rabbi-engine

In en-croissant:
  Engines -> Add -> Local -> Path -> select this executable
```

Before adding the engine to en-croissant, the CLI can verify the executable:

```bash
rabbi smoke-test --engine /path/to/example-style/rabbi-engine
```

## TUI Design

Use a practical terminal UI with keyboard-first workflows.

Recommended stack:

```text
Python + Textual + Rich
```

Reasons:

- Good forms, tables, progress bars, and log views.
- Works well for local ML workflows.
- Easier packaging than a full desktop app.

Main screens:

1. Project list.
2. New engine wizard.
3. Source manager.
4. Filter preview.
5. Hardware check.
6. Training progress.
7. Evaluation report.
8. Package/export screen.

The CLI should remain available for automation and testing.
