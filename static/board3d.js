/* 3D board (Three.js)
   A raised board with keycap tiles. Picked tiles press down, found words rise in your
   team colour, and the characters stand on coloured pedestals. If Three.js or WebGL is
   missing, nothing here runs and the flat board is used instead.
   THREE is a global from the <script> tag in index.html. */

import { $ } from './util.js';

const { AVATARS } = window.WordDuelAvatars;

export const B3 = (() => {
    const api = { ready: false, tried: false };
    let R, scene, cam, stage, group, N = 0, round3 = -1, tiles = [], pawns3 = new Map();
    let col = {}, colKey = '', lastW = 0, sideMat, slabMat, topGeo, flatGeo;
    const letterCache = new Map(), avCache = new Map();
    const rm = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

    function readColours() {
        const root = getComputedStyle(document.documentElement), main = getComputedStyle($('mainCol'));
        const g = (cs, n, d) => cs.getPropertyValue(n).trim() || d;
        const raw = {
            paper: g(root, '--paper', '#ffffff'), ink: g(root, '--ink', '#17131f'),
            tc: g(main, '--tc', '#ff2d78')
        };
        const key = Object.values(raw).join('|');
        const changed = key !== colKey;
        colKey = key;
        col = { raw };
        for (const k in raw) col[k] = new THREE.Color(raw[k]);
        return changed;
    }

    function paintLetter(e) {
        const x = e.cv.getContext('2d');
        x.clearRect(0, 0, 128, 128);
        x.fillStyle = e.light ? '#ffffff' : col.raw.ink;
        x.font = '800 88px "Bricolage Grotesque", "DM Sans", sans-serif';
        x.textAlign = 'center'; x.textBaseline = 'middle';
        x.fillText(e.ch, 64, 70);
        e.tex.needsUpdate = true;
    }

    function letterMat(ch, light) {
        const key = ch + (light ? 'w' : 'k');
        let e = letterCache.get(key);
        if (!e) {
            const cv = document.createElement('canvas'); cv.width = cv.height = 128;
            const tex = new THREE.CanvasTexture(cv);
            tex.anisotropy = R.capabilities.getMaxAnisotropy();
            e = { cv, tex, ch, light, mat: new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }) };
            letterCache.set(key, e);
            paintLetter(e);
        }
        return e.mat;
    }

    // The SVG badge drawn onto a canvas, with a ring in the team colour.
    function avatarTex(i, ring, me) {
        const key = i + '|' + ring + '|' + me;
        let e = avCache.get(key);
        if (e) return e;
        const cv = document.createElement('canvas'); cv.width = cv.height = 256;
        const tex = new THREE.CanvasTexture(cv);
        tex.anisotropy = R.capabilities.getMaxAnisotropy();
        e = tex;
        avCache.set(key, e);
        const img = new Image();
        img.onload = () => {
            const x = cv.getContext('2d');
            x.clearRect(0, 0, 256, 256);
            x.beginPath(); x.arc(128, 128, 126, 0, 7); x.fillStyle = me ? col.raw.ink : ring; x.fill();
            if (me) { x.beginPath(); x.arc(128, 128, 118, 0, 7); x.fillStyle = ring; x.fill(); }
            const pad = me ? 16 : 10;
            x.drawImage(img, pad, pad, 256 - 2 * pad, 256 - 2 * pad);
            tex.needsUpdate = true;
        };
        img.src = 'data:image/svg+xml;charset=utf-8,' +
            encodeURIComponent(AVATARS[i % AVATARS.length].svg.replace('<svg ', '<svg width="256" height="256" '));
        return e;
    }

    api.init = function (host) {
        api.tried = true;
        if (typeof THREE === 'undefined') { api.why = 'Three.js did not load (no internet, or the CDN is blocked)'; return false; }
        try {
            R = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            if (!R.getContext()) { api.why = 'WebGL is not available in this browser'; return false; }
        } catch (err) { api.why = 'WebGL failed to start: ' + err.message; return false; }
        stage = host;
        R.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        R.domElement.className = 'gl';
        R.domElement.setAttribute('aria-hidden', 'true');
        stage.append(R.domElement);
        stage.classList.add('gl');
        scene = new THREE.Scene();
        cam = new THREE.PerspectiveCamera(22, 1, 0.1, 400);
        scene.add(new THREE.AmbientLight(0xffffff, 0.64));
        const sun = new THREE.DirectionalLight(0xffffff, 0.46);
        sun.position.set(-4, 10, 6);
        scene.add(sun);
        topGeo = new THREE.BoxGeometry(0.94, 0.5, 0.94);
        flatGeo = new THREE.PlaneGeometry(0.8, 0.8);
        if (window.ResizeObserver) new ResizeObserver(() => fit()).observe(stage);
        if (document.fonts) document.fonts.load('800 88px "Bricolage Grotesque"').then(() => letterCache.forEach(paintLetter)).catch(() => { });
        api.ready = true;
        tick();
        return true;
    };

    function fit() {
        if (!R) return;
        const w = Math.max(240, stage.clientWidth), h = Math.round(w * 0.76);
        lastW = stage.clientWidth;
        R.setSize(w, h, false);
        cam.aspect = w / h;
        const n = N || 13, d = n * 2.6, pitch = 56 * Math.PI / 180;
        cam.position.set(0, d * Math.sin(pitch), d * Math.cos(pitch) + n * 0.02);
        cam.lookAt(0, -0.2, n * 0.02 + 0.9);
        cam.updateProjectionMatrix();
    }

    function buildBoard(S) {
        if (group) {
            scene.remove(group);
            tiles.forEach(t => t.top.dispose());
            sideMat.dispose(); slabMat.dispose();
        }
        pawns3.forEach(pw => scene.remove(pw.g));
        pawns3.clear();
        N = S.size; round3 = S.round;
        group = new THREE.Group();
        scene.add(group);
        sideMat = new THREE.MeshLambertMaterial({ color: 0xffffff });
        slabMat = new THREE.MeshLambertMaterial({ color: 0xffffff });
        const rim = 0.3;
        const slab = new THREE.Mesh(new THREE.BoxGeometry(N + 2 * rim, 0.16, N + 2 * rim), slabMat);
        slab.position.y = -0.58;
        group.add(slab);
        // a raised frame on all four sides, so the far (top) edge of the board has a border too
        const bar = (w, d, x, z) => {
            const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.5, d), slabMat);
            m.position.set(x, -0.25, z);
            group.add(m);
        };
        const mid = N / 2 + rim / 2;
        bar(N + 2 * rim, rim, 0, -mid); bar(N + 2 * rim, rim, 0, mid);
        bar(rim, N, -mid, 0); bar(rim, N, mid, 0);
        tiles = [];
        const half = (N - 1) / 2;
        for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
            const g = new THREE.Group();
            g.position.set(c - half, 0, r - half);
            const top = new THREE.MeshLambertMaterial({ color: 0xffffff });
            const box = new THREE.Mesh(topGeo, [sideMat, sideMat, top, sideMat, sideMat, sideMat]);
            box.position.y = -0.25;
            const letter = new THREE.Mesh(flatGeo, letterMat(S.grid[r][c], false));
            letter.rotation.x = -Math.PI / 2;
            letter.position.y = 0.004;
            g.add(box, letter);
            group.add(g);
            tiles.push({ g, top, letter, cur: 0, tgt: 0, ch: S.grid[r][c], light: false });
        }
        fit();
    }

    function recolour() {
        sideMat.color.copy(col.paper).lerp(col.ink, 0.38);
        slabMat.color.copy(col.paper).lerp(col.ink, 0.16);
        letterCache.forEach(paintLetter);
        pawns3.forEach(pw => pw.ped.material.color.copy(col.tc));
    }

    const mix = (a, b, t) => new THREE.Color().copy(a).lerp(b, t);

    /* states: one entry per cell. 'f' found, 's' picked by you, 'a' picked by a teammate,
       'h' the cell you stand on, '' plain. */
    api.update = function (S, states) {
        if (!api.ready) return;
        const changed = readColours();
        if (S.round !== round3 || S.size !== N) { buildBoard(S); recolour(); }
        else if (changed) recolour();
        if (stage.clientWidth !== lastW) fit();
        for (let k = 0; k < tiles.length; k++) {
            const t = tiles[k], st = states[k];
            let top, h = 0, light = false;
            if (st === 'f') { top = col.tc; h = 0.14; light = true; }
            else if (st === 's') { top = mix(col.paper, col.ink, 0.24); h = -0.12; }
            else if (st === 'a') { top = mix(col.paper, col.tc, 0.45); h = -0.07; }
            else if (st === 'h') { top = mix(col.paper, col.tc, 0.3); h = 0.04; }
            else top = col.paper;
            t.top.color.copy(top);
            t.tgt = h;
            if (rm) t.cur = h;
            if (t.light !== light) { t.light = light; t.letter.material = letterMat(t.ch, light); }
        }
        const ids = new Set(S.players.map(p => p.id));
        pawns3.forEach((pw, id) => { if (!ids.has(id)) { scene.remove(pw.g); pawns3.delete(id); } });
        const half = (N - 1) / 2, inCell = {};
        S.players.forEach(p => {
            const k = p.r * N + p.c;
            const o = inCell[k] = (k in inCell ? inCell[k] + 1 : 0);
            const me = p.id === S.you;
            let pw = pawns3.get(p.id);
            if (!pw) {
                const g = new THREE.Group();
                const ped = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.4, 0.14, 28), new THREE.MeshLambertMaterial({ color: col.tc }));
                ped.position.y = 0.07;
                const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.5, 28), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.2, depthWrite: false }));
                shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.006;
                const sp = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true }));
                g.add(shadow, ped, sp);
                scene.add(g);
                pw = { g, ped, sp, x: p.c - half, z: p.r - half, hop: 0, drop: rm ? 0 : 1, k, key: '' };
                pawns3.set(p.id, pw);
            }
            if (pw.k !== k) { pw.k = k; if (!rm) pw.hop = 1; }
            pw.me = me;
            pw.ox = Math.min(o, 3) * 0.24;
            pw.tx = p.c - half; pw.tz = p.r - half;
            if (rm) { pw.x = pw.tx; pw.z = pw.tz; }
            const key = p.avatar + col.raw.tc + me;
            if (pw.key !== key) {
                pw.key = key;
                pw.sp.material.map = avatarTex(p.avatar, col.raw.tc, me);
                pw.sp.material.needsUpdate = true;
                const size = me ? 1.12 : 1.0;
                pw.sp.scale.set(size, size, 1);
                pw.sp.position.y = 0.14 + size * 0.5 - 0.04;
            }
        });
    };

    function tick() {
        requestAnimationFrame(tick);
        if (!N || !stage.offsetParent) return;  // nothing to draw while the board is hidden
        const f = rm ? 1 : 0.22, now = performance.now() / 1000;
        for (const t of tiles) { t.cur += (t.tgt - t.cur) * f; t.g.position.y = t.cur; }
        pawns3.forEach(pw => {
            pw.x += (pw.tx - pw.x) * (rm ? 1 : 0.3);
            pw.z += (pw.tz - pw.z) * (rm ? 1 : 0.3);
            pw.hop = Math.max(0, pw.hop - 0.09);
            pw.drop = Math.max(0, pw.drop - 0.035);
            const tile = tiles[pw.k], base = tile ? tile.cur : 0;
            const y = base + (pw.me ? Math.sin(now * 3) * 0.025 : 0) + 0.28 * Math.sin(Math.PI * (1 - pw.hop)) * (pw.hop > 0 ? 1 : 0) + 6 * pw.drop * pw.drop;
            pw.g.position.set(pw.x + pw.ox, y, pw.z);
        });
        R.render(scene, cam);
    }

    return api;
})();