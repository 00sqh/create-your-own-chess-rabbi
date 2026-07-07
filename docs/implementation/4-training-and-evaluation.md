# 4. Training And Evaluation

## Training

Training should run locally and resume safely.

TUI training screen should show:

- Stage name.
- Current epoch/step.
- Training loss.
- Validation move-matching accuracy.
- Estimated remaining time when available.
- GPU/CPU device being used.
- Log tail.

The trainer should support:

```text
personal-maia train --resume
personal-maia train --device cuda
personal-maia train --device cpu
personal-maia train --max-steps N
personal-maia train --preset quick
personal-maia train --preset balanced
personal-maia train --preset thorough
```

MVP can call Maia Individual training scripts as a subprocess inside a managed environment.

Long-term, wrap the training code behind a stable internal interface:

```text
Trainer.prepare()
Trainer.train()
Trainer.export()
Trainer.evaluate()
```

This avoids coupling the user-facing product to research-script paths.

## Evaluation

A finished run should produce a local report:

```text
report.md
report.json
```

Metrics:

- Validation move-matching accuracy.
- Comparison with base Maia model.
- Top-1 and top-3 move prediction if available.
- Accuracy by opening family.
- Accuracy by phase: opening, middlegame, endgame.
- Accuracy by color.
- Accuracy by time control.

The most important check is:

```text
personal model predicts the target player's held-out moves better than the base model
```

If it does not, the tool should still package the model only after warning the user.

