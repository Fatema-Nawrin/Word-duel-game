"""Word Duel server. Run with:  python -m uvicorn main:app --reload"""
import asyncio
import json
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game import TIME_LIMIT, VALID_SIZES, Room

app = FastAPI()
BASE = Path(__file__).parent


@app.middleware("http")
async def always_recheck(request, call_next):
    """Make the browser re-check the page, scripts and styles on every load, so edits show up at once.
    (It still uses its saved copy when nothing changed, so this is cheap.)"""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount(
    "/static",
    StaticFiles(directory=BASE / "static"),
    name="static",
)


rooms = {}        # room code -> Room
sockets = {}      # room code -> {player id -> WebSocket}
tokens = {}       # room code -> {secret token -> player id}, used to come back to a seat
empty_since = {}  # room code -> when the last player left a running game
clocks = {}       # room code -> (round number, task that tells everyone when time is up)

# How long a running game is kept after everyone has left, so people can come back.
KEEP_EMPTY_ROOM_SECONDS = 600

# No 0/O or 1/I, so codes are easy to read out loud.
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@app.get("/")
async def index():
    return FileResponse(BASE / "index.html")


def new_code():
    while True:
        code = "".join(secrets.choice(CODE_CHARS) for _ in range(4))
        if code not in rooms:
            return code


def drop_room(code):
    rooms.pop(code, None)
    sockets.pop(code, None)
    tokens.pop(code, None)
    empty_since.pop(code, None)
    old = clocks.pop(code, None)
    if old:
        old[1].cancel()


def drop_room_if_still_empty(code):
    """Runs a while after the last player left a running game."""
    since = empty_since.get(code)
    if since is not None and not sockets.get(code) and time.monotonic() - since >= KEEP_EMPTY_ROOM_SECONDS - 1:
        drop_room(code)


async def broadcast(code):
    room = rooms[code]
    dead = []
    for pid, ws in list(sockets[code].items()):
        try:
            await ws.send_json(room.snapshot(pid))
        except Exception:
            dead.append(pid)
    for pid in dead:
        sockets[code].pop(pid, None)
        room.remove_player(pid)


async def announce_time_up(code, round_no, delay):
    """Sleep until the round's time runs out, then send everyone the final state."""
    await asyncio.sleep(delay)
    room = rooms.get(code)
    if room and room.round == round_no and room.time_up:
        await broadcast(code)


def arm_clock(code):
    """Make sure a time-up message is scheduled for the current round of a running game."""
    room = rooms[code]
    if not room.started or room.over:
        return
    current = clocks.get(code)
    if current and current[0] == room.round and not current[1].done():
        return
    if current:
        current[1].cancel()
    delay = max(0.0, TIME_LIMIT - room.elapsed()) + 0.3
    clocks[code] = (room.round, asyncio.get_running_loop().create_task(
        announce_time_up(code, room.round, delay)))


async def refuse(ws, text):
    await ws.send_json({"type": "error", "text": text})
    await ws.close()


async def run_player(ws, code, name, rejoin=""):
    """Seat one player in an existing room and handle their messages until they leave.

    `rejoin` is the secret token a player was given the first time. If it matches a
    seat in a game that is already running, they get that seat back (same team,
    same avatar, same picks) instead of being turned away.
    """
    room = rooms[code]
    pid = tokens[code].get(rejoin) if rejoin else None
    if pid and room.reconnect(pid):
        token = rejoin
        old = sockets[code].pop(pid, None)  # a stale connection of the same player, if any
        if old is not None:
            try:
                await old.close()
            except Exception:
                pass
    else:
        pid = secrets.token_hex(4)
        if not room.add_player(pid, name.strip()[:14] or "Player"):
            await refuse(ws, "That room is full, or its game has already started.")
            return
        token = secrets.token_urlsafe(12)
        tokens[code][token] = pid

    empty_since.pop(code, None)
    sockets[code][pid] = ws
    # The token goes only to this player. Other players only ever see the public id.
    await ws.send_json({"type": "hello", "code": code, "token": token})
    arm_clock(code)
    await broadcast(code)

    try:
        while True:
            try:
                msg = json.loads(await ws.receive_text())
            except ValueError:
                continue
            kind = msg.get("type")
            if kind == "move":
                room.move(pid, msg.get("dy", 0), msg.get("dx", 0))
            elif kind == "select":
                room.select(pid)
            elif kind == "cancel":
                room.cancel(pid)
            elif kind == "restart" and room.over:
                room.new_round()
                arm_clock(code)
            else:
                continue
            await broadcast(code)
    except WebSocketDisconnect:
        pass
    finally:
        # Only clean up if this is still the player's current connection.
        if sockets.get(code, {}).get(pid) is ws:
            sockets[code].pop(pid, None)
            room.remove_player(pid)
            if not room.started:
                for t in [t for t, i in tokens[code].items() if i == pid]:
                    del tokens[code][t]
            if not sockets[code]:
                if room.started:
                    empty_since[code] = time.monotonic()
                    asyncio.get_running_loop().call_later(
                        KEEP_EMPTY_ROOM_SECONDS, drop_room_if_still_empty, code)
                else:
                    drop_room(code)
            else:
                await broadcast(code)


@app.websocket("/ws/create")
async def create_room(ws: WebSocket, name: str = "Player", size: int = 4):
    await ws.accept()
    if size not in VALID_SIZES:
        await refuse(ws, "Pick 1, 2, 3, 4, 6 or 8 players.")
        return
    code = new_code()
    rooms[code] = Room(size, code=code)
    sockets[code] = {}
    tokens[code] = {}
    await run_player(ws, code, name)


@app.websocket("/ws/join/{code}")
async def join_room(ws: WebSocket, code: str, name: str = "Player", rejoin: str = ""):
    await ws.accept()
    code = "".join(ch for ch in code.upper() if ch.isalnum())[:8]
    if code not in rooms:
        await refuse(ws, "No room with that code. It may have closed.")
        return
    await run_player(ws, code, name, rejoin)