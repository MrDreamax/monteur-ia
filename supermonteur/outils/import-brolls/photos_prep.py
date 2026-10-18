"""Photos : netteté + empreinte visuelle, regroupe les rafales / quasi-doublons, garde la plus nette de chaque scène.
Sortie : photos_scenes.json [{path, dossier, date, w, h, sharp, n_scene, thumb}]
"""
import json, os, subprocess, unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import numpy as np
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
TH = os.path.join(HERE, "pthumbs"); os.makedirs(TH, exist_ok=True)
SEL = [r for r in json.load(open(os.path.join(HERE, "selection.json"))) if r["type"] == "photo"]

def feat(r):
    try:
        src = r["path"]
        if src.lower().endswith((".cr3", ".heic", ".dng")):              # RAW / HEIC : PIL ne sait pas, sips oui
            src = os.path.join(TH, f"conv_{abs(hash(r['path']))}.jpg")
            if not os.path.exists(src):
                subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1600", r["path"], "--out", src], capture_output=True)
        im = Image.open(src); im.draft("RGB", (800, 800))
        ex = im.getexif(); dto = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        im = ImageOps.exif_transpose(im).convert("RGB")
        w0, h0 = r["w"], r["h"]
        o = ex.get(274, 1)
        if o in (5, 6, 7, 8): w0, h0 = h0, w0
        g = np.asarray(im.convert("L").resize((480, int(480 * im.height / im.width))), np.float32)
        lap = np.abs(g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
        sharp = float(np.percentile(lap, 99))                      # netteté du sujet (zones les plus nettes)
        d = np.asarray(im.convert("L").resize((9, 8)), np.int16)
        h = "".join("1" if b else "0" for b in (d[:, 1:] > d[:, :-1]).flatten())
        t = im.copy(); t.thumbnail((300, 300)); th = os.path.join(TH, f"{abs(hash(r['path']))}.jpg"); t.save(th, quality=80)
        ts = datetime.strptime(dto, "%Y:%m:%d %H:%M:%S").timestamp() if dto else os.stat(r["path"]).st_mtime
        return {**r, "dossier": unicodedata.normalize("NFC", r["dossier"]), "w": w0, "h": h0, "sharp": round(sharp, 1),
                "hash": h, "ts": ts, "thumb": th, "bri": float(g.mean())}
    except Exception as e:
        print("ERR", r["path"], e); return None

with ThreadPoolExecutor(6) as ex:
    F = [x for x in ex.map(feat, SEL) if x]
F.sort(key=lambda x: (x["dossier"], x["ts"], x["path"]))
ham = lambda a, b: sum(x != y for x, y in zip(a, b))
scenes, cur = [], []
for x in F:
    if cur and x["dossier"] == cur[-1]["dossier"] and (
            x["ts"] - cur[-1]["ts"] <= 3 or (x["ts"] - cur[-1]["ts"] <= 180 and min(ham(x["hash"], c["hash"]) for c in cur[-4:]) <= 12)):
        cur.append(x)
    else:
        if cur: scenes.append(cur)
        cur = [x]
scenes.append(cur)
best = []
for S in scenes:
    b = max(S, key=lambda x: x["sharp"] - (40 if x["bri"] < 30 or x["bri"] > 230 else 0))
    best.append({**b, "n_scene": len(S)})
json.dump(best, open(os.path.join(HERE, "photos_scenes.json"), "w"), ensure_ascii=False)
from collections import Counter
print(len(F), "photos ->", len(best), "scènes"); print(Counter(b["dossier"] for b in best))
