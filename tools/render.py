"""Render a code-driven HTML animation to video.

Each scene HTML must define:
  window.SCENE = {w, h, fps, duration}
  window.seek(t)  -> draws the frame at time t (seconds), deterministic
Usage: python3 render.py scenes/xxx.html out/xxx.mp4 [audio.wav]
"""
import sys, subprocess, pathlib, json
from playwright.sync_api import sync_playwright

import os
CHROME = os.environ.get("CHROME_PATH") or None

def render(html, out, audio=None):
    html = pathlib.Path(html).resolve()
    out = pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"], **({"executable_path": CHROME} if CHROME else {}))
        pg = b.new_page()
        pg.goto(html.as_uri())
        pg.wait_for_function("!!(window.SCENE && window.seek)")
        sc = pg.evaluate("window.SCENE")
        pg.set_viewport_size({"width": sc["w"], "height": sc["h"]})
        pg.evaluate("document.fonts.ready")
        n = int(round(sc["duration"] * sc["fps"]))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(sc["fps"]),
               "-i", "-"]
        if audio:
            cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-shortest"]
        vf = ["-vf", "tblend=all_mode=average,framestep=2"] if sc["fps"] >= 60 else []
        cmd += vf + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium",
                "-movflags", "+faststart", str(out)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            pg.evaluate(f"window.seek({i / sc['fps']})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
        ff.stdin.close(); ff.wait()
        b.close()
    print(json.dumps({"out": str(out), "frames": n, **sc}))

if __name__ == "__main__":
    render(*sys.argv[1:])
