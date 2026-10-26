"""Note auto /10 d'un reel monté (étape 5 du process client, 13/10 ; codé le 25/10/2026). Grille SEULE de note-10.md, sans
vidéo de référence, + garde-fous BLOQUANTS. Sous 8/10 on refait (2 essais de plus max, visuels réutilisés), puis on livre avec la note.
  python3 note.py <dossier du reel>
1er passage : mesure tout (score.py, gardien.json, saccades, néon, visages des visuels générés), sort score/planche.jpg et
score/hook.jpg, et écrit oeil.json À REMPLIR (ce qu'aucune mesure ne voit : fautes, chiffres, listes, B-rolls, hook, fini).
Claude regarde les planches, remplit oeil.json (0 / 0.5 / 1 ; dans le doute 0.5), relance : note /10 + verdict.
Verdict (code de sortie) : 0 = LIVRER (ou livrer avec la note après 3 versions), 1 = REFAIRE, 2 = NE PAS LIVRER (garde-fou), 3 = oeil.json à remplir.
Historique des versions : note.json (une version = un final.mp4 différent).
Garde-fous (un seul = pas de livraison, quelle que soit la note) : chrome / néon, faux visage, flash de tête entre deux pleins
écrans, sous-titres illisibles, saccades, plus d'1 silence, et tout ❌ du Gardien (erreurs déjà signalées).
"""
import glob, json, os, re, subprocess, sys
import numpy as np

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
J = lambda f, d=None: json.load(open(os.path.join(D, f))) if os.path.exists(os.path.join(D, f)) else d
P = lambda f: os.path.join(D, f)
FINAL = P("final.mp4")
if not os.path.exists(FINAL): sys.exit("pas de final.mp4 dans " + D)
plan = J("plan.json", {})

# ---------- mesures ----------
G = J("gardien.json")
if G is None or os.path.getmtime(P("gardien.json")) < os.path.getmtime(FINAL):   # Gardien périmé = relancé sur ce final
    subprocess.run([sys.executable, os.path.join(S, "gardien.py"), D], capture_output=True)
    G = J("gardien.json", [])
KO = {g["controle"] for g in G if g.get("ok") is False}
subprocess.run([sys.executable, os.path.join(S, "score.py"), FINAL, FINAL], cwd=D, capture_output=True)   # ref = lui-même : aucun étalon externe
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", FINAL, "-vf", "fps=1,scale=180:-2,tile=10x7", "-frames:v", "1", P("score/planche.jpg")])
M = (J("score/metrics.json") or {}).get("final", {})
mixlog = open(P("mix.log")).read() if os.path.exists(P("mix.log")) else ""


def saccades(path):
    """Images en double isolées au milieu du mouvement (ex. B-roll 24 i/s posé dans une vidéo 30 i/s) : ça saccade.
    Une image fixe (carton, photo) n'est pas une saccade : on ne compte que les doublons entourés d'images qui bougent."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=72:128,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 128, 72).astype(np.int16)
    fps = eval(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                        "stream=avg_frame_rate", "-of", "csv=p=0", path]).decode().strip() or "30")
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))            # d[i] = écart image i -> i+1
    dup = [i for i in range(1, len(d) - 1) if d[i] < 0.3 and d[i - 1] > 1.2 and d[i + 1] > 1.2]
    t = np.array(dup) / fps
    zones = sorted({round(float(x), 1) for x in t if ((t >= x) & (t < x + 2)).sum() >= 4})   # >= 4 doublons en 2 s
    # 25/10 : HyperFrames 0.6.81 prend l'image floor((i/30)*30) = i-1 pour certaines images (4,10 / 8,17 / 16,33 / 32,17 s…) :
    # doublon + image sautée, mêmes instants sur TOUS les reels. Corrigé dans HyperFrames 0.8 (+1e-9). Sinon : B-roll à une autre cadence.
    r = round(fps)   # cadence du rendu (le final mixé affiche 30,01 en moyenne)
    arrondi = {i for i in range(len(f) + 2) if int(np.floor((i / r) * r)) != i}
    hf = len(dup) > 0 and sum(1 for i in dup if i in arrondi or i + 1 in arrondi) >= 0.8 * len(dup)
    return zones, len(dup), hf


def neon(p):
    from lookstats import measure
    try: return measure(p)["neon"]
    except Exception: return None


def visage(p):
    from lookstats import face, frames
    try: return face(p, 6).get("visage_vu", 0)
    except Exception: return 0


# visuels générés (Higgsfield, Gemini) : dossier genere/ du reel + éléments du plan marqués "genere": true
items = [x for k in ("brolls", "inserts", "motions", "proofs") for x in (plan.get(k) or []) if isinstance(x, dict)]
genere = sorted(set(glob.glob(P("genere/*")) + [os.path.join(D, x["src"]) if not os.path.isabs(x["src"]) else x["src"]
                                                for x in items if x.get("genere") and x.get("src")]))
genere = [g for g in genere if os.path.exists(g)]
ajoutes = sorted(set(genere + [os.path.join(D, x["src"]) if not os.path.isabs(x["src"]) else x["src"]
                               for x in items if x.get("src") and re.search(r"\.(png|jpe?g|webp)$", x["src"], re.I)]))
ajoutes = [a for a in ajoutes if os.path.exists(a)]
sacc, ndup, sacc_hf = saccades(FINAL)
html = open(P("index.html")).read() if os.path.exists(P("index.html")) else ""
css_chrome = bool(re.search(r"background-clip\s*:\s*text[^}]*gradient|gradient[^}]*background-clip\s*:\s*text", html)) or \
             bool(re.search(r"(chrome|metal|silver|neon|néon)", " ".join(re.findall(r'class="([^"]+)"', html)), re.I))
neon_vis = {os.path.basename(a): n for a in ajoutes if (n := neon(a)) is not None and n >= 0.5}
faux = {os.path.basename(g): v for g in genere if (v := visage(g)) > 0}
silences = plan.get("silences") or ((plan.get("music") or {}).get("silences", []) if isinstance(plan.get("music"), dict) else [])
car = M.get("car_par_s_max")

# ---------- l'œil (ce qu'aucune mesure ne voit) ----------
mots = J("words.json", [])
mots = mots.get("words", mots) if isinstance(mots, dict) else mots
a_chiffres = bool(plan.get("numbers")) or any(re.search(r"\d", w.get("text", "")) for w in mots)
a_listes = bool(plan.get("lists") or plan.get("bullets"))
a_brolls = bool(plan.get("brolls"))
QUESTIONS = {
    "1": "Hook : dans les 3 premières s, quelque chose bouge ou claque ? (score/hook.jpg)",
    "3": "Sous-titres : 1 bloc à la fois, mots forts seuls, rien sur le cou ? (fautes comptées à part)",
    "4": "Chiffres : tête devant chaque chiffre, lisible, pas coupé ?" if a_chiffres else None,
    "5": "Listes / pastilles : lisibles, contenu de la personne (rien d'inventé) ?" if a_listes else None,
    "7": "B-rolls : montrent EXACTEMENT ce qui est dit, beaux, nets, même personne ?" if a_brolls else None,
    "10": "Fini pro : aucun visage coupé, aucun bug visuel ?",
}
QUESTIONS = {k: v for k, v in QUESTIONS.items() if v}
EXTRA = {"fautes_sous_titres": "nombre de fautes lues dans les sous-titres (entier)",
         "chrome": "true si un texte ou visuel fait chrome / métal / néon",
         "faux_visage": "true si un visuel généré montre un visage (humain ou pas la personne)",
         "sous_titres_illisibles": "true si un sous-titre est illisible (trop petit, sur fond clair sans ombre, coupé)"}
O = J("oeil.json")
if O is None or os.path.getmtime(P("oeil.json")) < os.path.getmtime(FINAL) or any(O.get(k) is None for k in list(QUESTIONS) + list(EXTRA)):
    json.dump({**{k: None for k in QUESTIONS}, **{k: None for k in EXTRA},
               "_questions": {**QUESTIONS, **EXTRA}, "_regle": "0 / 0.5 / 1 ; dans le doute 0.5. Ne pas se gonfler la note."},
              open(P("oeil.json"), "w"), indent=1, ensure_ascii=False)
    print("À L'ŒIL : regarder score/planche.jpg (1 image/s) et score/hook.jpg (3 premières s), remplir oeil.json, relancer note.py")
    for k, q in {**QUESTIONS, **EXTRA}.items(): print(f"  {k:24} {q}")
    sys.exit(3)
eye = lambda k: float(O[k]) if O.get(k) is not None else 1.0

# ---------- la grille (10 critères, 0 / 0.5 / 1 ; sans objet = retiré, note ramenée sur 10) ----------
crit, why = {}, {}


def C(k, nom, v, raison=""):
    crit[k] = (nom, v); why[k] = raison


def palier(n): return 1.0 if n == 0 else 0.5 if n == 1 else 0.0


pc = M.get("premier_changement_s")
hook_plan = bool(plan.get("title") or plan.get("hook") or any(z.get("start", 9) < 3 for z in (plan.get("zooms") or []) if isinstance(z, dict)))
C("1", "Hook", min(1.0 if (pc is not None and pc <= 3) or hook_plan else 0.5, eye("1")),
  "" if (pc is not None and pc <= 3) or hook_plan else f"rien ne change avant {pc} s")
der = KO & {"Micro-coupes", "Silences entendus", "Pas de trou de son", "Pas de mot coupé", "Pas de respiration en début de phrase", "Zéro micro-coupure"}
v = palier(len(der))
if (M.get("mots_par_min") or 0) > 240: v = min(v, 0.5)
C("2", "Dérush", v, ", ".join(sorted(der)) + (f" débit {M.get('mots_par_min')} mots/min > 240" if (M.get("mots_par_min") or 0) > 240 else ""))
v = 1.0 if car is None or car <= 20 else 0.5 if car <= 24 else 0.0
if "Zones mortes Insta" in KO: v = 0.0
f = int(O.get("fautes_sous_titres") or 0)
C("3", "Sous-titres", min(v, palier(f), eye("3")),
  f"{car} car/s (max 20)" * (car is not None and car > 20) + (f" {f} faute(s)" if f else "") + (" hors zone sûre" if "Zones mortes Insta" in KO else ""))
if a_chiffres: C("4", "Chiffres", eye("4"))
if a_listes: C("5", "Listes", eye("5"))
pl = M.get("plus_long_plan_fixe_s") or 0
tol = 3 if plan.get("zoom") or plan.get("zooms") else 0          # le détecteur ne voit pas les zooms
v = 1.0 if pl <= 7 + tol else 0.5 if pl <= 10 + tol else 0.0
if "Plans ≥ 2 s" in KO: v = min(v, 0.5)
C("6", "Rythme", v, f"plan fixe de {pl} s" if v < 1 else "")
if a_brolls:
    b = KO & {"B-rolls sans HDR", "Plans ≥ 1,2 s"}
    C("7", "B-rolls", min(palier(len(b)), eye("7")), ", ".join(sorted(b)))
mus = plan.get("music")
mk = KO & {"Musique dès 0 s", "Musique jusqu'au bout", "Musique jamais coupée"}
v = 0.0 if not mus else palier(len(mk))
src_mus = (mus or {}).get("src") if isinstance(mus, dict) else None
livres = os.path.expanduser(json.load(open(os.path.join(os.path.dirname(S), "config.json"))).get("livres", "~/Documents/Montage/LIVRES")) \
    if os.path.exists(os.path.join(os.path.dirname(S), "config.json")) else os.path.expanduser("~/Documents/Montage/LIVRES")
prec = sorted(glob.glob(os.path.join(livres, "*", "note.json")), key=os.path.getmtime)
prec = [p for p in prec if os.path.dirname(p) != D]
meme = bool(src_mus and prec and (json.load(open(prec[-1])).get("musique") == src_mus))
if meme: v = min(v, 0.5)
C("8", "Musique", v, "pas de musique" * (not mus) + ", ".join(sorted(mk)) + " même musique que le reel précédent" * meme)
lufs = M.get("lufs")
v = 1.0 if lufs is not None and -15 <= lufs <= -13 else 0.5 if lufs is not None and -16 <= lufs <= -12 else 0.0
nsfx = int((re.findall(r"(\d+) SFX", mixlog) or [0])[-1])
dur = M.get("duree_s") or 1
if "Bruitages espacés" in KO or nsfx > dur / 4: v = min(v, 0.5)
if nsfx > 12 * dur / 40: v = 0.0
C("9", "Son", v, f"{lufs} LUFS (cible -15 à -13)" * (v < 1) + f" {nsfx} SFX en {dur:.0f} s" * (nsfx > dur / 4))
fin = KO & {"Image dès 0 s", "Pas de flash d'image", "Pas de fin muette"}
cam = []
if M.get("cam_noirs_P1") is not None and not (1 <= M["cam_noirs_P1"] <= 8): cam.append(f"noirs P1 {M['cam_noirs_P1']}")
if (M.get("cam_P99") or 0) > 235: cam.append(f"blancs brûlés P99 {M['cam_P99']}")
C("10", "Fini pro", min(palier(len(fin) + (len(cam) > 0)), eye("10")), ", ".join(sorted(fin) + cam))

note = round(10 * sum(v for _, v in crit.values()) / len(crit), 1)

# ---------- garde-fous bloquants ----------
B = []
if css_chrome or neon_vis or (M.get("cam_neon_%") or 0) >= 0.5 or O.get("chrome"):
    B.append("chrome / néon : " + ", ".join(filter(None, ["texte en dégradé métal dans index.html" if css_chrome else "",
                                                          f"néon dans {neon_vis}" if neon_vis else "",
                                                          f"cam néon {M.get('cam_neon_%')} %" if (M.get("cam_neon_%") or 0) >= 0.5 else "",
                                                          "vu à l'œil" if O.get("chrome") else ""])))
if faux or O.get("faux_visage"):
    B.append("faux visage : " + (f"visage trouvé dans {list(faux)}" if faux else "vu à l'œil") + " (jamais un visage généré)")
if KO & {"Pas de flash de tête", "Pas de flash d'image"}:
    B.append("flash de tête entre deux pleins écrans (voir gardien.json)")
if (car or 0) > 24 or "Zones mortes Insta" in KO or O.get("sous_titres_illisibles"):
    B.append("sous-titres illisibles : " + ", ".join(filter(None, [f"{car} car/s > 24" if (car or 0) > 24 else "",
                                                                   "hors zone sûre Instagram" if "Zones mortes Insta" in KO else "",
                                                                   "vu à l'œil" if O.get("sous_titres_illisibles") else ""])))
if sacc:
    B.append(f"saccades vers {sacc[:6]} s ({ndup} images en double) : " + (
        "bug d'arrondi du rendu HyperFrames 0.6.81 : rien à corriger dans le plan, rendre avec monte.sh (HyperFrames 0.8.149)" if sacc_hf
        else "B-roll à une autre cadence, le repasser à 30 i/s (broll.py prep)"))
if len(silences) > 1 or "silences demandés" in mixlog:
    B.append(f"{max(len(silences), 2)} silences : 1 seul par reel")
reste = KO - {"Pas de flash de tête", "Pas de flash d'image", "Zones mortes Insta"}
if reste:
    B.append("Gardien ❌ : " + ", ".join(sorted(reste)))

# ---------- historique des versions + verdict ----------
H = J("note.json", {"essais": []})
sig = f"{os.path.getsize(FINAL)}-{int(os.path.getmtime(FINAL))}"
E = {"final": sig, "note": note, "bloquants": B, "criteres": {k: {"nom": n, "note": v, "pourquoi": why[k]} for k, (n, v) in crit.items()}}
if H["essais"] and H["essais"][-1]["final"] == sig: H["essais"][-1] = E
else: H["essais"].append(E)
n = len(H["essais"])
H["musique"] = src_mus
print(f"NOTE {note}/10  (version {n}/3, {len(crit)} critères notés)")
for k, (nom, v) in crit.items():
    print(f"  {'✅' if v == 1 else '🟠' if v == 0.5 else '❌'} {k:>2}. {nom:12} {v}" + (f"  {why[k].strip(' ,')}" if v < 1 and why[k].strip() else ""))
for b in B: print("  ⛔ " + b)
rates = [f"{nom} {v}" + (f" ({why[k].strip(' ,')})" if why[k].strip() else "") for k, (nom, v) in crit.items() if v < 1]
if note >= 8 and not B:
    H["verdict"] = "LIVRER"; code = 0
    print(f"\n✅ LIVRER : {note}/10")
elif n < 3:
    H["verdict"] = "REFAIRE"; code = 1
    print(f"\n🔁 REFAIRE (version {n + 1}/3, visuels réutilisés) : corriger " + "; ".join(B + rates))
elif B:
    H["verdict"] = "NE PAS LIVRER"; code = 2
    print(f"\n⛔ NE PAS LIVRER après 3 versions : {B[0]}. Le dire au client en 1 ligne.")
else:
    H["verdict"] = "LIVRER AVEC LA NOTE"; code = 0
    print(f"\n📦 LIVRER AVEC LA NOTE {note}/10 (3 versions faites). Ce qui coince : " + "; ".join(rates))
json.dump(H, open(P("note.json"), "w"), indent=1, ensure_ascii=False)
sys.exit(code)
