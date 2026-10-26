"""Planches numérotées pour le tri visuel (photos + vidéos courtes), + photo de référence du visage de la personne."""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
OUT = "planches"; os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
COLS, ROWS, W, H = 8, 6, 250, 210

def sheet(items, name, title):
    S = Image.new("RGB", (COLS * W, ROWS * H + 34), "white"); d = ImageDraw.Draw(S)
    d.text((8, 6), title, font=F, fill="black")
    for k, (iid, th, sub) in enumerate(items):
        x, y = (k % COLS) * W, 34 + (k // COLS) * H
        try:
            im = Image.open(th).convert("RGB"); im.thumbnail((W - 6, H - 24)); S.paste(im, (x + 3 + (W - 6 - im.width) // 2, y))
        except Exception:
            d.text((x + 20, y + 80), "illisible", font=F, fill="red")
        d.rectangle((x + 3, y, x + 3 + 8 + 14 * len(iid), y + 26), fill="black"); d.text((x + 7, y + 2), iid, font=F, fill="yellow")
        d.text((x + 6, y + H - 22), sub[:34], font=f, fill="black")
    S.save(os.path.join(OUT, name), quality=82)

P = json.load(open("photos_scenes.json"))
for i, p in enumerate(P): p["id"] = f"P{i:03d}"
json.dump(P, open("photos_scenes.json", "w"), ensure_ascii=False)
V = json.load(open("videos_courtes.json"))
items = [(p["id"], p["thumb"], f'{p["dossier"]} · {p["n_scene"]} ph') for p in P] + \
        [(v["id"], v["thumb"], f'{v["dossier"]} · vidéo {v["duree_s"]:.0f}s') for v in V]
n = COLS * ROWS; names = []
for k in range(0, len(items), n):
    chunk = items[k:k + n]; nm = f"planche_{k // n:02d}.jpg"
    sheet(chunk, nm, f"{chunk[0][0]} à {chunk[-1][0]} — " + ", ".join(sorted({c[2].split(' · ')[0] for c in chunk})))
    names.append(nm)
# référence visage : portraits récents (Photo perso)
refs = [p["thumb"] for p in P if p["dossier"] == "Photo perso"][:4]
R = Image.new("RGB", (4 * 300, 320), "white")
for k, t in enumerate(refs):
    im = Image.open(t).convert("RGB"); im.thumbnail((296, 300)); R.paste(im, (k * 300, 0))
ImageDraw.Draw(R).text((8, 298), "LA PERSONNE (visage actuel)", font=F, fill="black"); R.save(os.path.join(OUT, "ref_visage.jpg"))
print(len(items), "éléments,", len(names), "planches")
