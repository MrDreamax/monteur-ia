"""B-rolls : créneaux réguliers + recherche dans la bibliothèque.

  python3 broll.py slots plan.json words.json --density low|high
      -> créneaux répartis RÉGULIÈREMENT sur toute la vidéo (jamais groupés), hors hook, chiffres, listes, pastilles.
         low  = 1 plan de ~1.8 s toutes les ~8 s (illustration posée)
         high = 1 plan de ~1 s toutes les ~3.5 s (très dynamique)
         Pour chaque créneau : les mots prononcés à ce moment-là (= ce qu'il faut illustrer).
  python3 broll.py prep plan.json
      -> copie chaque B-roll choisi (plan.brolls[].src absolu + from) dans broll/ : coupé, recadré 1080x1920, 30 i/s.
  python3 broll.py search mot1 mot2 ...
      -> 12 plans de la bibliothèque (config.json : brolls_index), 1 seul par geste (colonne action).
         Ordre (20/10, 2e plainte « toujours les mêmes ») : mots qui collent > vidéo caméra avant photo avant téléphone
         > vertical (un plan horizontal recadré en 9:16 est flou) > JAMAIS MONTÉ d'abord (broll_utilises.csv)
         > rang « beau » (broll_tri.csv) > tirage au sort,
         différent à chaque reel (graine = dossier du reel). Avant : tri fixe « vertical puis le plus long » = les 12
         mêmes plans en tête à chaque fois. Les plans « ecarte » (tremble, flou, refusés : broll_refuses.txt) ne sortent
         plus ; --tout pour les revoir. Bibliothèque modifiée ? relancer scripts/broll_tri.py (ne mesure que les nouveaux).
  python3 broll.py recents [3]
      -> les plans déjà montés dans les 3 derniers reels (broll_utilises.csv) : search ne les propose plus.
         20/10 (Titanic) : « tu me recommandes toujours les mêmes b-rolls, il y a une redondance : varie, change ».
         search --deja-vus = les remettre (seulement si la bibliothèque n'a rien d'autre qui colle).
  python3 broll.py steady fichier.mp4 2.5
      -> le passage de 2,5 s le plus STABLE du fichier (13/10 : « toujours des plans stables en b-roll »).
         Tremblement = déplacement de l'image d'une image à l'autre (px, image de 270 px de large).
         Bon : moyenne <= 1,2 et pic <= 6 (son monteur : 0 à 1,4). prep l'utilise tout seul si "from": "auto".
B-rolls BRUTS : jamais de filtre ni d'étalonnage créatif (13/10 : « filtres bizarres, super moche »).
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reglages  # config.json du skill + réglages de cette machine (Brain)
CFG = reglages.config()
PASSE = ("souvenir", "passe", "avant", "enfan", "jeune", "ado", "etudi", "papa", "pere", "debut", "ancien", "galere", "ouvrier")

def slots(plan_p, words_p, density):
    plan = json.load(open(plan_p)); W = json.load(open(words_p))["words"]
    import subprocess
    cam = os.path.join(os.path.dirname(os.path.abspath(plan_p)), plan["cam"])
    dur = plan.get("duration") or float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", cam]))
    every, length = {"low": (8.0, 1.8), "high": (3.5, 1.0)}[density]
    busy = [(0, 2.2), (dur - 1.0, dur)]                       # hook + fin
    busy += [(n["start"] - .3, n["end"] + .3) for n in plan.get("numbers", [])]
    busy += [(l["start"] - .3, l["end"] + .3) for l in plan.get("lists", [])]
    if plan.get("bullets"): busy.append((plan["bullets"]["at"][0] - .3, plan["bullets"]["end"] + .3))
    free = lambda a, b: all(b <= x or a >= y for x, y in busy)
    out, t = [], 2.2 + every / 2
    while t < dur - 1.5:
        # on cherche le début de mot libre le plus proche de la cible t (créneaux réguliers, calés sur la voix)
        cands = sorted((abs(w["start"] - t), w["start"]) for w in W if free(w["start"], w["start"] + length))
        if cands and cands[0][0] < every / 2:
            a = round(cands[0][1] - 0.03, 2); b = round(a + length, 2)
            said = " ".join(w["text"] for w in W if a - 0.6 <= w["start"] <= b + 0.3)
            out.append({"start": a, "end": b, "dit": said})
        t += every
    print(json.dumps(out, ensure_ascii=False, indent=1))

RANG = {"beau": 0, "ok": 1}                                   # dans les vidéos caméra
GROUPE = {"photo": 1, "telephone": 2}                         # 0 = vidéo caméra ; « plans téléphone moches » (19/10) en dernier
def rangs():
    p = os.path.join(HERE, "broll_tri.csv")                   # écrit par scripts/broll_tri.py
    return {r["fichier"]: r["rang"] for r in csv.DictReader(open(p, encoding="utf-8"))} if os.path.exists(p) else {}
def usages():
    """{fichier: nombre de reels où il a déjà été monté}."""
    if not os.path.exists(USED): return {}
    n = {}
    for f_, _ in {(r["fichier"], r["reel"]) for r in csv.DictReader(open(USED, encoding="utf-8"))}: n[f_] = n.get(f_, 0) + 1
    return n

def search(terms):
    import hashlib
    deja, tout = "--deja-vus" in terms, "--tout" in terms
    terms = [t for t in terms if t not in ("--deja-vus", "--tout")]
    vus = {} if deja else recents()
    tri, nb, graine, ecartes = rangs(), usages(), os.path.basename(os.getcwd()), 0
    alea = lambda f_: hashlib.md5((graine + f_).encode()).hexdigest()   # même ordre pendant un montage, autre ordre au suivant
    p = CFG.get("brolls_index")
    if not p or not os.path.exists(p):
        print("Bibliothèque B-roll introuvable (config.json : brolls_index). Disque branché ?"); return
    terms = [t.lower() for t in terms]
    rows, mini = [], CFG.get("brolls_min_date", "")
    passe = any(t.startswith(PASSE) for t in terms)
    ex = os.path.join(HERE, "broll_exclus.txt")   # plans où la personne N'EST PAS l'utilisateur (ex. un ami, 14/10)
    exclus = {l.split("#")[0].strip() for l in open(ex, encoding="utf-8")} - {""} if os.path.exists(ex) else set()
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r.get("action") in exclus: continue
        if r.get("fichier") in vus: continue                       # 20/10 : déjà monté dans un des 3 derniers reels -> on varie
        rang = tri.get(r.get("fichier"), "ok")
        if rang == "ecarte" and not tout: ecartes += 1; continue   # tremble, flou, refusé par l'utilisateur (broll_tri.csv)
        if mini and r.get("date_tournage", "") < mini: continue   # tourné trop tôt (ancien visage) ou non daté
        if r.get("usage") == "souvenir" and not passe: continue   # photo de jeunesse : seulement quand il parle de son passé
        hay = " ".join([r.get("theme", ""), r.get("action", ""), r.get("lieu", ""), r.get("tenue", ""), r.get("usage", "")]).lower()
        score = sum(t in hay for t in terms)
        if score and (r.get("qualite", "ok") == "ok" or r.get("usage") == "souvenir"):   # vieille photo = qualité moyenne normale
            f_ = r.get("fichier")
            rows.append(((-score, GROUPE.get(rang, 0), r.get("orientation") != "V", nb.get(f_, 0), RANG.get(rang, 1), alea(f_)),
                         score, rang, float(r.get("duree_s") or 0), r))
    rows.sort(key=lambda x: x[0])
    gestes, pick = set(), []
    for row in rows:                                           # 1 plan par geste : pas 3 fois « joue aux échecs »
        if row[4].get("action") in gestes: continue
        gestes.add(row[4].get("action")); pick.append(row)
        if len(pick) == 12: break
    for _, s, rang, d, r in pick:
        n = nb.get(r["fichier"], 0)
        print(f'{s} {r["orientation"]} {d:5.1f}s {rang:9} {"jamais monté" if not n else f"monté {n}x":12} {os.path.join(CFG["brolls_root"], r["dossier"], r["fichier"])}  [{r["action"]} · {r["lieu"]} · personne visible={r.get(reglages.colonne_visible(CFG))} · {r.get("date_tournage")}{" · SOUVENIR" if r.get("usage") == "souvenir" else ""}]')
    if vus: print(f"({len(vus)} plans des 3 derniers reels écartés pour varier : broll.py recents ; --deja-vus pour les remettre)")
    if ecartes: print(f"({ecartes} plans écartés par le tri : tremblent, flous ou refusés ; --tout pour les revoir)")
    if not tri: print("(tri de la bibliothèque absent : lancer scripts/broll_tri.py)")
    if not rows: print("Rien d'adapté." + (" -> générer avec Higgsfield." if CFG.get("higgsfield") else " (Higgsfield désactivé : pas de B-roll ici.)"))

USED = os.path.join(HERE, "broll_utilises.csv")   # date,reel,fichier,from,duree : 1 ligne par plan monté (prep l'écrit)
def recents(n=3):
    """{fichier: reel} pour les plans montés dans les n derniers reels (ordre d'écriture du journal)."""
    if not os.path.exists(USED): return {}
    rows = list(csv.DictReader(open(USED, encoding="utf-8")))
    reels = []
    for r in rows:
        if r["reel"] not in reels: reels.append(r["reel"])
    last = set(reels[-n:])
    return {r["fichier"]: r["reel"] for r in rows if r["reel"] in last}
def log_used(reel, fichier, frm, du):
    import datetime
    new = not os.path.exists(USED)
    rows = [] if new else list(csv.DictReader(open(USED, encoding="utf-8")))
    if any(r["reel"] == reel and r["fichier"] == fichier for r in rows): return
    with open(USED, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["date", "reel", "fichier", "from", "duree"])
        w.writerow([datetime.date.today().isoformat(), reel, fichier, f"{float(frm):.2f}", f"{du:.2f}"])

SHAKE_MAX, PEAK_MAX = 1.2, 6.0

def shakes(path, ss=0, du=None):
    """Déplacement global image à image (corrélation de phase), à 15 i/s, en px pour 270x480."""
    import subprocess
    import numpy as np
    W, H = 270, 480
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss)] + (["-t", str(du)] if du else []) + ["-i", path, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=15", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    f = np.frombuffer(subprocess.check_output(cmd), np.uint8).reshape(-1, H, W).astype(np.float32)
    win = np.outer(np.hanning(H), np.hanning(W)); F = [np.fft.fft2(x * win) for x in f]; d = []
    for A, B in zip(F, F[1:]):
        R = A * np.conj(B); R /= np.abs(R) + 1e-9; r = np.abs(np.fft.ifft2(R)); y, x = np.unravel_index(r.argmax(), r.shape)
        y, x = (y - H if y > H // 2 else y), (x - W if x > W // 2 else x); d.append((x * x + y * y) ** .5 / 2)   # /2 : 15 i/s -> px par image à 30 i/s
    return np.array(d)

def steady(path, du):
    """(from, moyenne, pic) du passage de du secondes le plus stable."""
    import numpy as np
    d = shakes(path); n = max(1, int(du * 15)); best = None
    for i in range(0, max(1, len(d) - n + 1)):
        w = d[i:i + n]; sc = (w.mean(), w.max())
        if best is None or sc[0] + sc[1] / 10 < best[1] + best[2] / 10: best = (i / 15, *sc)
    return best

def hdr(path):
    import subprocess
    t = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return t in ("arib-std-b67", "smpte2084")

def prep(plan_p):
    import subprocess
    d = os.path.dirname(os.path.abspath(plan_p)); plan = json.load(open(plan_p))
    os.makedirs(os.path.join(d, "broll"), exist_ok=True)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
    for i, b in enumerate(plan.get("brolls", [])):
        if not os.path.isabs(b["src"]): continue
        img = b["src"].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        name = f"broll/b{i}.jpg" if img else f"broll/b{i}.mp4"
        if not img:   # plan stable obligatoire : "from": "auto" = meilleur passage ; sinon on mesure et on prévient
            du = b["end"] - b["start"]
            if b.get("from") == "auto": b["from"], m, pk = steady(b["src"], du)
            else: d_ = shakes(b["src"], b.get("from", 0), du); m, pk = d_.mean(), d_.max()
            print(f"  tremblement {m:.2f} px/img, pic {pk:.1f}" + ("  <-- INSTABLE : prendre un autre passage (from auto) ou un autre plan" if m > SHAKE_MAX or pk > PEAK_MAX else "  (stable)"))
        src_cut, ss = b["src"], b.get("from", 0)
        # 20/10 (Titanic) : un B-roll iPhone HDR (HLG, BT.2020 10 bits) faisait passer tout le rendu HyperFrames en « HDR
        # layered composite » : mot géant et chiffres cachés derrière la tête, sortie HEVC 10 bits. Tout B-roll HDR est
        # converti en SDR bt709 par la conversion Apple (avconvert, la plus naturelle des 4 testées le 16/10) avant la coupe.
        if not img and hdr(b["src"]):
            src_cut = os.path.join(d, "broll", f"_sdr{i}.mov")
            subprocess.check_call(["avconvert", "-p", "Preset3840x2160", "-s", b["src"], "-o", src_cut, "--replace",
                                   "--start", f"{float(ss):.3f}", "--duration", f"{b['end'] - b['start'] + 1.2:.2f}"],
                                  stdout=subprocess.DEVNULL)
            ss = 0
            print(f"  HDR -> SDR (avconvert) : {os.path.basename(b['src'])}")
        cmd = ["ffmpeg", "-y", "-v", "error"] + ([] if img else ["-ss", str(ss)]) + ["-i", src_cut]
        cmd += ["-vf", vf.replace(",fps=30", "") if img else vf] + (["-frames:v", "1", "-q:v", "2"] if img else
               # 20/10 (« Mode difficile » v4 : 0,13 s d'écran NOIR à 33,8 s) : build.mjs fait chevaucher les pleins écrans enchaînés
               # (B-roll qui démarre 0,35 s plus tôt sous un carton, ou qui se prolonge 0,35 s sous le suivant) : marge de 0,9 s en fin.
               ["-t", f"{b['end'] - b['start'] + 0.9:.2f}", "-an", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"])
        subprocess.check_call(cmd + [os.path.join(d, name)])
        log_used(os.path.basename(d), os.path.basename(b["src"]), b.get("from", 0), b["end"] - b["start"])
        b["orig"], b["src"], b["from"] = b["src"], name, 0
        print(name, "<-", b["orig"])
    json.dump(plan, open(plan_p, "w"), ensure_ascii=False, indent=1)

if sys.argv[1] == "prep":
    prep(sys.argv[2])
elif sys.argv[1] == "steady":
    f_, m, pk = steady(sys.argv[2], float(sys.argv[3]))
    print(f"from {f_:.2f}s  tremblement {m:.2f} px/img, pic {pk:.1f}" + ("  <-- INSTABLE, changer de plan" if m > SHAKE_MAX or pk > PEAK_MAX else "  (stable)"))
elif sys.argv[1] == "recents":
    for f_, r_ in recents(int(sys.argv[2]) if len(sys.argv) > 2 else 3).items(): print(r_, f_)
elif sys.argv[1] == "slots":
    slots(sys.argv[2], sys.argv[3], sys.argv[sys.argv.index("--density") + 1] if "--density" in sys.argv else "low")
else:
    search(sys.argv[2:])
