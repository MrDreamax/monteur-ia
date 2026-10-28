"""Sort d'un reel les meilleures images pour un carrousel, quand l'utilisateur n'a pas de photos perso (23/10/2026).
  python3 reel2frames.py <video> <dossier_sortie> [--words words.json] [--n 16]
<video> : le RUSH d'abord (vidéo avant montage, zéro texte sur l'image, ex. montages/<projet>/clip.mp4) ;
le reel fini seulement s'il n'y a rien d'autre (choisir alors des images sans texte sur le visage).
Choisit des instants entre deux mots (bouche fermée, pas de grimace), nets et calmes, étalés dans le temps.
Écrit image-NN.jpg (pleine résolution), 00-candidates.jpg (planche numérotée à lire pour choisir) et texte.txt
(la transcription, pour écrire les slides depuis le script du reel). Les images servent ensuite de "src" dans
les "photos" d'une description "style": "apple".
"""
import argparse
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("out")
ap.add_argument("--words", help="words.json du montage ({'words': [{'text','start','end'}]})")
ap.add_argument("--n", type=int, default=16)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps


def frame_at(t):
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0, t) * 1000)
    ok, f = cap.read()
    return f if ok else None


# instants candidats : milieu des silences entre deux mots et fin des mots (bouche au repos), sinon toutes les 0,5 s
words = json.load(open(a.words))["words"] if a.words else []
if words:
    times = [w["end"] - 0.03 for w in words]
    times += [(p["end"] + n["start"]) / 2 for p, n in zip(words, words[1:]) if n["start"] - p["end"] >= 0.08]
else:
    times = list(np.arange(0.5, dur - 0.5, 0.5))
times = sorted(t for t in times if 0.3 < t < dur - 0.3)

rows = []
for t in times:
    f, prev = frame_at(t), frame_at(t - 0.1)
    if f is None or prev is None:
        continue
    h, w = f.shape[:2]
    zone = (slice(int(h * .08), int(h * .55)), slice(int(w * .2), int(w * .8)))  # là où est le visage en face cam
    g, gp = cv2.cvtColor(f[zone], cv2.COLOR_BGR2GRAY), cv2.cvtColor(prev[zone], cv2.COLOR_BGR2GRAY)
    sharp = cv2.Laplacian(g, cv2.CV_64F).var()
    motion = float(np.mean(cv2.absdiff(g, gp)))
    rows.append((t, sharp, motion))
if not rows:
    raise SystemExit("aucune image lisible dans la vidéo")

s = np.array([r[1] for r in rows])
m = np.array([r[2] for r in rows])
score = (s - s.min()) / (np.ptp(s) or 1) - (m - m.min()) / (np.ptp(m) or 1)  # net et immobile
gap = max(1.2, dur / (a.n * 1.5))  # images étalées dans le temps (expressions variées)
picked = []
for i in np.argsort(-score):
    t = rows[i][0]
    if all(abs(t - p) >= gap for p in picked):
        picked.append(t)
    if len(picked) == a.n:
        break
picked.sort()

thumbs = []
for k, t in enumerate(picked, 1):
    f = frame_at(t)
    path = os.path.join(a.out, f"image-{k:02d}.jpg")
    cv2.imwrite(path, f, [cv2.IMWRITE_JPEG_QUALITY, 95])
    im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    im.thumbnail((270, 480))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 92, 34), fill=(0, 0, 0))
    d.text((8, 8), f"{k:02d} {t:.1f}s", fill=(255, 255, 255))
    thumbs.append(im)

cols = 8
tw, th = thumbs[0].size
sheet = Image.new("RGB", (cols * (tw + 8) + 8, ((len(thumbs) + cols - 1) // cols) * (th + 8) + 8), (40, 40, 40))
for k, im in enumerate(thumbs):
    sheet.paste(im, (8 + (k % cols) * (tw + 8), 8 + (k // cols) * (th + 8)))
sheet.save(os.path.join(a.out, "00-candidates.jpg"), quality=90)
if words:
    with open(os.path.join(a.out, "texte.txt"), "w") as fh:
        fh.write(" ".join(w["text"] for w in words).replace(" '", "'") + "\n")
print(len(picked), "images ->", a.out)
