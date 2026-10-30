"""Tri de la bibliothèque B-roll (20/10 : « tu utilises souvent les mêmes b-rolls : varie, ou fais un tri »).
  python3 -E broll_tri.py            -> mesure les plans pas encore mesurés, puis classe toute la bibliothèque
  python3 -E broll_tri.py classe     -> reclasse seulement (après un changement de seuil), sans remesurer
Sorties (à côté de ce dossier, rien n'est écrit sur son disque externe) :
  broll_tri_mesures.csv : tremblement, netteté, luminosité par plan (long à calculer : gardé d'une fois sur l'autre)
  broll_tri.csv         : fichier, rang (beau / ok / photo / telephone / ecarte), raison  -> lu par broll.py search
Rangs : beau = vidéo caméra stable et nette ; ok = vidéo caméra correcte ; photo ; telephone = dossier B-ROLL-TELEPHONE
(« plans téléphone moches », 19/10) ; ecarte = tremble, « flou » dans le nom, trop court, trop sombre, illisible ou refusé
par l'utilisateur (broll_refuses.txt).
Rien n'est supprimé : un plan écarté reste sur son disque externe et revient avec broll.py search --tout.
Tremblement : même mesure que broll.shakes et outils/extraire-brolls (270x480, 15 i/s, seuils moyenne <= 1,2 et pic <= 6),
calculée sur la meilleure fenêtre de 2,5 s du plan (on n'en monte jamais plus d'un morceau).
Jamais -hwaccel (image verte, 19/10)."""
import csv, json, os, subprocess, sys
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reglages  # config.json du skill + réglages de cette machine (Brain)
CFG = reglages.config()
INDEX, ROOT = CFG["brolls_index"], CFG["brolls_root"]
MES, TRI = os.path.join(HERE, "broll_tri_mesures.csv"), os.path.join(HERE, "broll_tri.csv")
REFUS = os.path.join(HERE, "broll_refuses.txt")
W, H, FPS, WIN_S = 270, 480, 15, 2.5
HAN = np.outer(np.hanning(H), np.hanning(W)).astype(np.float32)
COLS = ["fichier", "frames", "tremble_moy", "tremble_pic", "nettete", "lum"]
# Période où la personne ne veut pas être vue (ex. un look refusé) : « brolls_periode_exclue » des réglages = [début, fin] (AAAA-MM-JJ).
# Ses plans de cette période où elle est visible sont écartés. Vide = rien d'écarté.
RASE = tuple(CFG.get("brolls_periode_exclue") or ("9999", "9999"))


def lap(x):
    return float((x[1:-1, 1:-1] * 4 - x[:-2, 1:-1] - x[2:, 1:-1] - x[1:-1, :-2] - x[1:-1, 2:]).var())


def mesure(r):
    path = os.path.join(ROOT, r["dossier"], r["fichier"])
    img = r["fichier"].lower().endswith((".jpg", ".jpeg", ".png", ".heic"))
    if path.lower().endswith(".heic"):                         # ffmpeg ne lit pas les HEIC iPhone : conversion Apple (sips)
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), f"tri_{os.getpid()}.jpg")
        subprocess.run(["sips", "-s", "format", "jpeg", path, "--out", tmp], capture_output=True)
        path = tmp
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" + ("" if img else f",fps={FPS}")
    cmd = ["ffmpeg", "-v", "error"] + ([] if img else ["-t", "40"]) + ["-i", path, "-vf", vf] + \
          (["-frames:v", "1"] if img else []) + ["-f", "rawvideo", "-pix_fmt", "gray", "-"]
    try:
        raw = subprocess.run(cmd, capture_output=True, timeout=300).stdout
    except subprocess.TimeoutExpired:
        raw = b""
    n = len(raw) // (W * H)
    if not n:
        return [r["fichier"], 0, "", "", "", ""]
    fr = np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W)   # uint8 : une image à la fois en float (Mac 8 Go)
    sharp, lum, d, prev = [], [], [], None
    for u in fr:
        x = u.astype(np.float32); sharp.append(lap(x)); lum.append(float(x.mean()))
        if img or n < 3: continue
        F = np.fft.fft2(x * HAN)
        if prev is not None:
            R = prev * np.conj(F); R /= np.abs(R) + 1e-9; c = np.abs(np.fft.ifft2(R))
            y, xx = np.unravel_index(c.argmax(), c.shape)
            y, xx = (y - H if y > H // 2 else y), (xx - W if xx > W // 2 else xx)
            d.append((xx * xx + y * y) ** .5 / 2)
        prev = F
    sharp, lum = np.array(sharp), np.array(lum)
    if img or n < 3:
        return [r["fichier"], n, 0, 0, round(float(np.median(sharp)), 1), round(float(np.median(lum)), 1)]
    d = np.array(d); k = min(len(d), int(WIN_S * FPS))
    means = np.convolve(d, np.ones(k) / k, "valid"); i = int(means.argmin())   # meilleure fenêtre de 2,5 s
    return [r["fichier"], n, round(float(means[i]), 2), round(float(d[i:i + k].max()), 2),
            round(float(np.median(sharp[i:i + k + 1])), 1), round(float(np.median(lum[i:i + k + 1])), 1)]


def lire(p):
    return {r["fichier"]: r for r in csv.DictReader(open(p, encoding="utf-8"))} if os.path.exists(p) else {}


def mesurer(rows):
    deja = lire(MES)
    todo = [r for r in rows if r["fichier"] not in deja]
    print(f"{len(deja)} plans déjà mesurés, {len(todo)} à mesurer", flush=True)
    if not todo: return
    new = not os.path.exists(MES)
    with open(MES, "a", encoding="utf-8", newline="") as f, Pool(3) as pool:   # 3 coeurs : Mac 8 Go
        w = csv.writer(f)
        if new: w.writerow(COLS)
        for i, res in enumerate(pool.imap_unordered(mesure, todo), 1):
            w.writerow(res); f.flush()
            if i % 25 == 0: print(f"  {i}/{len(todo)}", flush=True)


def classer(rows):
    m = lire(MES)
    refus = {l.split("#")[0].strip() for l in open(REFUS, encoding="utf-8")} - {""} if os.path.exists(REFUS) else set()
    vid = [float(m[r["fichier"]]["nettete"]) for r in rows
           if r["dossier"].startswith("VIDEOS") and m.get(r["fichier"], {}).get("nettete")]
    p10, p50 = (np.percentile(vid, 10), np.percentile(vid, 50)) if vid else (0, 0)
    out, cpt = [], {}
    for r in rows:
        f_, x = r["fichier"], m.get(r["fichier"], {})
        img = f_.lower().endswith((".jpg", ".jpeg", ".png", ".heic"))
        why = []
        if f_ in refus or r.get("action") in refus: why.append("refusé par l'utilisateur")
        if RASE[0] <= r.get("date_tournage", "") <= RASE[1] and r.get(reglages.colonne_visible(CFG)) != "False":
            why.append(CFG.get("brolls_periode_motif") or f"période exclue ({RASE[0]} - {RASE[1]})")
        if "-flou" in r.get("action", "") or r.get("action", "").startswith("flou"): why.append("flou (nom du plan)")
        if not x or not x.get("frames") or x["frames"] == "0": why.append("illisible")
        else:
            moy, pic, net, lum = (float(x[k] or 0) for k in ("tremble_moy", "tremble_pic", "nettete", "lum"))
            if not img and (moy > 1.2 or pic > 6): why.append(f"tremble ({moy} / pic {pic})")
            if not img and float(r.get("duree_s") or 0) < 2.2: why.append("trop court")
            # pas de rejet « flou » à la mesure : le 20/10 elle écartait 2 plans gardés par l'utilisateur (Tesla de profil, silhouette
            # skyline Singapour : peu de détails = plan cinématique, pas flou). La netteté sert seulement à classer beau / ok.
            if lum < 14: why.append("trop sombre")
            if lum > 235: why.append("brûlé")
        if why: rang = "ecarte"
        elif img: rang = "photo"
        elif r["dossier"].startswith("B-ROLL-TELEPHONE"): rang = "telephone"
        elif float(x["tremble_moy"]) <= 0.5 and float(x["nettete"]) >= p50: rang = "beau"
        else: rang = "ok"
        cpt[rang] = cpt.get(rang, 0) + 1
        out.append([f_, rang, " ; ".join(why)])
    with open(TRI, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["fichier", "rang", "raison"]); w.writerows(out)
    print("classement :", cpt, f"(netteté vidéo p10 {p10:.0f}, médiane {p50:.0f}) ->", TRI)


if __name__ == "__main__":
    if not os.path.exists(INDEX): sys.exit("Bibliothèque introuvable : son disque externe branché ?")
    rows = list(csv.DictReader(open(INDEX, encoding="utf-8")))
    if sys.argv[1:2] != ["classe"]: mesurer(rows)
    classer(rows)
