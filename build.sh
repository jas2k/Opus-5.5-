#!/bin/zsh
# Полная сборка: голос → кадры → музыка/эффекты/микс → mp4 (1080×1920, 60 fps, −14 LUFS)
#   ./build.sh ["Имя файла.mp4"]
set -e
cd "$(dirname "$0")"
OUT="${1:-Opus 5.5 — что нового.mp4}"
[ -f assets/stickers/u09.json ] || { echo "Сначала: .venv/bin/python prepare_assets.py"; exit 1; }
mkdir -p build
.venv/bin/python voice.py build/vo build/voice.wav
node render.mjs --out build/frames --fps 60 --workers 6
.venv/bin/python audio.py build/frames/sfx.json build/mix.wav build/voice.wav
DUR=$(node -p "require('./build/frames/timeline.json').dur")
ffmpeg -v error -y -framerate 60 -i build/frames/f_%05d.jpg -i build/mix.wav -t "$DUR" \
  -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$OUT"
echo "готово: $OUT ($DUR с)"
