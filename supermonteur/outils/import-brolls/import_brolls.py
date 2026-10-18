"""Ajoute à la bibliothèque B-ROLLS les éléments gardés par le tri (photos, vidéos courtes, moments de vidéos longues).
Originaux jamais touchés : on copie / on extrait. Index + catalogue + vignettes + journal mis à jour.
  python3 import_brolls.py --dry   -> affiche ce qui serait fait
"""
import csv, glob, json, os, re, shutil, subprocess, sys, unicodedata
from datetime import datetime
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
_CFG = json.load(open(os.path.join(HERE, "..", "..", "config.json"))) if os.path.exists(os.path.join(HERE, "..", "..", "config.json")) else {}
B = os.path.expanduser(_CFG.get("brolls_root") or "~/Documents/Montage/B-ROLLS")   # bibliothèque du client (config.json)
DRY = "--dry" in sys.argv
CLIP = 7.0
FIELDS = ["fichier", "dossier", "theme", "action", "tenue", "lieu", "orientation", "resolution", "duree_s", "qualite",
          "cyril_visible", "date_tournage", "usage"]
THEMES = {"01-TRAVAIL", "02-TOURNAGE", "03-TELEPHONE", "04-SPORT", "05-REPAS", "06-LUXE", "07-VILLE-VOYAGE", "08-MAISON",
          "09-SOCIAL", "10-ARGENT", "11-STUDIO-MUSIQUE", "12-PORTRAIT", "14-AUTRE"}

def slug(s):
    s = unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")[:48] or "plan"
def plain(s): return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().strip()
def res(w, h): m = max(w, h); return "4K" if m >= 3000 else "HD" if m >= 1280 else "SD"
def dhash(im):
    import numpy as np
    d = np.asarray(im.convert("L").resize((9, 8)), "int16"); return (d[:, 1:] > d[:, :-1]).flatten()

# ---------- ce que le tri a gardé ----------
kept = {}
for f in sorted(glob.glob("tri_*.json")):
    for x in json.load(open(f)):
        if x.get("theme") in THEMES:
            if x["theme"] == "14-AUTRE":                            # même rangement que la biblio existante
                if re.search(r"piano|billard|echecs|cigare|barbier|coiffeur", x.get("action", "")): x["theme"] = "06-LUXE"
                elif re.search(r"magazine|livre|carnet", x.get("action", "")): x["theme"] = "01-TRAVAIL"
            kept[x["id"]] = x
P = {p["id"]: p for p in json.load(open("photos_scenes.json"))}
V = {v["id"]: v for v in json.load(open("videos_courtes.json"))}
L = {l["id"]: l for l in json.load(open("moments_ids.json"))} if os.path.exists("moments_ids.json") else {}
dup = json.load(open("doublons_biblio.json"))

# Da Nang 21-22/10/2025 : la biblio a déjà 167 photos de cette séance -> on écarte les scènes à moins de 60 s d'une photo déjà en biblio
lib_ts = []
for r in csv.DictReader(open(f"{B}/_INDEX.csv", encoding="utf-8")):
    if r["date_tournage"] in ("2025-10-21", "2025-10-22") and r["dossier"].startswith("PHOTOS"):
        try:
            t = Image.open(f'{B}/{r["dossier"]}/{r["fichier"]}').getexif().get_ifd(0x8769).get(36867)
            lib_ts.append(datetime.strptime(t, "%Y:%m:%d %H:%M:%S").timestamp())
        except Exception: pass

# empreintes des vignettes de la biblio (doublon visuel = écarté)
lib_h = []
for v in glob.glob(f"{B}/_vignettes/*.jpg"):
    try: lib_h.append(dhash(Image.open(v)))
    except Exception: pass

rows, skipped = [], []
for iid, x in kept.items():
    src = P.get(iid) or V.get(iid) or L.get(iid)
    if not src: skipped.append((iid, "id inconnu")); continue
    if src["path"] in dup: skipped.append((iid, "déjà en biblio")); continue
    if iid.startswith("P") and src["dossier"] == "Da Nang" and any(abs(src["ts"] - t) < 60 for t in lib_ts):
        skipped.append((iid, "séance Da Nang déjà en biblio")); continue
    th = src.get("thumb") or src.get("img")
    try:
        h = dhash(Image.open(th))
        if any((h != g).sum() <= 5 for g in lib_h): skipped.append((iid, "doublon visuel biblio")); continue
    except Exception: pass
    rows.append((iid, x, src))

# numérotation : suite du plus grand numéro existant par thème
num = {}
for f in glob.glob(f"{B}/*/*/*.*"):
    m = re.match(r"(?:TEL_)?([A-Z-]+?)_.*_(\d{3})\.\w+$", os.path.basename(f))
    if m: num[m[1]] = max(num.get(m[1], 0), int(m[2]))

idx_new, cat_new, journal = [], [], []
for iid, x, src in sorted(rows, key=lambda r: r[0]):
    theme_dir = x["theme"]; theme = theme_dir.split("-", 1)[1]
    kind = "PHOTOS" if iid.startswith("P") else "VIDEOS"
    w, h = src.get("w", 0), src.get("h", 0)
    rot = int(x.get("rotation") or 0) if kind == "VIDEOS" else 0
    if rot: w, h = h, w
    o = "V" if h > w else "H"
    num[theme] = num.get(theme, 0) + 1
    ext = "jpg" if kind == "PHOTOS" else "mp4"
    name = f"{theme}_{slug(x['action'])}_{o}_{res(w, h)}_{num[theme]:03d}.{ext}"
    folder = f"{kind}/{theme_dir}"; dst = f"{B}/{folder}/{name}"; vig = f"{B}/_vignettes/{name[:-4]}.jpg"
    t0 = src.get("t", 0.0)
    dur = 0.0 if kind == "PHOTOS" else (min(CLIP, src["duree_s"] - t0) if iid.startswith("L") else src["duree_s"])
    if iid.startswith("V") and rot: t0 = 0.0
    if not DRY:
        os.makedirs(os.path.dirname(dst), exist_ok=True); assert not os.path.exists(dst), dst
        if kind == "PHOTOS":
            p = src["path"]
            if p.lower().endswith((".cr3", ".heic", ".dng")):
                tmp = os.path.join(HERE, "conv_full.jpg"); subprocess.run(["sips", "-s", "format", "jpeg", p, "--out", tmp], capture_output=True); p = tmp
            im = Image.open(p); ex = im.getexif(); im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((3840, 3840)); ex[274] = 1
            im.save(dst, quality=92, exif=ex.tobytes())
            os.utime(dst, (src["ts"], src["ts"]))
        elif iid.startswith("V") and not rot:
            shutil.copy2(src["path"], dst)
        else:
            br = "45M" if res(w, h) == "4K" else "20M"
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-i", src["path"], "-t", str(dur),
                                   "-map_metadata", "0"] + (["-vf", "transpose=1" if rot == 90 else "transpose=2"] if rot else []) + ["-c:v", "h264_videotoolbox", "-b:v", br, "-pix_fmt", "yuv420p",
                                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst])
        # vignette 600 px
        if kind == "PHOTOS":
            t = Image.open(dst); t.thumbnail((600, 600)); t.save(vig, quality=85)
        else:
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", str(dur * .4), "-i", dst, "-frames:v", "1",
                                   "-vf", "scale=600:-2", vig])
    idx_new.append({"fichier": name, "dossier": folder, "theme": theme, "action": slug(x["action"]), "tenue": plain(x.get("tenue")),
                    "lieu": plain(x.get("lieu")), "orientation": o, "resolution": res(w, h), "duree_s": round(dur, 1),
                    "qualite": x.get("qualite", "moyen"), "cyril_visible": str(bool(x.get("cyril_visible"))),
                    "date_tournage": src["date"], "usage": ""})
    cat_new.append({"name": name, "folder": folder, "theme": theme, "action": slug(x["action"]), "tenue": plain(x.get("tenue")),
                    "lieu": plain(x.get("lieu")), "orient": o, "res": res(w, h), "dur": round(dur, 1), "kind": kind,
                    "qualite": x.get("qualite", "moyen"), "date": src["date"], "usage": ""})
    journal.append({"source": src["path"], "debut_s": t0 if iid.startswith("L") else "", "duree_s": round(dur, 1),
                    "nouveau_chemin": dst, "id_tri": iid})

print(f"gardés par le tri : {len(kept)} | ajoutés : {len(idx_new)} | écartés : {len(skipped)}")
from collections import Counter
print("écartés :", Counter(r for _, r in skipped)); print("ajoutés par thème :", Counter(r["dossier"] for r in idx_new))
if DRY: sys.exit()

stamp = "2026-10-13"
shutil.copy2(f"{B}/_INDEX.csv", f"{HERE}/_INDEX_avant_import.csv"); shutil.copy2(f"{B}/_CATALOGUE.html", f"{HERE}/_CATALOGUE_avant_import.html")
old = list(csv.DictReader(open(f"{B}/_INDEX.csv", encoding="utf-8")))
with open(f"{B}/_INDEX.csv", "w", encoding="utf-8", newline="") as f:
    wr = csv.DictWriter(f, FIELDS, extrasaction="ignore"); wr.writeheader(); wr.writerows(old + idx_new)
cat = open(f"{B}/_CATALOGUE.html", encoding="utf-8").read()
i = cat.index("const D=") + len("const D="); D, end = json.JSONDecoder().raw_decode(cat, i)
open(f"{B}/_CATALOGUE.html", "w", encoding="utf-8").write(cat[:i] + json.dumps(D + cat_new, ensure_ascii=False) + cat[end:])
with open(f"{B}/_JOURNAL-AJOUT-PHOTOS-{stamp}.csv", "w", encoding="utf-8", newline="") as f:
    wr = csv.DictWriter(f, ["source", "debut_s", "duree_s", "nouveau_chemin", "id_tri"]); wr.writeheader(); wr.writerows(journal)
json.dump(idx_new, open("ajoutes.json", "w"), ensure_ascii=False)
print("index :", len(old), "->", len(old) + len(idx_new), "| catalogue :", len(D), "->", len(D) + len(cat_new))
