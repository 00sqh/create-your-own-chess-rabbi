# 2. Engine Runtime

## Where Engine Code Comes From

### Search And UCI Runtime

Use Lc0 as the actual engine executable.

Lc0 supplies the search program and UCI interface:

```text
personal-maia-engine wrapper
-> lc0 binary
-> trained Maia-compatible weight file
```

The wrapper should not implement chess search. It should:

- Start Lc0 with the correct `-w` weights path.
- Forward UCI commands between the GUI and Lc0.
- Optionally rewrite `go` commands to a style-preserving setting such as `go nodes 1`.
- Expose friendlier engine metadata and options.

The implemented wrapper rewrites Lc0's `id name` and `id author` lines to package-specific Personal Maia metadata, and injects wrapper UCI options before `uciok`.

### Neural Network Architecture

Use the Maia/Lc0-compatible network format expected by the selected Maia Individual training code and Lc0 runtime.

The project should avoid inventing a new network architecture for MVP. A new architecture would also require changing training, export, inference, and engine runtime at the same time.

### Training Code

Use Maia Individual as the first trainer backend.

The app wraps it through adapters:

```text
personal_maia.maia.converter.MaiaDataConverter
personal_maia.maia.trainer.MaiaIndividualTrainer
```

Those adapters translate our project config into the files and command-line calls expected by Maia Individual. This keeps the product stable even if the research-code layout changes later.

## Engine Runtime Strategy

The final package should expose a simple UCI executable. Internally it can be one of two designs:

### Option A: Thin UCI Wrapper

`personal-maia-engine` is a small executable or script that forwards UCI traffic to Lc0:

```text
GUI <-> personal-maia-engine <-> lc0 -w weights/example-style.pb.gz
```

Advantages:

- Easy for en-croissant and other GUIs.
- Allows us to force stable defaults.
- Lets us hide platform-specific Lc0 arguments.
- Lets us report a friendly engine name through UCI.

Recommended default.

### Option B: Direct Lc0 Package

Tell the user to add the Lc0 binary directly and manually set the weights path.

Advantages:

- Less code.

Disadvantages:

- Worse user experience.
- More fragile across GUIs.
- Not truly one-click.

Use only as a fallback or debug mode.

## UCI Defaults

The personalized engine should be optimized for move imitation, not maximum strength.

Default runtime should likely include:

```text
weights = trained personal network
search = very low nodes, usually nodes 1
multipv = 1 unless analysis mode asks otherwise
temperature = disabled or controlled by our wrapper
opening book = optional, generated from target player's own openings
```

The `nodes 1` behavior is important because Maia-style play is usually about the network's policy prediction. Deep search can make the engine less human-like and more engine-like.

The wrapper should still accept normal UCI commands:

```text
uci
isready
ucinewgame
position ...
go depth N
go nodes N
go movetime N
stop
quit
```

For compatibility, it can translate most `go` commands to the configured Maia-style move policy unless the user enables an "analysis" profile.
