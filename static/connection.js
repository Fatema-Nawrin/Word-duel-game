/* Connecting, and coming back.
   The server gives every player a secret token. It is kept in this tab's sessionStorage, so
   a refresh or a dropped connection can take the same seat (same team, avatar and picks). */

import { $, state } from './util.js';
import { render } from './render.js';

const wsBase = () => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
const rejoinUrl = x => `${wsBase()}/join/${x.code}?name=${encodeURIComponent(x.name)}&rejoin=${encodeURIComponent(x.token)}`;

let ws = null, session = null, retries = 0, retryTimer = 0, gaveUp = false;

function loadSession() { try { return JSON.parse(sessionStorage.getItem('wd-session')); } catch (err) { return null; } }
function saveSession() { try { sessionStorage.setItem('wd-session', JSON.stringify(session)); } catch (err) { } }
function clearSession() { session = null; try { sessionStorage.removeItem('wd-session'); } catch (err) { } }

function connect(url, name) {
    $('joinErr').textContent = '';
    clearTimeout(retryTimer);
    const sock = ws = new WebSocket(url);
    sock.onmessage = ev => {
        const m = JSON.parse(ev.data);
        if (m.type === 'hello') {
            session = { code: m.code, token: m.token, name: name || (session && session.name) || 'Player' };
            saveSession();
        } else if (m.type === 'error') {
            gaveUp = true;  // the server said no, so retrying would not help
            clearSession();
            $('rejoinBox').hidden = true;
            if (state.S) $('connMsg').textContent = m.text + ' Reload the page to start again.';
            else $('joinErr').textContent = m.text;
        } else if (m.type === 'state') {
            if (!state.S) { $('join').hidden = true; $('rejoinBox').hidden = true; $('game').hidden = false; }
            retries = 0;
            $('connMsg').textContent = state.notice;
            m.recv = performance.now();
            state.S = m;
            render();
        }
    };
    sock.onclose = () => {
        if (sock !== ws || gaveUp) return;
        if (state.S && session && retries < 30) {
            // Connection dropped mid-game: keep trying to take the same seat back.
            retries++;
            $('connMsg').textContent = 'Connection lost. Reconnecting...';
            retryTimer = setTimeout(() => connect(rejoinUrl(session), session.name), Math.min(1000 * retries, 5000));
        } else if (state.S) {
            $('connMsg').textContent = 'Disconnected from the server. Reload the page to rejoin.';
        } else if (!$('joinErr').textContent) {
            $('joinErr').textContent = 'Could not connect to the server.';
        }
    };
}

export function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

export function createRoom(name, size) {
    connect(`${wsBase()}/create?name=${encodeURIComponent(name)}&size=${size}`, name);
}

export function joinRoom(name, code) {
    connect(`${wsBase()}/join/${code}?name=${encodeURIComponent(name)}`, name);
}

// After a refresh: returns the saved seat, if there is one, so the page can offer to take it back.
export function savedSeat() {
    const old = loadSession();
    if (old && old.code && old.token) { session = old; return old; }
    return null;
}

export function rejoin(seat) {
    gaveUp = false;
    connect(rejoinUrl(seat), seat.name);
}