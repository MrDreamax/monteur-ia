#!/usr/bin/env python3
"""Cherche dans la biblio B-ROLLS les plans qui illustrent le sujet du reel, et sort une planche numérotée pour choisir la cover.
Règles : la personne visible, tournée après brolls_min_date (config du monteur de cette machine), vertical d'abord.
Usage : broll.py --mots "tournage,camera,trepied,podcast" --out DOSSIER [--max 12]
Sorties : DOSSIER/planche.jpg (numéros en jaune) + DOSSIER/candidats.json ({numéro: {fichier, image}}).
Pour un plan vidéo, l'image prise est celle du milieu du plan. Images : cand_N.jpg (2400 px de haut max).
"""
import argparse, csv, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import config_monteur

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "Montserrat.ttf")

ap = argparse.ArgumentParser()
ap.add_argument("--mots", required=True, help="mots-clés séparés par des virgules (cherchés dans thème, action, lieu, nom)")
ap.add_argument("--out", required=True)
ap.add_argument("--max", type=int, default=12)
a = ap.parse_args()

cfg = config_monteur()
racine, index, mini = cfg["brolls_root"], cfg["brolls_index"], cfg.get("brolls_min_date", "2024-01-01")
if not os.path.exists(index):
    raise SystemExit(f"Index B-roll introuvable : {index} (SSD branché ?)")
mots = [m.strip().lower() for m in a.mots.split(",") if m.strip()]
cands = []
for r in csv.DictReader(open(index)):
    if r.get(cfg.get("colonne_visible", "personne_visible")) != "True" or (r.get("date_tournage") or "0") < mini or r.get("qualite") == "mauvais":
        continue
    txt = " ".join([r["fichier"], r["theme"], r["action"], r["lieu"]]).lower()
    score = sum(m in txt for m in mots)
    if score:
        cands.append((score, r["orientation"] == "V", r["resolution"] == "4K", r["date_tournage"], r))
cands.sort(key=lambda c: c[:4], reverse=True)
cands = cands[:a.max]
if not cands:
    raise SystemExit("Aucun B-roll trouvé : élargir les mots-clés")

os.makedirs(a.out, exist_ok=True)
sortie, vignettes = {}, []
for i, (*_, r) in enumerate(cands, 1):
    src = os.path.join(racine, r["dossier"], r["fichier"])
    img = os.path.join(a.out, f"cand_{i}.jpg")
    entree = ["-i", src]
    if r["dossier"].startswith("VIDEOS"):
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                 capture_output=True, text=True).stdout.strip() or 0)
        entree = ["-ss", str(d / 2), "-i", src]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entree, "-frames:v", "1", "-vf", "scale='if(gt(ih,2400),-2,iw)':'min(ih,2400)'", "-q:v", "2", img], check=True)
    vig = os.path.join(a.out, f"vig_{i}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", img, "-vf",
                    f"scale=300:533:force_original_aspect_ratio=increase,crop=300:533,"
                    f"drawtext=text='{i}':fontfile={FONT}:fontcolor=yellow:fontsize=44:x=12:y=10:borderw=2",
                    vig], check=True)
    vignettes.append(vig)
    sortie[i] = {"fichier": src, "image": img, "action": r["action"], "date": r["date_tournage"]}
    print(i, r["fichier"])
n = len(vignettes)
cols = min(6, n)
lignes = [vignettes[k:k + cols] for k in range(0, n, cols)]
noir = os.path.join(a.out, "vide.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=black:s=300x533,format=rgb24", "-frames:v", "1", noir], check=True)
rangs = []
for j, ligne in enumerate(lignes):
    ligne = ligne + [noir] * (cols - len(ligne))
    out = os.path.join(a.out, f"rang_{j}.png")
    if cols == 1:
        subprocess.run(["cp", ligne[0], out], check=True)
    else:
        args = sum([["-i", x] for x in ligne], [])
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", f"hstack={cols}", out], check=True)
    rangs.append(out)
planche = os.path.join(a.out, "planche.jpg")
if len(rangs) == 1:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", rangs[0], planche], check=True)
else:
    args = sum([["-i", x] for x in rangs], [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", f"vstack={len(rangs)}", planche], check=True)
json.dump(sortie, open(os.path.join(a.out, "candidats.json"), "w"), ensure_ascii=False, indent=1)
for x in vignettes + rangs + [noir]:
    os.remove(x)
print("OK", planche)
