import random

import pytest

from game import AVATAR_COUNT, VALID_SIZES, WORD_SETS, Room, layout, make_grid, occurrences

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


def full_room(capacity, seed=1, clock=None):
    room = Room(capacity, random.Random(seed), clock=clock)
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
    word = room.words[0]
    cells = find_word(room.grid, word)
    pick(room, "p2", cells[:-1])  # one cell short
    assert room.found == [{}, {}]
    pick(room, "p2", cells[-1:])
    assert word in room.found[1]  # p2 is in the second team
    assert room.players["p2"].picked == []


def test_each_team_has_its_own_board():
    room = full_room(4, seed=3)
    word = room.words[0]
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


def test_first_team_to_find_every_word_wins():
    clock = Clock()
    room = full_room(2, seed=5, clock=clock)
    clock.t = 90.0
    for w in room.words[:-1]:
        pick(room, "p0", find_word(room.grid, w))
    assert not room.over
    pick(room, "p1", find_word(room.grid, room.words[0]))  # the other player is progressing too
    pick(room, "p0", find_word(room.grid, room.words[-1]))
    assert room.over and room.winner == 0
    assert room.elapsed() == 90.0
    clock.t = 500.0
    assert room.elapsed() == 90.0  # frozen at the winner's time

    p1 = room.players["p1"]
    p1.r, p1.c = 3, 3
    room.move("p1", 1, 0)
    assert (p1.r, p1.c) == (3, 3)  # the board is frozen once someone has won


def test_new_round_starts_fresh():
    room = full_room(1, seed=6)
    for w in room.words:
        pick(room, "p0", find_word(room.grid, w))
    assert room.over
    room.new_round()
    assert not room.over and room.winner is None
    assert room.found == [{}] and room.players["p0"].picked == []


def test_snapshot_shows_only_your_own_team():
    room = full_room(4, seed=6)
    pick(room, "p2", find_word(room.grid, room.words[0]))
    mine, other = room.snapshot("p0"), room.snapshot("p2")
    assert [p["id"] for p in mine["players"]] == ["p0", "p1"]
    assert mine["found"] == [] and not mine["words"][0]["found"]
    assert other["words"][0]["found"] and len(other["found"]) == 1
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