# 6. Project Management

## Repository Layout

Proposed layout:

```text
personal-maia/
  IMPLEMENTATION.md
  README.md
  pyproject.toml
  src/
    personal_maia/
      __init__.py
      cli.py
      tui.py
      config.py
      sources/
        lichess.py
        chesscom.py
        pgn.py
      data/
        normalize.py
        filter.py
        split.py
      maia/
        weights.py
        convert.py
        trainer.py
        evaluate.py
      engine/
        wrapper.py
        package.py
        uci.py
      system/
        dependencies.py
        platform.py
        process.py
  tests/
    fixtures/
    test_sources.py
    test_filtering.py
    test_uci_wrapper.py
    test_packaging.py
  docs/
    implementation/
      0-overview.md
      1-training-model.md
      2-engine-runtime.md
      3-data-sources.md
      4-training-and-evaluation.md
      5-packaging-and-gui.md
      6-project-management.md
```

## Dependency Strategy

Separate dependencies into three groups:

### Core App

- Python runtime.
- Textual/Rich for TUI.
- HTTP client.
- PGN parser.
- Config and schema validation.

### Chess/Engine Runtime

- Lc0 binary.
- Maia weight files.
- Optional opening-book tooling.

### Training

- Maia Individual code or vendored adapter.
- PyTorch/TensorFlow stack required by Maia Individual.
- CUDA support when available.
- pgn-extract and Lc0 training-data tools if required by the selected pipeline.

The tool should run a first-time dependency check:

```text
personal-maia doctor
personal-maia doctor --maia-repo ../maia-individual --base-model ./weights/maia-1900 --lc0 /path/to/lc0
```

`doctor` should report missing tools and offer installation instructions. It should not silently install heavyweight dependencies without user confirmation.

## Privacy And Consent

The tool is specifically designed to imitate a person, so it needs clear boundaries.

Rules:

- Default wording should assume the user is training on their own games or has permission.
- Store sources and training metadata locally.
- Do not upload PGNs or trained weights unless the user explicitly chooses to.
- Include provenance metadata in every package.
- Warn users that a personalized style model can be identifying.

## MVP Scope

The first version should be intentionally narrow:

1. Accept Lichess username/profile URL and local PGN.
2. Standard chess only.
3. One target player.
4. Download/cache one base Maia model.
5. Run local transfer training through Maia Individual scripts.
6. Package Lc0 plus trained weights behind one UCI wrapper.
7. Verify the wrapper with a smoke test:

```text
uci
isready
position startpos moves e2e4
go nodes 1
bestmove ...
quit
```

Chess.com support can be added immediately after the first Lichess/local-PGN path works.

## Milestones

### Milestone 1: Project Skeleton

- CLI entry point.
- TUI entry point.
- Config model.
- Project workspace format.
- `doctor` command.

### Milestone 2: Game Ingestion

- Lichess downloader.
- Local PGN importer.
- PGN normalization.
- Player identity matching.
- Filtering report.

### Milestone 3: Training Adapter

- Base Maia weight cache.
- Dataset conversion.
- Maia Individual training subprocess.
- Resume support.
- Training logs.

### Milestone 4: Evaluation

- Holdout split.
- Base-vs-personal comparison.
- Report generation.

### Milestone 5: Engine Package

- UCI wrapper.
- Lc0 invocation.
- Package directory.
- Smoke test.
- en-croissant instructions.

### Milestone 6: Chess.com And Polish

- Chess.com archive downloader.
- More filters.
- Better TUI progress screens.
- Cross-platform packaging.

## Main Risks

### Training Fragility

Maia Individual is research code. Its dependencies and scripts may require adaptation.

Mitigation:

- Keep the trainer behind an adapter.
- Pin known-good versions.
- Add `doctor`.
- Store all generated configs and logs.

### Hardware Requirements

Fine-tuning can be slow on CPU and complex on GPU.

Mitigation:

- Provide quick/balanced/thorough presets.
- Estimate runtime before training.
- Support resume.
- Warn clearly when CPU training is selected.

### Small Dataset Overfitting

Few games may create a model that memorizes quirks but does not generalize.

Mitigation:

- Use validation split.
- Compare against base Maia.
- Warn before packaging weak results.
- Encourage larger game sets.

### Engine GUI Compatibility

GUIs vary in how they send UCI options and `go` commands.

Mitigation:

- Make wrapper UCI-compliant.
- Test with raw UCI smoke tests first.
- Test with en-croissant as the first GUI target.

## First Implementation Decision

Start with Python for the app and wrapper.

Reason:

- Training stack is already Python-heavy.
- TUI is straightforward with Textual.
- Subprocess control and logs are simple.
- Later, the wrapper can be rewritten in Rust or Go if single-binary packaging becomes important.

The first working package may require a Python runtime. A later packaging milestone should create standalone executables with PyInstaller, Nuitka, or a small compiled wrapper.
