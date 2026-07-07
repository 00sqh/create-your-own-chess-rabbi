from __future__ import annotations

from dataclasses import dataclass
import re


HEADER_RE = re.compile(r'^\[([A-Za-z0-9_]+)\s+"(.*)"\]$')
COMMENT_RE = re.compile(r"\{[^}]*\}")
VARIATION_RE = re.compile(r"\([^()]*\)")
MOVE_NUMBER_RE = re.compile(r"\d+\.(?:\.\.)?")
NAG_RE = re.compile(r"\$\d+")
RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}


@dataclass(slots=True)
class PgnGame:
    headers: dict[str, str]
    moves: str
    raw: str

    @property
    def white(self) -> str:
        return self.headers.get("White", "")

    @property
    def black(self) -> str:
        return self.headers.get("Black", "")

    @property
    def variant(self) -> str:
        return self.headers.get("Variant", "Standard")

    @property
    def rated(self) -> bool:
        value = self.headers.get("Rated", "")
        return value.lower() in {"true", "yes", "1"}


@dataclass(slots=True)
class FilterReport:
    total_games: int
    kept_games: int
    dropped_wrong_player: int
    dropped_variant: int
    dropped_unrated: int
    dropped_short: int
    target_player: str
    target_moves_estimate: int


def parse_pgn(text: str) -> list[PgnGame]:
    chunks = _split_games(text)
    games: list[PgnGame] = []
    for chunk in chunks:
        headers: dict[str, str] = {}
        move_lines: list[str] = []
        in_headers = True
        for line in chunk.splitlines():
            stripped = line.strip()
            if not stripped:
                if headers:
                    in_headers = False
                continue
            match = HEADER_RE.match(stripped)
            if in_headers and match:
                headers[match.group(1)] = match.group(2)
            else:
                in_headers = False
                move_lines.append(stripped)
        if headers:
            games.append(PgnGame(headers=headers, moves=" ".join(move_lines), raw=chunk.strip()))
    return games


def filter_games(
    games: list[PgnGame],
    target_player: str,
    *,
    min_ply: int = 10,
    standard_only: bool = True,
    rated_only: bool = False,
) -> tuple[list[PgnGame], FilterReport]:
    target_key = normalize_player(target_player)
    kept: list[PgnGame] = []
    dropped_wrong_player = 0
    dropped_variant = 0
    dropped_unrated = 0
    dropped_short = 0
    target_moves_estimate = 0

    for game in games:
        target_color = target_color_for_game(game, target_key)
        if target_color is None:
            dropped_wrong_player += 1
            continue
        if standard_only and game.variant.lower() not in {"", "standard", "chess"}:
            dropped_variant += 1
            continue
        if rated_only and not game.rated:
            dropped_unrated += 1
            continue
        ply = estimate_ply_count(game.moves)
        if ply < min_ply:
            dropped_short += 1
            continue
        kept.append(game)
        target_moves_estimate += (ply + (0 if target_color == "white" else 1)) // 2

    report = FilterReport(
        total_games=len(games),
        kept_games=len(kept),
        dropped_wrong_player=dropped_wrong_player,
        dropped_variant=dropped_variant,
        dropped_unrated=dropped_unrated,
        dropped_short=dropped_short,
        target_player=target_player,
        target_moves_estimate=target_moves_estimate,
    )
    return kept, report


def target_color_for_game(game: PgnGame, normalized_target: str) -> str | None:
    if normalize_player(game.white) == normalized_target:
        return "white"
    if normalize_player(game.black) == normalized_target:
        return "black"
    return None


def normalize_player(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def estimate_ply_count(moves: str) -> int:
    tokens = clean_movetext(moves).split()
    return sum(1 for token in tokens if token not in RESULTS)


def clean_movetext(moves: str) -> str:
    cleaned = COMMENT_RE.sub(" ", moves)
    while True:
        updated = VARIATION_RE.sub(" ", cleaned)
        if updated == cleaned:
            break
        cleaned = updated
    cleaned = NAG_RE.sub(" ", cleaned)
    cleaned = MOVE_NUMBER_RE.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def games_to_pgn(games: list[PgnGame]) -> str:
    return "\n\n".join(game.raw for game in games).strip() + ("\n" if games else "")


def _split_games(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    starts = [match.start() for match in re.finditer(r"(?m)^\[Event\s+\"", normalized)]
    if not starts:
        return [normalized]
    chunks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(normalized)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
    return chunks

