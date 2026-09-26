// Анимация ролика: детерминированная, управляется только временем → window.renderAt(t).
// Тайминг сцен и метки синхронизации приходят из assets/timeline.js (его пишет voice.py).
const H = 1920, FPS = 60;
const MIN = [5, 5.5, 5.5, 3.5, 4.5, 4];
const SC = window.SCENES || MIN.reduce((a, d, i) => (a.push({ start: i ? a[i - 1].start + MIN[i - 1] : 0, dur: d, marks: {} }), a), []);
const DUR = SC.at(-1).start + SC.at(-1).dur;
const $ = id => document.getElementById(id);
const SFX = [];
const sfx = (t, type, o = {}) => SFX.push({ t: +t.toFixed(3), type, ...o });
const mk = (i, k, def) => SC[i].marks?.[k] ?? SC[i].start + def;   // метка из озвучки или запасное время

const tl = gsap.timeline({ paused: true, defaults: { ease: 'power2.out' } });
const P = { cam: 0, mb: 0, fade: 0, n1a: 0, n1b: 20, v2a: 0, v2b: 0, v2c: 0, r4a: 0, r4b: 0 };

document.querySelectorAll('.sec').forEach((s, i) => (s.style.top = i * H + 'px'));

// ---------------------------------------------------------------- фон: восьмиконечная звезда
$('starp').setAttribute('d', [...Array(16)].map((_, k) => {
  const r = k % 2 ? 52 : 100, a = (k / 16) * Math.PI * 2 - Math.PI / 2;
  return `${k ? 'L' : 'M'}${(Math.cos(a) * r).toFixed(2)} ${(Math.sin(a) * r).toFixed(2)}`;
}).join('') + 'Z');

// ---------------------------------------------------------------- пунктирные стрелки между сценами
const CONN = [];
document.querySelectorAll('.sec').forEach((s, i) => {
  if (!i) return;
  const hdr = s.querySelector('.row'), top = parseFloat(hdr.style.top) - 26, from = -560;
  const len = top - from;
  const wrap = document.createElement('div');
  wrap.className = 'conn'; wrap.style.top = from + 'px'; wrap.style.height = '0px'; wrap.style.opacity = '0';
  wrap.innerHTML = `<div style="position:absolute;left:-40px;top:0;width:86px;height:100%;overflow:hidden">
      <svg width="86" height="${len}" style="left:0"><path class="dash" d="M43 0V${len - 8}" stroke="#4fe3b2" stroke-width="6" stroke-dasharray="22 16" fill="none" stroke-linecap="round"/></svg></div>
    <svg width="86" height="40" style="position:absolute;left:-40px;bottom:-6px;top:auto"><path d="M21 8l22 22 22-22" stroke="#4fe3b2" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  s.appendChild(wrap);
  CONN.push({ el: wrap, len, i });
});

// ---------------------------------------------------------------- QR
(function buildQR() {
  const q = window.QR, n = q.length, svg = $('qrsvg');
  svg.setAttribute('viewBox', `-0.5 -0.5 ${n + 1} ${n + 1}`);
  const inFinder = (x, y) => (x < 7 && y < 7) || (x >= n - 7 && y < 7) || (x < 7 && y >= n - 7);
  let out = '';
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    if (!q[y][x] || inFinder(x, y)) continue;
    out += `<g class="qm" data-d="${Math.hypot(x - n / 2, y - n / 2).toFixed(2)}"><rect x="${x + .06}" y="${y + .12}" width=".88" height=".88" rx=".24" fill="#1f45b8"/>` +
      `<rect x="${x + .06}" y="${y + .04}" width=".88" height=".86" rx=".24" fill="#3a6ff0"/></g>`;
  }
  for (const [fx, fy] of [[0, 0], [n - 7, 0], [0, n - 7]]) {
    out += `<g class="qf"><rect x="${fx + .5}" y="${fy + .62}" width="6" height="6" rx="1.5" fill="none" stroke="#15151c" stroke-width="1"/>` +
      `<rect x="${fx + .5}" y="${fy + .5}" width="6" height="6" rx="1.5" fill="none" stroke="#2b2b35" stroke-width="1"/>` +
      `<rect x="${fx + 2}" y="${fy + 2.1}" width="3" height="3" rx=".7" fill="#15151c"/><rect x="${fx + 2}" y="${fy + 2}" width="3" height="2.9" rx=".7" fill="#2b2b35"/></g>`;
  }
  svg.innerHTML = out;
})();

// ---------------------------------------------------------------- помощники анимации
const pop = (el, t, o = {}) => tl.fromTo(el, { scale: o.s ?? .6, opacity: o.o ?? 0, y: o.y ?? 0, x: o.x ?? 0, rotation: o.r ?? 0 },
  { scale: 1, opacity: 1, y: 0, x: 0, rotation: 0, duration: o.d ?? .45, ease: o.ease ?? 'back.out(1.8)' }, t);
const fadeUp = (el, t) => tl.fromTo(el, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: .4 }, t);
const pulse = (el, t, s = 1.08) => tl.to(el, { scale: s, duration: .12, ease: 'power2.out', yoyo: true, repeat: 1 }, t);
const shake = (el, t) => tl.to(el, { keyframes: { x: [0, -14, 12, -8, 5, 0] }, duration: .42, ease: 'none' }, t);
const glow = (el, t) => tl.fromTo(el, { boxShadow: '0 0 0 0px rgba(79,227,178,0), 0 18px 0 rgba(30,0,60,.18), 0 26px 50px rgba(20,0,40,.35)' },
  { boxShadow: '0 0 0 7px rgba(79,227,178,1), 0 18px 0 rgba(30,0,60,.18), 0 26px 60px rgba(40,230,160,.45)', duration: .35 }, t);
const ticks = (t0, d, n, f0 = 1, f1 = 1.6) => { for (let k = 0; k < n; k++) sfx(t0 + d * k / n, 'tick', { f: f0 + (f1 - f0) * k / n, g: .7 }); };

// камера: переход в сцену i занимает [start-0.5, start+0.2]
for (let i = 1; i < SC.length; i++) {
  const t = SC[i].start - .5;
  tl.fromTo(P, { cam: (i - 1) * H }, { cam: i * H, duration: .7, ease: 'power3.inOut', immediateRender: false }, t);
  tl.fromTo(P, { mb: 0 }, { mb: 28, duration: .35, ease: 'power2.in', immediateRender: false }, t);
  tl.to(P, { mb: 0, duration: .35, ease: 'power2.out' }, t + .35);
  const c = CONN[i - 1];
  tl.fromTo(c.el, { height: 0, opacity: 0 }, { height: c.len, opacity: 1, duration: .55, ease: 'power2.inOut', immediateRender: false }, t + .05);
  sfx(t, 'whoosh', { d: .62 });
}
const hdr = (i, el) => { pop(el, SC[i].start + .02, { s: .7, d: .5 }); sfx(SC[i].start + .02, 'thump', { g: .8 }); };

// ================================================================ 1. хук
{
  const s = SC[0].start, a = mk(0, 'a', 1.9), b = mk(0, 'b', 4.2);
  // первый кадр уже содержательный (превью в ленте): всё на месте, лишь «доезжает»
  pop('#h1', s, { s: 1.25, o: 1, d: .6, ease: 'power3.out' }); sfx(s, 'thump', { g: .8 });
  pop('#c1a', s, { y: 90, r: -5, s: .92, o: 1, d: .65, ease: 'back.out(1.6)' });
  pop('#c1b', s + .08, { y: 90, r: 5, s: .92, o: 1, d: .65, ease: 'back.out(1.6)' }); sfx(s + .1, 'pop', { f: 1.15 });
  pop('#k1', s + 1.05, { s: .8 }); sfx(s + 1.05, 'blip', { f: .9 });
  fadeUp('#f1', s + 1.35);
  // Opus 5: 0 → 20+ часов
  const a0 = Math.max(s + .9, a - .35);
  tl.set('#u1a', { opacity: 1 }, a0);
  tl.fromTo(P, { n1a: 0 }, { n1a: 20, duration: .8, ease: 'power2.out', immediateRender: false }, a0);
  ticks(a0, .7, 9, 1, 1.5);
  shake('#c1a', a0 + .8); sfx(a0 + .8, 'bonk');
  // Opus 5.5: 20 → 3, «меньше трёх»
  const b0 = Math.max(a0 + 1.2, b - .15);
  tl.set('#u1b', { opacity: 1 }, b0);
  tl.fromTo(P, { n1b: 20 }, { n1b: 3, duration: .5, ease: 'power3.out', immediateRender: false }, b0);
  ticks(b0, .45, 7, 1.6, 1.1);
  pulse('#c1b', b0 + .5, 1.09); glow('#c1b', b0 + .5); sfx(b0 + .5, 'success'); sfx(b0 + .55, 'sparkle');
}

// ================================================================ 2. бенчмарк
{
  const s = SC[1].start, a = mk(1, 'a', .9), b = mk(1, 'b', 2.6);
  hdr(1, '#h2');
  pop('#k2', s + .3, { s: .8 }); sfx(s + .3, 'blip');
  const row = (id, t, f) => { pop(id, t, { x: -90, s: .9, d: .45, ease: 'back.out(1.4)' }); sfx(t, 'pop', { f }); };
  row('#r2a', s + .45, 1); row('#r2b', s + .62, 1.1); row('#r2c', s + .79, 1.2);
  const bar = (fill, key, v, t, d) => {
    tl.fromTo(fill, { width: '0%' }, { width: (v / 70 * 100).toFixed(1) + '%', duration: d, ease: 'power2.out' }, t);
    tl.fromTo(P, { [key]: 0 }, { [key]: v, duration: d, ease: 'power2.out', immediateRender: false }, t);
  };
  bar('#b2a', 'v2a', 52.3, s + .75, .7); bar('#b2b', 'v2b', 55.8, s + .92, .7);
  pulse('#r2b', Math.max(a, s + 1.7), 1.04);
  const b0 = Math.max(s + 1.9, b - .1);
  bar('#b2c', 'v2c', 66.4, b0, .75); sfx(b0, 'zip', { d: .7 });
  tl.set('#bd2', { opacity: 0 }, 0);
  pop('#bd2', b0 + .75, { s: .3, d: .4 }); glow('#r2c', b0 + .75); sfx(b0 + .75, 'success'); sfx(b0 + .8, 'sparkle');
  pop('#p2', b0 + 1.1, { s: .6 }); sfx(b0 + 1.1, 'pop', { f: 1.3 });
  fadeUp('#f2', b0 + 1.35);
}

// ================================================================ 3. цена
{
  const s = SC[2].start, a = mk(2, 'a', 1.2), b = mk(2, 'b', 2.9);
  hdr(2, '#h3');
  pop('#k3', s + .3, { s: .8 }); sfx(s + .3, 'blip');
  [['#c3a', .45], ['#c3b', .6], ['#c3c', .75]].forEach(([id, d], k) => { pop(id, s + d, { y: 120, s: .85, d: .5 }); sfx(s + d, 'pop', { f: 1 + k * .1 }); });
  tl.set('#bd3', { opacity: 0 }, 0);
  tl.set('#c3c', { boxShadow: '0 0 0 0px rgba(79,227,178,0), 0 18px 0 rgba(30,0,60,.18), 0 26px 50px rgba(20,0,40,.35)' }, 0);
  const a0 = Math.max(s + 1.3, a);
  pop('#bd3', a0, { s: .3, d: .4 }); glow('#c3c', a0); pulse('#c3c', a0, 1.05); sfx(a0, 'coin');
  const b0 = Math.max(a0 + .8, b);
  shake('#c3a', b0); sfx(b0, 'bonk', { g: .7 });
  pop('#p3', b0 + .35, { s: .6 }); sfx(b0 + .35, 'coin'); sfx(b0 + .4, 'sparkle');
  fadeUp('#f3', b0 + .65);
}

// ================================================================ 4. скорость
{
  const s = SC[3].start, a = mk(3, 'a', .8);
  hdr(3, '#h4');
  pop('#fire', s + .15, { s: .2, d: .55, ease: 'back.out(2.2)' }); sfx(s + .15, 'pop', { f: .8 });
  pop('#r4a', s + .3, { x: -90, s: .9, ease: 'back.out(1.4)' }); pop('#r4b', s + .42, { x: -90, s: .9, ease: 'back.out(1.4)' });
  sfx(s + .3, 'pop'); sfx(s + .42, 'pop', { f: 1.15 });
  const r0 = s + .55, T = 1.25;
  tl.fromTo(P, { r4b: 0 }, { r4b: 1, duration: T, ease: 'power1.inOut', immediateRender: false }, r0);
  tl.fromTo(P, { r4a: 0 }, { r4a: 1, duration: T * 1.3, ease: 'power1.inOut', immediateRender: false }, r0);
  sfx(r0, 'zip', { d: T }); sfx(r0 + T, 'ding');
  const n0 = Math.max(r0 + T + .05, a - .05);
  pop('#n4', n0, { s: .3, d: .5, ease: 'back.out(2.4)' }); sfx(n0, 'impact', { g: .55 });
  fadeUp('#f4', n0 + .3);
}

// ================================================================ 5. где юзать (дроп музыки)
{
  const s = SC[4].start;
  hdr(4, '#h5');
  pop('#party', s + .12, { s: .2, d: .7, ease: 'elastic.out(1, .55)' }); sfx(s + .12, 'impact'); sfx(s + .2, 'sparkle');
  let prev = s + .5;
  [['#l5a', 'b', 1.4], ['#l5b', 'c', 2.0], ['#l5c', 'd', 2.6]].forEach(([id, k, def], j) => {
    const t = Math.max(prev + .28, mk(4, k, def) - .1); prev = t;
    pop(id, t, { x: 140, s: .9, d: .45, ease: 'back.out(1.5)' }); sfx(t, 'check', { g: .9 });
  });
}

// ================================================================ 6. QR
{
  const s = SC[5].start, a = mk(5, 'a', 2);
  pop('#h6', s + .02, { s: .7 }); sfx(s + .02, 'thump', { g: .8 });
  pop('#qr', s + .15, { s: .75, d: .55 }); sfx(s + .15, 'pop', { f: .9 });
  tl.fromTo('#qrsvg .qm', { opacity: 0, scale: .2, transformOrigin: '50% 50%' },
    { opacity: 1, scale: 1, duration: .3, ease: 'back.out(2)', stagger: { each: 0, from: 'center', amount: .5 } }, s + .25);
  tl.fromTo('#qrsvg .qf', { opacity: 0 }, { opacity: 1, duration: .25 }, s + .3);
  ticks(s + .25, .5, 6, 1.2, 1.9);
  pop('#qrlogo', s + .65, { s: .2, d: .5, ease: 'back.out(2.5)' }); sfx(s + .65, 'pop', { f: 1.3 });
  pop('#p6', s + .8, { s: .6 }); sfx(s + .8, 'blip', { f: 1.2 });
  fadeUp('#f6', s + 1.0);
  pulse('#h6', Math.max(s + 1.2, a), 1.1); sfx(Math.max(s + 1.2, a), 'ding', { f: 1.2 });
  tl.fromTo(P, { fade: 0 }, { fade: .72, duration: .45, ease: 'power1.in', immediateRender: false }, DUR - .45);
}
tl.set({}, {}, DUR);

// ---------------------------------------------------------------- Lottie-утки
const ANIMS = [];
const cache = {};
async function loadStickers() {
  const els = [...document.querySelectorAll('[data-anim]')];
  await Promise.all([...new Set(els.map(e => e.dataset.anim))].map(async n => (cache[n] = await (await fetch(`assets/stickers/${n}.json`)).text())));
  await Promise.all(els.map(el => new Promise(res => {
    const anim = lottie.loadAnimation({ container: el, renderer: 'svg', loop: false, autoplay: false, animationData: JSON.parse(cache[el.dataset.anim]),
      rendererSettings: { preserveAspectRatio: 'xMidYMid meet', progressiveLoad: false } });
    const sec = [...document.querySelectorAll('.sec')].indexOf(el.closest('.sec'));
    ANIMS.push({ anim, sec, t0: SC[sec].start, n: 0 });
    if (anim.isLoaded) res(); else { anim.addEventListener('DOMLoaded', res); setTimeout(res, 3000); }
  })));
  ANIMS.forEach(o => (o.n = o.anim.totalFrames));
}

// ---------------------------------------------------------------- кадр
const fmt = v => v.toFixed(1).replace('.', ',') + '%';
let lastFilter = '';
function apply(t) {
  $('world').style.transform = `translate3d(0,${-P.cam}px,0)`;
  $('grid').style.transform = `translate3d(0,${-(P.cam % 108)}px,0)`;
  $('star').style.transform = `rotate(${(t * 3 + P.cam * .012).toFixed(2)}deg) scale(${1 + .03 * Math.sin(t * .8)})`;
  $('arc').style.transform = `rotate(${(-t * 5 - P.cam * .02).toFixed(2)}deg)`;
  const f = P.mb > .3 ? 'url(#mb)' : 'none';
  $('mbg').setAttribute('stdDeviation', `0 ${P.mb.toFixed(2)}`);
  if (f !== lastFilter) { $('view').style.filter = f; lastFilter = f; }
  $('fade').style.opacity = P.fade;
  // счётчики
  $('n1a').textContent = !+$('u1a').style.opacity ? '?' : Math.round(P.n1a) + (P.n1a >= 19.99 ? '+' : '');
  $('n1b').innerHTML = !+$('u1b').style.opacity ? '?' : (P.n1b <= 3.01 ? '<span class="pre">&lt;</span>3' : Math.round(P.n1b));
  $('v2a').textContent = fmt(P.v2a); $('v2b').textContent = fmt(P.v2b); $('v2c').textContent = fmt(P.v2c);
  // гонка
  for (const [k, id] of [['r4a', 'a'], ['r4b', 'b']]) {
    $('rn4' + id).style.left = (P[k] * 100).toFixed(2) + '%';
    $('rf4' + id).style.width = (P[k] * 100).toFixed(2) + '%';
  }
  // пунктир «бежит»
  document.querySelectorAll('.dash').forEach(d => d.setAttribute('stroke-dashoffset', (-t * 90).toFixed(1)));
  // утки: играют циклом с момента появления сцены, считаем только видимые
  const cur = P.cam / H;
  for (const o of ANIMS) {
    if (Math.abs(o.sec - cur) > 1.05) continue;
    const fr = Math.max(0, (t - o.t0) * FPS) % o.n;
    o.anim.goToAndStop(fr, true);
  }
}

window.renderAt = t => { tl.seek(Math.min(t, DUR), false); apply(t); };
window.DUR = DUR;
window.SFX = SFX.sort((a, b) => a.t - b.t);
window.TIMELINE = { dur: DUR, drop: SC[4].start, scenes: SC };
window.READY = (async () => {
  await Promise.all([...document.fonts].map(f => f.load()));
  await document.fonts.ready;
  await loadStickers();
  window.renderAt(0);
  return true;
})();

// превью в браузере: ?t=12.3 — стоп-кадр, иначе проигрывание в реальном времени
const qs = new URLSearchParams(location.search);
if (!qs.has('render')) window.READY.then(() => {
  if (qs.has('t')) return window.renderAt(+qs.get('t'));
  const t0 = performance.now();
  const loop = () => { window.renderAt(((performance.now() - t0) / 1000) % DUR); requestAnimationFrame(loop); };
  loop();
});
