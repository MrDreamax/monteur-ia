"""Prépare une VRAIE photo de l'utilisateur pour une slide : recadrage 3:4, étalonnage validé le 16/10
(teintes naturelles + légère touche bleue dans les ombres, dégradé navy en bas pour lire le texte),
et détourage local (RVM) pour poser le mot géant DERRIÈRE la tête sur la couverture.
  python3 prep.py <photo> <nom> [--fx 0.5] [--fy 0.45] [--zoom 1.0] [--bright 1.03] [--grad 0.55]
Écrit ~/open-carrusel/public/uploads/<nom>-bg.jpg (fond) et <nom>-fg.png (sujet seul, même étalonnage).
fx/fy = centre du recadrage (0 à 1), zoom > 1 = plus serré, grad = où commence le dégradé du bas (0 à 1).
Affiche « tête y≈ » : le haut de la tête en pixels, pour placer le mot géant juste au-dessus (couverture).
"""
import argparse
import os

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

W, H = 1080, 1440
OUT = os.path.expanduser("~/open-carrusel/public/uploads")
MODEL = os.path.expanduser("~/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx")  # modèle du skill supermonteur
DEEP = np.array([0x0B, 0x16, 0x2B], np.float32) / 255
# tri-ton navy -> bleu -> blanc, mélangé à 20 % seulement : la photo garde ses vraies couleurs
STOPS = np.array([0.0, 0.3, 0.62, 1.0], np.float32)
COLS = np.array([[0x06, 0x10, 0x1F], [0x13, 0x25, 0x3F], [0x2F, 0x6F, 0xA8], [0xF4, 0xF8, 0xFC]], np.float32) / 255
TRI = 0.2

ap = argparse.ArgumentParser()
ap.add_argument("photo")
ap.add_argument("nom")
ap.add_argument("--fx", type=float, default=0.5)
ap.add_argument("--fy", type=float, default=0.45)
ap.add_argument("--zoom", type=float, default=1.0)
ap.add_argument("--bright", type=float, default=1.03)
ap.add_argument("--grad", type=float, default=0.55)
a = ap.parse_args()

im = ImageOps.exif_transpose(Image.open(a.photo)).convert("RGB")
iw, ih = im.size
cw = min(iw, ih * 3 / 4) / a.zoom
ch = cw * 4 / 3
cx = min(max(a.fx * iw, cw / 2), iw - cw / 2)
cy = min(max(a.fy * ih, ch / 2), ih - ch / 2)
im = im.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.LANCZOS)
rgb = np.asarray(im, np.float32) / 255

# détourage : la même image passée 4 fois pour stabiliser l'état récurrent de RVM
sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
x = rgb.transpose(2, 0, 1)[None]
rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
for _ in range(4):
    fgr, pha, *rec = sess.run(None, {"src": x, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                      "downsample_ratio": np.array([0.25], np.float32)})
alpha = pha[0, 0]

lum = (rgb * np.array([0.299, 0.587, 0.114], np.float32)).sum(axis=2)
tri = np.stack([np.interp(lum, STOPS, COLS[:, c]) for c in range(3)], axis=2).astype(np.float32)
g = (tri * TRI + rgb * (1 - TRI)) * a.bright
yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
bottom = np.clip((yy - a.grad) / (1 - a.grad), 0, 1) ** 1.3 * 0.88
top = np.clip((0.16 - yy) / 0.16, 0, 1) * 0.55
g = g * (1 - bottom) + DEEP * bottom
g = np.clip(g * (1 - top) + DEEP * top, 0, 1)

os.makedirs(OUT, exist_ok=True)
Image.fromarray((g * 255).astype(np.uint8)).save(f"{OUT}/{a.nom}-bg.jpg", quality=90)
Image.fromarray((np.dstack([g, alpha]) * 255).astype(np.uint8)).save(f"{OUT}/{a.nom}-fg.png")
ys = np.where(alpha > 0.5)[0]
print(a.nom, "tête y≈", int(ys.min()) if len(ys) else None)
