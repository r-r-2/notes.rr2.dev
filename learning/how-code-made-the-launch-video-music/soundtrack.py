"""The 16-second soundtrack of the notes.rr2.dev launch video, made only from numbers.
120 BPM. 0-2.5 s thinking (tick-tock), 2.5 s light-bulb ding, 3.5 s the beat starts,
whooshes for the pushed posts, a slide whistle down the rope, small bells for the
filters and dark mode, and a big C chord under the end card at 13.5 s.
Needs: numpy, scipy. Writes soundtrack.wav."""
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR, DUR, BPM = 44100, 16.0, 120
BEAT = 60 / BPM
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)

def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR); j = min(N, i + len(sig))
    if i >= N: return
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i:j] += sig[: j - i] * gain * l * 1.414; R[i:j] += sig[: j - i] * gain * r * 1.414

def tt(sec): return np.arange(int(sec * SR)) / SR
def hz(note): return 440 * 2 ** ((note - 69) / 12)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, btype="high", fs=SR, output="sos"), x)

def marimba(note, length=1.2, bright=1.0):   # the marimba-like note
    t = tt(length); f = hz(note)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2)
         + 0.28 * bright * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 13)
         + 0.07 * bright * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 32))
    s *= np.minimum(1, t / 0.002)
    s[: int(0.004 * SR)] += rng.normal(0, 0.15, int(0.004 * SR)) * np.linspace(1, 0, int(0.004 * SR))
    return s

def glock(note, length=2.5):
    t = tt(length); f = hz(note)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 4)) * np.exp(-t * 1.6) * np.minimum(1, t / 0.001)

def kick():
    t = tt(0.35); f = 48 + 110 * np.exp(-t * 38)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

def clap():
    out = np.zeros(int(0.25 * SR))
    for k, off in enumerate((0, 0.011, 0.022)):
        b = rng.normal(0, 1, int(0.009 * SR)) * np.linspace(1, 0.3, int(0.009 * SR)); i = int(off * SR)
        out[i:i + len(b)] += b * (0.8 if k < 2 else 1)
    tail = rng.normal(0, 1, len(out)) * np.exp(-tt(0.25) * 22); out[int(0.022 * SR):] += 0.6 * tail[: len(out) - int(0.022 * SR)]
    return bp(out, 900, 2600)

def shaker(): return hp(rng.normal(0, 1, int(0.06 * SR)) * np.exp(-tt(0.06) * 70), 6000)

def whoosh(length=0.35):
    t = tt(length); env = np.sin(np.pi * t / length) ** 2
    return bp(rng.normal(0, 1, len(t)), 500, 3500) * env

def slide_whistle(t0, t1, f0, f1):
    t = tt(t1 - t0); f = np.geomspace(f0, f1, len(t)) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t))
    env = np.minimum(1, t / 0.06) * np.minimum(1, (t[-1] - t) / 0.12)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.15 * np.sin(4 * np.pi * np.cumsum(f) / SR)) * env

def wood(pitch=1.0):
    t = tt(0.12); f = 820 * pitch
    return (np.sin(2*np.pi*f*t) + 0.4*np.sin(2*np.pi*f*2.7*t)) * np.exp(-t*55)

C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, G5, A5, C6, E6, G6 = 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 79, 81, 84, 88, 91
# 0-2.5 s: thinking. Tick-tock under a few curious notes.
for k in range(5): add(wood(1.0 if k % 2 == 0 else 0.75), 0.25 + k * BEAT, 0.28, 0.3 if k % 2 else -0.3)
for t, n in ((0.5, E5), (1.0, D5), (1.5, F4 + 12), (2.0, E5)): add(marimba(n, 0.9, 0.5), t, 0.2, 0.15)
# 2.5 s: the idea. Bright ding with a sparkle.
add(glock(C6, 2.0), 2.5, 0.32, 0.1); add(glock(G6, 1.6), 2.56, 0.16, 0.35); add(glock(E6, 1.4), 2.62, 0.12, -0.3)
# 2.75-3.5 s: a quick run up into the drop
for k, n in enumerate([C5, D5, E5, G5, A5, C6]): add(marimba(n, 0.5), 2.94 + k * 0.09, 0.22 + 0.02 * k, -0.3 + 0.12 * k)
# 3.5-11.5 s: the groove, four bars
CH = {3.5: (48, [C5, E5, G5, E5, C5, G4, E5, G5]), 5.5: (43, [B4, D5, G5, D5, B4, G4, D5, G5]),
      7.5: (45, [C5, E5, A5, E5, C5, A4, E5, A5]), 9.5: (41, [A4, C5, F4 + 12, C5, A4, F4, C5, F4 + 12]),
      11.5: (43, [B4, D5, G5, D5, B4, D5, G5, B4 + 12])}
for t0, (bass, arp) in CH.items():
    for k, n in enumerate(arp):
        add(marimba(n, 0.9), t0 + k * BEAT / 2, 0.30 if k % 2 == 0 else 0.22, -0.35 if k % 2 else 0.35)
    add(marimba(bass, 1.6, 0.4), t0, 0.55); add(marimba(bass, 1.0, 0.4), t0 + 2 * BEAT, 0.4)
    for b in range(4):
        t = t0 + b * BEAT
        if b in (0, 2): add(kick(), t, 0.85)
        if b in (1, 3): add(clap(), t, 0.42, 0.1)
        add(shaker(), t + BEAT / 2, 0.10, -0.3); add(shaker(), t, 0.05, 0.3)
add(whoosh(0.5), 3.3, 0.22, 0.5)                                   # the wipe
for t in (4.18, 5.18): add(whoosh(), t, 0.30, -0.4)               # posts pushed away
add(slide_whistle(0, 1.5, 1300, 420), 6.15, 0.14, 0.15)           # down the rope
for t, n in ((8.1, E6), (9.1, G6)): add(glock(n, 0.8), t, 0.12, 0.3)   # chip taps
add(glock(C6, 0.8), 10.2, 0.14, -0.3)                              # dark mode
add(whoosh(0.3), 10.87, 0.18, 0.4)                                 # cut to the phone
# 13.5 s: end card
for k, n in enumerate([48, C4, E4, G4, C5, E5]): add(marimba(n, 2.6, 0.7), 13.5 + k * 0.035, 0.36, -0.3 + 0.12 * k)
add(glock(C6, 2.5), 13.58, 0.22, 0.2); add(glock(G5, 2.2), 13.95, 0.12, -0.2)

mix = np.stack([L, R], 1)
fade = np.ones(N); f0 = int(15.0 * SR); fade[f0:] = np.linspace(1, 0, N - f0) ** 1.5
fade[: int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR))
mix *= fade[:, None]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 0.89 / np.max(np.abs(mix))
wavfile.write("soundtrack.wav", SR, (mix * 32767).astype(np.int16))
print("ok")
