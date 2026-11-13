#!/usr/bin/env python3
"""Builds the scene timeline from vo.json: scene starts snapped to 2-second bars (120 bpm) and cue times for key words."""
import json, math
vo = json.load(open("vo.json"))
LEAD = [1.4, 0.6, 0.6, 0.6, 0.6, 0.9]          # silence before each line inside its scene
TAIL = [0.5, 0.6, 1.2, 0.7, 0.5, 1.8]
CUES = {  # scene index -> {cue name: word prefix}
    0: {"friday": "Пʼятниця", "evening": "Вечір", "space": "Десь", "deploy": "задеплоїв", "prod": "прод"},
    1: {"armada": "Армада", "planet": "планету", "fires": "Пожежі", "legacy": "Легасі", "bombs": "Бомби"},
    2: {"captain": "капітан", "stop": "зупинити", "roma": "Рома", "plasma": "плазмовий", "ball": "мʼяч"},
    3: {"tori": "Торі", "myr": "Мир", "multi": "Блискавка", "rocket": "ракета", "burn": "пропалює"},
    4: {"wall": "стіну", "sprint": "спринт", "board": "таблицю"},
    5: {"title": "Деплой", "play": "Грай", "telegram": "Телеграмі", "now": "зараз"},
}
scenes, t = [], 0.0
for i, v in enumerate(vo):
    dur = math.ceil((LEAD[i] + v["dur"] + TAIL[i]) / 2) * 2
    cues = {}
    for name, prefix in CUES[i].items():
        w = next(w for w in v["words"] if w["w"].lower().startswith(prefix.lower()))
        cues[name] = round(t + LEAD[i] + w["t"], 3)
    scenes.append({"start": t, "dur": dur, "vo": round(t + LEAD[i], 3), "voDur": v["dur"], "cues": cues})
    t += dur
tl = {"total": t, "bpm": 120, "scenes": scenes}
json.dump(tl, open("timeline.json", "w"), indent=1)
open("timeline.js", "w").write("window.TL = " + json.dumps(tl) + ";\n")
print("total", t, [(s["start"], s["dur"]) for s in scenes])
