"""Word Duel server. Run with:  python -m uvicorn main:app --reload"""
import json
import secrets
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from game import VALID_SIZES, Room

app = FastAPI()
BASE = Path(__file__).parent

rooms = {}    # room code -> Room
sockets = {}  # room code -> {player id -> WebSocket}

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


async def refuse(ws, text):
    await ws.send_json({"type": "error", "text": text})
    await ws.close()


async def run_player(ws, code, name):
    """Seat one player in an existing room and handle their messages until they leave."""
    room = rooms[code]
    pid = secrets.token_hex(4)
    if not room.add_player(pid, name.strip()[:14] or "Player"):
        await refuse(ws, "That room is full, or its game has already started.")
        return
    sockets[code][pid] = ws
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
            else:
                continue
            await broadcast(code)
    except WebSocketDisconnect:
        pass
    finally:
        room.remove_player(pid)
        sockets[code].pop(pid, None)
        if not sockets[code]:
            rooms.pop(code, None)
            sockets.pop(code, None)
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
    await run_player(ws, code, name)


@app.websocket("/ws/join/{code}")
async def join_room(ws: WebSocket, code: str, name: str = "Player"):
    await ws.accept()
    code = "".join(ch for ch in code.upper() if ch.isalnum())[:8]
    if code not in rooms:
        await refuse(ws, "No room with that code.")
        return
    await run_player(ws, code, name)