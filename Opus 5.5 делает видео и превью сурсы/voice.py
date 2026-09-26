"""Закадровый голос → voice.wav + assets/timeline.js (тайминг сцен под длину реплик).
   .venv/bin/python voice.py <workdir> <out.wav> [--engine auto|elevenlabs|say]

ElevenLabs: ключ берётся из ELEVENLABS_API_KEY (окружение или .env рядом со скриптом).
  ELEVENLABS_VOICE_ID — голос (по умолчанию ниже), ELEVENLABS_MODEL — модель.
Без ключа — черновой системный голос macOS (Milena), чтобы можно было собрать монтаж.

Метки |a| |b| … в тексте — моменты, к которым привязана анимация (время начала следующего слова).
Длительность сцены = max(минимум, вступление + реплика + хвост), округлено до 0.25 с.
"""
import argparse, base64, json, math, os, re, subprocess, urllib.request
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))

# (минимальная длительность сцены, задержка голоса от начала сцены, текст)
CUES = [
    (5.0, 0.20, "Опус пять возился с кодом |a|двадцать часов. Новый Опус пять и пять — |b|меньше трёх."),
    (5.5, 0.30, "В кодинге он |a|обошёл даже старшую Фейбл: |b|шестьдесят шесть против пятидесяти шести."),
    (5.5, 0.30, "Он дешевле Опус пять |a|на двадцать процентов, а |b|Фейбл — в два с половиной раза."),
    (3.5, 0.30, "А отвечает на |a|тридцать процентов быстрее."),
    (4.5, 0.30, "|a|Клод Опус пять и пять уже доступен в |b|Клоде, |c|Клод Коде и |d|по эй-пи-ай."),
    (4.0, 0.30, "Больше про ИИ — в моём канале. |a|Наводи камеру!"),
]
TAIL = 0.45      # воздух после реплики (включает уход камеры)
STEP = 0.25

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('out')
ap.add_argument('--engine', default='auto')
a = ap.parse_args()
os.makedirs(a.work, exist_ok=True)

def load_env():
    p = os.path.join(HERE, '.env')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()
KEY = os.environ.get('ELEVENLABS_API_KEY', '')
VOICE = os.environ.get('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')   # Adam (премейд, мультиязычный)
MODEL = os.environ.get('ELEVENLABS_MODEL', 'eleven_multilingual_v2')
engine = a.engine if a.engine != 'auto' else ('elevenlabs' if KEY else 'say')

def parse(text):
    """'…|a|слово…' → чистый текст и {метка: индекс символа}."""
    clean, marks, i = '', {}, 0
    for part in re.split(r'(\|\w+\|)', text):
        if re.fullmatch(r'\|\w+\|', part): marks[part.strip('|')] = len(clean)
        else: clean += part
    return clean, marks

def to_wav48(src, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ac', '1', '-ar', str(SR), dst], check=True)
    return wavfile.read(dst)[1].astype(np.float64) / 32768

def tts_eleven(i, text, prev, nxt):
    body = {'text': text, 'model_id': MODEL, 'previous_text': prev, 'next_text': nxt,
            'voice_settings': {'stability': 0.45, 'similarity_boost': 0.8, 'style': 0.35, 'use_speaker_boost': True, 'speed': 1.12}}
    req = urllib.request.Request(
        f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128',
        data=json.dumps(body).encode(), headers={'xi-api-key': KEY, 'Content-Type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    mp3 = os.path.join(a.work, f'cue{i}.mp3'); open(mp3, 'wb').write(base64.b64decode(r['audio_base64']))
    x = to_wav48(mp3, os.path.join(a.work, f'cue{i}.wav'))
    al = r['alignment']
    return x, (lambda idx: al['character_start_times_seconds'][min(idx, len(al['characters']) - 1)])

def tts_say(i, text, prev, nxt):
    p = os.path.join(a.work, f'cue{i}.aiff')
    subprocess.run(['say', '-v', 'Milena', '-o', p, text], check=True)
    x = to_wav48(p, os.path.join(a.work, f'cue{i}.wav'))
    return x, None

def trim(x):
    idx = np.where(np.abs(x) > 0.02 * np.max(np.abs(x)))[0]
    s = max(0, idx[0] - 240)
    return x[s: idx[-1] + 2400], s / SR

def process(x):
    x = sosfilt(butter(2, 70, 'high', fs=SR, output='sos'), x)
    env = np.sqrt(sosfilt(butter(1, 12, 'low', fs=SR, output='sos'), x ** 2) + 1e-9)
    thr = np.percentile(env, 80) * .8
    x = x * np.where(env > thr, (thr / env) ** 0.4, 1.0)      # мягкая компрессия
    return x / np.max(np.abs(x)) * .75

texts = [parse(t) for _, _, t in CUES]
clips, marks = [], []
for i, (clean, mk) in enumerate(texts):
    prev = texts[i - 1][0] if i else ''
    nxt = texts[i + 1][0] if i + 1 < len(texts) else ''
    x, at = (tts_eleven if engine == 'elevenlabs' else tts_say)(i, clean, prev, nxt)
    x, off = trim(x)
    L = len(x) / SR
    # время метки внутри клипа: по выравниванию ElevenLabs, иначе — пропорционально позиции символа
    m = {k: (at(idx) - off if at else L * idx / len(clean)) for k, idx in mk.items()}
    clips.append(process(x)); marks.append(m)

scenes, t = [], 0.0
for (mind, lead, _), c, m in zip(CUES, clips, marks):
    L = len(c) / SR
    dur = max(mind, math.ceil((lead + L + TAIL) / STEP) * STEP)
    scenes.append({'start': round(t, 3), 'dur': dur, 'vo': [round(t + lead, 3), round(t + lead + L, 3)],
                   'marks': {k: round(t + lead + max(0, v), 3) for k, v in m.items()}})
    t += dur
total = t

track = np.zeros(int(SR * total) + SR)
for s, c in zip(scenes, clips):
    i0 = int(s['vo'][0] * SR); track[i0:i0 + len(c)] += c
track = track[:int(SR * total)]
wavfile.write(a.out, SR, (np.clip(track, -1, 1) * 32767).astype(np.int16))
open(os.path.join(HERE, 'assets', 'timeline.js'), 'w').write(
    f"window.SCENES = {json.dumps(scenes, ensure_ascii=False)};\nwindow.VOICE_ENGINE = {json.dumps(engine)};\n")

print(f'engine={engine}' + (f' voice={VOICE} model={MODEL}' if engine == 'elevenlabs' else ''))
for s, (clean, _) in zip(scenes, texts):
    print(f"{s['start']:6.2f} +{s['dur']:.2f}  голос {s['vo'][0]:.2f}–{s['vo'][1]:.2f}  {clean}")
print(f'длительность {total:.2f} с')
