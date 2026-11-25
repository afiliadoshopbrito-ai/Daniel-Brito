#!/usr/bin/env python3
"""Montagem final: vídeo-base + áudio original + narração + cards.

Uso:
  compose.py config.json

config.json:
{
  "video": "base.video.mp4",          # de render_cuts.py
  "orig":  "base.orig.wav",           # de render_cuts.py
  "orig_volume": 0.3,                 # som original baixinho por baixo da voz
  "narration": "narr/narracao.wav",   # de narration.py place (opcional)
  "fx_volume": 0.5,                   # volume do som de choque dos cards
  "overlays": [                       # de cards.py; "at" = segundo em que o card entra
    {"seq": "fx/title", "at": 0.25},
    {"seq": "fx/links", "at": 6.0},
    {"seq": "fx/fornecedor", "at": 35.75},
    {"seq": "fx/comenta", "at": 80.0}
  ],
  "out": "final.mp4"
}
Dica: para achar o "at" de um card, transcreva a narração final com
narration.py check e use ~0,3 s antes da palavra (o glitch dura 0,4 s).
"""
import json
import subprocess
import sys

cfg = json.load(open(sys.argv[1]))
ins = ["-i", cfg["video"], "-i", cfg["orig"]]
fl, amix = [], []
fl.append(f"[1:a]volume={cfg.get('orig_volume', 0.3)}[orig]")
amix.append("[orig]")
idx, vlast = 2, "0:v"
for k, ov in enumerate(cfg.get("overlays", [])):
    ins += ["-framerate", "30", "-i", f"{ov['seq']}/f%03d.png"]
    fl.append(f"[{idx}:v]setpts=PTS+{ov['at']}/TB[o{k}]")
    fl.append(f"[{vlast}][o{k}]overlay=0:0:eof_action=pass[v{k}]")
    vlast = f"v{k}"
    idx += 1
    ins += ["-i", ov["seq"].rstrip("/") + ".wav"]
    ms = int(ov["at"] * 1000)
    fl.append(f"[{idx}:a]volume={cfg.get('fx_volume', 0.5)},adelay={ms}|{ms},apad[s{k}]")
    amix.append(f"[s{k}]")
    idx += 1
if cfg.get("narration"):
    ins += ["-i", cfg["narration"]]
    fl.append(f"[{idx}:a]apad[nr]")
    amix.append("[nr]")
fl.append("".join(amix) + f"amix=inputs={len(amix)}:duration=first:normalize=0,alimiter=limit=0.95[a]")
vmap = f"[{vlast}]" if vlast != "0:v" else "0:v"
cmd = (["ffmpeg", "-nostdin", "-v", "error", "-y"] + ins +
       ["-filter_complex", ";".join(fl), "-map", vmap, "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cfg["out"]])
subprocess.run(cmd, check=True)
print(cfg["out"])
