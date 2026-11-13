#!/bin/sh
# Rebuilds space-promo.mp4. Needs: chromium, ffmpeg, node 22+, and ../.venv with edge-tts and numpy
# (python -m venv ../.venv && ../.venv/bin/pip install edge-tts numpy).
set -e
cd "$(dirname "$0")"
../.venv/bin/python vo.py          # voiceover lines + word timings -> vo*.mp3, vo.json
python3 timeline.py                # scene timeline synced to the voiceover -> timeline.json, timeline.js
../.venv/bin/python music.py       # synth score + sound effects + voiceover -> audio.wav
node render.mjs video.mp4          # renders space.html frame by frame -> video.mp4 (silent)
ffmpeg -y -v error -i video.mp4 -i audio.wav -c:v copy -af "loudnorm=I=-14:TP=-1.2:LRA=11" \
  -c:a aac -b:a 192k -ar 48000 -t 60 -movflags +faststart space-promo.mp4
