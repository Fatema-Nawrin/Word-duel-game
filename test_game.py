import random

import pytest

import game
from game import (AVATAR_COUNT, BOARD_SIZE, DECOY_COUNT, MAX_PER_WORD, TIME_LIMIT, VALID_SIZES,
                  WORD_COUNTS, WORD_POOL, Room, layout, make_grid, occurrences)

DIRS = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]


class Clock:
    """A clock the test controls, so finish times are exact."""
    t = 0.0

    def __call__(self):
        return self.t


def find_word(grid, word):
    """Brute force: the cells of the word if it is hidden in the grid, else None."""
    n = len(grid)
    for r in range(n):
        for c in range(n):
            for dr, dc in DIRS:
                er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                if 0 <= er < n and 0 <= ec < n:
                    if all(grid[r + dr * i][c + dc * i] == word[i] for i in range(len(word))):
                        return [(r + dr * i, c + dc * i) for i in range(len(word))]
    return None


def pick(room, pid, cells):
    """Walk the avatar to each cell and press Space."""
    p = room.players[pid]
    for r, c in cells:
        p.r, p.c = r, c
        room.select(pid)


def solve(room, pid, words=None):
    """Find every word (or just the given ones) that the player's team has not found yet."""
    p = room.players[pid]
    for w in (words if words is not None else room.words):
        if w in room.found[p.team]:
            continue
        pick(room, pid, [c for c in find_word(room.grid, w) if c not in p.picked])


def full_room(capacity, seed=1, clock=None):
    room = Room(capacity, random.Random(seed), clock=clock)
    for i in range(capacity):
        room.add_player(f"p{i}", f"P{i}")
    return room


def test_every_word_is_in_the_grid():
    for seed in range(30):
        room = Room(1, random.Random(seed))
        assert len(room.grid) == BOARD_SIZE
        assert all(len(row) == BOARD_SIZE for row in room.grid)
        for w in room.words:
            assert find_word(room.grid, w), (w, seed)
            assert room.spots[w], (w, seed)


def test_each_round_has_16_words_from_the_right_pools():
    assert sum(WORD_COUNTS.values()) == 16
    for seed in range(30):
        room = Room(1, random.Random(seed))
        assert len(room.words) == 16 and len(set(room.words)) == 16
        for kind, n in WORD_COUNTS.items():
            assert sum(w in WORD_POOL[kind] for w in room.words) == n
        assert any(len(w) in (11, 12) for w in room.words)  # one 11 or 12 letter word every round


def test_word_pools_have_no_repeats_and_fit_the_board():
    every = [w for pool in WORD_POOL.values() for w in pool]
    assert len(every) == len(set(every))
    assert all(len(w) <= BOARD_SIZE for w in every)
    assert max(map(len, WORD_POOL["huge"])) == 12 and min(map(len, WORD_POOL["huge"])) == 11


def test_decoys_are_added_without_changing_any_existing_letter():
    rng = random.Random(1)
    words = ["TELESCOPE", "PORCUPINE", "KANGAROO", "GALAXY", "ROCKET"]
    grid = [[""] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    for w in words:
        assert game._place(grid, w, BOARD_SIZE, rng)
    before = [row[:] for row in grid]
    assert game._decoys(grid, words, BOARD_SIZE, rng, DECOY_COUNT) == DECOY_COUNT
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            assert before[r][c] in ("", grid[r][c])  # letters that were there are untouched
    assert sum(cell != "" for row in grid for cell in row) > sum(cell != "" for row in before for cell in row)


def test_occurrences_includes_the_hidden_word():
    grid = make_grid(["OTTER"], BOARD_SIZE, random.Random(1))
    assert find_word(grid, "OTTER") in occurrences(grid, "OTTER")


def test_layout_for_each_room_size():
    assert [layout(n) for n in VALID_SIZES] == [(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (2, 4)]
    with pytest.raises(ValueError):
        layout(5)
    with pytest.raises(ValueError):
        Room(5)


@pytest.mark.parametrize("capacity, teams, mode", [
    (1, [0], "solo"),
    (2, [0, 1], "ffa"),
    (3, [0, 1, 2], "ffa"),
    (4, [0, 0, 1, 1], "teams"),
    (6, [0, 0, 1, 1, 2, 2], "teams"),
    (8, [0, 0, 1, 1, 2, 2, 3, 3], "teams"),
])
def test_teams_for_each_room_size(capacity, teams, mode):
    room = full_room(capacity)
    assert room.started
    assert room.size == BOARD_SIZE
    assert room.mode == mode
    assert [p.team for p in room.players.values()] == teams
    assert len(room.found) == max(teams) + 1  # one board per team


def test_each_player_gets_a_different_random_avatar():
    room = full_room(8, seed=2)
    assert sorted(p.avatar for p in room.players.values()) == list(range(AVATAR_COUNT))
    firsts = {full_room(1, seed=s).players["p0"].avatar for s in range(40)}
    assert len(firsts) > 3  # not always the same character


def test_game_waits_until_the_room_is_full():
    room = Room(4, random.Random(2))
    for i in range(3):
        room.add_player(f"p{i}", f"P{i}")
    assert not room.started
    pick(room, "p0", [(1, 1)])
    assert room.players["p0"].picked == []  # picks are ignored before the start
    room.add_player("p3", "P3")
    assert room.started
    assert room.add_player("late", "Late") is None  # full, and already running


def test_word_counts_only_when_every_cell_is_picked():
    room = full_room(4, seed=3)
    word = min(room.words, key=len)  # short enough for one player in a team to finish alone
    cells = find_word(room.grid, word)
    pick(room, "p2", cells[:-1])  # one cell short
    assert room.found == [{}, {}]
    pick(room, "p2", cells[-1:])
    assert word in room.found[1]  # p2 is in the second team
    assert room.players["p2"].picked == []


def test_each_team_has_its_own_board():
    room = full_room(4, seed=3)
    word = min(room.words, key=len)
    cells = find_word(room.grid, word)
    pick(room, "p2", cells)
    assert word in room.found[1] and word not in room.found[0]
    pick(room, "p0", cells)  # the other team can still find the same word
    assert word in room.found[0]


def test_players_in_a_free_for_all_have_their_own_boards():
    room = full_room(3, seed=4)
    word = room.words[0]
    pick(room, "p1", find_word(room.grid, word))
    assert [len(f) for f in room.found] == [0, 1, 0]


def test_teammates_can_finish_a_word_together():
    room = full_room(4, seed=11)  # p0 and p1 are one team, p2 and p3 the other
    word = room.words[0]
    cells = find_word(room.grid, word)
    half = len(cells) // 2
    pick(room, "p0", cells[:half])
    assert word not in room.found[0]
    pick(room, "p1", cells[half:])
    assert word in room.found[0]
    assert room.players["p0"].picked == [] and room.players["p1"].picked == []


def test_picks_do_not_combine_across_teams_or_between_solo_players():
    room = full_room(4, seed=12)
    cells = find_word(room.grid, room.words[0])
    half = len(cells) // 2
    pick(room, "p0", cells[:half])  # team 0
    pick(room, "p2", cells[half:])  # team 1
    assert room.found == [{}, {}]

    ffa = full_room(2, seed=12)
    cells = find_word(ffa.grid, ffa.words[0])
    half = len(cells) // 2
    pick(ffa, "p0", cells[:half])
    pick(ffa, "p1", cells[half:])
    assert ffa.found == [{}, {}]


def test_order_and_extra_picks_do_not_matter():
    room = full_room(1, seed=9)
    word = room.words[0]
    cells = find_word(room.grid, word)
    shuffled = cells[:]
    random.Random(1).shuffle(shuffled)
    noise = [(0, 0)] if (0, 0) not in cells else [(11, 11)]
    pick(room, "p0", noise + shuffled)
    assert word in room.found[0]
    assert room.players["p0"].picked == noise  # the extra pick stays picked


def test_space_on_a_picked_letter_deselects_just_that_letter():
    room = full_room(1, seed=8)
    p = room.players["p0"]
    pick(room, "p0", [(1, 1), (7, 4), (3, 9)])
    assert p.picked == [(1, 1), (7, 4), (3, 9)]
    pick(room, "p0", [(7, 4)])
    assert p.picked == [(1, 1), (3, 9)]


def test_cancel_clears_picks():
    room = full_room(1, seed=4)
    pick(room, "p0", [(1, 1), (2, 2)])
    room.cancel("p0")
    assert room.players["p0"].picked == []


def test_move_stays_inside_grid():
    room = full_room(1, seed=5)
    p = room.players["p0"]
    p.r, p.c = 0, 0
    room.move("p0", -1, -1)
    assert (p.r, p.c) == (0, 0)
    p.r, p.c = room.size - 1, room.size - 1
    room.move("p0", 1, 1)
    assert (p.r, p.c) == (room.size - 1, room.size - 1)


def test_a_team_that_finds_every_word_waits_and_the_round_runs_on():
    clock = Clock()
    room = full_room(2, seed=5, clock=clock)
    clock.t = 90.0
    solve(room, "p0")
    assert room.finished_at == [90.0, None]
    assert not room.over  # p1 is still playing, so the round continues
    cell = (5, 5)
    n = len(room.players["p0"].picked)
    pick(room, "p0", [cell])
    assert len(room.players["p0"].picked) == n  # a finished team cannot pick any more
    pick(room, "p1", find_word(room.grid, room.words[0]))  # the other player keeps going
    assert len(room.found[1]) >= 1


def test_the_round_ends_early_only_if_every_team_finishes():
    clock = Clock()
    room = full_room(2, seed=5, clock=clock)
    clock.t = 90.0
    solve(room, "p0")
    clock.t = 150.0
    assert not room.over
    solve(room, "p1")
    assert room.over and not room.time_up
    assert room.ended_at == 150.0 and room.elapsed() == 150.0
    clock.t = 400.0
    assert room.elapsed() == 150.0  # frozen
    assert [r["team"] for r in room.ranking()] == [0, 1]  # p0 finished first


def test_time_runs_out_after_ten_minutes_and_the_board_freezes():
    clock = Clock()
    room = full_room(2, seed=5, clock=clock)
    assert TIME_LIMIT == 600
    clock.t = TIME_LIMIT - 1
    assert not room.over and room.remaining() == 1
    clock.t = TIME_LIMIT
    assert room.over and room.time_up and room.remaining() == 0
    clock.t = TIME_LIMIT + 500
    assert room.elapsed() == TIME_LIMIT  # never longer than the limit

    p = room.players["p1"]
    p.r, p.c = 3, 3
    room.move("p1", 1, 0)
    assert (p.r, p.c) == (3, 3)  # frozen
    pick(room, "p1", find_word(room.grid, room.words[0]))
    assert room.found == [{}, {}] and p.picked == []


def test_ranking_orders_by_words_then_by_who_got_there_first():
    clock = Clock()
    room = full_room(3, seed=6, clock=clock)
    clock.t = 10.0
    solve(room, "p1", room.words[:2])   # p1: two words at 10s
    clock.t = 20.0
    solve(room, "p2", room.words[:2])   # p2: two words at 20s
    clock.t = 30.0
    solve(room, "p0", room.words[:1])   # p0: one word
    clock.t = TIME_LIMIT
    rank = room.ranking()
    assert [r["team"] for r in rank] == [1, 2, 0]
    assert [r["rank"] for r in rank] == [1, 2, 3]
    assert [r["found"] for r in rank] == [2, 2, 1]
    assert rank[0]["at"] == 10.0 and rank[0]["done"] is False


def test_teams_that_are_completely_level_share_a_rank():
    room = full_room(3, seed=6)  # nobody has found anything
    assert [r["rank"] for r in room.ranking()] == [1, 1, 1]


def test_snapshot_has_the_ranking_and_the_clock():
    room = full_room(2, seed=5)
    snap = room.snapshot("p0")
    assert snap["limit"] == TIME_LIMIT and snap["timeUp"] is False and snap["over"] is False
    assert len(snap["ranking"]) == 2 and "winner" not in snap
    room.clock = lambda: room.t0 + TIME_LIMIT
    snap = room.snapshot("p0")
    assert snap["over"] and snap["timeUp"] and snap["elapsed"] == TIME_LIMIT


def test_in_team_games_one_player_can_pick_at_most_six_letters_of_a_word():
    assert MAX_PER_WORD == 6
    room = full_room(4, seed=5)
    word = max(room.words, key=len)  # 11 or 12 letters
    cells = find_word(room.grid, word)
    p0 = room.players["p0"]
    pick(room, "p0", cells[:8])
    assert sum(c in p0.picked for c in cells) == 6  # the 7th and 8th are refused
    pick(room, "p1", cells[6:])  # the teammate adds the rest
    assert word in room.found[0]


def test_a_word_of_six_letters_or_fewer_can_be_finished_by_one_player_in_a_team():
    room = full_room(4, seed=5)
    word = min(room.words, key=len)
    pick(room, "p0", find_word(room.grid, word))
    assert word in room.found[0]


def test_one_player_cannot_finish_a_long_word_alone_in_a_team_but_can_when_playing_solo():
    room = full_room(4, seed=5)
    word = max(room.words, key=len)
    pick(room, "p0", find_word(room.grid, word))
    assert word not in room.found[0]
    solo = full_room(1, seed=5)
    word = max(solo.words, key=len)
    pick(solo, "p0", find_word(solo.grid, word))
    assert word in solo.found[0]


def test_new_round_starts_fresh():
    room = full_room(1, seed=6)
    solve(room, "p0")
    assert room.over and room.ended_at is not None  # the only team finished, so the round ends
    room.new_round()
    assert not room.over and room.ended_at is None and room.finished_at == [None]
    assert room.found == [{}] and room.players["p0"].picked == []
    assert room.last_at == [None]


def test_snapshot_shows_only_your_own_team():
    room = full_room(4, seed=6)
    word = min(room.words, key=len)
    i = room.words.index(word)
    pick(room, "p2", find_word(room.grid, word))
    mine, other = room.snapshot("p0"), room.snapshot("p2")
    assert [p["id"] for p in mine["players"]] == ["p0", "p1"]
    assert mine["found"] == [] and not mine["words"][i]["found"]
    assert other["words"][i]["found"] and len(other["found"]) == 1
    assert [t["found"] for t in mine["teams"]] == [0, 1]  # counts are shared, not which words
    assert [m["name"] for m in mine["teams"][1]["members"]] == ["P2", "P3"]
    assert [m["you"] for m in mine["teams"][0]["members"]] == [True, False]
    assert all(0 <= p["avatar"] < AVATAR_COUNT for p in mine["players"])
    assert mine["myTeam"] == 0 and other["myTeam"] == 1
    assert "spots" not in mine
    assert all(set(w) == {"word", "found"} for w in mine["words"])


def test_leaving_before_the_start_frees_the_seat():
    room = Room(4, random.Random(2))
    room.add_player("a", "A")
    room.add_player("b", "B")
    room.remove_player("a")
    assert list(room.players) == ["b"]


def test_a_player_who_leaves_a_running_game_keeps_their_seat_and_can_return():
    room = full_room(4, seed=7)
    pick(room, "p1", [(2, 2)])
    room.remove_player("p1")
    p = room.players["p1"]
    assert not p.connected and p.team == 0 and p.picked == [(2, 2)]
    assert room.add_player("stranger", "S") is None  # the seat is still taken
    assert room.reconnect("p1") is p and p.connected
    assert room.reconnect("nobody") is None
    snap = room.snapshot("p0")
    assert [m["connected"] for m in snap["teams"][0]["members"]] == [True, True]


def test_the_away_players_picks_still_count_for_the_team():
    room = full_room(4, seed=11)
    word = room.words[0]
    cells = find_word(room.grid, word)
    half = len(cells) // 2
    pick(room, "p1", cells[half:])
    room.remove_player("p1")  # p1 leaves after picking
    pick(room, "p0", cells[:half])
    assert word in room.found[0]