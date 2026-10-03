"""Assemble 娜乌斯嘉AI episode: per-segment base composition + overlay + SFX, then concat."""
import json, subprocess, pathlib, sys, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
from playwright.sync_api import sync_playwright

import os
ROOT = pathlib.Path(os.environ.get("NANA_ROOT", pathlib.Path(__file__).resolve().parents[2])); PK = pathlib.Path(__file__).resolve().parent; FIN = ROOT / "final"; FIN.mkdir(exist_ok=True)
U = pathlib.Path(os.environ.get("NANA_CLIPS", ROOT / "clips"))   # 口播片段放这里（不随仓库开源）
CHROME = os.environ.get("CHROME_PATH") or None   # 不设则用 Playwright 自带的 Chromium
YEL, PINK, MINT, LIL, PEACH, CREAM, INK = "#FFD84D", "#FF6FA8", "#5FD3B3", "#B9A7FF", "#FFB38A", "#FFF4EA", "#3B2340"
V1_INTRO, V2_INTRO = ROOT/"out/nausicaa_intro.mp4", ROOT/"out/nausicaa_v2.mp4"
F1, F2 = ROOT/"koubo/../out/案例二_原理图_v1.mp4", ROOT/"out/案例二_原理图_v2.mp4"
H1, H2 = ROOT/"koubo/案例三_花字_v1.mp4", ROOT/"koubo/案例三_花字_v2_左侧.mp4"

CASE = dict(slot=dict(x=470, y=150, w=1090, h=613), avatar=dict(cx=215, cy=858, r=150), subX=1035, subSize=58)
SPLIT_SLOTS = [dict(x=60, y=262, w=740, h=416), dict(x=860, y=262, w=740, h=416)]
def run(*a, **k): subprocess.run(a, check=True, **k)
def dur(p): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],capture_output=True,text=True).stdout)

def trim(src, keeps, out):
    """keep list of (a,b) ranges from src video+audio."""
    parts = "".join(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps=30,scale=1280:720[v{i}];[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={b-a-.04:.3f}:d=0.04[a{i}];" for i,(a,b) in enumerate(keeps))
    cat = "".join(f"[v{i}][a{i}]" for i in range(len(keeps)))
    run("ffmpeg","-y","-loglevel","error","-i",str(src),"-filter_complex",parts+cat+f"concat=n={len(keeps)}:v=1:a=1[v][a]","-map","[v]","-map","[a]","-c:v","libx264","-crf","16","-c:a","aac","-b:a","192k",str(out))
def remap(t, keeps):
    acc = 0
    for a, b in keeps:
        if t < a: return acc
        if t <= b: return acc + t - a
        acc += b - a
    return acc

def write_cfg(cfg):
    (PK/"cfg.js").write_text("window.CFG=" + json.dumps(cfg, ensure_ascii=False, default=str) + ";", encoding="utf-8")

def render_layer(cfg, layer, out_png=None, base=None, out=None):
    write_cfg(cfg)
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": CHROME} if CHROME else {}))
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((PK/"pack.html").as_uri() + f"?layer={layer}")
        pg.wait_for_function("!!(window.SCENE && window.seek)")
        if layer == "bg":
            pg.screenshot(path=str(out_png)); b.close(); return
        fps = 30; n = int(cfg["dur"] * fps)
        ff = subprocess.Popen(["ffmpeg","-y","-loglevel","error","-i",str(base),"-f","image2pipe","-framerate",str(fps),"-i","-",
            "-filter_complex","[0:v]fps=30,scale=1920:1080,setsar=1[b];[1:v]format=rgba[o];[b][o]overlay=0:0:shortest=1,format=yuv420p[v]",
            "-map","[v]","-map","0:a?","-c:v","libx264","-crf","17","-preset","medium","-c:a","copy",str(out)], stdin=subprocess.PIPE)
        for i in range(n):
            pg.evaluate(f"window.seek({i/fps})")
            ff.stdin.write(pg.screenshot(type="png", omit_background=True))
        ff.stdin.close(); ff.wait(); b.close()

def compose_base(cfg, voice, out):
    """bg png + slot clips + circular avatar cropped from voice clip; audio = voice."""
    bgpng = FIN/"tmp_bg.png"; render_layer(cfg, "bg", out_png=bgpng)
    D = cfg["dur"]; ins = ["-loop","1","-t",f"{D}","-i",str(bgpng),"-i",str(voice)]; fc = []; last = "0:v"; k = 2
    for si, s in enumerate(cfg["slots"]):
        for ci, cl in enumerate(s["clips"]):
            path, t0, t1 = cl[:3]; ss = cl[3] if len(cl) > 3 else 0
            ins += ["-stream_loop","-1","-ss",f"{ss}","-i",str(path)]
            L = min(t1, D) - t0
            fc.append(f"[{k}:v]fps=30,scale={s['w']}:{s['h']},setsar=1,trim=0:{L:.3f},setpts=PTS-STARTPTS+{t0}/TB[c{k}]")
            fc.append(f"[{last}][c{k}]overlay={s['x']}:{s['y']}:eof_action=pass:enable='between(t,{t0},{t1})'[o{k}]"); last = f"o{k}"; k += 1
    a = cfg["avatar"]; r = a["r"]; d = 2*r
    fc.append(f"[1:v]crop=440:440:380:24,scale={d}:{d},format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(hypot(X-{r},Y-{r}),{r-1}),255,0)'[av]")
    fc.append(f"[{last}][av]overlay={a['cx']-r}:{a['cy']-r},format=yuv420p[v]")
    run("ffmpeg","-y","-loglevel","error",*ins,"-filter_complex",";".join(fc),"-map","[v]","-map","1:a","-t",f"{D}","-r","30",
        "-c:v","libx264","-crf","16","-c:a","aac","-b:a","192k",str(out))

# ---------------- SFX ----------------
SR = 48000; rng = np.random.default_rng(9)
def ar(d): return np.arange(int(d*SR))/SR
def pop(f=800): x=ar(.09); return np.sin(2*np.pi*(f+f*2*np.exp(-x*60))*x)*np.exp(-x*45)
def mar(m,d=.35): x=ar(d); f=440*2**((m-69)/12); return (np.sin(2*np.pi*f*x)+.3*np.sin(2*np.pi*4*f*x)*np.exp(-x*30))*np.exp(-x*9)
def boing(): x=ar(.35); f=300+500*x/.35+40*np.sin(2*np.pi*14*x); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*6)
def slap():
    x=ar(.45); n=rng.standard_normal(len(x))
    crack=sosfilt(butter(2,[1200,7000],'band',fs=SR,output='sos'),n)*np.exp(-x*55)
    body=np.sin(2*np.pi*(95+140*np.exp(-x*40))*x)*np.exp(-x*16)
    tail=sosfilt(butter(2,[300,1500],'band',fs=SR,output='sos'),n)*np.exp(-x*22)*.35
    return np.tanh(2.5*(crack*1.3+body+tail))
def whoosh(d=.35):
    x=ar(d); n=rng.standard_normal(len(x)); k=x/d; o=np.zeros_like(x)
    for i,(a,b) in enumerate([(300,900),(900,2500),(2500,7000)]): o+=sosfilt(butter(2,[a,b],'band',fs=SR,output='sos'),n)*np.clip(1-abs(k*3-i-.5)/1.2,0,1)
    return o*np.sin(np.pi*k)
def stamp(): x=ar(.3); return np.tanh(3*np.sin(2*np.pi*(70+80*np.exp(-x*30))*x)*np.exp(-x*14))+sosfilt(butter(2,[800,4000],'band',fs=SR,output='sos'),rng.standard_normal(len(x)))*np.exp(-x*40)*.4
def sfx_for(cfg, out):
    N = int(cfg["dur"]*SR)+SR; o = np.zeros(N)
    def put(s,t,g):
        i=int(max(0,t)*SR); n=min(len(s),N-i); o[i:i+n]+=s[:n]*g
    for s in cfg.get("stickers",[])+cfg.get("bubbles",[]): put(pop(700+rng.integers(0,500)),s["t0"],.5); put(mar(84),s["t0"]+.02,.22)
    for g in cfg.get("tags",[]):
        if g.get("t0",0) > .2: put(pop(900),g["t0"],.4); put(whoosh(.25),g["t0"]-.15,.25)
    for s in cfg.get("stamps",[]): put(slap(),s["t0"]+.1,.95)
    for c in cfg.get("cards",[]):
        put(pop(600),c["t0"],.45)
        for j,(t,_) in enumerate(c["items"]): put(mar(76+[0,2,4,7,9,12][j%6]),t,.28)
    if cfg.get("mascot"):
        for a,b,m in cfg["mascot"]["acts"]: put(boing(),a-.1,.35)
    put(whoosh(.4),0,.35)
    o = o[:int(cfg["dur"]*SR)]
    wavfile.write(str(out), SR, (np.stack([o,o],1)*0.9*32767).clip(-32767,32767).astype(np.int16))

def mix(video, sfx, out):
    run("ffmpeg","-y","-loglevel","error","-i",str(video),"-i",str(sfx),"-filter_complex","[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
        "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k",str(out))

def build(seg):
    name = seg["name"]; print("==", name, flush=True)
    voice = FIN/f"voice_{name}.mp4"
    keeps = seg.get("keeps")
    if seg["layout"] == "watch":
        a0, a1 = seg["range"]; keeps = [(a0, a1)]
        run("ffmpeg","-y","-loglevel","error","-ss",f"{a0}","-t",f"{a1-a0}","-i",str(seg["src"]),"-vf","fps=30,scale=1920:1080,setsar=1","-c:v","libx264","-crf","16","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(voice))
        seg = dict(seg, subs=[], tight=False); keeps=[(0, a1-a0)]
    elif seg.get("tight", True) and seg.get("layout"):
        ph = [x for x in json.load(open(FIN/f"asr_{name}.json")) if x["text"].strip() not in ("嗯","啊","呃","嗯嗯")]
        tot = dur(seg["src"]); keeps = []
        for i, x in enumerate(ph):
            a = max(0, x["start"]-0.12); b = min(tot, x["end"] + (seg.get("tail", 0.18) if i == len(ph)-1 else 0.15))
            if keeps and a <= keeps[-1][1]: keeps[-1] = (keeps[-1][0], b)
            else: keeps.append((a, b))
        print("   keeps", [(round(a,2),round(b,2)) for a,b in keeps], flush=True)
    if seg["layout"] == "watch": pass
    elif keeps: trim(seg["src"], keeps, voice)
    else: run("ffmpeg","-y","-loglevel","error","-i",str(seg["src"]),"-vf","fps=30,scale=1280:720","-c:v","libx264","-crf","16","-c:a","aac","-b:a","192k",str(voice)); keeps=[(0,dur(seg["src"]))]
    D = round(dur(voice), 3)
    R = lambda t: round(remap(t, keeps), 3)
    cfg = dict(dur=D, title=seg.get("title"), subX=seg.get("subX", 860), subSize=seg.get("subSize", 66))
    cfg["subs"] = [[R(a), R(b), txt, hl] for a, b, txt, *rest in seg["subs"] for hl in [rest[0] if rest else []]]
    for key in ("stickers","stamps","bubbles"):
        cfg[key] = [dict(x, t0=R(x["t0"]), t1=R(x["t1"]) if x.get("t1") is not None else D) for x in seg.get(key, [])]
    cfg["tags"] = [dict(x, t0=R(x.get("t0",0)), t1=R(x["t1"]) if x.get("t1") is not None else D+1) for x in seg.get("tags", [])]
    cfg["cards"] = [dict(c, t0=R(c["t0"]), t1=R(c["t1"]) if c.get("t1") is not None else D+1, items=[[R(t),s] for t,s in c["items"]]) for c in seg.get("cards", [])]
    if seg.get("mascot"): cfg["mascot"] = dict(x=seg["mascot"]["x"], acts=[[R(a), R(b) if b is not None else D+1, m] for a,b,m in seg["mascot"]["acts"]])
    base = FIN/f"base_{name}.mp4"
    if seg["layout"] in ("full", "watch"):
        base = voice
    else:
        if seg["layout"] == "case":
            cfg.update(avatar=CASE["avatar"], subX=CASE["subX"], subSize=CASE["subSize"])
            cfg["slots"] = [dict(CASE["slot"], clips=[(c[0], R(c[1]), R(c[2]) if c[2] is not None else D, *(c[3:])) for c in seg["clips"]])]
        else:
            cfg.update(avatar=CASE["avatar"], subX=1100, subSize=CASE["subSize"])
            cfg["slots"] = [dict(SPLIT_SLOTS[i], clips=[(c[0], 0, D, c[1]) if isinstance(c, tuple) else (c, 0, D)]) for i,c in enumerate(seg["clips"])]
        compose_base(cfg, voice, base)
    over = FIN/f"over_{name}.mp4"; render_layer(cfg, "top", base=base, out=over)
    sfx = FIN/f"sfx_{name}.wav"; sfx_for(cfg, sfx)
    if seg.get("endcard"):
        ec = seg["endcard"]; t0 = R(ec["t0"]); mixed = FIN/f"mix_{name}.mp4"; mix(over, sfx, mixed)
        run("ffmpeg","-y","-loglevel","error","-i",str(mixed),"-itsoffset",f"{t0}","-i",str(ec["file"]),
            "-filter_complex",f"[1:v]scale=iw*{ec.get('scale',1)}:-1,format=rgba[e];[0:v][e]overlay={ec['x']}:{ec['y']}:eof_action=repeat,format=yuv420p[v]",
            "-map","[v]","-map","0:a","-c:v","libx264","-crf","16","-c:a","copy",str(FIN/f"seg_{name}.mp4"))
    else:
        mix(over, sfx, FIN/f"seg_{name}.mp4")
    print("   ok", D, flush=True)

if __name__ == "__main__":
    from segments import SEGS
    only = sys.argv[1:]
    for s in SEGS:
        if not only or s["name"] in only: build(s)
