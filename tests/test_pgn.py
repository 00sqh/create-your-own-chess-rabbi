from personal_maia.data.pgn import estimate_ply_count, filter_games, parse_pgn


PGN = """
[Event "Rated Blitz game"]
[Site "https://lichess.org/abc"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[Variant "Standard"]
[Rated "True"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0

[Event "Casual Blitz game"]
[Site "https://lichess.org/def"]
[White "Carol"]
[Black "Alice"]
[Result "0-1"]
[Variant "Standard"]
[Rated "False"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 0-1

[Event "Chess960 game"]
[Site "https://lichess.org/ghi"]
[White "Alice"]
[Black "Dan"]
[Result "*"]
[Variant "Chess960"]
[Rated "True"]

1. g3 g6 2. Bg2 Bg7 3. Nf3 Nf6 *
"""


def test_parse_pgn_multiple_games():
    games = parse_pgn(PGN)
    assert len(games) == 3
    assert games[0].white == "Alice"
    assert games[1].black == "Alice"


def test_estimate_ply_count_ignores_move_numbers_and_results():
    assert estimate_ply_count("1. e4 e5 2. Nf3 Nc6 1-0") == 4


def test_filter_games_for_target_player():
    games = parse_pgn(PGN)
    kept, report = filter_games(games, "alice", min_ply=6, standard_only=True)
    assert len(kept) == 2
    assert report.total_games == 3
    assert report.dropped_variant == 1
    assert report.target_moves_estimate == 10


def test_filter_rated_only():
    games = parse_pgn(PGN)
    kept, report = filter_games(games, "Alice", min_ply=6, standard_only=True, rated_only=True)
    assert len(kept) == 1
    assert report.dropped_unrated == 1

