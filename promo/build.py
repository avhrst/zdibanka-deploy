#!/usr/bin/env python3
"""Builds promo.mp4: Hutsul-style slides + voiceover (v1..v6.mp3) + generated tsymbaly-like tune."""
import math, random, struct, subprocess, wave
W, H, PAD = 1280, 720, 0.45
CHROME = "/usr/bin/chromium"
CREAM, RED, BLACK, ORANGE, GREEN = "#f6efdc", "#c8102e", "#1a1a1a", "#f39c12", "#2e7d32"

def band(y, flip=False):
    """Embroidery-like band of diamonds, crosses and zigzags."""
    out, s = [], 40
    for i in range(W // s + 1):
        x = i * s
        c = [RED, BLACK, RED, ORANGE, RED, GREEN][i % 6]
        cy = y + 40
        out.append(f'<path d="M{x} {cy-28} L{x+s/2} {cy} L{x} {cy+28} L{x-s/2} {cy} Z" fill="{c}"/>')
        out.append(f'<path d="M{x} {cy-12} L{x+s/5} {cy} L{x} {cy+12} L{x-s/5} {cy} Z" fill="{CREAM}"/>')
        out.append(f'<rect x="{x+s/2-4}" y="{cy-4}" width="8" height="8" fill="{BLACK}"/>')
    zy = y + (86 if not flip else -6)
    pts = " ".join(f"{i*20},{zy + (0 if i%2 else 10)}" for i in range(W // 20 + 1))
    out.append(f'<polyline points="{pts}" fill="none" stroke="{RED}" stroke-width="5"/>')
    zy2 = y + (-6 if not flip else 86)
    out.append(f'<rect x="0" y="{zy2}" width="{W}" height="6" fill="{BLACK}"/>')
    return "".join(out)

SLIDES = [
    ("🏔️", "Слава Ісу, ґазди айтішні!", "IT ZDYBANKA має файну новину"),
    ("🚀", "Пʼятниця, тринадцяте…", "а наш леґінь деплоїть на прод!"),
    ("🐛🔥🐛", "Йой, шо то сі діє!", "Баґи летє, прод горит, як ватра"),
    ("✅ ☕ 🦆", "Лови коміти та каву", "а гумова качка порєтує"),
    ("🏆", "ДЕПЛОЙ У ПʼЯТНИЦЮ", "Таблиця лідерів IT ZDYBANKA — будь перший ґазда!"),
    ("💻", "Тай гайда на прод!", "t.me/zdibanka_deploy_bot/deploy"),
]

def slide(i, emoji, title, sub):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
<rect width="{W}" height="{H}" fill="{CREAM}"/>{band(0)}{band(H-92, True)}
<text x="{W/2}" y="285" text-anchor="middle" font-family="Noto Color Emoji" font-size="120">{emoji}</text>
<text x="{W/2}" y="430" text-anchor="middle" font-family="Liberation Serif" font-weight="bold" font-size="{84 if len(title) < 22 else 72}" fill="{BLACK}">{title}</text>
<text x="{W/2}" y="515" text-anchor="middle" font-family="Liberation Sans" font-size="40" fill="{RED}">{sub}</text>
</svg>'''
    open(f"s{i}.svg", "w").write(svg)
    import os
    subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--disable-gpu", f"--window-size={W},{H}",
                    f"--screenshot={os.path.abspath(f's{i}.png')}", "file://" + os.path.abspath(f"s{i}.svg")],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "0", "-show_entries", "format=duration", "-of", "csv=p=0", f]))

def music(total, path="music.wav", sr=22050):
    """Kolomyika-ish tune on a plucked (Karplus-Strong) string in the Hutsul scale, with a bass pulse."""
    random.seed(13)
    scale = [293.66, 329.63, 349.23, 415.30, 440.0, 493.88, 523.25, 587.33, 659.25, 698.46]  # D E F G# A B C D E F
    A = [4, 4, 5, 4, 3, 4, 2, 0, 4, 4, 5, 7, 6, 5, 4, 4]
    B = [7, 7, 8, 7, 6, 5, 4, 2, 3, 4, 5, 4, 3, 2, 0, 0]
    tune = A + A + B + B
    step = 60 / 138 / 2
    n = int(total * sr); buf = [0.0] * n
    def pluck(freq, start, length, amp):
        p = int(sr / freq); ring = [random.uniform(-1, 1) for _ in range(p)]
        s0 = int(start * sr)
        for k in range(int(length * sr)):
            if s0 + k >= n: break
            v = ring[k % p]; ring[k % p] = 0.996 * 0.5 * (v + ring[(k + 1) % p])
            buf[s0 + k] += amp * v
    t, k = 0.0, 0
    while t < total:
        pluck(scale[tune[k % len(tune)]], t, 0.5, 0.5)
        if k % 2 == 0: pluck(146.83 if (k // 2) % 2 == 0 else 220.0, t, 0.45, 0.45)
        t += step; k += 1
    peak = max(abs(x) for x in buf) or 1
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(x / peak * 30000)) for x in buf))

durs = [dur(f"v{i}.mp3") + PAD for i in range(1, len(SLIDES) + 1)]
durs[-1] += 1.5
total = sum(durs)
for i, s in enumerate(SLIDES, 1): slide(i, *s)
music(total)

inputs, filt = [], []
for i, d in enumerate(durs, 1):
    inputs += ["-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", f"s{i}.png"]
for i in range(1, len(durs) + 1): inputs += ["-i", f"v{i}.mp3"]
inputs += ["-i", "music.wav"]
n = len(durs)
for i, d in enumerate(durs):
    fr = int(d * 30)
    filt.append(f"[{i}:v]scale=1600:900,zoompan=z='1.0+0.06*on/{fr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,"
                f"fade=t=in:st=0:d=0.3,fade=t=out:st={d-0.3:.3f}:d=0.3[v{i}]")
    filt.append(f"[{n+i}:a]aresample=44100,apad=whole_dur={d:.3f},atrim=0:{d:.3f}[a{i}]")
filt.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]")
filt.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,volume=1.6[voice]")
filt.append(f"[{2*n}:a]aresample=44100,volume=0.16,afade=t=in:d=0.5,afade=t=out:st={total-1.5:.3f}:d=1.5[mus]")
filt.append("[voice][mus]amix=inputs=2:duration=first:normalize=0[a]")
subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "promo.mp4"], check=True)
print("promo.mp4", f"{dur('promo.mp4'):.1f}s")
