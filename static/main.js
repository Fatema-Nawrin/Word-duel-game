/* Entry point: the lobby form, the rejoin offer and the keyboard. */

import { $, modeText, state } from './util.js';
import { send, createRoom, joinRoom, savedSeat, rejoin } from './connection.js'

/* ---------- lobby ---------- */
try { $('name').value = localStorage.getItem('wd-name') || ''; } catch (err) { }

function currentMode() { return document.querySelector('input[name=mode]:checked').value; }

function updateLobby() {
    const create = currentMode() === 'create';
    $('createFields').hidden = !create;
    $('joinFields').hidden = create;
    $('goBtn').textContent = create ? 'Create room' : 'Join room';
    $('sizeHint').textContent = modeText(+$('size').value);
    $('joinErr').textContent = '';
}
document.querySelectorAll('input[name=mode]').forEach(r => r.addEventListener('change', updateLobby));
$('size').addEventListener('change', updateLobby);
updateLobby();

$('join').addEventListener('submit', e => {
    e.preventDefault();
    const name = $('name').value.trim() || 'Player';
    try { localStorage.setItem('wd-name', name); } catch (err) { }
    if (currentMode() === 'create') {
        createRoom(name, $('size').value);
    } else {
        const code = $('code').value.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
        if (!code) { $('joinErr').textContent = 'Enter the room code.'; return; }
        joinRoom(name, code);
    }
});

/* ---------- rejoin offer ---------- */
{
    const seat = savedSeat();
    if (seat) {
        $('rejoinText').textContent = `You were playing in room ${seat.code} as ${seat.name}.`;
        $('rejoinBox').hidden = false;
        $('rejoinBtn').addEventListener('click', () => rejoin(seat));
    }
}

/* ---------- keyboard ---------- */
const MOVES = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };
document.addEventListener('keydown', e => {
    const S = state.S;
    if (!S || !S.started || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (MOVES[e.key]) {
        e.preventDefault();
        send({ type: 'move', dx: MOVES[e.key][0], dy: MOVES[e.key][1] });
    } else if (e.code === 'Space') {
        e.preventDefault();
        if (!e.repeat) send({ type: 'select' });
    } else if (e.key === 'Escape') {
        send({ type: 'cancel' });
    }
});