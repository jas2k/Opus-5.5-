"""Стикеры для ролика и обложек: пак UtyaDuck из Telegram → assets/stickers/*.json + assets/thumb/*.png
   .venv/bin/python prepare_assets.py

Нужен токен любого своего бота: BOT_TOKEN в .env (или в окружении). Бот только читает публичный пак.
Сами стикеры в репозиторий не кладутся — это официальный пак Telegram, скрипт скачивает их локально.
Номера — позиции в паке на момент создания ролика (эмодзи рядом — для сверки, если пак поменяют).
"""
import gzip, json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = 'UtyaDuck'
# позиция в паке → зачем
VIDEO = {9: '😎 Opus 5.5', 13: '🔥 скорость', 16: '🤔 Opus 5', 17: '🤑 Fable 5.1', 24: '😴 Opus 5 спит', 29: '🥳 финал'}
# кадры для обложек: (позиция, кадр, размер px)
THUMB = [(9, 0, 1100), (24, 60, 600), (3, 30, 900)]

def load_env():
    p = os.path.join(HERE, '.env')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()
TOKEN = os.environ.get('BOT_TOKEN', '')
if not TOKEN:
    raise SystemExit('Нет BOT_TOKEN: впиши токен своего бота в .env (см. .env.example)')

def get(url, tries=5):
    for k in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=40).read()
        except Exception:
            if k == tries - 1: raise
            time.sleep(2)

def api(method, **params):
    r = json.loads(get(f'https://api.telegram.org/bot{TOKEN}/{method}?' + urllib.parse.urlencode(params)))
    if not r.get('ok'): raise SystemExit(f'Telegram API: {r}')
    return r['result']

stickers = api('getStickerSet', name=PACK)['stickers']
os.makedirs(os.path.join(HERE, 'assets', 'stickers'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'assets', 'thumb'), exist_ok=True)
tgs = {}
for i in sorted(set(VIDEO) | {i for i, _, _ in THUMB}):
    f = api('getFile', file_id=stickers[i]['file_id'])
    tgs[i] = get(f'https://api.telegram.org/file/bot{TOKEN}/{f["file_path"]}')
    print(f'#{i:02d} {stickers[i].get("emoji", "")}  {VIDEO.get(i, "обложка")}')

for i in VIDEO:   # .tgs — это gzip с Lottie JSON внутри
    open(os.path.join(HERE, 'assets', 'stickers', f'u{i:02d}.json'), 'wb').write(gzip.decompress(tgs[i]))

from rlottie_python import LottieAnimation
for i, frame, size in THUMB:
    anim = LottieAnimation.from_data(gzip.decompress(tgs[i]).decode('utf-8'))
    anim.render_pillow_frame(frame_num=frame, width=size, height=size).save(os.path.join(HERE, 'assets', 'thumb', f'u{i:02d}.png'))
print('готово: assets/stickers и assets/thumb')
