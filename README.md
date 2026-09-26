# Opus 5.5 делает видео и превью

Исходники Shorts-ролика «Claude Opus 5.5 — что нового» (30 с, 1080×1920, 60 fps) и трёх обложек к нему. Всё это собрал Claude Opus 5.5 в Claude Code по одному референсу.

🎬 Автор снял об этом ролик на YouTube — как Opus 5.5 создаёт Shorts и превью: <https://www.youtube.com/watch?v=J3c8060710k>
Автор — StriverDev, Telegram-канал: <https://t.me/StriverDev>

Ролик — это HTML-страница с анимацией на GSAP. Headless Chrome снимает её кадр за кадром, голос озвучивает ElevenLabs, а музыку и звуковые эффекты синтезирует Python-код. Сторонние аудиофайлы не нужны.

## Что внутри

| Файл | Что делает |
|---|---|
| `index.html`, `scene.js` | Шесть сцен ролика: вёрстка и хореография. Анимация детерминированная: `window.renderAt(t)` рисует ровно момент `t`. |
| `voice.py` | Озвучка через ElevenLabs (или черновой голос macOS). По длине реплик раскладывает тайминг сцен и пишет `assets/timeline.js`. |
| `render.mjs` | Покадровый рендер `index.html` через Chrome, кадры рендерятся в несколько потоков. Заодно выгружает список звуковых событий `sfx.json`. |
| `audio.py` | Музыка (120 BPM), эффекты по `sfx.json`, приглушение музыки под голос, итоговый микс. |
| `build.sh` | Полная сборка: голос → кадры → звук → mp4 с громкостью −14 LUFS. |
| `thumb.html`, `thumb-yt.html`, `thumb.mjs`, `thumbs.sh` | Обложки: 16:9 и 9:16 для Shorts плюс 16:9 для ролика «Opus 5.5 делает видео». |
| `gen_qr.mjs`, `qrcheck.mjs` | Генерация QR (`assets/qr.js`) и проверка, что он считывается с кадра. |
| `prepare_assets.py` | Скачивает стикеры UtyaDuck из Telegram и отрисовывает кадры уток для обложек. |

## Что нужно

- macOS: черновой голос `say` и путь к Chrome по умолчанию рассчитаны на Mac. На других системах задай переменную `CHROME` и используй ElevenLabs.
- Node.js 18+, Python 3.9+, `ffmpeg`, Google Chrome.
- Ключ ElevenLabs с доступом **Text to Speech**. Без ключа ролик соберётся с черновым голосом.
- Токен любого своего Telegram-бота — чтобы скачать стикеры.

## Установка

```bash
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # впиши ELEVENLABS_API_KEY и BOT_TOKEN
.venv/bin/python prepare_assets.py
```

## Сборка

```bash
./build.sh                  # → «Opus 5.5 — что нового.mp4», около 3 минут
./thumbs.sh                 # → «Превью — *.png/jpg» (нужен уже собранный ролик)
```

Каждый запуск `build.sh` заново генерирует голос: ElevenLabs каждый раз выдаёт немного другой дубль, и тайминг сцен подстраивается под него сам.

## Как менять

- **Текст озвучки** — список `CUES` в `voice.py`. Метки `|a|`, `|b|` ставятся перед словом, к которому привязана анимация. Например, счётчик «20+ ч» срабатывает на слове «двадцать». Время меток берётся из тайм-кодов ElevenLabs.
- **Сцены** — вёрстка в `index.html`, анимация в `scene.js`, по блоку на сцену.
- **Ссылка в QR:** `node gen_qr.mjs https://t.me/твой_канал`. Проверить готовый кадр: `node qrcheck.mjs кадр.png`.
- **Предпросмотр в браузере:** `python3 -m http.server`, затем открой `http://localhost:8000/index.html`. Для стоп-кадра добавь к адресу `?t=12.3`.

## Откуда цифры

Анонс Anthropic от 22.09.2026: <https://www.anthropic.com/claude-opus-5-5>.

- Terminal-Bench 4.0: Opus 5 — 52,3%, Fable 5.1 — 55,8%, Opus 5.5 — 66,4%.
- Цена за 1M токенов (вход / выход): Opus 5.5 — $4 / $20, Opus 5 — $5 / $25, Fable 5.1 — $10 / $50.
- Скорость генерации — +30% к Opus 5.
- «20+ ч против <3 ч» — кейс одного раннего тестера из того же анонса, в кадре есть сноска.

## Сторонние материалы

- **Стикеры** — пак [Utya Duck](https://t.me/addstickers/UtyaDuck), © Telegram. В репозиторий не входят, `prepare_assets.py` скачивает их локально.
- **Шрифты** — Unbounded, Manrope, Press Start 2P, JetBrains Mono, лицензия SIL Open Font License 1.1. Тексты лицензий лежат в `assets/fonts/licenses/`.
- **npm-пакеты** — GSAP, lottie-web, puppeteer-core, qrcode.
