#!/bin/sh
# Generates the voiceover segments v1..vN.mp3 from segs.txt (needs: python -m venv .venv && .venv/bin/pip install edge-tts).
cd "$(dirname "$0")" || exit 1
i=0
while IFS= read -r line; do
  i=$((i+1))
  .venv/bin/edge-tts --voice uk-UA-OstapNeural --rate=-4% --pitch=-2Hz --text "$line" --write-media "v$i.mp3"
done < segs.txt
