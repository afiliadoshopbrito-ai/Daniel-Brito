#!/usr/bin/env python3
"""Cards com a identidade do site (dmchoice) + efeito de "choque" (glitch).

Cada comando gera uma pasta com quadros PNG (1080x1920, fundo transparente,
30 fps) e um <pasta>.wav com o som de choque, prontos para o compose.py.

Uso:
  cards.py text  <saida> --big "8[KG]" --small "DIRETO DA [CHINA]" --order big-small --flag
  cards.py text  <saida> --small "TODOS OS LINKS" --big "[NA BIO]"
  cards.py text  <saida> --small "COMENTA" --big "[“QUERO”]" --hold-to-end
  cards.py image <saida> <card.png> [--width 880]

Texto entre [colchetes] fica com o degradê laranja->âmbar->dourado do site;
o resto fica creme. --order define qual linha vem em cima (padrão small-big).
--flag põe a bandeira da China tremulando ao lado da linha grande.
--dur (padrão 3.65 s), --hold-to-end (sem saída; fica até o fim do vídeo).

Estilo fixo (aprovado pelo Daniel):
- Fonte Archivo 900 (linha grande, tracking -0.03em) e Archivo 800
  (linha pequena, maiúsculas, tracking +0.14em), igual ao site.
- Cores: creme #F4E8D4, degradê #D9530F -> #FF8A2A -> #F0A54A,
  cartão #0B0806 (85%) com cantos arredondados e borda sutil.
- Tamanho 70% do original, centralizado no topo (centro em y=370).
- Entrada e saída com glitch (cores separadas, faixas deslocadas,
  tremor, ruído) e microfalhas ocasionais. Som: só o ruído elétrico do
  choque, sem tons nem estalinhos.
"""
import argparse
import math
import os
import re
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
W, H, FPS, SR = 1080, 1920, 30, 48000
CREAM = (244, 232, 212)
GRAD = [(0, (217, 83, 15)), (0.6, (255, 138, 42)), (1, (240, 165, 74))]
PANEL = (11, 8, 6, 215)
SCALE, CY = 0.7, 370
rng = np.random.default_rng(7)


# ---------- glitch + som ----------
def glitch(img, g):
    if g <= 0.01:
        return img
    a = np.asarray(img).astype(np.float32)
    dy = int(rng.integers(-1, 2) * 18 * g * rng.random())
    dx = int(rng.normal() * 14 * g)
    a = np.roll(a, (dy, dx), axis=(0, 1))
    k = max(1, int(26 * g))
    out = np.zeros_like(a)
    out[..., 0] = np.roll(a[..., 0], k, axis=1)
    out[..., 1] = a[..., 1]
    out[..., 2] = np.roll(a[..., 2], -k, axis=1)
    out[..., 3] = np.maximum.reduce([np.roll(a[..., 3], k, axis=1), a[..., 3], np.roll(a[..., 3], -k, axis=1)])
    ys = np.where(out[..., 3].max(axis=1) > 0)[0]
    if len(ys):
        y0, y1 = ys.min(), ys.max()
        for _ in range(int(3 + 9 * g)):
            hgt = int(rng.integers(6, 45))
            y = int(rng.integers(y0, max(y0 + 1, y1 - hgt)))
            out[y:y + hgt] = np.roll(out[y:y + hgt], int(rng.normal() * 90 * g), axis=1)
        noise = rng.random(out.shape[:2]) * 255 * 0.5 * g
        mask = out[..., 3] > 0
        for c in range(3):
            out[..., c] = np.where(mask, np.clip(out[..., c] + noise * (rng.random() > 0.5), 0, 255), out[..., c])
        out[::3, :, 3] *= 1 - 0.35 * g
    if rng.random() < 0.3 * g:
        out[..., 3] *= 0.25
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def intensity(t, t_in, t_out, d_in=0.42, d_out=0.3):
    if t < t_in:
        return False, 0
    if t < t_in + d_in:
        p = (t - t_in) / d_in
        return True, (1 - p) ** 1.3 * (0.75 + 0.5 * rng.random())
    if t < t_out:
        return True, (0.35 if rng.random() < 0.04 else 0)
    if t < t_out + d_out:
        return True, 0.3 + 0.9 * (t - t_out) / d_out
    return False, 0


def zap(L=0.38, gain=1.0):
    n = int(L * SR)
    t = np.arange(n) / SR
    buzz = np.sign(np.sin(2 * np.pi * 97 * t)) * 0.35 + np.sign(np.sin(2 * np.pi * 151 * t)) * 0.2
    noise = rng.standard_normal(n)
    gate = np.zeros(n)
    i = 0
    while i < n:
        seg = int(rng.integers(int(0.008 * SR), int(0.03 * SR)))
        gate[i:i + seg] = rng.random() > 0.35
        i += seg
    env = np.exp(-t * 5.5) * (1 - np.exp(-t * 400))
    return (buzz + noise * 0.6) * gate * env * gain


def make_seq(outdir, frame_fn, length, t_in=0.0, t_out=None):
    os.makedirs(outdir, exist_ok=True)
    t_out = length + 99 if t_out is None else t_out
    for i in range(int(length * FPS)):
        t = i / FPS
        vis, g = intensity(t, t_in, t_out)
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if vis:
            fr = glitch(frame_fn(t), g)
            if t > t_out:
                p = min(1, (t - t_out) / 0.3)
                fr.putalpha(fr.split()[3].point(lambda v: int(v * (1 - p))))
        fr.save(f"{outdir}/f{i:03d}.png")
    au = np.zeros(int(length * SR))
    for at, z in [(t_in, zap()), (t_out, zap(0.22, 0.45))]:
        s = int(at * SR)
        if s < len(au):
            au[s:s + len(z)] += z[:len(au) - s]
    au = au / max(1e-6, np.abs(au).max()) * 0.8
    with wave.open(outdir.rstrip("/") + ".wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((au * 32767).astype(np.int16).tobytes())
    print(f"{outdir}/ ({int(length*FPS)} quadros) + {outdir.rstrip('/')}.wav")


# ---------- texto ----------
def grad_img(w, h):
    yy, xx = np.mgrid[0:h, 0:w]
    p = ((xx / w) + (yy / h)) / 2
    out = np.zeros((h, w, 3))
    for c in range(3):
        out[..., c] = np.interp(p, [s for s, _ in GRAD], [col[c] for _, col in GRAD])
    return Image.fromarray(out.astype(np.uint8), "RGB")


def text_img(markup, font, track):
    parts = [(m.group(1) or m.group(2), bool(m.group(1))) for m in re.finditer(r"\[([^\]]+)\]|([^\[]+)", markup)]
    chars = [(c, acc) for txt, acc in parts for c in txt]
    w = int(sum(font.getlength(c) + track for c, _ in chars)) + 40
    h = font.getbbox("ÁQG")[3] + 30
    mc, ma = Image.new("L", (w, h), 0), Image.new("L", (w, h), 0)
    x = 10
    for c, acc in chars:
        ImageDraw.Draw(ma if acc else mc).text((x, 8), c, font=font, fill=255)
        x += font.getlength(c) + track
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cream = Image.new("RGBA", (w, h), CREAM + (255,))
    cream.putalpha(mc)
    g = grad_img(w, h).convert("RGBA")
    g.putalpha(ma)
    img.alpha_composite(cream)
    img.alpha_composite(g)
    return img.crop(img.getbbox())


def star(d, cx, cy, r, rot, fill):
    d.polygon([(cx + (r if k % 2 == 0 else r * 0.382) * math.sin(rot + k * math.pi / 5),
                cy - (r if k % 2 == 0 else r * 0.382) * math.cos(rot + k * math.pi / 5)) for k in range(10)],
              fill=fill)


def china_flag(fh=130):
    fw, S = int(fh * 1.5), 3
    b = Image.new("RGB", (fw * S, fh * S), (222, 41, 16))
    d = ImageDraw.Draw(b)
    u = fw * S / 30
    star(d, 5 * u, 5 * u, 3 * u, 0, (255, 222, 0))
    for (x, y) in [(10, 2), (12, 4), (12, 7), (10, 9)]:
        star(d, x * u, y * u, u, math.atan2(5 - y, 5 - x) + math.pi / 2 + math.pi, (255, 222, 0))
    base = np.asarray(b.resize((fw, fh), Image.LANCZOS)).astype(float)

    def frame(t):
        amp, pad = 7, 11
        out = np.zeros((fh + 2 * pad, fw, 4))
        xs = np.arange(fw)
        ph = xs / fw * 2 * math.pi * 1.1 - t * 7
        off = amp * np.sin(ph) * (0.25 + 0.75 * xs / fw)
        sh = 1 + 0.22 * np.cos(ph)
        for x in range(fw):
            y0 = int(round(pad + off[x]))
            out[y0:y0 + fh, x, :3] = np.clip(base[:, x, :] * sh[x], 0, 255)
            out[y0:y0 + fh, x, 3] = 255
        return Image.fromarray(out.astype(np.uint8), "RGBA")
    return frame


def text_card(big, small, order="small-big", flag=False):
    fb = ImageFont.truetype(os.path.join(FONTS, "Archivo-900.ttf"), 168)
    fs = ImageFont.truetype(os.path.join(FONTS, "Archivo-800.ttf"), 54)
    B = text_img(big, fb, -0.03 * 168) if big else None
    S = text_img(small, fs, 0.14 * 54) if small else None
    flag_fn = china_flag() if flag else None
    fw = int(130 * 1.5) + 26 if flag else 0
    lines = [x for x in ([B, S] if order == "big-small" else [S, B]) if x is not None]
    widths = [(l.width + (fw if l is B else 0)) for l in lines]
    PX, PY, GAP = 70, 48, 26
    pw = max(widths) + 2 * PX
    ph = sum(l.height for l in lines) + GAP * (len(lines) - 1) + 2 * PY

    def frame(t):
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(full)
        x0, y0 = (W - pw) // 2, CY - ph // 2
        d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=34, fill=PANEL, outline=(255, 255, 255, 22), width=2)
        y = y0 + PY
        for l, wd in zip(lines, widths):
            x = (W - wd) // 2
            full.alpha_composite(l, (x, y))
            if l is B and flag_fn:
                fl = flag_fn(t)
                full.alpha_composite(fl, (x + l.width + 26, y + (l.height - fl.height) // 2))
            y += l.height + GAP
        sm = full.resize((int(W * SCALE), int(H * SCALE)), Image.LANCZOS)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(sm, (int((W - W * SCALE) / 2), int(CY - CY * SCALE)))
        return out
    if not flag:
        static = frame(0)
        return lambda t: static
    return frame


def image_card(path, width=880):
    card = Image.open(path).convert("RGBA")
    card = card.resize((width, int(card.height * width / card.width)), Image.LANCZOS)
    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    full.alpha_composite(card, ((W - width) // 2, CY - card.height // 2))
    return lambda t: full


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["text", "image"])
    ap.add_argument("out")
    ap.add_argument("image", nargs="?")
    ap.add_argument("--big", default="")
    ap.add_argument("--small", default="")
    ap.add_argument("--order", default="small-big")
    ap.add_argument("--flag", action="store_true")
    ap.add_argument("--width", type=int, default=880)
    ap.add_argument("--dur", type=float, default=3.65)
    ap.add_argument("--hold-to-end", action="store_true")
    a = ap.parse_args()
    fn = text_card(a.big, a.small, a.order, a.flag) if a.kind == "text" else image_card(a.image, a.width)
    make_seq(a.out, fn, a.dur, 0.0, None if a.hold_to_end else a.dur - 0.35)
