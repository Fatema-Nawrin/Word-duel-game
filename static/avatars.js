
/* Word Duel avatar module.
 * Contains the eight SVG characters and the DOM badge factory.
 * Loaded before the main game script in index.html.
 */
(() => {
    'use strict';

    const INK = '#1d1b2e';

    const ST = `stroke="${INK}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"`;

    const LINE = (d, w = 2.2) => `<path d="${d}" fill="none" stroke="${INK}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
    const bigEye = (x, y) => `<circle cx="${x}" cy="${y}" r="4.8" fill="${INK}"/><circle cx="${x + 1.7}" cy="${y - 1.9}" r="1.8" fill="#fff"/><circle cx="${x - 1.5}" cy="${y + 1.8}" r="0.9" fill="#fff"/>` + LINE(`M${x - 5} ${y - 3} q5 -4.5 10 0`, 1.8);
    const eyeDot = (x, y, r = 4.2) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${INK}"/><circle cx="${x + r * 0.35}" cy="${y - r * 0.4}" r="${r * 0.34}" fill="#fff"/>`;
    const NERD_HAIR = '#2a2840';
    const blush = (x, y) => `<ellipse cx="${x}" cy="${y}" rx="5.2" ry="3" fill="#ff6b8e" opacity=".5"/>`;

    const smile = (x, y, w = 9) => LINE(`M${x - w / 2} ${y} q${w / 2} ${w * 0.7} ${w} 0`);

    function star(cx, cy, ro, ri, fill) {

        const pts = [];

        for (let i = 0; i < 10; i++) {

            const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? ri : ro;

            pts.push((cx + r * Math.cos(a)).toFixed(1) + ',' + (cy + r * Math.sin(a)).toFixed(1));

        }

        return `<polygon points="${pts.join(' ')}" fill="${fill}" stroke="${INK}" stroke-width="1.6" stroke-linejoin="round"/>`;

    }

    // Shoulders whose lower edge follows the badge circle, so nothing sticks out of it.

    function torso(y, fill) {

        const dx = Math.sqrt(48 * 48 - (y - 50) * (y - 50));

        const x1 = (50 - dx).toFixed(1), x2 = (50 + dx).toFixed(1);

        return `<path d="M${x1} ${y} Q50 ${y - 16} ${x2} ${y} A48 48 0 0 1 ${x1} ${y} Z" fill="${fill}" ${ST}/>`;

    }

    const badge = (bg, inner) =>

        `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +

        `<circle cx="50" cy="50" r="48.5" fill="${bg}"/>${inner}` +

        `<circle cx="50" cy="50" r="48.5" fill="none" stroke="${INK}" stroke-width="3"/></svg>`;



    const AVATARS = [

        {

            name: 'Moon alien', svg: badge('#c8f2dc',

                torso(82, '#7c6cf0') +

                LINE('M38 24 Q33 10 26 9') + `<circle cx="26" cy="9" r="4" fill="#ffd166" ${ST}/>` +

                LINE('M62 24 Q67 10 74 9') + `<circle cx="74" cy="9" r="4" fill="#ffd166" ${ST}/>` +

                `<ellipse cx="50" cy="46" rx="27" ry="28" fill="#86e08a" ${ST}/>` +

                `<ellipse cx="50" cy="42" rx="14" ry="12" fill="#fff" ${ST}/>` +

                `<circle cx="50" cy="43" r="7.5" fill="${INK}"/><circle cx="53" cy="40" r="2.6" fill="#fff"/>` +

                blush(33, 58) + blush(67, 58) + smile(50, 60, 12))

        },

        {

            name: 'Little wizard', svg: badge('#ffe9a8',

                torso(82, '#4a49b8') +

                `<circle cx="29" cy="56" r="8" fill="#8a5a3c" ${ST}/><circle cx="71" cy="56" r="8" fill="#8a5a3c" ${ST}/>` +

                `<circle cx="50" cy="56" r="22" fill="#ffdcbc" ${ST}/>` +

                eyeDot(42, 58) + eyeDot(58, 58) + blush(35, 65) + blush(65, 65) + smile(50, 66, 8) +

                `<ellipse cx="50" cy="42" rx="30" ry="8" fill="#6a4fd8" ${ST}/>` +

                `<path d="M28 41 Q44 30 54 7 Q60 28 72 41 Q50 47 28 41 Z" fill="#7b5ff0" ${ST}/>` +

                star(52, 28, 6.5, 2.8, '#ffd166'))

        },

        {

            name: 'Warrior', svg: badge('#ffd0cc',

                torso(82, '#8f9bb3') + `<path d="M38 74 Q50 82 62 74 L60 84 L40 84 Z" fill="#d6453d" ${ST}/>` +

                `<circle cx="50" cy="58" r="21" fill="#f3c9a1" ${ST}/>` +

                eyeDot(42, 60) + eyeDot(58, 60) + LINE('M37 55 l6 1.5') + LINE('M63 55 l-6 1.5') +

                blush(36, 67) + blush(64, 67) + LINE('M45 70 q5 3 10 0') + LINE('M60 62 l4 6', 1.8) +

                `<path d="M44 26 Q50 4 68 9 Q57 14 59 27 Z" fill="#d6453d" ${ST}/>` +

                `<path d="M28 54 Q27 24 50 24 Q73 24 72 54 L65 54 Q50 44 35 54 Z" fill="#aab4c8" ${ST}/>` +

                `<path d="M28 52 L36 52 L35 69 Q30 66 27 58 Z" fill="#8f9bb3" ${ST}/><path d="M72 52 L64 52 L65 69 Q70 66 73 58 Z" fill="#8f9bb3" ${ST}/>` +

                `<rect x="48" y="44" width="4" height="17" rx="1.5" fill="#8f9bb3" ${ST}/>` +

                `<path d="M32 36 Q50 28 68 36" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" opacity=".7"/>`)

        },

        {

            name: 'Witch', svg: badge('#ffdcb8',

                torso(82, '#3b2a63') + `<path d="M42 74 Q50 80 58 74 L56 82 L44 82 Z" fill="#ff8a3d" ${ST}/>` +

                `<path d="M28 52 Q20 66 26 80 Q34 72 33 58 Z" fill="#ff8a3d" ${ST}/><path d="M72 52 Q80 66 74 80 Q66 72 67 58 Z" fill="#ff8a3d" ${ST}/>` +

                `<circle cx="50" cy="57" r="22" fill="#ffe0c7" ${ST}/>` +

                eyeDot(42, 59) + eyeDot(58, 59) + LINE('M37 54 l-3 -2') + LINE('M63 54 l3 -2') +

                blush(35, 66) + blush(65, 66) + smile(50, 67, 8) +

                `<ellipse cx="50" cy="43" rx="33" ry="8.5" fill="#2d2a4a" ${ST}/>` +

                `<path d="M32 42 Q44 32 48 18 Q50 10 62 6 Q58 16 60 24 Q66 34 69 42 Q50 49 32 42 Z" fill="#3a3560" ${ST}/>` +

                `<path d="M33 40 Q50 47 68 40 L69 44 Q50 51 32 44 Z" fill="#ff8a3d" ${ST}/>` +

                `<rect x="45" y="40" width="10" height="8" rx="1.5" fill="#ffd166" ${ST}/>`)

        },

        {
            name: 'Shieldmaiden', svg: badge('#ffd9c2',
                torso(82, '#a6764a') +
                `<ellipse cx="24" cy="79" rx="10" ry="6.5" fill="#aab4c8" ${ST}/><ellipse cx="76" cy="79" rx="10" ry="6.5" fill="#aab4c8" ${ST}/>` +
                `<circle cx="50" cy="85" r="3.4" fill="#ffc233" ${ST}/>` +
                `<path d="M27 56 Q22 24 50 22 Q78 24 73 56 L72 70 Q50 62 28 70 Z" fill="#c0502d" ${ST}/>` +
                `<ellipse cx="70" cy="71" rx="4.5" ry="5.5" fill="#c0502d" ${ST}/><ellipse cx="71" cy="77.5" rx="4.5" ry="5.5" fill="#c0502d" ${ST}/><ellipse cx="70" cy="84" rx="4.2" ry="5" fill="#c0502d" ${ST}/>` +
                `<circle cx="70.5" cy="89.5" r="2.6" fill="#ffc233" ${ST}/>` +
                `<circle cx="50" cy="57" r="21" fill="#f3c9a1" ${ST}/>` +
                `<path d="M29 55 Q26 28 50 28 Q74 28 71 55 Q66 40 52 41 Q38 44 29 55 Z" fill="#c0502d" ${ST}/>` +
                `<path d="M30 40 Q50 31 70 40 L69 45 Q50 36 31 45 Z" fill="#ffc233" ${ST}/>` +
                `<circle cx="50" cy="38" r="2.6" fill="#e5484d" ${ST}/>` +
                eyeDot(42, 59) + eyeDot(58, 59) +
                LINE('M37.5 58 l-3 -2', 1.8) + LINE('M62.5 58 l3 -2', 1.8) +
                LINE('M36 53 l8 2') + LINE('M64 53 l-8 2') +
                `<path d="M46 67 Q50 71 54 67 Q50 68.4 46 67 Z" fill="#e5484d" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>` +
                `<path d="M60 63 l5 2.5 M60 67 l5 2.5" fill="none" stroke="#d6453d" stroke-width="2" stroke-linecap="round"/>`)
        },

        {
            name: 'Nerdy girl', svg: badge('#ffd7e6',
                torso(82, '#6fbf73') + `<path d="M40 73 L50 84 L60 73 Z" fill="#fff" ${ST}/>` +
                `<path d="M26 56 Q20 22 50 20 Q80 22 74 56 L79 84 Q70 90 66 80 L66 64 L34 64 L34 80 Q30 90 21 84 Z" fill="${NERD_HAIR}" ${ST}/>` +
                `<circle cx="50" cy="55" r="22" fill="#ffdcbc" ${ST}/>` +
                `<path d="M27 52 Q25 26 50 26 Q75 26 73 52 Q70 40 50 38 Q30 40 27 52 Z" fill="${NERD_HAIR}" ${ST}/>` +
                `<circle cx="39" cy="57" r="10" fill="#cfe8ff" fill-opacity=".6" ${ST}/><circle cx="61" cy="57" r="10" fill="#cfe8ff" fill-opacity=".6" ${ST}/>` +
                bigEye(39, 58) + bigEye(61, 58) + LINE('M49 56 q1 -2 2 0') +
                LINE('M29 55 L25 53', 2) + LINE('M71 55 L75 53', 2) +
                `<path d="M33 52 q2 -3 5 -3" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/>` +
                `<path d="M44 68 Q50 76 56 68 Z" fill="#fff" stroke="${INK}" stroke-width="1.8" stroke-linejoin="round"/>`)
        },
        {

            name: 'Pirate', svg: badge('#e0d6ff',

                torso(82, '#2f4b8a') + `<path d="M40 73 L50 84 L60 73 Z" fill="#eef0f8" ${ST}/>` +

                `<circle cx="50" cy="55" r="23" fill="#f3c9a1" ${ST}/>` +

                eyeDot(40, 57) + `<ellipse cx="62" cy="56" rx="8" ry="7" fill="${INK}"/>` + LINE('M54 53 L30 46') +

                blush(34, 65) + smile(50, 66, 14) +

                `<circle cx="27" cy="64" r="2.8" fill="none" stroke="#ffc233" stroke-width="2"/>` +

                `<path d="M72 44 q13 -3 15 9 q-9 -5 -15 -3 Z" fill="#e5484d" ${ST}/>` +

                `<path d="M26 49 Q50 14 74 49 Q50 39 26 49 Z" fill="#e5484d" ${ST}/>` +

                `<circle cx="40" cy="40" r="2" fill="#fff"/><circle cx="50" cy="36" r="2" fill="#fff"/><circle cx="60" cy="40" r="2" fill="#fff"/>`)

        },

        {

            name: 'Astronaut', svg: badge('#cbc3ff',

                torso(82, '#f4f6ff') + `<rect x="41" y="83" width="18" height="9" rx="3" fill="#ff6b6b" ${ST}/>` +

                LINE('M70 22 L75 15') + `<circle cx="76" cy="13" r="3.4" fill="#ff6b6b" ${ST}/>` +

                `<circle cx="50" cy="46" r="29" fill="#f4f6ff" ${ST}/>` +

                `<circle cx="21" cy="46" r="3.6" fill="#ffb347" ${ST}/><circle cx="79" cy="46" r="3.6" fill="#ffb347" ${ST}/>` +

                `<ellipse cx="50" cy="47" rx="21" ry="18" fill="#8fd3ff" ${ST}/>` +

                `<circle cx="50" cy="50" r="12" fill="#ffdcbc"/>` +

                eyeDot(45.5, 50, 2.6) + eyeDot(54.5, 50, 2.6) + smile(50, 55.5, 6) +

                LINE('M36 40 Q40 31 50 30', 3).replace(INK, '#fff'))

        },

    ];

    const badgeEl = (i, extra) => {

        const d = document.createElement('div');

        d.className = 'badge' + (extra ? ' ' + extra : '');

        d.title = AVATARS[i % AVATARS.length].name;

        d.innerHTML = AVATARS[i % AVATARS.length].svg;

        return d;

    };




    window.WordDuelAvatars = Object.freeze({ AVATARS, badgeEl });
})();
