#!/usr/bin/env python3
"""Generates the trailer voiceover lines (vo1..voN.mp3) and word timings (vo.json) with edge-tts."""
import asyncio, json, subprocess
import edge_tts

VOICE, RATE, PITCH = "uk-UA-OstapNeural", "-10%", "-14Hz"
LINES = [
    "Пʼятниця. Вечір. Десь у далекому космосі хтось задеплоїв на прод.",
    "Армада багів оточила планету. Пожежі. Легасі. Бомби.",
    "Лише один капітан може їх зупинити. Рома. І його плазмовий мʼяч.",
    "Торі подвоює щит. Мир його стискає. Блискавка множить мʼячі. А ракета пропалює все.",
    "Зруйнуй стіну. Пройди спринт. Очоль таблицю лідерів.",
    "Деплой у пʼятницю. Грай у Телеграмі. Просто зараз.",
]

async def synth(i, text):
    com = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary")
    words = []
    with open(f"vo{i}.mp3", "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7, "w": ch["text"]})
    dur = float(subprocess.check_output(["ffprobe", "-v", "0", "-show_entries", "format=duration", "-of", "csv=p=0", f"vo{i}.mp3"]))
    return {"text": text, "dur": dur, "words": words}

async def main():
    out = [await synth(i, t) for i, t in enumerate(LINES, 1)]
    json.dump(out, open("vo.json", "w"), ensure_ascii=False, indent=1)
    for i, o in enumerate(out, 1): print(i, round(o["dur"], 2), " ".join(f'{w["w"]}@{w["t"]:.2f}' for w in o["words"]))
asyncio.run(main())
