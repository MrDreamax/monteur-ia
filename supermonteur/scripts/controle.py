"""Contrôle d'une rush AVANT le montage (étape 2 du process client, 13/10 ; codé le 25/10/2026). Feu tricolore :
  🟢 VERT   = on monte tel quel.
  🟠 ORANGE = on répare (débruitage + volume, recadrage, lumière légère ; JAMAIS de stabilisation) et on prévient en 1 ligne.
  🔴 ROUGE  = on refuse, avec 1 ligne pour refaire. Rare : seulement quand aucun montage ne peut sauver la rush.
  python3 controle.py rush.mov [--out dossier] [--apply] [--rapide]
    --out    dossier du reel (défaut : dossier courant) : controle.json, words_rush.json (réutilisé au montage), controle.jpg
    --apply  si ORANGE : écrit <out>/rush_repare.mp4 (la rush d'origine n'est jamais modifiée) ; à monter à la place de la rush
    --rapide sans la parole (pas de transcription)
Code de sortie : 0 vert, 1 orange, 2 rouge. Mesures : lookstats.py (lumière, netteté, visage), transcribe.py (parole).
Seuils calés le 25/10 sur les rushes iPhone de l'utilisateur (IMG_6799, IMG_6850 = vert) et sur des copies abîmées exprès
(floue, sombre, bruitée, couchée, sans voix). Rush intouchable (23/10) : chez l'utilisateur on ne répare rien, le contrôle sert au client.
"""
import json, os, re, subprocess, sys
import numpy as np

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
from lookstats import _size, frames, stats, face, sharp

a = sys.argv[1:]
src = next(x for x in a if not x.startswith("--") and (a.index(x) == 0 or a[a.index(x) - 1] != "--out"))
OUT = a[a.index("--out") + 1] if "--out" in a else "."
APPLY, RAPIDE = "--apply" in a, "--rapide" in a
os.makedirs(OUT, exist_ok=True)
VERT, ORANGE, ROUGE = 0, 1, 2
ICON = {VERT: "🟢", ORANGE: "🟠", ROUGE: "🔴"}
R = []      # {critere, feu, mesure, message}
FIX = {}    # réparations à faire si --apply


def note(critere, feu, mesure, message=""):
    R.append({"critere": critere, "feu": feu, "mesure": mesure, "message": message})


# ---------- 1. Format : vertical, >= 1080 de large ----------
w, h, dur = _size(src)
pr = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                         "stream=codec_type,r_frame_rate,color_transfer", "-of", "json", src]))
vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
has_audio = any(s["codec_type"] == "audio" for s in pr["streams"])
fps = eval(vs.get("r_frame_rate", "30/1")) if vs.get("r_frame_rate", "0/0") != "0/0" else 30
hdr = vs.get("color_transfer") in ("arib-std-b67", "smpte2084")
fmt = f"{w}x{h}, {fps:.0f} i/s, {dur:.0f} s" + (", HDR" if hdr else "")
if dur < 5:
    note("format", ROUGE, fmt, "rush de moins de 5 s : renvoie la vidéo entière")
elif h > w:
    if w >= 1080:
        note("format", VERT, fmt)
    elif w >= 720:
        FIX["scale"] = True
        note("format", ORANGE, fmt, f"rush en {w} de large : agrandie en 1080, un peu moins nette (filme en 1080p ou 4K la prochaine fois)")
    else:
        note("format", ROUGE, fmt, "rush trop petite : refilme en 1080p ou 4K (Réglages > Appareil photo > Enregistrer vidéo)")
else:
    cw = int(h * 9 / 16)   # largeur d'une découpe 9:16 dans une vidéo couchée
    if cw >= 720:
        FIX["crop916"] = True
        note("format", ORANGE, fmt, "vidéo filmée couchée : recadrée en vertical autour de ton visage (filme téléphone debout la prochaine fois)")
    else:
        note("format", ROUGE, fmt, "vidéo couchée et trop petite pour être recadrée : refilme téléphone debout")

# ---------- 2. Son : niveau, bruit, saturation ----------
if not has_audio:
    note("son", ROUGE, "aucune piste son", "la vidéo n'a pas de son : refilme avec le micro branché (ou celui du téléphone)")
else:
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = len(x) // 160 * 160
    db = 20 * np.log10(np.sqrt((x[:n].reshape(-1, 160) ** 2).mean(1)) + 1e-9) if n else np.array([-120.0])
    voix, fond = float(np.percentile(db, 95)), float(np.percentile(db, 2))   # fond = les pauses (2 % les plus calmes)
    rsb = voix - fond                                   # écart voix / bruit de fond (dB) : rushes iPhone de l'utilisateur 25 à 51
    sat = float(100 * (np.abs(x) >= 0.99).mean()) if len(x) else 0.0
    loud = subprocess.run(["ffmpeg", "-nostdin", "-i", src, "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    li = re.findall(r"I:\s+(-?[\d.]+) LUFS", loud)
    lufs = float(li[-1]) if li else -70.0
    mes = f"{lufs:.0f} LUFS, voix {rsb:.0f} dB au-dessus du bruit, saturé {sat:.2f} %"
    if voix < -50 or lufs < -45:
        note("son", ROUGE, mes, "on n'entend presque rien : refilme plus près du micro (30 cm max)")
    elif rsb < 12:
        note("son", ROUGE, mes, "le bruit couvre la voix : refilme dans une pièce calme, fenêtres fermées")
    else:
        msg = []
        if rsb < 18: FIX["denoise"] = True; msg.append("bruit de fond baissé")
        if lufs < -36 or lufs > -9: FIX["volume"] = True; msg.append("volume remis au bon niveau")
        if sat > 0.5: msg.append("son saturé par endroits (micro trop près ou trop fort : 1 main d'écart la prochaine fois)")
        note("son", ORANGE if msg else VERT, mes, " · ".join(msg))

# ---------- 3. Lumière, 4. Netteté, 5. Cadre ----------
fr = frames(src, 8, long_side=960)
st = stats(fr)
F = face(src, 12)
joue = F.get("joue")
lum = joue if joue is not None and not np.isnan(joue) else st["p50"]
mes = f"médiane {st['p50']:.0f}/255, visage {lum:.0f}/255, hautes lumières P99 {st['p99']:.0f}"
if lum < 30:
    note("lumière", ROUGE, mes, "trop sombre : refilme face à une fenêtre (lumière du jour devant toi, jamais derrière)")
elif lum < 75:
    FIX["light"] = "up"
    note("lumière", ORANGE, mes, "image sombre : éclaircie légèrement (mets-toi face à une fenêtre la prochaine fois)")
elif st["p95"] >= 250 and lum > 215:
    FIX["light"] = "down"
    note("lumière", ORANGE, mes, "image brûlée : assombrie légèrement (évite le soleil direct)")
else:
    note("lumière", VERT, mes)

# netteté mesurée au même format (960 px de haut) : variance du laplacien, médiane de 8 images
nt = sharp(fr) or 0.0
mes = f"netteté {nt:.0f}"
if nt < 8:
    note("netteté", ROUGE, mes, "image floue : nettoie l'objectif et touche ton visage sur l'écran avant de filmer")
elif nt < 20:
    note("netteté", ORANGE, mes, "image un peu molle : montable (nettoie l'objectif la prochaine fois)")
else:
    note("netteté", VERT, mes)

vu = F.get("visage_vu", 0)
if vu == 0:
    note("cadre", ROUGE, "aucun visage trouvé", "on ne voit pas ton visage : refilme face caméra, tête dans le haut de l'écran")
else:
    mes = f"visage vu {vu} %, yeux à {F['yeux_y']} % de la hauteur, visage {F['visage_largeur']} % de la largeur, centre {F['visage_x']} %"
    FIX["face_x"] = F["visage_x"]
    msg = []
    if vu < 40: msg.append("ton visage sort souvent du cadre (reste au centre la prochaine fois)")
    elif F["visage_x"] < 22 or F["visage_x"] > 78: msg.append("visage au bord de l'image (reste au centre)")
    if h > w and F["visage_largeur"] < 22: msg.append("filmé de loin : resserré au montage, un peu moins net (rapproche le téléphone : visage = 1/3 de la largeur)")
    # yeux bas avec un visage assez grand = normal, cadre.py le remonte à 35 % au montage (pas d'alerte)
    if vu < 15:
        note("cadre", ROUGE, mes, "ton visage n'est presque jamais dans le cadre : refilme face caméra")
    else:
        note("cadre", ORANGE if msg else VERT, mes, " · ".join(msg))

# ---------- 6. Parole ----------
if RAPIDE or not has_audio:
    note("parole", VERT if RAPIDE else ROUGE, "non vérifiée" if RAPIDE else "pas de son")
else:
    wj = os.path.join(OUT, "words_rush.json")
    p = subprocess.run([sys.executable, os.path.join(S, "transcribe.py"), src, wj], capture_output=True, text=True)
    W = []
    if os.path.exists(wj):
        W = json.load(open(wj)); W = W.get("words", W) if isinstance(W, dict) else W
    if not W:
        note("parole", ROUGE, "aucun mot reconnu" + (f" ({p.stderr.strip()[-120:]})" if p.returncode else ""),
             "on ne t'entend pas parler : vérifie que le micro est branché et parle face au téléphone")
    else:
        parle = sum(x["end"] - x["start"] for x in W)
        mpm = round(len(W) / max(W[-1]["end"] - W[0]["start"], 1) * 60)
        mes = f"{len(W)} mots, {mpm} mots/min, parole sur {100 * parle / max(dur, 1):.0f} % de la rush"
        if len(W) < 8:
            note("parole", ROUGE, mes, "presque aucune parole : renvoie la rush où tu parles")
        elif mpm < 60 or mpm > 260:
            note("parole", ORANGE, mes, "débit inhabituel (" + ("très lent : les blancs seront coupés" if mpm < 60 else "très rapide : sous-titres serrés") + ")")
        else:
            note("parole", VERT, mes)

# ---------- verdict ----------
feu = max(r["feu"] for r in R)
for r in R:
    print(f"{ICON[r['feu']]} {r['critere']:8} {r['mesure']}" + (f"  → {r['message']}" if r["message"] else ""))
lignes = [r["message"] for r in R if r["feu"] == feu and r["message"]]
if feu == ROUGE:
    ligne = "🔴 ROUGE : je ne monte pas cette rush. " + lignes[0][0].upper() + lignes[0][1:] + "."
elif feu == ORANGE:
    ligne = "🟠 ORANGE : je monte, j'ai réparé : " + " ; ".join(m.split(" (")[0] for m in lignes) + "."
else:
    ligne = "🟢 VERT : rush OK, je monte."
print("\n" + ligne)

# planche : 4 images de la rush pour la preuve
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", src, "-vf", f"fps={4 / max(dur, 1):.4f},scale=270:-2,tile=4x1",
                "-frames:v", "1", os.path.join(OUT, "controle.jpg")])

# ---------- réparation (ORANGE + --apply) : jamais de stabilisation ----------
repare = None
if feu == ORANGE and APPLY:
    vf, af = [], []
    if FIX.get("crop916"):
        cx = FIX.get("face_x", 50) / 100
        vf.append(f"crop=trunc(ih*9/16/2)*2:ih:max(0\\,min(iw-ih*9/16\\,{cx:.3f}*iw-ih*9/32)):0")
    if FIX.get("light") == "up":
        vf.append("eq=gamma=1.25:brightness=0.03:saturation=1.03")
    elif FIX.get("light") == "down":
        vf.append("eq=gamma=0.88:brightness=-0.02")
    if FIX.get("crop916") or FIX.get("scale"):
        vf.append("scale=1080:1920:flags=lanczos")
    if FIX.get("denoise"):
        af += ["highpass=f=70", "afftdn=nr=12:nf=-40:tn=1"]
    if FIX.get("volume") or FIX.get("denoise"):
        af.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    repare = os.path.join(OUT, "rush_repare.mp4")
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", src]
    cmd += (["-vf", ",".join(vf), "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"] if vf else ["-c:v", "copy"])
    cmd += (["-af", ",".join(af), "-c:a", "aac", "-b:a", "256k", "-ar", "48000"] if af else ["-c:a", "copy"])
    cmd += ["-movflags", "+faststart", repare]
    subprocess.run(cmd, check=True)
    print(f"réparée : {repare} (à monter à la place de la rush)")

json.dump({"rush": os.path.abspath(src), "feu": ["vert", "orange", "rouge"][feu], "ligne": ligne, "criteres": R,
           "reparations": [k for k in FIX if k != "face_x"], "rush_repare": repare},
          open(os.path.join(OUT, "controle.json"), "w"), indent=1, ensure_ascii=False)
sys.exit(feu)
