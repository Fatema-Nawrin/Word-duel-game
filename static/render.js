/* Drawing: turns the latest server state (state.S) into the page. */

import { $, el, fmt, modeText, TEAM_NAMES, state } from './util.js';
import { B3 } from './board3d.js';

const { badgeEl } = window.WordDuelAvatars;

let builtRound = -1, cells = [];
const waitingIds = new Set();
const pawns = new Map();  // player id -> the character's element on the flat board

function teamLabel(t) {
    const S = state.S;
    if (S.mode === 'teams') return TEAM_NAMES[t] + ' team';
    const m = S.teams[t].members;
    return m.length ? m[0].name : TEAM_NAMES[t];
}

function updateTimer() {
    const S = state.S;
    if (!S || !S.started) return;
    // countdown: the time left in the 10 minutes
    const used = S.elapsed + (performance.now() - S.recv) / 1000;
    const left = Math.max(0, Math.ceil(S.limit - used));
    $('timer').textContent = fmt(left);
    $('timer').classList.toggle('low', left <= 60);
}

// The round is over: keep the final result for the results page and go there.
// (The game page itself never shows who won.)
function goToResults() {
    const S = state.S;
    try {
        sessionStorage.setItem('wd-results', JSON.stringify({
            mode: S.mode, total: S.words.length, myTeam: S.myTeam,
            timeUp: S.timeUp, elapsed: S.elapsed, ranking: S.ranking,
            teams: S.teams.map(t => ({ team: t.team, members: t.members.map(m => m.name) })),
        }));
        sessionStorage.removeItem('wd-session');  // the lobby should not offer to rejoin a finished game
    } catch (err) { }
    location.href = '/static/results.html';
}
setInterval(updateTimer, 500);

function renderWaiting() {
    const S = state.S;
    $('wCount').textContent = `(${S.players.length} of ${S.capacity})`;
    $('wCode').textContent = S.code;
    const ul = $('wList');
    ul.innerHTML = '';
    S.players.forEach(p => {
        const li = el('li', waitingIds.has(p.id) ? '' : 'pop');
        li.append(badgeEl(p.avatar), document.createTextNode(p.name + (p.id === S.you ? ' (you)' : '')));
        ul.append(li);
    });
    S.players.forEach(p => waitingIds.add(p.id));
    $('wMode').textContent = modeText(S.capacity) + ' The game starts when the room is full.';
}

// The letters are built once per round; after that only their classes change.
function buildGrid() {
    const S = state.S;
    const grid = $('grid');
    grid.innerHTML = '';
    cells = [];
    for (let r = 0; r < S.size; r++) {
        for (let c = 0; c < S.size; c++) {
            const d = el('div', 'cell', S.grid[r][c]);
            d.dataset.l = S.grid[r][c];
            grid.append(d);
            cells.push(d);
        }
    }
    $('pawns').innerHTML = '';
    pawns.clear();
    builtRound = S.round;
}

function hop(node) {
    const b = node.firstChild;
    b.classList.remove('hop');
    void b.offsetWidth;  // restart the animation
    b.classList.add('hop');
}

// Characters live in their own layer, so they slide from cell to cell instead of jumping.
function syncPawns() {
    const S = state.S;
    const layer = $('pawns');
    const ids = new Set(S.players.map(p => p.id));
    for (const [id, node] of pawns) {
        if (!ids.has(id)) { node.remove(); pawns.delete(id); }
    }
    const inCell = {};
    S.players.forEach(p => {
        const k = p.r * S.size + p.c;
        const o = inCell[k] = (k in inCell ? inCell[k] + 1 : 0);
        let node = pawns.get(p.id);
        if (!node) {
            node = el('div', 'pawn');
            node.append(badgeEl(p.avatar, 'drop'));
            layer.append(node);
            pawns.set(p.id, node);
        }
        node.classList.toggle('me', p.id === S.you);
        const pos = p.r + ',' + p.c;
        if (node.dataset.pos && node.dataset.pos !== pos) hop(node);
        node.dataset.pos = pos;
        node.style.setProperty('--r', p.r);
        node.style.setProperty('--c', p.c);
        node.style.setProperty('--o', Math.min(o, 3));
    });
}

export function render() {
    const S = state.S;
    if (S.over) { goToResults(); return; }
    $('roomCode').textContent = S.code;
    $('waiting').hidden = S.started;
    $('board').hidden = !S.started;
    $('timerWrap').hidden = !S.started;
    if (!S.started) { renderWaiting(); return; }
    updateTimer();
    const n = S.size, mt = S.myTeam;
    $('mainCol').className = 'main t' + mt;  // passes your team's colour to the board
    $('stage').style.setProperty('--n', n);
    if (!B3.tried) {
        B3.init($('stage'));
        if (!B3.ready) {
            state.notice = '3D view is off: ' + B3.why + '. Showing the flat board.';
            $('connMsg').textContent = state.notice;
        }
    }
    if (S.round !== builtRound) buildGrid();

    // Only your own team's board is sent: its found words, its players and its picks.
    const foundCells = new Set();
    for (const f of S.found) for (const [r, c] of f.cells) foundCells.add(r * n + c);
    const me = S.players.find(p => p.id === S.you);
    const sel = new Set();
    if (me) me.picked.forEach(([r, c]) => sel.add(r * n + c));
    const mates = new Set();
    S.players.forEach(p => {
        if (p.id !== S.you) p.picked.forEach(([r, c]) => mates.add(r * n + c));
    });
    const hereK = me ? me.r * n + me.c : -1;
    const states = [];
    for (let k = 0; k < cells.length; k++) {
        let cls = 'cell';
        if (foundCells.has(k)) cls += ' f';
        if (mates.has(k)) cls += ' anch';
        if (sel.has(k)) cls += ' sel';
        if (k === hereK) cls += ' here';
        if (cells[k].className !== cls) cells[k].className = cls;
        states.push(foundCells.has(k) ? 'f' : sel.has(k) ? 's' : mates.has(k) ? 'a' : k === hereK ? 'h' : '');
    }
    syncPawns();
    B3.update(S, states);

    // Progress of every team. You see how many words the others have, not which ones.
    const teams = $('teams');
    teams.innerHTML = '';
    for (const T of S.teams) {
        const box = el('div', 't' + T.team + ' tbox');
        const head = el('span', 'tl');
        if (S.mode !== 'teams' && T.members[0]) head.append(badgeEl(T.members[0].avatar));
        head.append(document.createTextNode(teamLabel(T.team) + (T.team === mt ? ' (you)' : '')));
        box.append(head, el('span', 'sc', `${T.found}/${S.words.length}`));
        if (S.mode === 'teams') {
            const mems = el('span', 'mems');
            T.members.forEach(m => {
                const row = el('span', 'mem');
                row.append(badgeEl(m.avatar), document.createTextNode(m.name + (m.you ? ' (you)' : '') + (m.connected === false ? ' (away)' : '')));
                mems.append(row);
            });
            box.append(mems);
        }
        if (T.done) box.append(el('span', 'done', 'Finished'));
        teams.append(box);
    }

    const ul = $('wordList');
    ul.innerHTML = '';
    for (const w of S.words) {
        const li = el('li', w.found ? 'f t' + mt : '');
        li.append(el('span', 'w', w.word), el('span', 'n', String(w.word.length)));
        ul.append(li);
    }
}