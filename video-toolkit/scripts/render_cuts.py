#!/usr/bin/env python3
"""Monta o vídeo-base a partir de uma lista de cortes.

Uso:
  render_cuts.py cortes.txt saida [--preview]

Formato de cortes.txt (uma linha por corte, '#' = comentário):
  <arquivo_de_video> <inicio_s> <duracao_s> <rotulo>
  ex.: videos/IMG_8818.MOV 41.24 0.6 aba1

Gera:
  saida.video.mp4  vídeo 1080x1920 30fps (sem áudio)
  saida.orig.wav   áudio original dos cortes, sample-exato

Por que separado: juntar pedaços em AAC com "concat -c copy" cria
estalos em cada emenda e dessincroniza. Aqui cada corte tem duração
arredondada para frames inteiros e o áudio é montado em PCM com fade
de 12 ms em cada emenda (sem cliques).

--preview: 540x960 com o rótulo de cada corte escrito na tela (para revisar).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

FPS, SR = 30, 48000


def read_cuts(path):
    cuts = []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        cuts.append((p[0], float(p[1]), float(p[2]), p[3] if len(p) > 3 else ""))
    return cuts


def render(cuts, out, preview=False):
    W, H = (540, 960) if preview else (1080, 1920)
    tmp = tempfile.mkdtemp(dir=".")
    aud = []
    with open(f"{tmp}/list.txt", "w") as lst:
        for i, (src, s, d, lab) in enumerate(cuts):
            nf = max(1, round(d * FPS))
            dur = nf / FPS
            vf = f"scale={W}:{H},setsar=1,fps={FPS}"
            if preview:
                vf += (f",drawtext=text='{i+1:03d} {os.path.basename(src)}@{s} {lab}':"
                       "x=6:y=6:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.7")
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(s), "-i", src, "-an",
                            "-vf", vf, "-frames:v", str(nf), "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "18", "-pix_fmt", "yuv420p", f"{tmp}/{i:03d}.mp4"], check=True)
            lst.write(f"file '{i:03d}.mp4'\n")
            raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(s), "-t", str(dur + 0.1),
                                  "-i", src, "-vn", "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"],
                                 capture_output=True, check=True).stdout
            a = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
            n = int(round(dur * SR))
            a = a[:n]
            if len(a) < n:
                a = np.vstack([a, np.zeros((n - len(a), 2), np.float32)])
            f = int(0.012 * SR)
            ramp = np.linspace(0, 1, f)[:, None]
            a[:f] *= ramp
            a[-f:] *= ramp[::-1]
            aud.append(a)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", f"{tmp}/list.txt", "-c", "copy", out + ".video.mp4"], check=True)
    A = np.vstack(aud)
    with wave.open(out + ".orig.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(A, -1, 1) * 32767).astype(np.int16).tobytes())
    shutil.rmtree(tmp)
    total = sum(max(1, round(c[2] * FPS)) for c in cuts) / FPS
    print(f"{len(cuts)} cortes, {total:.2f}s -> {out}.video.mp4 / {out}.orig.wav")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    render(read_cuts(sys.argv[1]), sys.argv[2], "--preview" in sys.argv)
