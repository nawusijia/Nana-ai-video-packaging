"""Code-synthesized soundtrack for nausicaa_intro (6s), timed to the animation."""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000; DUR = 6.0
t = np.arange(int(SR * DUR)) / SR
out = np.zeros((len(t), 2))
rng = np.random.default_rng(7)

def env(t0, a, d, length=None):
    x = t - t0
    e = np.where(x < 0, 0, np.where(x < a, x / max(a, 1e-4), np.exp(-(x - a) / d)))
    return e

def place(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR); n = min(len(sig), len(t) - i)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    out[i:i + n, 0] += sig[:n] * gain * l
    out[i:i + n, 1] += sig[:n] * gain * r

def lp(x, f): return sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)
def hz(m): return 440 * 2 ** ((m - 69) / 12)

# 1) warm pad: Dmaj9-ish, detuned saws -> lowpass, slow fade in, fade out at end
pad = np.zeros_like(t)
for m in [50, 57, 62, 64, 66, 69]:
    for d in (-0.08, 0.08):
        f = hz(m + d)
        pad += 2 * ((t * f) % 1) - 1
pad = lp(pad / 12, 1400)
pad *= np.clip(t / 1.4, 0, 1) * np.clip((DUR - t) / 0.6, 0, 1) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t))
out[:, 0] += pad * 0.22; out[:, 1] += pad * 0.22

# 2) sub pulse on the beat (88 bpm feel) after card lands
beat = 60 / 88
for k in range(8):
    t0 = 1.3 + k * beat
    if t0 > 5.4: break
    n = int(0.5 * SR); x = np.arange(n) / SR
    kick = np.sin(2 * np.pi * (55 + 60 * np.exp(-x * 30)) * x) * np.exp(-x * 7)
    place(kick, t0, 0.35)

# 3) whoosh as the glass card rises (0.4-1.3s)
n = int(1.1 * SR); x = np.arange(n) / SR
noise = rng.standard_normal(n)
sweep = np.zeros(n)
for j, (lo, hi) in enumerate([(300, 900), (900, 2500), (2500, 6000)]):
    seg = bp(noise, lo, hi)
    sweep += seg * np.clip(np.sin(np.pi * np.clip(x / 1.1 - j * 0.12, 0, 1)), 0, 1)
place(sweep / 3, 0.35, 0.28)

# 4) typing ticks, one per character (mirrors typed() timings)
L1, L2, cps = 11, 7, 14
t2 = 1.25 + L1 / cps + 0.15
for i in range(L1): times = None
ticks = [1.25 + i / cps for i in range(L1)] + [t2 + i / cps for i in range(L2)]
for i, t0 in enumerate(ticks):
    n = int(0.04 * SR); x = np.arange(n) / SR
    s = bp(rng.standard_normal(n), 2500, 7000) * np.exp(-x * 160)
    s += np.sin(2 * np.pi * (1800 + 200 * (i % 3)) * x) * np.exp(-x * 220) * 0.4
    place(s, t0, 0.16, pan=((i % 5) - 2) * 0.15)

# 5) bell chime when the gradient rule draws (3.3s) and sparkle on brand (3.9s)
def bell(f, length=2.2):
    n = int(length * SR); x = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * dk) for r, a, dk in
            [(1, 1, 2.2), (2.01, .45, 3.5), (3.02, .25, 5), (4.17, .12, 7)])
    return s * np.minimum(x / 0.004, 1)
for f, t0, p in [(hz(81), 3.3, -.3), (hz(85), 3.42, 0), (hz(88), 3.54, .3)]:
    place(bell(f) * np.clip((DUR - 0.1 - (t0 + np.arange(int(2.2 * SR)) / SR)) / 0.5, 0, 1), t0, 0.10, p)
for i in range(6):
    place(bell(hz(93 + (i * 5) % 9), 0.8), 3.9 + i * 0.05, 0.045, (i - 2.5) * 0.25)

# simple stereo reverb-ish: a few delayed, filtered taps
wet = np.zeros_like(out)
for dly, g in [(0.031, .35), (0.047, .3), (0.071, .25), (0.113, .2), (0.167, .15)]:
    k = int(dly * SR)
    wet[k:, 0] += lp(out[:-k, 1], 4000) * g
    wet[k:, 1] += lp(out[:-k, 0], 4000) * g
out = out + wet * 0.6
out *= np.clip((DUR - t) / 0.5, 0, 1)[:, None]
out /= np.max(np.abs(out)) / 0.89
wavfile.write("out/nausicaa_intro.wav", SR, (out * 32767).astype(np.int16))
print("ok")
