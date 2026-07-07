# 3. Data Sources

## Source Handling

### Lichess

Accept:

```text
https://lichess.org/@/username
https://lichess.org/@/username/perf/blitz
username
```

Use Lichess's public game export endpoint where possible. Store the raw PGN output before cleaning so runs are reproducible.

Supported filters:

- Time controls.
- Rated only.
- Date range.
- Color.
- Max games.
- Exclude variants other than standard chess by default.
- Exclude games shorter than a minimum ply count.

### Chess.com

Accept:

```text
https://www.chess.com/member/username
username
```

Use Chess.com's monthly game archive API. Download month archives, convert to PGN, and store raw files before cleaning.

Supported filters should mirror Lichess where possible.

### Local PGN

Accept:

```text
--pgn file.pgn
--pgn-dir ./games
```

The TUI should ask which player name to imitate if multiple names appear.

## Data Processing

The data pipeline should produce explicit artifacts:

```text
raw source files
-> normalized PGN
-> filtered target-player PGN
-> training examples
-> train/validation split
```

Filtering rules:

- Keep standard chess only by default.
- Drop ultra-short games.
- Drop obvious bot games unless the user allows them.
- Deduplicate games by site game id, headers, or move text hash.
- Preserve clock data when available, but do not require it for MVP.
- Keep only moves made by the target player.

Validation should report:

- Number of downloaded games.
- Number of usable games.
- Number of target-player moves.
- Openings distribution summary.
- Color split.
- Time-control split.
- Estimated rating range if available.

The tool should warn when there is not enough data. A practical first threshold:

```text
< 200 games: allow only demo/sanity training
200-1000 games: possible, high overfit risk
1000-5000 games: useful experiment
5000+ games: preferred
```

## Base Model Selection

The base model manager should download and cache official/open Maia weights.

Default selection:

1. Estimate the target player's rating from source metadata.
2. Pick the nearest Maia rating bucket.
3. Let the user override manually.

Initial supported base models:

```text
maia-1100
maia-1200
...
maia-1900
```

If integration with Maia Individual requires a specific base such as Maia 1900, the tool should start there and document the limitation in `training.json`.

