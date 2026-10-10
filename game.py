"""Word Duel game rules. Plain Python, no web code, so it is easy to test."""
import random
import time
from dataclasses import dataclass, field
from typing import Optional

# (row change, column change) for the eight directions a word can run in.
DIRS = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

WORD_SETS = {
    "animals": ["TIGER", "ZEBRA", "OTTER", "FALCON", "PANDA", "LEMUR", "BADGER", "GIRAFFE"],
    "kitchen": ["WHISK", "LADLE", "SPATULA", "COLANDER", "GRATER", "SKILLET", "TEAPOT", "MORTAR"],
    "space": ["COMET", "ORBIT", "GALAXY", "NEBULA", "ROCKET", "PLANET", "METEOR", "ECLIPSE"],
    "cities": ["LONDON", "PARIS", "ROME", "MADRID", "VIENNA", "PRAGUE", "LISBON", "OSLO"],
}

VALID_SIZES = (1, 2, 3, 4, 6, 8)
AVATAR_COUNT = 8  # the page draws 8 characters; each player in a room gets a different one
START_MESSAGE = "Find the words. Arrows move, Space picks a letter."


def layout(capacity):
    """Return (team_size, team_count) for a room with this many players.

    1 to 3 players: everyone plays alone (1 player is solo, 2 or 3 race each other).
    4, 6 or 8 players: teams of 2.
    """
    if capacity not in VALID_SIZES:
        raise ValueError("Rooms hold 1, 2, 3, 4, 6 or 8 players")
    team_size = 2 if capacity >= 4 else 1
    return team_size, capacity // team_size


def _place(grid, word, size, rng):
    """Try to put one word somewhere in the grid. Returns True if it fit."""
    for _ in range(400):
        dr, dc = rng.choice(DIRS)
        r, c = rng.randrange(size), rng.randrange(size)
        er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
        if not (0 <= er < size and 0 <= ec < size):
            continue
        if all(grid[r + dr * i][c + dc * i] in ("", word[i]) for i in range(len(word))):
            for i, ch in enumerate(word):
                grid[r + dr * i][c + dc * i] = ch
            return True
    return False


def make_grid(words, size=12, rng=None):
    """Return a size x size grid (list of rows) with every word hidden in it."""
    rng = rng or random.Random()
    size = max(size, max(len(w) for w in words))
    ordered = sorted(words, key=len, reverse=True)
    for _ in range(60):
        grid = [[""] * size for _ in range(size)]
        if all(_place(grid, w, size, rng) for w in ordered):
            pool = "".join(words) + ALPHABET  # filler leans on the word letters
            for r in range(size):
                for c in range(size):
                    if not grid[r][c]:
                        grid[r][c] = rng.choice(pool)
            return grid
    raise ValueError("Could not fit the words into the grid")


def occurrences(grid, word):
    """Every place the word appears in the grid, as a list of cell lists.

    This includes copies that formed by chance, so finding one of those counts too.
    """
    n = len(grid)
    spots = []
    for r in range(n):
        for c in range(n):
            for dr, dc in DIRS:
                er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                if not (0 <= er < n and 0 <= ec < n):
                    continue
                if all(grid[r + dr * i][c + dc * i] == word[i] for i in range(len(word))):
                    spots.append([(r + dr * i, c + dc * i) for i in range(len(word))])
    return spots


@dataclass
class Player:
    id: str
    name: str
    team: Optional[int]  # set when the game starts
    r: int
    c: int
    picked: list = field(default_factory=list)  # cells this player has picked
    avatar: int = 0  # which of the 8 characters this player is
    connected: bool = True  # False while they are away from a game that has started


class Room:
    """One game. Every team gets the same puzzle on its own board and races to
    find all the words first. Teams cannot see each other's boards, only how
    many words the other teams have found."""

    def __init__(self, capacity=4, rng=None, code="", clock=None):
        self.capacity = capacity
        self.team_size, self.team_count = layout(capacity)
        self.code = code
        self.rng = rng or random.Random()
        self.clock = clock or time.monotonic
        self.players = {}
        self.started = False
        self.round = 0
        self.new_round()

    @property
    def mode(self):
        if self.capacity == 1:
            return "solo"
        return "ffa" if self.team_size == 1 else "teams"

    def new_round(self):
        self.round += 1
        self.theme = self.rng.choice(list(WORD_SETS))
        self.words = list(WORD_SETS[self.theme])
        self.grid = make_grid(self.words, 12, self.rng)
        self.size = len(self.grid)
        self.spots = {w: occurrences(self.grid, w) for w in self.words}  # server only
        self.found = [{} for _ in range(self.team_count)]  # per team: word -> {"cells": [[r, c], ...]}
        self.messages = [START_MESSAGE] * self.team_count
        self.finished_at = [None] * self.team_count  # seconds from the start
        self.winner = None
        self.t0 = self.clock()
        for p in self.players.values():
            p.picked = []
            p.r, p.c = self._spawn()

    def _spawn(self):
        return self.rng.randrange(self.size), self.rng.randrange(self.size)

    @property
    def over(self):
        return self.winner is not None

    def elapsed(self):
        """Seconds since the round began, frozen at the winner's time once it is over."""
        if not self.started:
            return 0.0
        if self.winner is not None:
            return self.finished_at[self.winner]
        return self.clock() - self.t0

    def add_player(self, pid, name):
        """Add a player. The game starts by itself once the room is full."""
        if self.started or len(self.players) >= self.capacity:
            return None
        r, c = self._spawn()
        taken = {q.avatar for q in self.players.values()}
        avatar = self.rng.choice([a for a in range(AVATAR_COUNT) if a not in taken])
        player = Player(pid, name, None, r, c, avatar=avatar)
        self.players[pid] = player
        if len(self.players) == self.capacity:
            self.start()
        return player

    def start(self):
        """Hand out teams in join order (the first two together, the next two, ...)."""
        for i, p in enumerate(self.players.values()):
            p.team = i // self.team_size
        self.started = True
        self.new_round()

    def remove_player(self, pid):
        """Called when a player's connection closes.

        Before the game starts the seat is freed. Once it has started the player
        keeps their seat and team and is only marked away, so they can come back.
        """
        p = self.players.get(pid)
        if not p:
            return
        if self.started:
            p.connected = False
        else:
            del self.players[pid]

    def reconnect(self, pid):
        """Give a seat back to a player who left a game that is already running."""
        p = self.players.get(pid)
        if p and self.started:
            p.connected = True
            return p
        return None

    def move(self, pid, dr, dc):
        p = self.players.get(pid)
        if not p or not self.started or self.over:
            return
        dr = max(-1, min(1, int(dr)))
        dc = max(-1, min(1, int(dc)))
        p.r = max(0, min(self.size - 1, p.r + dr))
        p.c = max(0, min(self.size - 1, p.c + dc))

    def cancel(self, pid):
        """Esc: drop every letter picked so far."""
        p = self.players.get(pid)
        if p:
            p.picked = []

    def select(self, pid):
        """Space key: pick the letter under the avatar, or deselect it if already picked.

        Any letters can be picked, in any order, with extras in between. A word
        counts for the team as soon as every cell of it is picked by the player
        or by their teammate, so two teammates can finish a word between them.
        Cells used by a finished word are dropped from the team's picks, and any
        other picks stay. The first team to find every word wins.
        """
        p = self.players.get(pid)
        if not p or not self.started or self.over:
            return
        cell = (p.r, p.c)
        if cell in p.picked:
            p.picked.remove(cell)
            return
        p.picked.append(cell)

        teammates = [q for q in self.players.values() if q.team == p.team]
        picked = set()
        for q in teammates:
            picked.update(q.picked)
        found = self.found[p.team]
        done = []
        for word in self.words:
            if word in found:
                continue
            for cells in self.spots[word]:
                if all(c in picked for c in cells):
                    done.append((word, cells))
                    break
        if not done:
            return
        used = set()
        for word, cells in done:
            found[word] = {"cells": [list(x) for x in cells]}
            used.update(cells)
        for q in teammates:
            q.picked = [c for c in q.picked if c not in used]
        self.messages[p.team] = f"{p.name} found {', '.join(w for w, _ in done)}."
        if len(found) == len(self.words):
            self.finished_at[p.team] = self.clock() - self.t0
            self.winner = p.team

    def snapshot(self, you):
        """What gets sent to one player.

        A started game shows only that player's own team: their board, their
        teammates and their list. Other teams appear only as a name list and a
        count of words found. Word positions are never included.
        """
        me = self.players.get(you)
        team = me.team if me else None
        found = self.found[team] if team is not None else {}
        if self.started and team is not None:
            visible = [p for p in self.players.values() if p.team == team]
        else:
            visible = list(self.players.values())
        return {
            "type": "state",
            "you": you,
            "code": self.code,
            "capacity": self.capacity,
            "mode": self.mode,
            "teamCount": self.team_count,
            "started": self.started,
            "round": self.round,
            "size": self.size,
            "grid": self.grid,
            "theme": self.theme,
            "myTeam": team,
            "words": [{"word": w, "found": w in found} for w in self.words],
            "found": [{"cells": f["cells"]} for f in found.values()],
            "players": [
                {"id": p.id, "name": p.name, "team": p.team, "avatar": p.avatar,
                 "connected": p.connected,
                 "r": p.r, "c": p.c, "picked": [list(x) for x in p.picked]}
                for p in visible
            ],
            "teams": [
                {"team": t,
                 "members": [{"name": p.name, "avatar": p.avatar, "you": p.id == you,
                              "connected": p.connected}
                             for p in self.players.values() if p.team == t],
                 "found": len(self.found[t]),
                 "done": self.finished_at[t] is not None}
                for t in range(self.team_count)
            ],
            "winner": self.winner,
            "over": self.over,
            "elapsed": round(self.elapsed(), 1),
            "message": self.messages[team] if team is not None else START_MESSAGE,
        }