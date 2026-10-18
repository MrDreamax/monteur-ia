"""Planches des moments candidats des vidéos longues : 1 ligne par vidéo (L##), candidats L##-k.
  python3 planches_longues.py <prefixe_planche> [premier_index_video]
"""
import json, os, sys, unicodedata
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20); f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
SEL = {r["path"]: r for r in json.load(open("selection.json"))}
M = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "moments.json"))
prev = {x["id"]: x for x in json.load(open("moments_ids.json"))} if os.path.exists("moments_ids.json") else {}
vids = sorted(M, key=lambda p: (SEL[p]["dossier"], p))
known = sorted({x["path"] for x in prev.values()})
order = known + [p for p in vids if p not in known]          # ids stables entre deux passes
ids, new_rows = dict(prev), []
for n, p in enumerate(order):
    r = SEL[p]; lid = f"L{n:02d}"
    need = 1 if r["duree_s"] <= 180 else 2 if r["duree_s"] <= 600 else 3
    if p in known: continue
    cs = []
    for k, c in enumerate(M[p]):
        cid = f"{lid}-{k}"
        ids[cid] = {**{kk: r[kk] for kk in ("path", "date", "w", "h", "duree_s")}, "dossier": unicodedata.normalize("NFC", r["dossier"]),
                    "id": cid, "t": c["t"], "img": c["img"], "why": c["why"]}
        cs.append(ids[cid])
    new_rows.append((lid, need, unicodedata.normalize("NFC", r["dossier"]), r["duree_s"], cs))
json.dump(list(ids.values()), open("moments_ids.json", "w"), ensure_ascii=False)

COLS, W, H, LAB, PER = 9, 215, 175, 170, 6
for s in range(0, len(new_rows), PER):
    chunk = new_rows[s:s + PER]
    S = Image.new("RGB", (LAB + COLS * W, len(chunk) * H), "white"); d = ImageDraw.Draw(S)
    for i, (lid, need, dos, dur, cs) in enumerate(chunk):
        y = i * H
        d.text((6, y + 10), lid, font=F, fill="black"); d.text((6, y + 40), f"{dos[:20]}", font=f, fill="black")
        d.text((6, y + 60), f"durée {dur / 60:.1f} min", font=f, fill="black"); d.text((6, y + 82), f"GARDER {need} max", font=F, fill="red")
        for k, c in enumerate(cs[:COLS]):
            x = LAB + k * W
            try:
                im = Image.open(c["img"]).convert("RGB"); im.thumbnail((W - 6, H - 22)); S.paste(im, (x + 3, y))
            except Exception: d.text((x + 20, y + 60), "illisible", font=f, fill="red")
            d.rectangle((x + 3, y, x + 80, y + 24), fill="black"); d.text((x + 6, y + 2), c["id"], font=F, fill="yellow")
            d.text((x + 6, y + H - 20), f'{"SALLE" if c["why"] == "réaction salle" else "net"} · {int(c["t"] // 60)}:{int(c["t"] % 60):02d}', font=f, fill="black")
        d.line((0, y + H - 1, S.width, y + H - 1), fill="#999")
    S.save(f"planches/{sys.argv[1]}_{s // PER:02d}.jpg", quality=82)
print(len(new_rows), "vidéos ->", (len(new_rows) + PER - 1) // PER, "planches", sys.argv[1])
