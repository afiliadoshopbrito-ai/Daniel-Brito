#!/usr/bin/env python3
"""Narração: transcrever, limpar e posicionar.

Uso:
  narration.py transcribe <audio> [modelo=medium]
      Transcreve frase a frase (por blocos de fala) com tempo de início/fim.
      Use para achar as melhores tomadas e as repetições/gaguejos.

  narration.py words <audio> <inicio> <fim> [modelo=medium]
      Palavra por palavra com tempo, para acertar onde cortar dentro de uma frase.

  narration.py clean <secoes.json> <pasta_saida>
      secoes.json: {"nome_da_secao": [[arquivo, inicio, fim, (folga_final opcional)], ...], ...}
      Para cada seção: junta os trechos escolhidos, remove pausas/respirações
      e grava <pasta_saida>/clean_<nome>.wav + durs.json.

  narration.py place <pasta_saida> <ordem.json> <duracao_video> [inicio=0.3]
      ordem.json: ["intro","bolsa", ...]. Distribui as seções uma após a outra,
      SEM buracos, com o mesmo respiro entre elas, terminando no fim do vídeo.
      Grava place.json e narracao.wav (normalizada a -16 LUFS).

  narration.py check <audio> [modelo=small]
      Transcreve o resultado para conferir que nenhuma palavra foi cortada.

Regras (preferências do Daniel):
- Use sempre a melhor tomada; tire gaguejos, frases repetidas e tentativas.
- Corte as respirações/pausas, mas DEIXE A PALAVRA TERMINAR. Se a última
  palavra de um trecho soar cortada, aumente o 'fim' ou passe folga_final
  (ex.: 0.06). Confira com 'check' e com o perfil de energia.
- Não alongue o vídeo para caber a fala: tire as frases menos importantes.
- Nunca deixe espaço sem áudio entre as falas.
Requer: pip install faster-whisper
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

SR = 48000


def load(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def model(name):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device="cpu", compute_type="int8")


def islands(x, sr, thr=-40, merge=0.07, minlen=0.05):
    fr = int(0.01 * sr)
    n = len(x) // fr
    db = np.array([20 * np.log10(np.sqrt(np.mean(x[i * fr:(i + 1) * fr] ** 2)) + 1e-7) for i in range(n)])
    sp = db > thr
    isl, k = [], 0
    while k < n:
        if sp[k]:
            j = k
            while j < n and sp[j]:
                j += 1
            isl.append([k, j])
            k = j
        else:
            k += 1
    isl = [i for i in isl if (i[1] - i[0]) * 0.01 >= minlen or db[i[0]:i[1]].max() > thr + 12]
    out = []
    for i in isl:
        if out and (i[0] - out[-1][1]) * 0.01 < merge:
            out[-1][1] = i[1]
        else:
            out.append(i)
    return out


def transcribe(path, name="medium"):
    m = model(name)
    a = load(path, 16000)
    for i0, i1 in islands(a, 16000, merge=0.35):
        t0, t1 = i0 / 100, i1 / 100
        if t1 - t0 < 0.12:
            continue
        seg = a[max(0, int((t0 - 0.05) * 16000)):int((t1 + 0.05) * 16000)]
        pad = np.zeros(8000, np.float32)
        txt = " ".join(s.text.strip() for s in m.transcribe(np.concatenate([pad, seg, pad]), language="pt",
                                                           condition_on_previous_text=False)[0])
        print(f"{t0:7.2f}-{t1:7.2f}  {txt}")


def words(path, s, e, name="medium"):
    m = model(name)
    a = load(path, 16000)[int(s * 16000):int(e * 16000)]
    segs, _ = m.transcribe(a, language="pt", word_timestamps=True, condition_on_previous_text=False)
    print(" ".join(f"{w.word.strip()}[{w.start+s:.2f}-{w.end+s:.2f}]" for sg in segs for w in sg.words))


def clean_piece(x, pre=0.03, post=0.03):
    pieces = []
    for i0, i1 in islands(x, SR):
        a0 = max(0, i0 * int(0.01 * SR) - int(pre * SR))
        a1 = min(len(x), i1 * int(0.01 * SR) + int(post * SR))
        p = x[a0:a1].copy()
        f = int(0.015 * SR)
        p[:f] *= np.linspace(0, 1, f)
        p[-f:] *= np.linspace(1, 0, f)
        pieces.append(p)
    return pieces


def save(path, y, ch=1):
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())


def clean(cfg, outdir):
    os.makedirs(outdir, exist_ok=True)
    sections = json.load(open(cfg))
    cache, durs = {}, {}
    for name, parts in sections.items():
        out = []
        for part in parts:
            f, s, e = part[:3]
            post = part[3] if len(part) > 3 else 0.03
            if f not in cache:
                cache[f] = load(f)
            for p in clean_piece(cache[f][int(s * SR):int(e * SR)], post=post):
                out += [p, np.zeros(int(0.04 * SR), np.float32)]
        y = np.concatenate(out)
        save(f"{outdir}/clean_{name}.wav", y)
        durs[name] = len(y) / SR
        print(f"{name:14s} {len(y)/SR:6.2f}s")
    json.dump(durs, open(f"{outdir}/durs.json", "w"), indent=1)


def place(outdir, order_json, video_dur, start=0.3):
    durs = json.load(open(f"{outdir}/durs.json"))
    order = json.load(open(order_json))
    total = sum(durs[s] for s in order)
    end = float(video_dur) - 0.2
    gap = (end - float(start) - total) / max(1, len(order) - 1)
    if gap < 0.08:
        print(f"ATENÇÃO: a fala ({total:.1f}s) não cabe no vídeo; tire frases menos importantes.")
    t, pl = float(start), {}
    for s in order:
        pl[s] = round(t, 3)
        print(f"{s:14s} começa {t:6.2f}s  ({durs[s]:.2f}s)")
        t += durs[s] + gap
    json.dump(pl, open(f"{outdir}/place.json", "w"), indent=1)
    ins, flt = [], []
    for k, (s, t) in enumerate(pl.items()):
        ins += ["-i", f"{outdir}/clean_{s}.wav"]
        flt.append(f"[{k}:a]adelay={int(t*1000)}|{int(t*1000)}[n{k}]")
    n = len(pl)
    flt.append("".join(f"[n{k}]" for k in range(n)) + f"amix=inputs={n}:normalize=0,"
               "loudnorm=I=-16:TP=-1.5:LRA=11[o]")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(flt),
                    "-map", "[o]", "-ar", str(SR), "-ac", "2", f"{outdir}/narracao.wav"], check=True)
    print(f"gap entre falas {gap:.2f}s -> {outdir}/narracao.wav")


def check(path, name="small"):
    m = model(name)
    a = load(path, 16000)
    for s in m.transcribe(np.concatenate([a, np.zeros(8000, np.float32)]), language="pt",
                          word_timestamps=True)[0]:
        print(f"[{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    x = sys.argv[2:]
    if c == "transcribe":
        transcribe(x[0], *(x[1:2]))
    elif c == "words":
        words(x[0], float(x[1]), float(x[2]), *(x[3:4]))
    elif c == "clean":
        clean(x[0], x[1])
    elif c == "place":
        place(x[0], x[1], x[2], *(x[3:4]))
    elif c == "check":
        check(x[0], *(x[1:2]))
    else:
        print(__doc__)
        sys.exit(1)
