"""Concat segments in ORDER, add ducked BGM (muted during watch moments), normalize, export."""
import subprocess, json, sys
from segments import ORDER, FIN
def dur(p): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],capture_output=True,text=True).stdout)
files = [FIN/f"seg_{n}.mp4" for n in ORDER]
ins, fc, t, mute = [], "", 0.0, []
for i, f in enumerate(files):
    ins += ["-i", str(f)]; d = dur(f)
    fc += f"[{i}:v]fps=30,scale=1920:1080,setsar=1,format=yuv420p[v{i}];[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{d:.3f}[a{i}];"
    if ORDER[i].startswith("W"): mute.append([t, t + d])
    t += d
fc += "".join(f"[v{i}][a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=1:a=1[v][a]"
subprocess.run(["ffmpeg","-y","-loglevel","error",*ins,"-filter_complex",fc,"-map","[v]","-map","[a]","-c:v","libx264","-crf","17","-preset","medium","-c:a","pcm_s16le",str(FIN/"cat.mkv")], check=True)
D = dur(FIN/"cat.mkv"); print("total", round(D, 2), "mute", mute)
subprocess.run(["python3","bgm.py",f"{D}",str(FIN/"bgm.wav"),json.dumps(mute)], check=True)
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(FIN/"cat.mkv"),"-vn","-af","apad=pad_dur=4,loudnorm=I=-15:TP=-1.5:LRA=9","-ar","48000",str(FIN/"voice_norm.wav")], check=True)
out = FIN/sys.argv[1]
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(FIN/"cat.mkv"),"-i",str(FIN/"voice_norm.wav"),"-i",str(FIN/"bgm.wav"),"-filter_complex",
  "[1:a]asplit=2[vo][sc];[2:a]volume=1.3[bg];[bg][sc]sidechaincompress=threshold=0.08:ratio=2.5:attack=20:release=400:makeup=1[duck];"
  f"[vo][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89,atrim=0:{D:.3f}[a]",
  "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",str(out)], check=True)
print("done", out)
