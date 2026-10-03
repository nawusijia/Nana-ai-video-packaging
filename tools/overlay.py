"""Render a transparent HTML overlay (window.SCENE/seek like render.py) on top of a video, keeping its audio.
Usage: python3 overlay.py scene.html base.mp4 out.mp4
"""
import sys, subprocess, pathlib, json
from playwright.sync_api import sync_playwright
import os
CHROME = os.environ.get("CHROME_PATH") or None

def main(html, base, out):
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height:format=duration", "-of", "json", base], capture_output=True, text=True).stdout)
    W, H = probe["streams"][0]["width"], probe["streams"][0]["height"]; dur = float(probe["format"]["duration"])
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": CHROME} if CHROME else {}))
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(pathlib.Path(html).resolve().as_uri())
        pg.wait_for_function("!!(window.SCENE && window.seek)")
        fps = pg.evaluate("window.SCENE.fps"); n = int(dur * fps)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
               "-filter_complex", f"[0:v]scale=1920:1080,fps={fps}[b];[1:v]format=rgba[o];[b][o]overlay=0:0:shortest=1,format=yuv420p[v]",
               "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "17", "-c:a", "aac", "-b:a", "192k", out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            pg.evaluate(f"window.seek({i / fps})")
            ff.stdin.write(pg.screenshot(type="png", omit_background=True))
        ff.stdin.close(); ff.wait(); b.close()
    print(out, n, "frames")

if __name__ == "__main__":
    main(*sys.argv[1:])
