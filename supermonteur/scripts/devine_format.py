"""Devine le format d'un rush avant le montage (26/10 : « je dis toujours "monte cette vidéo", c'est à toi d'en déduire
le type de montage »). Mesure, ne décide pas : Claude regarde la planche, puis pose UNE question en boutons
(« Tu veux un montage tier list ? »), le format deviné en 1er. Règle complète : devine-format.md.
  python3 devine_format.py rush.MOV                    -> devine.json + devine.jpg (planche de 8 images) dans le dossier courant
  python3 devine_format.py rush.MOV --words words.json -> réutilise une transcription déjà faite (sinon Whisper small du Mac,
                                                          gratuit, sur les 150 premières secondes seulement)
  python3 devine_format.py rush.MOV --out dossier/
Signaux : nombre de visages, taille du visage, fond vert, caméra qui bouge, voix sans visage, mots du script.
"""
import json, os, re, subprocess, sys, unicodedata
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

SK = os.path.expanduser("~/.claude/skills/supermonteur")
src = sys.argv[1]
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
words_path = sys.argv[sys.argv.index("--words") + 1] if "--words" in sys.argv else None
os.makedirs(out, exist_ok=True)
N = 8

# --- Image ---------------------------------------------------------------------------------------------------------
a_video = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type",
                                  "-of", "csv=p=0", src]).strip()
if not a_video:                                          # fichier audio seul (mémo vocal) = voix off, rien à regarder
    print(json.dumps({"propositions": [{"format": "Voix off", "recette": "voix-off", "pourquoi": ["fichier audio seul"]}]},
                     ensure_ascii=False)); sys.exit(0)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
png = subprocess.check_output(["ffmpeg", "-v", "error", "-i", src, "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"])
h0, w0 = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR).shape[:2]   # rotation iPhone déjà appliquée
vertical = h0 > w0
fw, fh = (360, 640) if vertical else (640, 360)

det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.path.join(SK, "models", "face_landmarker.task")),
    running_mode=vision.RunningMode.IMAGE, num_faces=4, min_face_detection_confidence=0.6))
faces, face_h, green, frames = [], [], [], []
for i in range(N):
    t = dur * (i + 0.5) / N
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                                   "-vf", f"scale={fw}:{fh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(fh, fw, 3)
    frames.append(fr)
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(fr)))
    faces.append(len(r.face_landmarks))
    face_h.append(max(((max(l.y for l in f) - min(l.y for l in f)) for f in r.face_landmarks), default=0.0))
    hsv = cv2.cvtColor(fr, cv2.COLOR_RGB2HSV)
    green.append(float(((hsv[..., 0] > 35) & (hsv[..., 0] < 85) & (hsv[..., 1] > 90) & (hsv[..., 2] > 60)).mean()))

# Caméra qui bouge (vlog, marche) : plus petit écart entre images à 0,5 s d'écart, sur 4 fenêtres de 2 s
moves, gh = [], int(160 * fh / fw)
for i in range(4):
    t = dur * (i + 0.5) / 4
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-t", "2.1", "-vf",
                                   f"fps=2,scale=160:{gh},format=gray", "-f", "rawvideo", "-"])
    g = np.frombuffer(raw, np.uint8)[: (len(raw) // (gh * 160)) * gh * 160].reshape(-1, gh, 160).astype(np.float32)
    if len(g) >= 2: moves.append(min(float(np.abs(g[k + 1] - g[k]).mean()) for k in range(len(g) - 1)))  # min : une coupe de montage ne compte pas

planche = np.vstack([np.hstack(frames[:4]), np.hstack(frames[4:])])
cv2.imwrite(os.path.join(out, "devine.jpg"), cv2.cvtColor(planche, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])

# --- Son -----------------------------------------------------------------------------------------------------------
if words_path:
    mots = json.load(open(words_path))
    mots = mots.get("words", mots) if isinstance(mots, dict) else mots
else:
    sys.path.insert(0, os.path.join(SK, "scripts"))
    from mots import whisper
    mots = whisper(src, 0, min(dur, 150))
texte = " ".join(m.get("text", m.get("word", "")) for m in mots)
plat = unicodedata.normalize("NFKD", texte.lower().replace("’", "'")).encode("ascii", "ignore").decode()
parle = sum(m["end"] - m["start"] for m in mots if "end" in m) / max(min(dur, 150), 1)

def n(*pats):
    return sum(len(re.findall(p, plat)) for p in pats)

# --- Score des formats (nom = celui du tableau des 25, recette = fichier du Monteur) ----------------------------------
avec_visage = sum(f > 0 for f in faces) / N
deux = sum(f >= 2 for f in faces) / N
gros_plan = float(np.median([h for h in face_h if h] or [0]))
vert = float(np.median(green))
bouge = float(np.median(moves or [0]))
S, why = {}, {}

def add(fmt, pts, raison):
    if pts <= 0: return
    S[fmt] = S.get(fmt, 0) + pts
    why.setdefault(fmt, []).append(raison)

add("Tier list", 6 * min(n(r"\btier\b", r"\bje (te )?classe", r"\bclassement\b"), 3), "il dit « tier » / « je classe »")
add("Comparaison en T", 3 * min(n(r"a ne pas faire", r"pas pour (toi|vous)", r"\bversus\b", r"\bvs\b"), 3), "« à ne pas faire / à faire »")
if n(r"\bmauvais") and n(r"\bexcellent"): add("Mauvais, bien, excellent", 8, "« mauvais … excellent »")
add("Liste", 2 * min(n(r"premierement", r"deuxiemement", r"numero (un|deux|trois|\d)",
                       r"\b(\d+|deux|trois|quatre|cinq|dix|dis) (erreurs?|conseils?|astuces?|choses?|regles?|outils?|raisons?|etapes?)\b"), 4),
    "il compte (« numéro 1, 2… »)")
add("Questions-réponses", 2 * min(n(r"\bquestion\b", r"on m'a demande", r"tu me demandes"), 3), "« question »")
add("Réaction", 2 * min(n(r"\bregarde(z)? (cette|ce|ca)\b", r"\bcette video\b", r"\bce reel\b"), 3), "il commente une autre vidéo")
add("Démonstration", 2 * min(n(r"je (vais )?(te|vous) montre", r"regarde comment", r"\bclique\b"), 3), "« je te montre »")
if vert > 0.25: add("Green screen", 10, f"fond vert sur {vert:.0%} de l'image")
if deux > 0.4:
    add("Podcast", 6, "2 visages à l'image")
    add("Débat", 2 + 2 * min(n(r"pas d'accord", r"non mais"), 3), "2 visages + désaccord")
    add("Clone", 1, "2 visages (si c'est 2 fois toi)")
if not vertical and deux > 0.3: add("Visio (Zoom)", 3, "image horizontale à plusieurs")
if avec_visage < 0.3 and parle > 0.4: add("Voix off", 8, "on entend parler mais on ne voit personne")
if avec_visage < 0.3 and parle <= 0.4: add("B-roll + texte", 6, "des plans sans visage, peu de voix")
if bouge > 18 and avec_visage >= 0.3: add("Vlog", 5, "la caméra bouge (tu marches)")
if avec_visage >= 0.6 and deux < 0.3:
    if 0 < gros_plan < 0.12: add("Conférence", 3, "visage petit dans le cadre (scène ?)")
    add("Face caméra", 3, "toi seul face caméra")
if not S: add("Face caméra", 1, "rien de spécial repéré")

RECETTE = {"Tier list": "montage-viral", "Comparaison en T": "montage-viral", "Mauvais, bien, excellent": "montage-viral",
           "Liste": "face-cam", "Face caméra": "face-cam", "Vlog": "broll-texte", "Conférence": "a-plusieurs",
           "Questions-réponses": "a-plusieurs", "Podcast": "a-plusieurs", "Débat": "a-plusieurs", "Clone": "a-plusieurs",
           "Visio (Zoom)": "a-plusieurs", "Green screen": "green-screen", "Réaction": "green-screen",
           "Voix off": "voix-off", "B-roll + texte": "broll-texte", "Démonstration": "face-cam"}
top = sorted(S, key=lambda k: -S[k])[:4]
res = {"rush": src, "duree": round(dur, 1), "vertical": vertical,
       "signaux": {"visage": round(avec_visage, 2), "deux_visages": round(deux, 2), "taille_visage": round(gros_plan, 2),
                   "vert": round(vert, 2), "camera_bouge": round(bouge, 1), "voix": round(parle, 2)},
       "propositions": [{"format": k, "recette": RECETTE.get(k, "face-cam"), "score": S[k], "pourquoi": why[k]} for k in top],
       "debut_du_texte": texte[:400], "planche": os.path.join(out, "devine.jpg")}
json.dump(res, open(os.path.join(out, "devine.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ("duree", "signaux", "propositions")}, ensure_ascii=False))
