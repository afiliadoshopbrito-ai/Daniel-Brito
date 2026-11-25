#!/usr/bin/env python3
"""Ferramentas de análise dos clipes brutos.

Uso:
  analyze.py sheet <video> <inicio> <duracao> <fps> <saida.jpg> [colunas]
      Folha de contato com o tempo (s*10) escrito em cada quadro.
      ex.: analyze.py sheet videos/IMG_8818.MOV 60 100 1 s.jpg 16
      Use fps=1 para mapear o clipe e fps=2..4 para achar o instante exato.

  analyze.py peaks <video> <inicio> <fim> [fator=15]
      Lista barulhos curtos e altos (abas estalando, pacote rasgando,
      fita) com o tempo de cada pico. Fator = quantas vezes acima da mediana.

  analyze.py snap <video> <inicio_aprox> <duracao_aprox>
      Para um corte de "barulho": acha o barulho mais forte perto do trecho e
      devolve início/duração para começar ~0,35 s antes e terminar logo
      depois que o som acaba (regra: estalou/rasgou -> corta).

  analyze.py cry <video> [inicio fim]
      Procura choro de bebê (som tonal sustentado 400-1300 Hz).
      Rode em todo clipe novo antes de usar os trechos.
"""
import subprocess
import sys

import numpy as np


def load(path, sr=16000, s=None, d=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error"]
    if s is not None:
        cmd += ["-ss", str(s)]
    if d is not None:
        cmd += ["-t", str(d)]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def sheet(video, s, d, fps, out, cols=16):
    n = int(float(d) * float(fps))
    rows = max(1, -(-n // int(cols)))
    vf = (f"fps={fps},scale=110:196,drawtext=text='%{{eif\\:(t+{s})*10\\:d}}':x=2:y=2:fontsize=14:"
          f"fontcolor=yellow:box=1:boxcolor=black@0.7,tile={cols}x{rows}")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(s), "-t", str(d), "-i", video,
                    "-vf", vf, "-frames:v", "1", out], check=True)
    print(out)


def envelope(a, sr, step):
    st = int(sr * step)
    e = np.array([np.sqrt(np.mean(a[i:i + st] ** 2)) for i in range(0, len(a) - st, st)])
    return e, np.median(e) + 1e-9


def peaks(video, s, e, factor=15):
    sr = 8000
    a = load(video, sr)
    env, med = envelope(a, sr, 0.05)
    out = []
    for k in range(1, len(env) - 1):
        t = k * 0.05
        if s <= t <= e and env[k] >= env[k - 1] and env[k] >= env[k + 1] and env[k] > factor * med:
            out.append((t, env[k] / med))
    sel = []
    for t, v in sorted(out, key=lambda x: -x[1]):
        if all(abs(t - u) > 0.8 for u, _ in sel):
            sel.append((t, v))
    for t, v in sorted(sel):
        print(f"{t:7.2f}s  ({v:.0f}x)")


def snap(video, s, d):
    sr = 8000
    a = load(video, sr)
    env, med = envelope(a, sr, 0.02)
    lo, hi = int((s - 0.2) * 50), int((s + d + 0.4) * 50)
    k = max(range(lo, hi), key=lambda i: env[i])
    thr = max(env[k] * 0.2, med * 4)
    on = k
    while on > lo - 25 and env[on - 1] > thr:
        on -= 1
    off = k
    while off < hi + 50 and env[off + 1] > thr:
        off += 1
    ns, ne = on / 50 - 0.35, off / 50 + 0.1
    ns = min(ns, ne - 0.6)
    print(f"{ns:.2f} {ne - ns:.2f}   (som {on/50:.2f}-{off/50:.2f}, {env[k]/med:.0f}x)")


def cry(video, s=0, e=None):
    sr = 16000
    a = load(video, sr, s, None if e is None else e - s)
    N, hop = 2048, 800
    f = np.fft.rfftfreq(N, 1 / sr)
    band = (f > 250) & (f < 3000)
    hits = []
    for i in range(0, len(a) - N, hop):
        S = np.abs(np.fft.rfft(a[i:i + N] * np.hanning(N))) + 1e-9
        B = S[band]
        flat = np.exp(np.mean(np.log(B))) / np.mean(B)
        E = 10 * np.log10(np.sum(B ** 2) * 32768 ** 2)
        pk = f[band][np.argmax(B)]
        if flat < 0.35 and E > 100 and 400 < pk < 1300:
            hits.append(s + i / sr)
    if not hits:
        print("sem choro detectado")
        return
    runs, start, prev = [], hits[0], hits[0]
    for t in hits[1:]:
        if t - prev > 0.5:
            runs.append((start, prev))
            start = t
        prev = t
    runs.append((start, prev))
    for a_, b_ in runs:
        if b_ - a_ >= 0.3:
            print(f"POSSÍVEL CHORO {a_:.1f}s - {b_:.1f}s  -> evitar esse trecho")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    x = sys.argv[2:]
    if c == "sheet":
        sheet(x[0], x[1], x[2], x[3], x[4], x[5] if len(x) > 5 else 16)
    elif c == "peaks":
        peaks(x[0], float(x[1]), float(x[2]), float(x[3]) if len(x) > 3 else 15)
    elif c == "snap":
        snap(x[0], float(x[1]), float(x[2]))
    elif c == "cry":
        cry(x[0], float(x[1]) if len(x) > 1 else 0, float(x[2]) if len(x) > 2 else None)
    else:
        print(__doc__)
        sys.exit(1)
