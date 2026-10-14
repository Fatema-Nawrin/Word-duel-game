/* Shared helpers and the one piece of state every module reads. */

export const $ = id => document.getElementById(id);

export const TEAM_NAMES = ['Pink', 'Blue', 'Green', 'Purple'];

/* S      the latest game state sent by the server (null until the first one arrives)
   notice a standing note under the room code, such as why 3D is off */
export const state = { S: null, notice: '' };

export function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
}

export function fmt(sec) {
    sec = Math.max(0, Math.floor(sec));
    return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0');
}

export function modeText(n) {
    if (n === 1) return 'Solo. Find every word on your own.';
    if (n < 4) return 'Everyone plays alone on their own board, racing to find all the words first.';
    return 'Teams of 2. Each team has its own board with the same words.';
}