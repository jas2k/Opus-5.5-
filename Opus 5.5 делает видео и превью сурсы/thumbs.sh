#!/bin/zsh
# Обложки: 16:9 и 9:16 для Shorts, затем 16:9 «Opus 5.5 делает видео» (в неё вставляются кадр ролика и первое превью)
#   ./thumbs.sh ["Ролик.mp4"]
set -e
cd "$(dirname "$0")"
VIDEO="${1:-Opus 5.5 — что нового.mp4}"
[ -f assets/thumb/u09.png ] || { echo "Сначала: .venv/bin/python prepare_assets.py"; exit 1; }
[ -f "$VIDEO" ] || { echo "Нет ролика «$VIDEO» — сначала ./build.sh"; exit 1; }
node thumb.mjs . "YouTube 16x9"
node thumb.mjs . "вертикальное"
ffmpeg -v error -y -ss 4.9 -i "$VIDEO" -frames:v 1 -vf scale=540:960 -q:v 2 assets/thumb/shorts_frame.jpg
ffmpeg -v error -y -i "Превью — YouTube 16x9 1920x1080.png" -vf scale=960:540 -q:v 2 assets/thumb/yt_thumb.jpg
node thumb.mjs . "делает видео"
echo "готово: Превью — *.png / *.jpg"
