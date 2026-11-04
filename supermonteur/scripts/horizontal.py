"""Style horizontal, pour du vertical (01/11, réf. SooWei Goh, validé par l’utilisateur : « nickel », publié) : rush horizontal en format court, image zoomée en 4:3 comme SooWei (02/11) entre deux bandes noires,
sous-titres blancs en minuscules SF Pro sur l'image (02/11), B-rolls de vie, musique continue, sans titre ni SFX. Recette : styles/horizontal.md.
  python3 horizontal.py derush <rush>   (dans le dossier du reel : plages.json + words.rush.json -> cut.mp4, cut.segments.json, cut.words.json)
  python3 horizontal.py teaser      (champ teaser de horizontal.json -> met le meilleur moment en ouverture dans cut.mp4, à lancer une fois avant le rendu)
  python3 horizontal.py             (horizontal.json -> final.mp4, plan.json pour le Gardien, ~20 s)
horizontal.json = {"titre": "Ne pas être viral m'a rapporté 6k€", "jaune": ["6 000 euros"], "musique": "In This Shirt.mp3", "debut": 9.21, "ecart": 15, "lignes": [["je vous dois des excuses", 5], ...],
  "brolls": [{"src": "09-SOCIAL/x.mp4", "from": 1.0, "de": "texte d'une ligne", "a": {"coupe": 1, "decale": 0.3}}, ...]}
teaser = {"de": "j'ai reçu", "a": "six mille euros", "lignes": [["j'ai reçu un virement", 4], ["près de 6 000 euros", 5]]} : de / a = mots exacts de la transcription.
lignes = texte + nombre de mots transcrits couverts (28 signes max), coupé seul en morceaux de 4 mots max à l'écran. de / a = le texte d'une ligne (son 1er mot) ou {"coupe": n, "decale": s}.
"""
import csv, datetime, json, os, re, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
CW, CH = 1080, 1920
S = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(os.path.dirname(S), "fonts", "SF-Pro.ttf")
IMG_H, IMG_Y = 810, 555                             # 02/11 : image zoomée en 4:3, 1080x810 centrée, mesurée sur son reel
SIZE, POIDS, Y = 56, 500, 1095                      # 02/11 : sur l'image, sous le menton même penché vers la caméra, ombre légère comme lui ; 40 fin essayé puis refusé le 02/11
MAX_MOTS = 4
FAIBLES = set("le la les l' de du des d' un une à au aux et ou mais que qui qu' ce cette ces ma mon mes ta ton tes sa son ses en dans sur pour par avec je j' tu il elle on nous vous ils elles ne n' se si quand très plus c'est j'ai t'es parce alors puis pas bon près dès".split())
LIES = {"in fine", "parce que", "alors que", "ultra viral", "tout le", "le monde", "de monde", "la vente", "la confiance", "la preuve", "viens voir", "pas du", "du tout"}
T_COULEUR = (255, 214, 10, 255)                     # 02/11 : titre jaune, validé par l’utilisateur
T_SIZE, T_POIDS, T_Y, T_LARGE = 76, 700, 424, 840   # 02/11 : titre d'une ligne dans la bande du haut, 131 px au-dessus de l'image, 840 px centrés
sys.path.insert(0, S)
from reglages import config

if sys.argv[1:2] == ["derush"]:
    subprocess.run(["python3", f"{S}/derush.py", sys.argv[2], "words.rush.json", "cut.mp4", "--plages", "plages.json", "--vf", f"fps={FPS},scale={W}:{H}:flags=lanczos",
                    "--fin-libre", "--tail", "0.25", "--lead", "0.03"], check=True)
    from mots import transcrire
    w, moteur = transcrire("cut.mp4", langue="fr")
    json.dump({"words": w}, open("cut.words.json", "w"), ensure_ascii=False)
    print(moteur, len(w), "mots :", " ".join(x["text"].strip() for x in w))
    sys.exit()

if sys.argv[1:2] == ["teaser"]:   # 02/11 : le meilleur moment en ouverture, coupe sèche, puis la vidéo. Relançable : repart toujours de cut sans teaser.
    T_ = json.load(open("horizontal.json"))["teaser"]
    for x in ("cut.mp4", "cut.words.json", "cut.segments.json"):
        if not os.path.exists("sans-teaser." + x): shutil.copy2(x, "sans-teaser." + x)
    w = json.load(open("sans-teaser.cut.words.json"))["words"]
    seg = json.load(open("sans-teaser.cut.segments.json"))
    txt = [x["text"].strip().lower() for x in w]
    def cherche(phrase):
        m = phrase.lower().split()
        return next(i for i in range(len(txt)) if txt[i:i + len(m)] == m), len(m)
    a, _ = cherche(T_["de"]); b, n = cherche(T_["a"]); b += n - 1
    deb = w[a]["start"] - .06
    fin = min(w[b]["end"] + .15, w[b + 1]["start"] - .02) if b + 1 < len(w) else w[b]["end"] + .15
    D = round((fin - deb) * FPS) / FPS; fin = deb + D
    fc = (f"[0:v]trim={deb:.4f}:{fin:.4f},setpts=PTS-STARTPTS[v1];[0:a]atrim={deb:.4f}:{fin:.4f},asetpts=PTS-STARTPTS[a1];"
          "[0:v]setpts=PTS-STARTPTS[v2];[0:a]asetpts=PTS-STARTPTS[a2];[v1][a1][v2][a2]concat=n=2:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", "sans-teaser.cut.mp4", "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-r", str(FPS),
                    "-c:v", "h264_videotoolbox", "-b:v", "40M", "-c:a", "aac", "-b:a", "320k", "cut.mp4"], check=True)
    nw = [dict(x, start=x["start"] - deb, end=x["end"] - deb) for x in w[a:b + 1]] + [dict(x, start=x["start"] + D, end=x["end"] + D) for x in w]
    json.dump({"words": nw}, open("cut.words.json", "w"), ensure_ascii=False)
    json.dump([[0, D]] + seg, open("cut.segments.json", "w"))
    print(f"teaser {D:.2f} s :", " ".join(txt[a:b + 1]))
    sys.exit()

R = config()
LIB = os.path.join(R["brolls_root"], "VIDEOS")
C = json.load(open("horizontal.json"))
MUSIQUE = C["musique"] if os.path.isabs(C["musique"]) else os.path.join(R["music_reels"], C["musique"])
mots = json.load(open("cut.words.json"))["words"]
LIGNES = C.get("teaser", {}).get("lignes", []) + C["lignes"]
assert sum(n for _, n in LIGNES) == len(mots), (sum(n for _, n in LIGNES), len(mots))
assert max(len(t) for t, _ in LIGNES) <= 28, "ligne de plus de 28 signes"
bords, t = [0.0], 0.0
for a, b in json.load(open("cut.segments.json")): t += b - a; bords.append(round(t * FPS) / FPS)

def police(taille, poids):
    p = ImageFont.truetype(FONT, taille)
    p.set_variation_by_axes([poids if a["name"] in (b"Weight", "Weight") else a["default"] for a in p.get_variation_axes()])
    return p
f = police(SIZE, POIDS)
titre = (C.get("titre") or "").strip().upper()   # 02/11 (l’utilisateur : « mets toujours le titre en majuscule »)
t_f = police(T_SIZE, T_POIDS)
while titre and t_f.getlength(titre) > T_LARGE: t_f = police(t_f.size - 2, T_POIDS)   # toujours sur une seule ligne
def calque(txt, p):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    if txt:
        masque = Image.new("L", (CW, CH), 0); ImageDraw.Draw(masque).text((CW / 2, Y), txt, font=f, fill=255, anchor="mm")
        img.putalpha(masque.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * .85)))   # ombre noire légère, pas de contour
        img.paste((255, 255, 255, 255), mask=masque)
        ligne = txt.replace("\u00a0", " ")
        for cle in C.get("jaune", []):   # 02/11 : chiffre clé en jaune, comme le titre
            if cle in ligne:
                x = (CW - f.getlength(ligne)) / 2 + f.getlength(ligne[:ligne.index(cle)])
                m2 = Image.new("L", (CW, CH), 0); ImageDraw.Draw(m2).text((x, Y), cle, font=f, fill=255, anchor="lm")
                img.paste(T_COULEUR, mask=m2)
    if titre:   # présent dès la 1re image et jusqu'à la fin
        masque = Image.new("L", (CW, CH), 0); ImageDraw.Draw(masque).text((CW / 2, T_Y), titre, font=t_f, fill=255, anchor="mm")
        img.paste(T_COULEUR, mask=masque)
    img.save(p, compress_level=1)

os.makedirs("horizontal", exist_ok=True)
calque("", "horizontal/vide.png")
flux, debuts, k = [], {}, 0
for txt, n in LIGNES:
    debuts.setdefault(txt, mots[k]["start"])
    t_mots = re.sub(r"(?<=\d) (?=\d)", "\u00a0", txt.replace(" ?", "\u00a0?")).split(" "); q = len(t_mots)   # le « ? » reste collé à son mot, « 6 000 » reste entier
    for i, m in enumerate(t_mots):
        u, v = k + i * n // q, k + (i + 1) * n // q - 1
        flux.append((m, mots[u]["start"], mots[max(u, v)]["end"], i == q - 1))
    k += n
def cout(i, j):   # 02/11 : coupe au sens : jamais finir sur un petit mot ni couper une expression, couper de préférence en fin de ligne ou sur une pause
    d, c = flux[j][2] - flux[i][1], 1
    fin_ligne = flux[j][3]
    if not fin_ligne and flux[j][0].lower().strip(",") in FAIBLES: c += 6
    if j + 1 < len(flux):
        if (flux[j][0].lower() + " " + flux[j + 1][0].lower()) in LIES: c += 8
        if flux[j + 1][1] - flux[j][2] >= .15: c -= 1
    if fin_ligne: c -= 2
    if any(x[3] for x in flux[i:j]): c += 4   # les lignes sont déjà écrites au sens : éviter de les enjamber
    if d < .5: c += 2     # moins de 0,5 s = ça clignote
    if i == j and d < .8: c += 1.5
    if i == j and flux[j][0].lower().strip(",") in FAIBLES: c += 6   # jamais un petit mot seul à l'écran
    return c
meilleur = [(0, None)] + [(1e9, None)] * len(flux)
for j in range(len(flux)):
    for i in range(max(0, j - MAX_MOTS + 1), j + 1):
        c = meilleur[i][0] + cout(i, j)
        if c < meilleur[j + 1][0]: meilleur[j + 1] = (c, i)
blocs, j = [], len(flux)
while j:
    i = meilleur[j][1]
    blocs.insert(0, (" ".join(x[0] for x in flux[i:j]), flux[i][1], flux[j - 1][2])); j = i
retard = 0
for i in range(len(blocs) - 1):   # 0,33 s minimum à l'écran (0,4 = 0,38 s de retard sur la voix) : le morceau suivant attend, il rattrape la voix à la prochaine pause
    t2, a2, b2 = blocs[i + 1]
    retard = max(retard, blocs[i][1] + 1 / 3 - a2)
    blocs[i + 1] = (t2, max(a2, blocs[i][1] + 1 / 3), b2)
print(" / ".join(t for t, _, _ in blocs)); print(f"retard max sur la voix : {retard:.2f} s")
blocs[0] = (blocs[0][0], 0.0, blocs[0][2])   # texte présent dès la 1re image
def temps(v):   # une ligne (même image que son sous-titre) ou une coupe du dérush, à cacher en la dépassant de 0,3 s
    if isinstance(v, dict): return bords[v["coupe"] + ("teaser" in C)] + v.get("decale", 0)
    return round(debuts[v] * FPS) / FPS
BROLLS = [(b["src"], b.get("from", 1.0), temps(b["de"]), temps(b["a"]) + b.get("deborde", 0)) for b in C["brolls"]]   # deborde : 2 B-rolls collés, le 1er passe sous le 2e, sinon la cam ressort 2 images

fin = bords[-1]
liste, cur = [], 0.0
for i, (txt, a, b) in enumerate(blocs):
    suite = blocs[i + 1][1] if i + 1 < len(blocs) else fin
    b = suite if suite - b < 0.5 else b + 0.2
    a, b = round(a * FPS) / FPS, round(b * FPS) / FPS
    if a > cur: liste.append(("vide.png", a - cur))
    p = f"s{i:02d}.png"; calque(txt, "horizontal/" + p); liste.append((p, b - a)); cur = b
if fin > cur: liste.append(("vide.png", fin - cur))
with open("horizontal/calques.txt", "w") as o:
    for p, d in liste: o.write(f"file '{p}'\nduration {d:.4f}\n")
    o.write(f"file '{liste[-1][0]}'\n")
print(len(blocs), "sous-titres")

entrees = ["-i", "cut.mp4"]
fc, base = [], "[0:v]"
for n, (nom, ss, a, b) in enumerate(BROLLS, 1):
    entrees += ["-ss", str(ss), "-t", f"{b - a + .5:.2f}", "-i", os.path.join(LIB, nom)]
    fc.append(f"[{n}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},format=yuv420p,setpts=PTS-STARTPTS+{a:.4f}/TB[b{n}]")
    fc.append(f"{base}[b{n}]overlay=enable='gte(t,{a - .001:.4f})*lt(t,{b - .001:.4f})':eof_action=pass[v{n}]")
    base = f"[v{n}]"
n = len(BROLLS) + 1
entrees += ["-f", "concat", "-safe", "0", "-i", "horizontal/calques.txt"]
fc.append(f"{base}scale={IMG_H * W // H}:{IMG_H}:flags=lanczos,crop={CW}:{IMG_H},pad={CW}:{CH}:0:{IMG_Y}:black,setsar=1[cadre];[{n}:v]fps={FPS},format=rgba[o];[cadre][o]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[sortie]")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + entrees + ["-filter_complex", ";".join(fc), "-map", "[sortie]", "-an", "-r", str(FPS),
    "-c:v", "h264_videotoolbox", "-profile:v", "high", "-b:v", "14M", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
    "-color_trc", "bt709", "-t", f"{fin:.3f}", "horizontal/rendu.mp4"], check=True)

# voix intacte, musique continue, départ sec + 6 dB pendant 2,5 s (28/10), basses allégées pour le téléphone
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(C.get("debut", 0)), "-t", f"{fin + .5:.2f}", "-i", MUSIQUE, "-af",
    "bass=g=-6:f=150,volume='if(lt(t,2.5),2,if(lt(t,4.5),2-(t-2.5)/2,1))':eval=frame", "horizontal/musique.wav"], check=True)
subprocess.run(["python3", f"{S}/mix_youtube.py", "horizontal/rendu.mp4", "cut.mp4", "final.mp4", "--musique", "horizontal/musique.wav", "--ecart", str(C.get("ecart", 15))], check=True)
if "/tmp/" not in os.getcwd():   # carnet des musiques (variété) : même format que mix.py, mix_youtube.py ne l'écrit pas
    J_ = os.path.join(S, "..", "musiques_utilisees.csv")
    rows = list(csv.reader(open(J_))) if os.path.exists(J_) else []
    rows = [r for r in rows[1:] if r and r[1] != os.getcwd()] + [[datetime.date.today().isoformat(), os.getcwd(), MUSIQUE]]
    w_ = csv.writer(open(J_, "w", newline="")); w_.writerow(["date", "reel", "musique"]); w_.writerows(rows)
json.dump({"cam": "clip.mp4", "words": "words.json", "zoom": False, "cases": {"titre": bool(titre), "sous_titres": True, "musique": True}, "duree_min": C.get("duree_min", 0),
    "_note": "style horizontal : image zoomée en 4:3 entre deux bandes noires, sous-titres sur l'image, scripts/horizontal.py + horizontal.json",
    "brolls": [{"src": n, "from": ss, "start": a, "end": b} for n, ss, a, b in BROLLS]}, open("plan.json", "w"), ensure_ascii=False, indent=1)
