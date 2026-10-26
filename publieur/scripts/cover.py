#!/usr/bin/env python3
"""Cover de reel 1080x1920 : photo B-roll (déjà retouchée Higgsfield), SANS texte par défaut (règle du 17/10).
Titre (police sans) + sous-titre (serif, couleur accent) seulement si --titre est donné.
Polices et couleurs : DA par défaut du kit (Montserrat blanc + Instrument Serif or), DA du client si config.json "da" est rempli.
Sorties dans --out : cover.png (pour Metricool), grille.jpg (aperçu 3:4 du profil), cover_480.jpg (pour la fiche).
Usage : cover.py --photo retouche.png --out DOSSIER   (texte : --titre "TIER LIST" --sous-titre "...", sur demande seulement)
"""
import argparse, html, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _rendu import rendre
from _config import da_cover

ap = argparse.ArgumentParser()
ap.add_argument("--photo", required=True)
ap.add_argument("--titre", default="")
ap.add_argument("--sous-titre", default="")
ap.add_argument("--out", required=True)
ap.add_argument("--haut", type=int, default=1395, help="haut du bloc texte en px (zone 3:4 visible = 240 à 1680)")
a = ap.parse_args()

mots = len((a.titre + " " + a.sous_titre).split())
if mots > 6:
    print(f"ALERTE : {mots} mots sur la cover, viser 2 à 4 (sinon coupé dans la grille)")

# Photo recadrée en 1080x1920 (rotation EXIF appliquée par ffmpeg)
tmp = tempfile.mkdtemp(prefix="publieur-cover-")
fond = os.path.join(tmp, "fond.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.photo, "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", fond], check=True)

DA = da_cover()
texte = (f'<div class="fade"></div><div class="t"><div class="a">{html.escape(a.titre)}</div><div class="b">{html.escape(a.sous_titre)}</div></div>'
         if a.titre.strip() else "")
page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:M;src:url(sans.ttf)}}
@font-face{{font-family:I;src:url(serif.ttf)}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}}
.bg{{position:absolute;inset:0;background:url(fond.png) center/cover}}
.fade{{position:absolute;left:0;right:0;top:{a.haut - 215}px;height:{1920 - a.haut + 215}px;background:linear-gradient(to bottom,rgba(0,0,0,0),rgba(0,0,0,.78) 45%,rgba(0,0,0,.85))}}
.t{{position:absolute;left:60px;right:60px;top:{a.haut}px;text-align:center;color:{DA['texte']}}}
.a{{font-family:M;font-weight:900;font-size:132px;letter-spacing:-2px;line-height:1;text-transform:uppercase}}
.b{{font-family:I;font-size:112px;line-height:1.05;margin-top:6px;color:{DA['accent']}}}
</style></head><body><div class="bg"></div>{texte}</body></html>"""

os.makedirs(a.out, exist_ok=True)
cover = os.path.join(a.out, "cover.png")
rendre(page, {"fond.png": fond, "sans.ttf": DA["sans"], "serif.ttf": DA["serif"]}, cover, 1080, 1920)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cover, "-vf", "crop=1080:1440:0:240,scale=360:-1",
                os.path.join(a.out, "grille.jpg")], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cover, "-vf", "scale=480:-1", "-q:v", "3",
                os.path.join(a.out, "cover_480.jpg")], check=True)
print("OK", cover)
