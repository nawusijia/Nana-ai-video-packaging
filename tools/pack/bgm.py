"""Tech-pop background track with an arrangement (code-synthesized).
Sections rotate: A (groove) -> B (lead melody + busier drums) -> breakdown (pads + bells, riser) -> A' (counter-melody) ...
Usage: python3 bgm.py seconds out.wav [mute_ranges_json]"""
import sys, json, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
SR = 48000; D = float(sys.argv[1]); N = int(D*SR); o = np.zeros((N, 2)); rng = np.random.default_rng(4)
BPM = 112; beat = 60/BPM; s16 = beat/4; BAR = 4*beat
def ar(d): return np.arange(int(d*SR))/SR
def hz(m): return 440*2**((m-69)/12)
def put(s, t, g, pan=0.0):
    i = int(t*SR); n = min(len(s), N-i)
    if n <= 0 or i < 0: return
    l, r = np.cos((pan+1)*np.pi/4), np.sin((pan+1)*np.pi/4)
    o[i:i+n, 0] += s[:n]*g*l; o[i:i+n, 1] += s[:n]*g*r
def lp(x, f): return sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
def hp(x, f): return sosfilt(butter(2, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], 'band', fs=SR, output='sos'), x)
def saw(f, x): return 2*((x*f) % 1) - 1
def sq(f, x): return np.sign(np.sin(2*np.pi*f*x))
# ---- drums
def kick(): x = ar(.35); return hp(np.sin(2*np.pi*(45*x + 110/30*(1-np.exp(-x*30))))*np.exp(-x*9), 50)
def clap():
    x = ar(.22); n = rng.standard_normal(len(x))
    return bp(n, 900, 5000)*(np.exp(-x*30) + .5*np.exp(-np.abs(x-.012)*400) + .4*np.exp(-np.abs(x-.024)*400))
def snare(): x = ar(.18); return bp(rng.standard_normal(len(x)), 1500, 8000)*np.exp(-x*25) + np.sin(2*np.pi*200*x)*np.exp(-x*30)*.5
def hat(op=False): x = ar(.2 if op else .05); return hp(rng.standard_normal(len(x)), 8000)*np.exp(-x*(16 if op else 90))
def tom(m): x = ar(.25); return np.sin(2*np.pi*hz(m)*(1+.3*np.exp(-x*20))*x)*np.exp(-x*12)
def crash(): x = ar(2.2); return hp(rng.standard_normal(len(x)), 5000)*np.exp(-x*1.8)
def riser(d):
    x = ar(d); k = x/d; n = rng.standard_normal(len(x))
    return (bp(n, 400, 9000)*k**2*.7 + np.sin(2*np.pi*np.cumsum(200+1800*k**2)/SR)*k**3*.25)
# ---- tonal
def sub(m, d): x = ar(d); f = hz(m); return hp((np.sin(2*np.pi*f*x)+.25*np.sin(2*np.pi*2*f*x))*np.minimum(1, x*200)*np.exp(-x*2.5), 45)
def arp(m, d, cut): x = ar(d); f = hz(m); return lp(saw(f, x)*.6 + saw(f*1.005, x)*.4, cut)*np.exp(-x*14)*np.minimum(1, x*300)
def pad(ch, d, cut=1400):
    x = ar(d); s = sum(saw(hz(m)*k, x) for m in ch for k in (0.997, 1.003))
    return lp(s/len(ch)/2, cut)*np.minimum(1, x/0.6)*np.minimum(1, np.maximum(d-x, 0)/0.6)
def bell(m, d=1.0):
    x = ar(d); f = hz(m)
    return sum(a*np.sin(2*np.pi*f*r*x)*np.exp(-x*k) for r, a, k in [(1, 1, 3), (2.76, .35, 6), (5.4, .15, 9)])*np.minimum(1, x*800)
def lead(m, d):   # bright pluck lead
    x = ar(d); f = hz(m); s = sq(f, x)*.5 + saw(f*1.003, x)*.5
    e = np.exp(-x*12); return (lp(s, 6000)*e + lp(s, 2500)*(1-e))*np.exp(-x*5)*np.minimum(1, x*400)
def keys(m, d):   # glassy FM keys
    x = ar(d); f = hz(m); return np.sin(2*np.pi*f*x + 1.6*np.exp(-x*6)*np.sin(2*np.pi*2*f*x))*np.exp(-x*3.5)*np.minimum(1, x*600)

PROG_A = [(45, [57, 60, 64, 67]), (41, [57, 60, 65, 69]), (48, [55, 60, 64, 67]), (43, [55, 59, 62, 67])]   # Am F C G
PROG_B = [(41, [57, 60, 65, 69]), (43, [55, 59, 62, 67]), (40, [55, 59, 64, 67]), (45, [57, 60, 64, 69])]   # F G Em Am
ARP1 = [0, 2, 1, 3, 2, 1, 3, 2]; ARP2 = [0, 3, 2, 3, 1, 3, 2, 3]
LEAD = [[(0, 76, 2), (3, 79, 1), (4, 81, 3), (8, 79, 2), (10, 76, 2), (12, 74, 4)],
        [(0, 72, 2), (2, 74, 2), (4, 76, 3), (8, 79, 2), (11, 77, 1), (12, 76, 4)],
        [(0, 76, 2), (3, 79, 1), (4, 84, 3), (8, 83, 2), (10, 79, 2), (12, 81, 4)],
        [(0, 79, 3), (4, 76, 2), (6, 74, 2), (8, 72, 4), (12, 74, 4)]]
COUNTER = [88, 86, 84, 83, 81, 83, 84, 86]
PLAN = ["A"]*8 + ["B"]*8 + ["D"]*4 + ["A2"]*8 + ["B"]*8 + ["D"]*4      # 40-bar cycle, then repeat

bar = 0; t = 0.0
while t < D:
    sec = PLAN[bar % len(PLAN)]; ib = bar % len(PLAN); nxt = PLAN[(ib+1) % len(PLAN)]
    prog = PROG_B if sec == "B" else PROG_A
    root, ch = prog[bar % 4]
    first_of_sec = ib == 0 or PLAN[ib-1] != sec
    last_of_sec = nxt != sec
    if first_of_sec and bar > 0: put(crash(), t, .16, -.2)
    # pad
    put(pad(ch, BAR+.3, 900 if sec == "D" else 1500), t, .34 if sec == "D" else .26)
    for k in range(16):
        tt = t + k*s16
        if tt >= D: break
        if sec != "D":
            if k in (0, 4, 8, 12): put(kick(), tt, .22)
            if k in (4, 12): put(clap(), tt, .42, .1)
            if sec == "B" and k in (7, 15): put(snare(), tt, .12, -.1)
            if k % 2 == 1: put(hat(), tt, .30 if sec != "B" else .36, .35)
            if sec == "B" and k % 4 == 2: put(hat(True), tt, .16, -.3)
            elif k == 14: put(hat(True), tt, .2, .35)
            bass_steps = (0, 3, 6, 8, 11, 14) if sec != "B" else (0, 2, 3, 6, 8, 10, 11, 14)
            if k in bass_steps: put(sub(root-12, s16*2.0), tt, .12)
            pat = ARP2 if sec == "B" else ARP1
            oct_ = 12 if (sec != "B" or k % 4) else 24
            put(arp(ch[pat[k % 8]] + oct_, .14, 4200), tt, .30 if sec != "B" else .24, -.35 + .7*((k % 4)/3))
            # drum fill into the next section
            if last_of_sec and k >= 12: put(tom(52 - (k-12)*3), tt, .25, (k-13.5)*.2)
        else:
            # breakdown: filtered arp opening up, bells
            cut = 900 + 2500*((bar % 4) + k/16)/4
            if k % 2 == 0: put(arp(ch[ARP1[(k//2) % 8]] + 12, .2, cut), tt, .26, -.3 + .6*((k % 8)/7))
            if k in (0, 6, 10): put(bell(ch[(k//4) % 4] + 24, 1.4), tt, .2, .3)
    if sec == "B":
        for st, m, ln in LEAD[bar % 4]: put(lead(m, ln*s16+.08), t + st*s16, .16, .15)
    if sec == "A2":
        for j in range(8): put(keys(COUNTER[(j + bar) % 8], .5), t + j*2*s16, .12, -.25)
    if sec == "A" and bar % 4 == 3:
        for j in range(3): put(bell([76, 79, 81][j], .9), t + (12+j)*s16, .2, .3)
    if last_of_sec and nxt in ("A", "A2") and sec == "D": put(riser(BAR), t, .3)
    t += BAR; bar += 1

tt = np.arange(N)/SR; ph = (tt % beat)/beat
o *= (0.6 + 0.4*np.clip(ph/0.35, 0, 1))[:, None]
o = np.stack([lp(o[:, 0], 10000), lp(o[:, 1], 10000)], 1)
o *= np.clip(tt/0.15, 0, 1)[:, None]*np.clip((D-tt)/2.0, 0, 1)[:, None]
o /= np.abs(o).max(); o *= 10**(-9/20)
if len(sys.argv) > 3:
    env = np.ones(N)
    for a, b in json.loads(sys.argv[3]):
        env = np.minimum(env, np.clip(np.maximum((a - tt)/0.4, (tt - b)/0.4), 0, 1))
    o *= env[:, None]
wavfile.write(sys.argv[2], SR, (o*32767).astype(np.int16))
