# 1. Training Model

## Core Technical Approach

This project should be a packaging and automation layer around the Maia/Lc0 ecosystem, not a new chess engine from scratch.

The chess engine has two major parts:

```text
search/runtime program + neural-network weights = playable engine
```

This project should train only the neural-network weights. The search/runtime program should come from Lc0, which already provides:

- UCI protocol support.
- Board state handling.
- Legal move generation.
- Neural-network inference.
- MCTS/search controls.
- Cross-platform engine binaries.

The personalized "style" comes from the trained network weights. The wrapper and Lc0 runtime make those weights usable as an engine in en-croissant or another UCI GUI.

The intended training flow is:

1. Download or import PGNs.
2. Identify target player names across sources.
3. Extract only positions where the target player made the move.
4. Convert those examples into Maia/Lc0-compatible training data.
5. Start from an existing Maia neural network weight file.
6. Fine-tune locally on the target player's moves.
7. Export the fine-tuned network.
8. Run the network through Lc0 as a UCI engine.

This matches the Maia Individual idea: use transfer learning from a general human-style Maia model to a player-specific model.

## What Gets Trained

The model training is supervised move prediction.

Each training example is approximately:

```text
input: board position before the target player's move
label: the move the target player actually played
```

The base network already knows general human chess patterns from Maia training. Personal training adjusts the network so its policy head puts more probability on the target player's moves.

For MVP, the project should call Maia Individual's transfer-training pipeline rather than reimplementing the neural training code. The local app is responsible for:

1. Creating the player-specific dataset.
2. Writing the training config.
3. Selecting the base weight file.
4. Running the trainer subprocess locally.
5. Monitoring logs and progress.
6. Exporting the trained weight file.

The project should not initially train a value head for maximum playing strength. The primary objective is move imitation accuracy on held-out games.

## Training Mechanics

The training job should be treated as fine-tuning, not full engine training from zero.

Conceptually, each batch contains encoded chess positions and target moves:

```text
position_tensor -> neural_network -> policy_logits
target_move -> cross_entropy(policy_logits, target_move)
```

The optimizer updates the Maia-compatible network weights so the target player's actual moves receive higher probability.

The MVP should not implement this neural loop directly. It should call Maia Individual's `train_transfer.py`, which already:

- Reads a YAML training config.
- Loads player-specific train and validation chunks.
- Creates TensorFlow datasets.
- Restores the base Maia model.
- Runs transfer training.
- Saves final Leela/Lc0-compatible `.pb.gz` weights.

The current upstream-shaped flow is:

```bash
bash 1-data_generation/9-pgn_to_training_data.sh input.pgn output_dir player_name
python 2-training/train_transfer.py generated_config.yaml player_name --copy_dir models
```

The implemented commands that wrap this are:

```bash
rabbi convert-data --project ./runs/example --maia-repo ../maia-individual --player example
rabbi prepare-train --project ./runs/example --maia-repo ../maia-individual --base-model ./weights/maia-1900 --player example
```

When those commands are run with `--run`, stdout/stderr is also saved under:

```text
logs/convert-data.log
logs/train.log
```

The training command our app generates is shaped like:

```bash
python 2-training/train_transfer.py generated_config.yaml player_name --gpu 0 --num_workers 8 --copy_dir models
```

The trainer output is a new `.pb.gz` network file. That file is the artifact the final engine package gives to Lc0.

## Why This Is Not Self-Play Training

Lc0's original training style can involve self-play and reinforcement learning. That is not the right first approach here.

For a personal-style model, we already have the target behavior: the human's moves. So the correct first objective is supervised imitation:

```text
minimize prediction error on the player's historical moves
```

Self-play would make the model stronger or different, but not necessarily more like the target player.

## What Might Be Fine-Tuned

For MVP, use Maia Individual's default transfer setup rather than choosing layers manually.

Possible later options:

- Fine-tune the whole network with a low learning rate.
- Freeze early residual blocks and train later blocks plus policy head.
- Train only a small adapter/head if overfitting is severe.

The validation report should decide whether personalization helped:

```text
base Maia move-match accuracy vs personalized model move-match accuracy
```
