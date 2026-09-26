"""Музыка (120 BPM, Am–F–C–G) + звуковые эффекты по sfx.json [+ голос] → WAV 48 кГц стерео.
   python audio.py <sfx.json> <out.wav> [voice.wav]
Рядом с sfx.json должен лежать timeline.json (длительность и момент дропа — их пишет render.mjs).
"""
import json, sys, os
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
_tl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), 'timeline.json')))
DUR = float(_tl['dur'])       # длительность ролика
D = float(_tl['drop'])        # дроп = приземление маскота
END = DUR
N = int(SR * DUR)
BEAT = 0.5
STEP = BEAT / 4
rng = np.random.default_rng(5)

def T(sec): return np.arange(int(sec * SR)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def noise(sec): return rng.uniform(-1, 1, int(sec * SR))
def saw(freq, t, ph=0.0): return 2 * ((freq * t + ph) % 1) - 1
def glide(f0, f1, t, tau):  # экспоненциальный glide частоты → фаза
    f = f1 + (f0 - f1) * np.exp(-t / tau)
    return 2 * np.pi * np.cumsum(f) / SR
def midi(m): return 440 * 2 ** ((m - 69) / 12)

class Bus:
    def __init__(self): self.x = np.zeros((N, 2))
    def add(self, sig, t0, g=1.0, pan=0.0):
        if sig.ndim == 1: sig = np.stack([sig * np.sqrt(.5 * (1 - pan)), sig * np.sqrt(.5 * (1 + pan))], 1) * np.sqrt(2)
        i0 = int(round(t0 * SR))
        if i0 >= N: return
        if i0 < 0: sig, i0 = sig[-i0:], 0
        n = min(len(sig), N - i0)
        self.x[i0:i0 + n] += sig[:n] * g

def reverb(x, sec=1.6, decay=.38, seed=1):
    r = np.random.default_rng(seed)
    t = T(sec)
    ir = np.stack([r.standard_normal(len(t)) * np.exp(-t / decay) for _ in range(2)], 1)
    ir[:, 0] = lp(ir[:, 0], 7000); ir[:, 1] = lp(ir[:, 1], 7000)
    ir /= np.sqrt((ir ** 2).sum(0))
    return np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)

# =============================================================== MUSIC
drums, bass, keys, lead, fx_m = Bus(), Bus(), Bus(), Bus(), Bus()
PROG = [[57, 60, 64], [57, 60, 65], [55, 60, 64], [55, 59, 62]]   # Am F C G
ROOT = [45, 41, 48, 43]

def kick():
    t = T(.45)
    s = np.sin(glide(160, 46, t, .03)) * np.exp(-t / .3)
    c = hp(noise(.45), 3000) * np.exp(-t / .003) * .35
    return np.tanh((s + c) * 1.6) * .9
def clap():
    t = T(.4); n = bp(noise(.4), 900, 3200)
    env = sum(np.exp(-np.clip(t - d, 0, None) / .006) * (t >= d) for d in (0, .011, .022)) * .6 + np.exp(-t / .09) * (t >= .03)
    return n * env * .9
def hat(open_=False):
    L = .28 if open_ else .07
    t = T(L); return hp(noise(L), 7500, 4) * np.exp(-t / (.1 if open_ else .018))
def pluck(m, L=.42):
    t = T(L); f = midi(m)
    x = saw(f * 1.004, t) + saw(f * .996, t, .3)
    y = lp(x, 4200) * np.exp(-t / .07) * .6 + lp(x, 1400) * np.exp(-t / .22)
    return y * np.minimum(1, t / .003) * .2
def bass_note(m, L=.2):
    t = T(L); f = midi(m)
    x = lp(saw(f, t) * .6 + np.sign(np.sin(2 * np.pi * f * t)) * .3, 700) + np.sin(2 * np.pi * f / 2 * t) * .9
    return x * np.exp(-t / .16) * np.minimum(1, t / .004) * np.minimum(1, (L - t) / .01) * .45
def pad(ms, L, att=.35):
    t = T(L); x = 0
    for m in ms:
        for d in (-.006, 0, .007): x = x + saw(midi(m) * (1 + d), t, rng.random())
    x = lp(x, 1100)
    return x * np.minimum(1, t / att) * np.minimum(1, (L - t) / .5) * .05
def arp_note(m):
    t = T(.22); f = midi(m)
    x = lp(saw(f, t), 2600) * .6 + np.sin(2 * np.pi * f * t) * .5
    return x * np.exp(-t / .07) * np.minimum(1, t / .002) * .16

CH_OFF = round((D - 21.0) / 2) * 2          # сдвиг гармонии вместе с дропом (аккорды остаются на границах тактов)
def chord_at(sec): return int((sec - CH_OFF) // 2) % 4
PLAY_END = END - 1.0
kicks = []
for step in range(int(PLAY_END / STEP)):
    ts = step * STEP
    s16 = step % 16
    brk = D - 1 <= ts < D
    ci = chord_at(ts)
    if s16 % 4 == 0 and not brk:
        drums.add(kick(), ts, .95 if ts >= 2 else .75); kicks.append(ts)
    if s16 in (4, 12) and ts >= 2 and not brk: drums.add(clap(), ts, .5)
    if not brk or ts < D - .5: drums.add(hat(), ts, (.16 if s16 % 4 == 2 else .09) * (1 if ts >= 2 else .7), pan=.2 if s16 % 2 else -.1)
    if s16 in (2, 6, 10, 14) and ts >= 4 and not brk: drums.add(hat(True), ts, .07, pan=-.25)
    if s16 in (2, 6, 10, 14) and ts >= 2 and not brk: bass.add(bass_note(ROOT[ci]), ts)
    if s16 in (3, 6, 10, 13) and not brk:
        for k, m in enumerate(PROG[ci]): keys.add(pluck(m + 12), ts, .9, pan=(k - 1) * .35)
    if D + 1 <= ts < END - 2:
        tones = PROG[ci] + [p + 12 for p in PROG[ci]]
        lead.add(arp_note(tones[[0, 1, 2, 3, 4, 3, 2, 1][step % 8]] + 12), ts, pan=.3 * np.sin(step * .7))
# пэд: подъём в брейке и второй половине
for bar_t in [D - 1] + list(np.arange(D + 1, END - 1, 2.0)):
    ci = chord_at(bar_t)
    keys.add(pad([m + 12 for m in PROG[ci]], 2.1 if bar_t >= D else 1.1, .6 if bar_t < D else .05), bar_t, 1.0)
# дробь перед дропом
for i, ts in enumerate(list(np.arange(D - 1, D - .5, .125)) + list(np.arange(D - .5, D - .25, .0625)) + list(np.arange(D - .25, D, .03125))):
    drums.add(clap(), ts, .15 + .35 * (ts - (D - 1)))
# финальный аккорд
fin = T(1.0)
for m in (57, 60, 64, 69):
    keys.add(pluck(m + 12, 1.0) * 1.3, END - 1, 1)
keys.add(pad([57, 60, 64, 69], 1.0, .01) * 2.5, END - 1)
bass.add(np.sin(2 * np.pi * 55 * fin) * np.exp(-fin / .5) * .6, END - 1)
drums.add(kick(), END - 1, 1)
cr = T(1.0); drums.add(hp(noise(1.0), 5000) * np.exp(-cr / .45) * .18, END - 1)
cr = T(1.6); drums.add(hp(noise(1.6), 5000) * np.exp(-cr / .5) * .2, D)

# сайдчейн от бочки
duck = np.ones(N); td = T(.35)
for k in kicks:
    i0 = int(k * SR); seg = 1 - .65 * np.exp(-td / .08); n = min(len(seg), N - i0)
    duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], seg[:n])
duck = duck[:, None]
# задержка на арпеджио (3/16)
dl = int(.375 * SR); lx = lead.x.copy()
for k in range(1, 4): lx[dl * k:] += lead.x[:-dl * k][:, ::-1] * (.35 ** k)
music = drums.x + bass.x * duck + (keys.x + lx) * duck
music += reverb((keys.x + lx) * duck + drums.x * .15, 1.8, .45, 2) * .22
music[:, 0] = hp(music[:, 0], 30); music[:, 1] = hp(music[:, 1], 30)
# выход из трека к 32 с
tail = np.clip((DUR - np.arange(N) / SR) / .15, 0, 1)[:, None]
music *= tail

# =============================================================== SFX
sfx = Bus()
def svf_sweep(x, f_curve, q=.5):
    """Chamberlin SVF bandpass с меняющейся частотой среза."""
    low = band = 0.0; out = np.empty_like(x)
    fc = 2 * np.sin(np.pi * np.clip(f_curve, 20, SR / 6) / SR)
    for i in range(len(x)):
        low += fc[i] * band; high = x[i] - low - q * band; band += fc[i] * high; out[i] = band
    return out
def whoosh(d, f=1.0):
    L = d + .35; t = T(L); p = np.clip(t / d, 0, 1)
    fcurve = (350 + 2600 * np.sin(np.pi * np.clip(p * .9, 0, 1)) ** 1.5) * f
    env = np.sin(np.pi * np.clip(p, 0, 1)) ** 1.4 + np.exp(-np.clip(t - d, 0, None) / .08) * (t > d) * 0
    y = svf_sweep(noise(L), fcurve, .7) * env
    return np.stack([y * (1 - .4 * p), y * (.6 + .4 * p)], 1) * .7
def swoosh(f=1.0):
    L = .3; t = T(L); p = t / L
    y = svf_sweep(noise(L), (900 + 4200 * p) * f, .8) * np.sin(np.pi * p) ** 1.2
    return y * .5
def pop(f=1.0):
    t = T(.12); ph = glide(480 * f, 1150 * f, t, .02)
    ph = 2 * np.pi * np.cumsum(480 * f + 700 * f * (1 - np.exp(-t / .018))) / SR
    return np.sin(ph) * np.exp(-t / .04) * np.minimum(1, t / .002) * .5
def thump():
    t = T(.3); return (np.sin(glide(150, 55, t, .04)) * np.exp(-t / .1) + lp(noise(.3), 900) * np.exp(-t / .02) * .3) * .6
def tick(f=1.0):
    t = T(.03); return (np.sin(2 * np.pi * 2200 * f * t) * .6 + hp(noise(.03), 4000) * .5) * np.exp(-t / .005) * .6
def bonk():
    out = []
    for m, L in ((64, .14), (60, .26)):
        t = T(L); f = midi(m)
        x = lp(np.sign(np.sin(2 * np.pi * f * t)) * .5 + saw(f * 1.01, t) * .4, 1600)
        out.append(x * np.exp(-t / (L * .7)) * np.minimum(1, t / .004))
    return np.concatenate(out) * .45
def bell(f0, L=1.2, g=1.0):
    t = T(L); y = 0
    for r, a, d in ((1, 1, .8), (2.0, .45, .45), (2.76, .3, .3), (5.4, .12, .15), (8.9, .05, .08)):
        y = y + a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t / d)
    return y * np.minimum(1, t / .002) * .28 * g
def ding(f=1.0): return bell(1318.5 * f)
def success():
    a = bell(1046.5, 1.0); b = bell(1568, 1.2); out = np.zeros(len(b) + int(.09 * SR))
    out[:len(a)] += a; out[int(.09 * SR):] += b; return out * .9
def coin():
    t1 = T(.07); t2 = T(.45)
    a = lp(np.sign(np.sin(2 * np.pi * 988 * t1)), 5000) * .25
    b = lp(np.sign(np.sin(2 * np.pi * 1319 * t2)), 5000) * .25 * np.exp(-t2 / .15)
    return np.concatenate([a, b]) * .8 + np.pad(bell(2637, .45, .5), (int(.07 * SR), 0))[:len(t1) + len(t2)]
def click():
    t = T(.05)
    a = (bp(noise(.05), 2000, 7000) * np.exp(-t / .003) + np.sin(2 * np.pi * 180 * t) * np.exp(-t / .01) * .6)
    out = np.zeros(int(.13 * SR)); out[:len(a)] += a; out[int(.075 * SR):int(.075 * SR) + len(a)] += a * .45
    return out * .8
def blip(f=1.0):
    t = T(.09); fr = 880 * f
    return (np.sin(2 * np.pi * fr * t) + .25 * np.sin(4 * np.pi * fr * t)) * np.exp(-t / .03) * np.minimum(1, t / .002) * .35
def check():
    return pop(1.3) * .8 + np.pad(bell(2093, .5, .5), (int(.04 * SR), 0))[:int(.12 * SR)]
def zip_(d):
    t = T(d); p = t / d
    ph = 2 * np.pi * np.cumsum(500 + 2200 * p ** 1.5) / SR
    return (np.sin(ph) * .3 + svf_sweep(noise(d), 1500 + 5000 * p, .9) * .4) * np.sin(np.pi * p) ** .8 * .5
def riser(d):
    L = d; t = T(L); p = t / L
    n = svf_sweep(noise(L), 300 + 7000 * p ** 2, .6) * (p ** 2.2)
    ph = 2 * np.pi * np.cumsum(110 * 2 ** (2.5 * p)) / SR
    s = lp(saw(1, t) * 0 + np.sin(ph) + .5 * np.sin(2 * ph), 3000) * p ** 3 * .3
    return (n * .9 + s)
def fall(d):
    t = T(d); ph = 2 * np.pi * np.cumsum(1900 * np.exp(-t / (d * .6)) + 250) / SR
    return np.sin(ph) * .25 * np.minimum(1, t / .01) * np.minimum(1, (d - t) / .03)
def impact():
    t = T(2.0)
    sub = np.sin(glide(95, 34, t, .12)) * np.exp(-t / .7)
    body = lp(noise(2.0), 1800) * np.exp(-t / .12) * .8
    crash = hp(noise(2.0), 4500) * np.exp(-t / .6) * .25
    return np.tanh((sub * 1.2 + body + crash) * 1.3) * .85
def sparkle(seed=0):
    r = np.random.default_rng(seed); L = .9; out = np.zeros(int(L * SR))
    for k in range(7):
        t0 = k * .045 + r.random() * .02; b = bell(2200 + r.random() * 2600, .45, .22)
        i = int(t0 * SR); out[i:i + len(b)] += b[:len(out) - i]
    return out

MONO = {'pop': lambda e: pop(e.get('f', 1)), 'thump': lambda e: thump(), 'tick': lambda e: tick(e.get('f', 1)),
        'bonk': lambda e: bonk(), 'ding': lambda e: ding(e.get('f', 1)), 'success': lambda e: success(), 'coin': lambda e: coin(),
        'click': lambda e: click(), 'blip': lambda e: blip(e.get('f', 1)), 'check': lambda e: check(),
        'zip': lambda e: zip_(e.get('d', .7)), 'riser': lambda e: riser(e.get('d', 1.5)), 'fall': lambda e: fall(e.get('d', .3)),
        'impact': lambda e: impact(), 'sparkle': lambda e: sparkle(int(e['t'] * 10)), 'swoosh': lambda e: swoosh(e.get('f', 1)),
        'swish': lambda e: swoosh(1.8 * e.get('f', 1)) * .6}
GAIN = {'pop': .8, 'thump': .7, 'tick': .5, 'bonk': .9, 'ding': .8, 'success': .8, 'coin': .8, 'click': 1, 'blip': .8, 'check': .9,
        'zip': .6, 'riser': .5, 'fall': .5, 'impact': 1.0, 'sparkle': .7, 'swoosh': .75, 'swish': .6, 'whoosh': .9}

events = json.load(open(sys.argv[1]))
for e in events:
    g = e.get('g', 1) * GAIN.get(e['type'], 1)
    if e['type'] == 'whoosh': sfx.add(whoosh(e.get('d', .6)), e['t'] - .05, g)
    else: sfx.add(MONO[e['type']](e), e['t'], g, pan=float(np.clip(rng.normal(0, .15), -.4, .4)))
sfx_x = sfx.x + reverb(sfx.x, 1.2, .3, 3) * .16

# =============================================================== MIX
from scipy.io import wavfile
voice = np.zeros(N)
if len(sys.argv) > 3:
    _, v = wavfile.read(sys.argv[3]); v = v.astype(np.float64) / 32768
    voice[:min(N, len(v))] = v[:N]
# дакинг: музыка −14 дБ, эффекты −8 дБ, пока звучит голос (атака ~30 мс, отпускание ~350 мс)
lvl = np.abs(voice) > .02
env = np.convolve(lvl.astype(float), np.ones(int(.12 * SR)), 'same') > 0
env = sosfilt(butter(1, 1.2, 'low', fs=SR, output='sos'), env.astype(float))
env = np.clip(env / .6, 0, 1)[:, None]
mix = music * .37 * (1 - .8 * env) + sfx_x * .54 * (1 - .6 * env) + voice[:, None] * 1.3
mix[:, 0] = hp(mix[:, 0], 25); mix[:, 1] = hp(mix[:, 1], 25)
mix = np.tanh(mix * 1.25) / np.tanh(1.25)
mix *= .89 / np.max(np.abs(mix))
fade = np.minimum(1, np.arange(N) / (SR * .01))[:, None]
mix *= fade
wavfile.write(sys.argv[2], SR, (mix * 32767).astype(np.int16))
print('ok', sys.argv[2], f'{len(events)} sfx events')
