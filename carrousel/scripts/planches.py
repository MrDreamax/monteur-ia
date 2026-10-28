"""Planches contact numérotées des photos de l'utilisateur (dossier `photos` de 00-Moi/marque.json), pour choisir les photos d'un carrousel.
  python3 planches.py <dossier_sortie> "<mot-clé 1>" "<mot-clé 2>" ...
Chaque argument = un mot-clé cherché dans le NOM des photos (dossier rangé à plat).
Écrit planche-01.jpg, planche-02.jpg… (40 photos par planche) + index.json (numéro -> chemin).
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.expanduser("~/Documents/Brain/_outils"))
import marque  # noqa: E402

ROOT = os.path.expanduser(marque.charger().get("photos") or "~/Documents/Contenu/medias/photos")
OUT, FOLDERS = sys.argv[1], sys.argv[2:]
TW, TH, COLS, ROWS = 220, 293, 8, 5
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
os.makedirs(OUT, exist_ok=True)

files = []
import unicodedata
nfc = lambda x: unicodedata.normalize("NFC", x).lower()
for f in FOLDERS:
    key = nfc(f.split("/")[-1]).split(" ", 1)[-1] if f[:4].isdigit() else nfc(f.split("/")[-1])
    for dp, _, fn in os.walk(ROOT):
        files += sorted(os.path.join(dp, n) for n in fn if n.lower().endswith((".jpg", ".jpeg", ".png")) and not n.startswith("._")
                        and (key in nfc(n) or key in nfc(os.path.relpath(dp, ROOT))))

index, per = {}, COLS * ROWS
for s in range(0, len(files), per):
    sheet = Image.new("RGB", (COLS * TW, ROWS * TH), "#333")
    d = ImageDraw.Draw(sheet)
    for i, path in enumerate(files[s:s + per]):
        n = s + i + 1
        index[n] = path
        try:
            im = ImageOps.exif_transpose(Image.open(path))
            im.draft("RGB", (TW * 2, TH * 2))
            im = ImageOps.fit(im.convert("RGB"), (TW - 4, TH - 4))
        except Exception:
            continue
        x, y = (i % COLS) * TW + 2, (i // COLS) * TH + 2
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 46, y + 28], fill="#000")
        d.text((x + 4, y + 2), str(n), fill="#FFD400", font=font)
    sheet.save(os.path.join(OUT, f"planche-{s // per + 1:02d}.jpg"), quality=80)
json.dump(index, open(os.path.join(OUT, "index.json"), "w"), ensure_ascii=False, indent=0)
print(len(files), "photos,", (len(files) + per - 1) // per, "planches dans", OUT)
