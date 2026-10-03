"""Offline Chinese speech recognition with a Paraformer ONNX model, numpy-only features.
Splits audio at pauses so every phrase gets a start/end time (enough to time on-screen captions).
Usage: python3 asr.py input.(mp4|wav) [model_dir] > out.json
"""
import sys, json, subprocess, numpy as np, onnxruntime as ort, pathlib

import os
MODEL = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ASR_MODEL", "asr_model"))
SR = 16000

def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32)  # int16 scale, as Kaldi expects

def mel_banks(n_mels=80, n_fft=512, lo=20.0, hi=SR / 2):
    mel = lambda f: 1127.0 * np.log(1 + f / 700.0)
    m_lo, m_hi = mel(lo), mel(hi)
    centers = np.linspace(m_lo, m_hi, n_mels + 2)
    fft_mel = mel(np.arange(n_fft // 2) * SR / n_fft)
    W = np.zeros((n_mels, n_fft // 2 + 1), np.float32)
    for i in range(n_mels):
        l, c, r = centers[i:i + 3]
        up = (fft_mel - l) / (c - l); down = (r - fft_mel) / (r - c)
        W[i, :n_fft // 2] = np.maximum(0, np.minimum(up, down))
    return W

MEL = mel_banks()
WIN = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(400) / 399)) ** 0.85  # povey

def fbank(x):
    if len(x) < 400: x = np.pad(x, (0, 400 - len(x)))
    n = 1 + (len(x) - 400) // 160
    idx = np.arange(400)[None, :] + 160 * np.arange(n)[:, None]
    f = x[idx].astype(np.float64)
    f -= f.mean(1, keepdims=True)
    f = np.concatenate([f[:, :1] - 0.97 * f[:, :1], f[:, 1:] - 0.97 * f[:, :-1]], 1)
    f *= WIN
    spec = np.abs(np.fft.rfft(f, 512)) ** 2
    return np.log(np.maximum(spec @ MEL.T, np.finfo(np.float32).eps)).astype(np.float32)

class Paraformer:
    def __init__(self, d):
        self.s = ort.InferenceSession(str(d / "model.int8.onnx"))
        meta = self.s.get_modelmeta().custom_metadata_map
        self.neg_mean = np.array(meta["neg_mean"].split(","), np.float32)
        self.inv_std = np.array(meta["inv_stddev"].split(","), np.float32)
        self.m, self.n = int(meta["lfr_window_size"]), int(meta["lfr_window_shift"])
        self.tok = [l.rsplit(" ", 1)[0] for l in open(d / "tokens.txt", encoding="utf-8").read().splitlines()]

    def lfr(self, F):
        pad = np.repeat(F[:1], (self.m - 1) // 2, 0); F = np.concatenate([pad, F])
        T = int(np.ceil(F.shape[0] / self.n)); out = []
        for i in range(T):
            seg = F[i * self.n:i * self.n + self.m]
            if len(seg) < self.m: seg = np.concatenate([seg, np.repeat(F[-1:], self.m - len(seg), 0)])
            out.append(seg.reshape(-1))
        return np.stack(out)

    def __call__(self, x):
        X = (self.lfr(fbank(x)) + self.neg_mean) * self.inv_std
        logits, num = self.s.run(None, {"speech": X[None].astype(np.float32),
                                        "speech_lengths": np.array([X.shape[0]], np.int32)})
        ids = logits[0].argmax(-1)[:int(num[0])]
        out = ""
        for i in ids:
            t = self.tok[i]
            if t in ("<blank>", "<s>", "</s>", "<OOV>"): continue
            if t.endswith("@@"): out += t[:-2]
            elif t.isascii(): out += t + " "
            else: out += t
        return out.strip()

def phrases(x, min_gap=0.28, thr_db=-38):
    """Energy VAD: returns (start,end) seconds of speech chunks separated by pauses."""
    hop = 160; e = np.array([np.sqrt(np.mean((x[i:i + 400] / 32768) ** 2) + 1e-10) for i in range(0, len(x) - 400, hop)])
    db = 20 * np.log10(e); speech = db > max(thr_db, db.max() - 35)
    segs, start, silence = [], None, 0
    for i, s in enumerate(speech):
        if s:
            if start is None: start = i
            silence = 0
        elif start is not None:
            silence += 1
            if silence * hop / SR >= min_gap:
                segs.append((start, i - silence + 1)); start = None; silence = 0
    if start is not None: segs.append((start, len(speech)))
    return [(a * hop / SR, b * hop / SR) for a, b in segs if (b - a) * hop / SR > 0.15]

if __name__ == "__main__":
    x = load_audio(sys.argv[1]); asr = Paraformer(MODEL); res = []
    for a, b in phrases(x):
        seg = x[max(0, int((a - .08) * SR)):int((b + .08) * SR)]
        txt = asr(seg)
        if txt: res.append({"start": round(a, 2), "end": round(b, 2), "text": txt})
    print(json.dumps(res, ensure_ascii=False, indent=1))
