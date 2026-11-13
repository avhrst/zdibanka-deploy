#!/usr/bin/env python3
"""Synthesizes the trailer soundtrack (synth score + sound effects) and mixes in the voiceover -> audio.wav."""
import json, subprocess, wave
import numpy as np

SR = 44100
TL = json.load(open("timeline.json"))
TOTAL = TL["total"] + 0.5
N = int(TOTAL * SR)
BAR, BEAT = 2.0, 0.5
rng = np.random.default_rng(13)
S = [s["start"] for s in TL["scenes"]]
CUE = {k: v for s in TL["scenes"] for k, v in s["cues"].items()}

def bus(): return np.zeros((2, N))
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def tt(dur): return np.arange(int(dur * SR)) / SR
def add(b, start, sig, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    b[0, i:i + len(sig)] += sig * gain * l * 1.414
    b[1, i:i + len(sig)] += sig * gain * r * 1.414
def saw(f, t, harm=8):
    out = np.zeros_like(t)
    for n in range(1, harm + 1):
        if f * n > 9000: break
        out += np.sin(2 * np.pi * f * n * t) / n
    return out * 0.6
def env(t, a=0.01, d=0.0, s=1.0, r=0.1):
    dur = t[-1] if len(t) else 0
    e = np.minimum(1, t / max(a, 1e-4))
    if d: e *= s + (1 - s) * np.exp(-np.maximum(0, t - a) / d)
    return e * np.clip((dur - t) / max(r, 1e-4), 0, 1)
def lowpass(x, k):   # moving average
    if k <= 1: return x
    c = np.cumsum(np.insert(x, 0, 0)); return (c[k:] - c[:-k]) / k
def hp(x): return np.diff(x, prepend=x[0])
def echo(b, delay, gains, swap=True):
    out = b.copy(); d = int(delay * SR)
    for n, g in enumerate(gains, 1):
        src = b[::-1] if (swap and n % 2) else b
        out[:, n * d:] += src[:, : N - n * d] * g
    return out
def reverb(b, amt=0.25):
    out = b.copy()
    for ms, g in ((29, .5), (37, .45), (47, .4), (61, .34), (83, .28), (109, .22), (151, .16), (211, .11), (283, .07)):
        d = int(ms * SR / 1000); out[0, d:] += b[1, :-d] * g * amt; out[1, d:] += b[0, :-d] * g * amt
    return out

# ---- arrangement: intensity per bar -------------------------------------------------
nbars = int(TL["total"] / BAR)
def scene_of(t): return max(i for i, s in enumerate(S) if t >= s - 1e-6)
LEVEL = {0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 1}
CH = [[45, 48, 52, 57], [41, 45, 48, 53], [48, 52, 55, 60], [43, 47, 50, 55]]   # Am F C G
pad, bass, arp, drums, fx = bus(), bus(), bus(), bus(), bus()

for b in range(nbars):
    t0 = b * BAR; lvl = LEVEL[scene_of(t0)]; ch = CH[b % 4]
    final = scene_of(t0) == 5
    # pad: detuned saws, slow attack
    t = tt(BAR + 0.6); e = env(t, a=0.5, r=0.6)
    for m in ch:
        for det, pan in ((-5, -0.7), (5, 0.7)):
            add(pad, t0, saw(mtof(m) * 2 ** (det / 1200), t, 6) * e, 0.11 if lvl else 0.09, pan)
    add(pad, t0, np.sin(2 * np.pi * mtof(ch[0] - 12) * t) * e, 0.22)           # sub drone
    # bass: eighth notes
    if lvl >= 1 and not final:
        for k in range(8):
            t = tt(0.23); f = mtof(ch[0] - 12)
            sig = (saw(f, t, 5) + np.sin(2 * np.pi * f * t)) * np.exp(-t * 9) * env(t, a=0.004, r=0.03)
            add(bass, t0 + k * 0.25, sig, 0.30 if lvl >= 2 else 0.2)
    # arp: plucks over two octaves
    notes = ch + [m + 12 for m in ch]
    order = [0, 2, 4, 3, 5, 7, 6, 4] if lvl < 3 else [0, 2, 4, 6, 7, 5, 3, 1, 2, 4, 6, 7, 5, 3, 4, 2]
    stepd = BAR / len(order)
    if lvl == 0: order, stepd = [0, None, 4, None, 7, None, 5, None], BAR / 8
    for k, o in enumerate(order):
        if o is None: continue
        t = tt(0.35); f = mtof(notes[o] + 12)
        sig = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 13) * env(t, a=0.003, r=0.05)
        add(arp, t0 + k * stepd, sig, (0.13 if lvl >= 3 else 0.10) * (0.6 if final else 1), (-0.5 if k % 2 else 0.5))
    # drums
    if lvl >= 2:
        for k in range(4):
            t = tt(0.4); ph = 2 * np.pi * np.cumsum(42 + 110 * np.exp(-t * 32)) / SR
            add(drums, t0 + k * BEAT, np.sin(ph) * np.exp(-t * 8.5) + 0.3 * hp(rng.standard_normal(len(t))) * np.exp(-t * 200), 0.62)
            if k % 2 == 1:
                t = tt(0.22); nz = hp(rng.standard_normal(len(t)))
                add(drums, t0 + k * BEAT, nz * (np.exp(-t * 26) + 0.5 * np.exp(-((t - 0.012) ** 2) * 4e4)), 0.17)
        if lvl >= 3:
            for k in range(16):
                t = tt(0.09 if k % 4 == 2 else 0.04); nz = hp(hp(rng.standard_normal(len(t))))
                add(drums, t0 + k * 0.125, nz * np.exp(-t * (38 if k % 4 == 2 else 110)), 0.035 if k % 2 else 0.05, 0.3)

# sidechain pump where the kick plays
duck = np.ones(N)
for b in range(nbars):
    if LEVEL[scene_of(b * BAR)] >= 2:
        for k in range(4):
            i = int((b * BAR + k * BEAT) * SR); t = tt(BEAT)[: N - i]
            duck[i:i + len(t)] = 1 - 0.55 * np.exp(-t * 9)
pad *= duck; bass *= duck; arp *= 0.6 + 0.4 * duck
arp = echo(arp, 0.375, (0.42, 0.24, 0.12))

# ---- cinematic effects --------------------------------------------------------------
def riser(t_end, dur=2.0, gain=0.3):
    t = tt(dur); nz = hp(rng.standard_normal(len(t))) * (t / dur) ** 2.5
    sw = np.sin(2 * np.pi * np.cumsum(180 * (2 ** (3.2 * t / dur))) / SR) * (t / dur) ** 2 * 0.25
    add(fx, t_end - dur, nz * 0.5 + sw, gain, -0.2); add(fx, t_end - dur, np.roll(nz, 211) * 0.5 + sw, gain, 0.2)
def impact(t0, gain=0.9):
    t = tt(3.0)
    boom = np.sin(2 * np.pi * np.cumsum(34 + 40 * np.exp(-t * 6)) / SR) * np.exp(-t * 1.9)
    crash = lowpass(rng.standard_normal(len(t) + 40), 40)[: len(t)] * np.exp(-t * 5) * 1.6
    air = hp(rng.standard_normal(len(t))) * np.exp(-t * 2.4) * 0.12
    add(fx, t0, boom + crash + air, gain)
def whoosh(tc, dur=0.7, gain=0.16):
    t = tt(dur); nz = lowpass(rng.standard_normal(len(t) + 12), 12)[: len(t)] * np.exp(-((t - dur / 2) ** 2) / (2 * (dur / 6) ** 2))
    add(fx, tc - dur / 2, nz, gain, -0.6); add(fx, tc - dur / 2 + 0.03, nz[::-1], gain, 0.6)
def sweep(t0, f1, f2, dur, gain, shape="sine", pan=0.0, decay=6):
    t = tt(dur); f = f1 * (f2 / f1) ** (t / dur); ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) if shape == "sine" else np.sign(np.sin(ph)) * 0.5
    add(fx, t0, sig * np.exp(-t * decay) * env(t, a=0.004, r=0.03), gain, pan)
def chirp(t0, midis, gain=0.16, step=0.07):
    for k, m in enumerate(midis):
        t = tt(0.16); f = mtof(m)
        add(fx, t0 + k * step, (np.sin(2 * np.pi * f * t) + 0.3 * np.sign(np.sin(2 * np.pi * f * t))) * np.exp(-t * 16), gain, (k % 2) * 0.6 - 0.3)
def boom(t0, gain=0.5, dur=1.1):
    t = tt(dur); nz = lowpass(rng.standard_normal(len(t) + 30), 30)[: len(t)] * np.exp(-t * 4.5) * 2.2
    lowb = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 10)) / SR) * np.exp(-t * 4)
    add(fx, t0, nz + lowb, gain)

# twinkles in the quiet intro
for k in range(22):
    t0 = rng.uniform(0.2, S[1] - 0.5); t = tt(0.9); f = mtof(rng.choice([81, 84, 88, 93, 96]))
    add(fx, t0, np.sin(2 * np.pi * f * t) * np.exp(-t * 5), 0.035, rng.uniform(-0.9, 0.9))
# keyboard ticks while the push command is typed, then the "enter" thud
for k in range(16):
    t = tt(0.02); add(fx, CUE["deploy"] - 0.75 + k * 0.075 + rng.uniform(0, 0.02), hp(rng.standard_normal(len(t))) * np.exp(-t * 300), 0.07, rng.uniform(-0.3, 0.3))
boom(CUE["prod"] + 0.25, 0.42)
for i in range(1, 6): whoosh(S[i])
riser(S[2], 2.0, 0.3); impact(S[2], 0.9)
riser(S[3], 1.0, 0.18); impact(S[3], 0.5)
riser(S[5], 2.0, 0.34); impact(S[5], 1.0)
impact(S[1], 0.45)
# scene 2: stingers for each enemy type
for name, f in (("fires", 110), ("legacy", 98), ("bombs", 82)):
    sweep(CUE[name], f * 2, f, 0.5, 0.22, "square", decay=4)
boom(CUE["bombs"] + 0.35, 0.35)
# scene 3: hero
chirp(CUE["roma"], [69, 76, 81, 88], 0.15, 0.09)
sweep(CUE["ball"], 1900, 280, 0.28, 0.22)
# scene 4: power-ups
chirp(CUE["tori"], [72, 76, 79, 84, 88], 0.16)
sweep(CUE["myr"], 620, 140, 0.45, 0.2, "square", decay=3)
for k in range(3): sweep(CUE["multi"] + k * 0.09, 900 + 500 * k, 2400, 0.12, 0.13, pan=(k - 1) * 0.7)
t = tt(1.2); add(fx, CUE["rocket"], hp(rng.standard_normal(len(t))) * (t / 1.2) * np.exp(-((t - 0.9) ** 2) * 9) + 0.5 * np.sin(2 * np.pi * np.cumsum(70 + 130 * t) / SR) * np.exp(-((t - 0.8) ** 2) * 6), 0.2)
for k in range(5): boom(CUE["burn"] + 0.1 + k * 0.13, 0.16, 0.5)
# scene 5: wall goes down, sprint, leaderboard
for k in range(6): boom(CUE["wall"] + 0.25 + k * 0.11, 0.22 if k else 0.4, 0.7)
chirp(CUE["sprint"], [76, 79, 83, 88], 0.14, 0.06)
chirp(CUE["board"], [84, 88, 91, 96], 0.13, 0.11)
# scene 6: final hits
boom(CUE["telegram"], 0.25, 0.6)
impact(CUE["now"] + 0.05, 0.7)

music = pad + bass + arp + drums * 0.95 + reverb(fx, 0.5)
music = reverb(music, 0.12)
fade = np.clip((TL["total"] + 0.3 - np.arange(N) / SR) / 2.5, 0, 1)
music *= fade

# ---- voiceover -----------------------------------------------------------------------
vo = bus()
for i, s in enumerate(TL["scenes"], 1):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", f"vo{i}.mp3", "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"])
    x = np.frombuffer(raw, dtype=np.int16).astype(float) / 32768
    add(vo, s["vo"], x / (np.abs(x).max() or 1), 0.9)
vo = vo + 0.6 * (reverb(vo, 0.35) - vo)
level = lowpass(np.abs(vo[0]) + np.abs(vo[1]), int(0.12 * SR))
level = np.pad(level, (0, N - len(level)))
duckv = 1 - 0.45 * np.clip(level * 6, 0, 1)
duckv = lowpass(np.pad(duckv, (2000, 2000), mode="edge"), 4001)[:N]
out = music * duckv * 0.8 + vo * 1.15
out = np.tanh(out * 1.1)
out = out / np.abs(out).max() * 0.94
with wave.open("audio.wav", "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out.T * 32767).astype("<i2").tobytes())
print("audio.wav", round(N / SR, 2), "s")
