import random

import pytest

from game import VALID_SIZES, WORD_SETS, Room, layout, make_grid, occurrences

DIRS = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]


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


def full_room(capacity, seed=1):
    room = Room(capacity, random.Random(seed))
    for i in range(capacity):
        room.add_player(f"p{i}", f"P{i}")
    return room


def test_every_word_is_in_the_grid():
    for words in WORD_SETS.values():
        for seed in range(20):
            grid = make_grid(words, 12, random.Random(seed))
            for w in words:
                assert find_word(grid, w), (w, seed)


def test_occurrences_includes_the_hidden_word():
    grid = make_grid(["OTTER"], 12, random.Random(1))
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
    assert room.mode == mode
    assert [p.team for p in room.players.values()] == teams
    assert len(room.scores) == max(teams) + 1


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
    word = room.words[0]
    cells = find_word(room.grid, word)
    pick(room, "p2", cells[:-1])  # one cell short
    assert room.scores == [0, 0] and word not in room.found
    pick(room, "p2", cells[-1:])
    assert room.found[word]["team"] == 1  # p2 is in the second team
    assert room.scores == [0, len(word)]
    assert room.players["p2"].picked == []


def test_everyone_scores_for_themselves_in_a_free_for_all():
    room = full_room(3, seed=4)
    word = room.words[0]
    pick(room, "p1", find_word(room.grid, word))
    assert room.scores == [0, len(word), 0]


def test_teammates_can_finish_a_word_together():
    room = full_room(4, seed=11)  # p0 and p1 are one team, p2 and p3 the other
    word = room.words[0]
    cells = find_word(room.grid, word)
    half = len(cells) // 2
    pick(room, "p0", cells[:half])
    assert word not in room.found
    pick(room, "p1", cells[half:])
    assert room.found[word]["team"] == 0
    assert room.scores == [len(word), 0]
    assert room.players["p0"].picked == [] and room.players["p1"].picked == []


def test_picks_do_not_combine_across_teams_or_between_solo_players():
    room = full_room(4, seed=12)
    cells = find_word(room.grid, room.words[0])
    half = len(cells) // 2
    pick(room, "p0", cells[:half])  # team 0
    pick(room, "p2", cells[half:])  # team 1
    assert room.found == {}

    ffa = full_room(2, seed=12)
    cells = find_word(ffa.grid, ffa.words[0])
    half = len(cells) // 2
    pick(ffa, "p0", cells[:half])
    pick(ffa, "p1", cells[half:])
    assert ffa.found == {}


def test_order_and_extra_picks_do_not_matter():
    room = full_room(1, seed=9)
    word = room.words[0]
    cells = find_word(room.grid, word)
    shuffled = cells[:]
    random.Random(1).shuffle(shuffled)
    noise = [(0, 0)] if (0, 0) not in cells else [(11, 11)]
    pick(room, "p0", noise + shuffled)
    assert word in room.found
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


def test_snapshot_does_not_leak_word_positions():
    room = full_room(2, seed=6)
    snap = room.snapshot("p0")
    assert snap["found"] == []
    assert all(set(w) == {"word", "team"} for w in snap["words"])
    assert "spots" not in snap
    assert snap["mode"] == "ffa" and snap["teamCount"] == 2 and snap["started"]