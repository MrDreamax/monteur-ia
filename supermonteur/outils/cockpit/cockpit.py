#!/usr/bin/env python3
"""Le Cockpit du Monteur (22/10/2026) : la page où l'on monte son reel en 5 étapes, sans rien écrire.
  python3 cockpit.py <dossier du reel> [--port 8790] [--lab]
  --lab = DERUSH LAB (23/10, interne) : la timeline seule, pour dérusher ; « Valider le dérush » = clip.mp4 + Gardien du dérush.
Puis ouvrir http://127.0.0.1:8790 (Chrome).

Le dossier est préparé par le Monteur (SKILL étapes 1-4 : transcription du rush, dérush, plan.json) + cockpit.json =
les propositions de Claude (3 hooks, 3 musiques, légende). Voir COCKPIT.md.
Rien n'est rendu avant « Fabriquer » : la page montre un aperçu (la vidéo + des calques HTML), puis monte.sh fabrique le
vrai reel (Gardien compris). Écrit dans le dossier : cockpit-etat.json (les choix), cockpit-notes.json (ce que la personne
dit à Claude), publication.json (demande de programmation : rien ne part sans un OK dans le chat), plan.json (à Fabriquer).
v2 (22/10) : l'Export fabrique les 6 contenus, un par un (Mac 8 Go) : story/, carrousel/ (skill carrousel), le reel,
essais/<id>/ (reels d'essai : même montage, autre hook, monte.sh + Gardien dans leur dossier), puis publication.json.
"""
import base64, datetime as dt, json, os, re, shutil, signal, subprocess, sys, threading, time, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ICI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(ICI, "..", ".."))
S = os.path.join(SKILL, "scripts")
D = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8790
LAB = "--lab" in sys.argv   # Derush Lab (23/10, l'utilisateur : « exclusivement pour dérusher ») : pas de plan.json, pas de Style ni d'Export
AP = os.path.join(D, "_cockpit")
os.makedirs(AP, exist_ok=True)
VERROU = threading.Lock()


def lire(nom, defaut=None):
    p = os.path.join(D, nom)
    return json.load(open(p)) if os.path.exists(p) else defaut


def ecrire(nom, v):
    tmp = os.path.join(D, nom + ".tmp")
    json.dump(v, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(D, nom))


_DUREES = {}


def duree(p):
    # mémorisée par date de modification : sinon chaque rafraîchissement de la page relance ffprobe (~1 s)
    cle = (p, os.path.getmtime(p) if p and os.path.exists(p) else 0)
    if cle not in _DUREES:
        _DUREES[cle] = _duree(p)
    return _DUREES[cle]


def _duree(p):
    try:
        return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                              "-of", "csv=p=0", p]).decode().strip())
    except Exception:
        return 0.0


COCKPIT = lire("cockpit.json")
if not COCKPIT:
    sys.exit("cockpit.json manquant : c'est Claude qui l'écrit (hooks, musiques), voir COCKPIT.md")
RUSH = COCKPIT.get("rush") or (lire("cadre.json") or {}).get("source")
RW = lire("words_rush.json")["words"]
RUSH_DUREE = duree(RUSH)

# Le plan de départ (écrit par Claude) est gardé une fois : chaque Fabriquer repart de lui + les choix.
if not os.path.exists(os.path.join(AP, "plan.base.json")) and not (LAB and not os.path.exists(os.path.join(D, "plan.json"))):
    shutil.copy(os.path.join(D, "plan.json"), os.path.join(AP, "plan.base.json"))
BASE = json.load(open(os.path.join(AP, "plan.base.json"))) if os.path.exists(os.path.join(AP, "plan.base.json")) else {}

ETAT = lire("cockpit-etat.json") or {
    "etape": 0, "remis": [],
    "hook": COCKPIT.get("reco_hook", COCKPIT["hooks"][0]["id"]),
    "taille": BASE.get("subSize", 52), "place": "normal", "mots_forts": True,
    "musique": COCKPIT.get("reco_musique") or (COCKPIT.get("musiques") or [{"id": "sans"}])[0]["id"],
}
ESSAIS, NOMS_C = [], {}


def relire_cockpit():
    """cockpit.json relu à chaque fabrication et à chaque rafraîchissement : Claude peut corriger un texte (hook d'un essai,
    slide du carrousel) pendant que la page tourne, sans relancer le serveur."""
    COCKPIT.clear()
    COCKPIT.update(lire("cockpit.json"))
    ESSAIS[:] = COCKPIT.get("essais", [])
    NOMS_C.clear()
    NOMS_C.update([("reel", "Le reel")] + ([("carrousel", "Un carrousel")] if COCKPIT.get("carrousel") else []) +
                  [("story", "Une story")] + [(e["id"], e.get("nom", e["id"])) for e in ESSAIS])


relire_cockpit()
ETAT.setdefault("coches", ["reel"])   # 23/10 (l'utilisateur) : carrousel, story et reels d'essai décochés ; proposés à la fin, après le reel
ETAT.setdefault("look", None)       # v3 (23/10) : aucun look = 1er lancement (3 looks proposés) ; plan inchangé tant qu'il n'y en a pas
ETAT.setdefault("affine", {})       # « Affiner » : polices, couleur des mots en serif, rythme
ETAT.setdefault("style", None)      # 23/10 : le style réglé (police, tailles, couleurs, position, plus) ; None = 1er lancement
ETAT.setdefault("coupes_ok", [])    # coupes validées « C'est bon » dans la conversation
ETAT.setdefault("passe", 1)         # 23/10 montage en 3 étapes : 1 Dérushage, 2 Style, 3 Motion / B-roll (maquettes passes-r1 validées)
ETAT.setdefault("moments_choix", {})   # étape 3 : id du moment -> un de CHOIX_MOMENT (zoom | carton | rien depuis le 23/10 ; absent = le conseil de Claude)
ETAT.setdefault("passe3", None)     # "sautee" = étape 3 sautée (la vidéo reste telle quelle)
ETAT.setdefault("prog", {"reseaux": ["instagram", "tiktok", "youtube"], "quand": "", "essais_heure": "18:00"})
JOB = {"nom": None, "etat": "libre", "lignes": [], "debut": 0, "fin": 0, "taches": [], "courante": None}


def sauver_etat():
    ecrire("cockpit-etat.json", ETAT)


def gardes():
    return lire("garde.json", [])


def gardes_ecrire(g):
    if g:
        ecrire("garde.json", g)
    elif os.path.exists(os.path.join(D, "garde.json")):
        os.remove(os.path.join(D, "garde.json"))


def gardes_indices(drop):
    mort = {k for a, b in drop for k in range(a, b + 1)}
    return [i for i in range(len(RW)) if i not in mort]


# Les corrections de texte (Whisper : « téléprompter », « boulettes ») faites par Claude dans words.json sont reportées par
# indice de mot du rush : un nouveau dérush (Remettre / Couper) les garde (sinon les fautes reviennent dans les sous-titres).
def corrections():
    p = os.path.join(AP, "corrections.json")
    if os.path.exists(p):
        return json.load(open(p))
    a, b = lire("words.json")["words"], lire("cut.words.json", {"words": []})["words"]
    k = gardes_indices(lire("drop.json", []))
    corr = {}
    if len(a) == len(b) == len(k):
        for i, (x, y) in enumerate(zip(a, b)):
            c = {}
            if x["text"] != y["text"]:
                c["text"] = x["text"]
            for f in ("start", "end"):
                if abs(x[f] - y[f]) > 0.01:
                    c[f] = round(x[f] - y[f], 3)
            if c:
                corr[str(k[i])] = c
    else:
        print(f"!! corrections non reportables ({len(a)} / {len(b)} / {len(k)} mots) : vérifier les sous-titres après un Remettre")
    json.dump(corr, open(p, "w"), ensure_ascii=False)
    return corr


CORR = corrections()


def appliquer_corrections(d=None, drop=None):
    d = d or D
    b = json.load(open(os.path.join(d, "cut.words.json")))["words"]
    k = gardes_indices(lire("drop.json", []) if drop is None else drop)
    if len(b) == len(k):
        for i, w in enumerate(b):
            c = CORR.get(str(k[i]))
            if c:
                w["text"] = c.get("text", w["text"])
                for f in ("start", "end"):
                    if f in c:
                        w[f] = round(w[f] + c[f], 3)
    json.dump({"words": b}, open(os.path.join(d, "words.json"), "w"), ensure_ascii=False, indent=1)


def norm(t):
    return re.sub(r"[.,!?;:«»\"]", "", t.lower()).strip()


def phrase(mots):
    t = ""
    for w in mots:
        x = w["text"].strip()
        t += x if (x.startswith("'") or not t) else " " + x
    return t


RAISONS = {"reprise": "Tu as recommencé ta phrase : Claude garde la dernière prise.",
           "blanc": "Un blanc entre deux phrases, raccourci pour le rythme.",
           "debut": "Avant que tu parles.", "fin": "Après ton dernier mot."}


def coupes():
    segs = lire("cut.segments.json", [])
    drop = lire("drop.json", [])
    mort = {k for a, b in drop for k in range(a, b + 1)}
    trous, t = [], 0.0
    for a, b in segs:
        if a - t > 0.05:
            trous.append((t, a))
        t = b
    if RUSH_DUREE - t > 0.05:
        trous.append((t, RUSH_DUREE))
    out = []
    for a, b in trous:
        dedans = [i for i, w in enumerate(RW) if w["start"] >= a - 0.08 and w["end"] <= b + 0.08]
        morts = [i for i in dedans if i in mort]
        if morts:
            typ = "reprise"
            plages = [[x, y] for x, y in drop if any(x <= i <= y for i in morts)]
            p = phrase([RW[i] for i in dedans])
            texte = "« " + p[:1].upper() + p[1:] + " »"
        else:
            typ = "debut" if a < 0.05 else ("fin" if b > RUSH_DUREE - 0.05 else "blanc")
            plages, texte = [], ""
        cle = "-".join(f"{x}-{y}" for x, y in plages)
        out.append({"id": f"{a:.2f}-{b:.2f}", "type": typ, "a": round(a, 2), "b": round(b, 2), "duree": round(b - a, 1),
                    "texte": texte, "drop": plages, "raison": (COCKPIT.get("raisons") or {}).get(cle, RAISONS[typ]),
                    "etat": "coupe", "remettable": typ in ("reprise", "blanc")})
    for r in ETAT["remis"]:
        out.append({**r, "etat": "remis", "remettable": True})
    return sorted(out, key=lambda c: c["a"])


# ---------- les tâches longues (une à la fois) : dérush après Remettre / Couper, fabrication du reel ----------
def lancer(nom, fn):
    with VERROU:
        if JOB["etat"] == "en cours":
            return False
        JOB.update(nom=nom, etat="en cours", lignes=[], debut=time.time(), fin=0, taches=[], courante=None)
    threading.Thread(target=_tache, args=(fn,), daemon=True).start()
    return True


def _tache(fn):
    try:
        ok = fn()
        JOB["etat"] = "fini" if ok else "erreur"
    except Exception as e:
        JOB["lignes"].append(f"⛔ {e}")
        JOB["etat"] = "erreur"
    JOB["fin"] = time.time()


def commande(cmd, log, cwd=None):
    with open(os.path.join(AP, log), "w") as f:
        p = subprocess.Popen(cmd, cwd=cwd or D, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for ligne in p.stdout:
            f.write(ligne)
            ligne = ligne.rstrip()
            if ligne:
                JOB["lignes"] = (JOB["lignes"] + [ligne])[-200:]
                if ligne.startswith("▶ ") and JOB["courante"]:   # étape de monte.sh : « ▶ Rendu (~3 min…)  (6 s) »
                    JOB["courante"]["detail"] = ligne[2:].split("  (")[0].split(" (")[0]
        return p.wait() == 0


def derush():
    vf = (lire("cadre.json") or {}).get("vf")
    cmd = ["python3", os.path.join(S, "derush.py"), RUSH, "words_rush.json", "cut.mp4", "--drop", "drop.json"]
    if vf:
        cmd += ["--vf", vf]
    if gardes():
        cmd += ["--garde", "garde.json"]
    if os.path.exists(os.path.join(D, "bords.json")):
        cmd += ["--bords", "bords.json"]
    if os.path.exists(os.path.join(D, "plages.json")):   # v5 : les plages gardées posées sur la timeline
        cmd += ["--plages", "plages.json"]
    if not commande(cmd, "derush.log") or not os.path.exists(os.path.join(D, "cut.mp4")):
        return False
    os.replace(os.path.join(D, "cut.mp4"), os.path.join(D, "clip.mp4"))
    appliquer_corrections()
    return True


def remettre(cid):
    c = next((x for x in coupes() if x["id"] == cid and x["etat"] == "coupe" and x["remettable"]), None)
    if not c:
        return False
    if c["type"] == "reprise":
        drop = [p for p in lire("drop.json", []) if p not in c["drop"]]
        ecrire("drop.json", drop)
    else:
        gardes_ecrire(gardes() + [[c["a"], c["b"]]])
    ETAT["remis"].append({k: c[k] for k in ("id", "type", "a", "b", "duree", "texte", "drop", "raison")})
    sauver_etat()
    return lancer("Je remets le passage", derush)


def recouper(cid):
    r = next((x for x in ETAT["remis"] if x["id"] == cid), None)
    if not r:
        return False
    if r["drop"]:
        ecrire("drop.json", sorted(lire("drop.json", []) + r["drop"]))
    else:
        gardes_ecrire([g for g in gardes() if g != [r["a"], r["b"]]])
    ETAT["remis"] = [x for x in ETAT["remis"] if x["id"] != cid]
    sauver_etat()
    return lancer("Je recoupe", derush)


# ---------- 23/10 v4 dérushage « phrase en grand » (maquette livrables/cockpit-montage/derush-r2/B.png validée) ----------
# Le texte du rush en phrases : la personne barre une phrase (ou un seul mot), ouvre une phrase pour voir son son en grand et
# pose ses bords au pixel. Ses choix : ETAT["derush"] = {"coupes": [indices de mots du rush], "bords": {"debut": {i: t}, "fin": {j: t}}}
# -> drop.json (plages de mots) + bords.json (lu par derush.py --bords). Le moteur ne tourne qu'à « Suivant ».
DROP_CLAUDE = os.path.join(AP, "drop.claude.json")
if not os.path.exists(DROP_CLAUDE):
    shutil.copy(os.path.join(D, "drop.json"), DROP_CLAUDE) if os.path.exists(os.path.join(D, "drop.json")) else json.dump([], open(DROP_CLAUDE, "w"))
DEBUTS = {"et", "mais", "parce", "alors", "donc", "sauf", "puis", "ensuite", "bref", "enfin"}


def phrases_rush():
    """cockpit.json "phrases" ([[i, j], ...], écrites par Claude) sinon découpage auto : ponctuation, vrai blanc, mot de liaison,
    bords des reprises de drop.json (une reprise = sa propre phrase, barrée d'entrée)."""
    if COCKPIT.get("phrases"):
        return COCKPIT["phrases"]
    dc = lire(os.path.relpath(DROP_CLAUDE, D), [])   # les reprises vues par Claude (pas les coupes de la personne : phrases stables)
    bornes = {a for a, b in dc} | {b + 1 for a, b in dc}
    out, i0 = [], 0
    for i in range(1, len(RW)):
        n, prev, w = i - i0, RW[i - 1], RW[i]
        if w["text"].startswith("'"):
            continue
        t, gap = w["text"].strip().lower().strip(".,!?"), w["start"] - prev["end"]
        if (i in bornes or prev["text"].rstrip()[-1:] in ".!?" or (gap > 0.5 and n >= 3) or (n >= 5 and t in DEBUTS)
                or (n >= 14 and gap > 0.15) or n >= 24):
            out.append([i0, i - 1])
            i0 = i
    return out + [[i0, len(RW) - 1]]


def mots_rush():
    fx = BASE.get("fixes", {})
    return [{"text": fx.get(t, t), "start": w["start"], "end": w["end"]}
            for i, w in enumerate(RW) for t in [CORR.get(str(i), {}).get("text", w["text"])]]


# ---------- 23/10 v5 : dérushage en TIMELINE (maquette livrables/cockpit-montage/timeline-r2/1.png validée) ----------
# Plus de texte : la personne voit le reel bout à bout (les coupes en petit) et ouvre n'importe quel bloc en grand pour remettre
# un bout du gris ou retirer un petit mot du bleu. Ses choix = les plages GARDÉES, en secondes du rush :
# ETAT["derush"] = {"plages": [[a, b], ...], "applique": sig} -> plages.json (derush.py --plages) au « Suivant ».
# Le 1er dérush de Claude (cut.segments.json du 1er lancement) est gardé dans _cockpit/segments.claude.json (« Remettre comme Claude »).
SEG_CLAUDE = os.path.join(AP, "segments.claude.json")
if not os.path.exists(SEG_CLAUDE) and os.path.exists(os.path.join(D, "cut.segments.json")):
    shutil.copy(os.path.join(D, "cut.segments.json"), SEG_CLAUDE)


def sig_plages(pl):
    return json.dumps([[round(a, 2), round(b, 2)] for a, b in pl])


def derush_choix():
    d = ETAT.get("derush")
    if not d or "plages" not in d:   # 1er lancement (ou état v4 « phrases ») : ce qui est monté aujourd'hui
        pl = lire("cut.segments.json", [])
        d = {"plages": pl, "applique": sig_plages(pl)}
    return {**d, "claude": lire(os.path.relpath(SEG_CLAUDE, D), []) or d["plages"]}


def plages(ks):
    out = []
    for k in sorted(ks):
        if out and k == out[-1][1] + 1:
            out[-1][1] = k
        else:
            out.append([k, k])
    return out


def plages_propres(liste):
    """Les plages envoyées par la page : bornées au rush, triées, collées si elles se touchent, sans bout < 0,05 s."""
    pl = []
    for a, b in sorted([max(0.0, float(a)), min(RUSH_DUREE, float(b))] for a, b in liste):
        if b - a < 0.05:
            continue
        if pl and a <= pl[-1][1] + 0.01:
            pl[-1][1] = max(pl[-1][1], round(b, 3))
        else:
            pl.append([round(a, 3), round(b, 3)])
    return pl


# Derush Lab : « Valider le dérush » (maquette livrables/cockpit-montage/derushlab-r1/A.png validée le 23/10) = le moteur recoupe
# si la timeline a changé (clip.mp4), puis le Gardien du dérush (gardien.py --derush). La page montre ses contrôles en vert / rouge.
GROUPES_LAB = ["mot coupé", "respiration", "plans ≥ 2 s", "micro-coupure", "silence", "flash"]


def valider(d):
    sig = sig_plages(d["plages"])
    if sig != d.get("applique"):
        derush_ecrire(d)
        if not derush():
            return False
        d["applique"] = sig
        ETAT["derush"] = d
    ok = commande(["python3", os.path.join(S, "gardien.py"), D, "--derush"], "gardien-derush.log")
    ETAT["lab"] = {"plages": d["plages"], "ok": ok, "quand": time.strftime("%H:%M")}
    sauver_etat()
    return True


def lab_etat():
    L = ETAT.get("lab")
    if not L:
        return {"valide": None, "groupes": []}
    r = lire("gardien-derush.json", [])
    return {"valide": L["plages"], "quand": L.get("quand"),
            "groupes": [{"nom": g, "ok": all(x["ok"] is not False for x in r if x.get("groupe") == g),
                         "detail": " · ".join(x["controle"] + " : " + x["detail"] for x in r if x.get("groupe") == g and x["ok"] is False)}
                        for g in GROUPES_LAB]}


def derush_ecrire(d):
    """v5 : plages.json = la timeline ; drop.json revient aux reprises vues par Claude (le calcul auto sert de référence
    pour savoir ce que la personne a changé) ; bords.json (v4) n'est plus utilisé."""
    ecrire("plages.json", d["plages"])
    ecrire("drop.json", lire(os.path.relpath(DROP_CLAUDE, D), []))
    if os.path.exists(os.path.join(D, "bords.json")):
        os.remove(os.path.join(D, "bords.json"))


def planche_rush():
    """Les images du rush pour la timeline : 2 par seconde, 54 x 96 px, sur une seule planche (20 par ligne)."""
    p = os.path.join(AP, "planche.jpg")
    n = int(RUSH_DUREE * 2) + 1
    meta = {"fps": 2, "w": 54, "h": 96, "cols": 20, "n": n}
    if not os.path.exists(p):
        src = os.path.join(AP, "rush.mp4") if os.path.exists(os.path.join(AP, "rush.mp4")) else RUSH
        rows = (n + 19) // 20
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"fps=2,scale=54:96:force_original_aspect_ratio=increase,crop=54:96,tile=20x{rows}",
                        "-frames:v", "1", "-q:v", "4", p + ".part.jpg"])
        if os.path.exists(p + ".part.jpg"):
            os.replace(p + ".part.jpg", p)
    return p, meta


def onde():
    """Le son du rush toutes les 10 ms, de 0 (bruit de la pièce) à 1 (voix forte), en dB : une respiration se voit."""
    p = os.path.join(AP, "onde.json")
    if os.path.exists(p):
        return json.load(open(p))
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", RUSH, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = len(x) // 160 * 160
    db = 20 * np.log10(np.sqrt((x[:n].reshape(-1, 160) ** 2).mean(1)) + 1e-9)
    lo, hi = np.percentile(db, 3), np.percentile(db, 99.5)
    v = [round(float(min(1, max(0, (d - lo) / (hi - lo)))), 2) for d in db]
    json.dump(v, open(p, "w"))
    return v


# ---------- le plan final = le plan de Claude + les choix de la personne ----------
PLACES = {"haut": -140, "normal": 0, "bas": 110}


# Styles de sous-titres des reels d'essai (22/10, l'utilisateur : « changer aussi la musique et le style de sous-titrage »).
# Toujours en MAJUSCULES, toujours sous 60 px (Style Lab). Police et couleur = le look du reel (décision 23/10 : les essais
# prennent le même look que le reel ; avant les looks : toujours Montserrat blanc).
STYLES_ST = {
    "classique": {"nom": "Classique", "taille": 52, "place": "normal", "mots_max": 4},
    "mot-a-mot": {"nom": "Mot à mot", "taille": 58, "place": "normal", "mots_max": 1},
    "duo": {"nom": "2 mots, plus haut", "taille": 56, "place": "haut", "mots_max": 2},
    "discret": {"nom": "Petit, plus bas", "taille": 46, "place": "bas", "mots_max": 4},
}


MUS_PERSO = os.path.join(AP, "musique-perso")
EXT_AUDIO = (".mp3", ".m4a", ".wav", ".aac")


def musique_perso():
    """« Ajoute ta musique » (v3, 23/10) : le fichier envoyé par la personne, gardé dans _cockpit/musique-perso.<ext>."""
    p = next((MUS_PERSO + e for e in EXT_AUDIO if os.path.exists(MUS_PERSO + e)), None)
    if not p:
        return None
    return {"id": "perso", "nom": "Ta musique", "titre": ETAT.get("musique_perso_nom") or "Ta musique", "artiste": "", "src": p, "from": 0}


def musiques():
    return (COCKPIT.get("musiques") or []) + ([musique_perso()] if musique_perso() else [])


def musique_choisie():
    """None = « Sans musique » (la personne l'ajoute dans Insta) ; sinon le morceau choisi (le 1er si l'id a disparu)."""
    if ETAT["musique"] == "sans":
        return None
    return next((x for x in musiques() if x["id"] == ETAT["musique"]), (musiques() or [None])[0])


def style_essai(e):
    s = e.get("sous_titres")
    if isinstance(s, str):
        s = STYLES_ST.get(s)
    return dict(STYLES_ST["classique"], **(s or {"nom": "Comme le reel", "taille": ETAT["taille"], "place": ETAT["place"]}))


def musique_essai(e):
    """Un id de l'étape Musique (pose / puissant / sombre) ou un morceau à part {nom, titre, artiste, src, from}."""
    m = e.get("musique")
    if isinstance(m, str):
        m = next((x for x in musiques() if x["id"] == m), None)
    return m or musique_choisie()


# ---------- v3 (23/10) : les looks = polices + couleur du texte + rythme. JAMAIS d'étalonnage ni de traitement du son du rush. ----------
LOOKS = [
    {"id": "premium", "nom": "Premium sombre", "sans": "Montserrat.ttf", "serif": "InstrumentSerif-Italic.ttf",
     "texte": "#FFFFFF", "serif_couleur": "#FFFFFF", "accent": "#4F9BFF", "rythme": "pose"},
    {"id": "clair", "nom": "Clair épuré", "sans": "Inter.ttf", "serif": "DMSerifDisplay-Italic.ttf",
     "texte": "#FFFFFF", "serif_couleur": "#BFDDFF", "accent": "#0071E3", "rythme": "pose"},
    {"id": "chaud", "nom": "Cinéma chaud", "sans": "Poppins-SemiBold.ttf", "serif": "PlayfairDisplay-Italic.ttf",
     "texte": "#FFF8EC", "serif_couleur": "#F3DDB0", "accent": "#E0B46A", "rythme": "pose"},
]
RYTHMES = {"pose": [5, 8], "nerveux": [2.5, 4]}   # zoomGap de build.mjs (Style Lab client 16/10)
NOMS_POLICES = {"Montserrat.ttf": "Montserrat", "Inter.ttf": "Inter", "Poppins-SemiBold.ttf": "Poppins",
                "InstrumentSerif-Italic.ttf": "Serif", "DMSerifDisplay-Italic.ttf": "DM Serif", "PlayfairDisplay-Italic.ttf": "Playfair"}
NOMS_COULEURS = {"#FFFFFF": "blanc", "#BFDDFF": "bleu", "#F3DDB0": "or doux", "#E8CF9A": "or", "#FFF8EC": "ivoire"}


def looks():
    """Les 3 looks par défaut, ou ceux de cockpit.json "looks" (même format) : un client peut avoir les siens."""
    return COCKPIT.get("looks") or LOOKS


def look_actif():
    """Le look choisi + ce que la personne a affiné (polices, couleur, rythme) ; None = pas encore de look."""
    lk = next((x for x in looks() if x["id"] == ETAT.get("look")), None)
    if not lk:
        return None
    lk, a = dict(lk), ETAT.get("affine") or {}
    pol = next((x for x in looks() if x["id"] == a.get("polices")), None)
    if pol:
        lk.update(sans=pol["sans"], serif=pol["serif"])
    if a.get("couleur"):
        lk["serif_couleur"] = a["couleur"]
    if a.get("rythme") in RYTHMES:
        lk["rythme"] = a["rythme"]
    return lk


# ---------- 23/10 (personnalisation, maquettes perso-r1 validées) : 6 POLICES + 5 réglages (police, taille, couleurs, position, plus).
# Remplace les 3 looks à l'écran. Police principale (titre ligne 1 + sous-titres) TOUJOURS sans serif, accent (ligne 2) libre.
# Couleurs à part (tout blanc par défaut). Jamais de bande ni d'étiquette derrière le titre, titre 2 lignes max (build.mjs rétrécit).
# "size" = taille du titre en px réels (taille M) ; sub.scale = équivalence de taille avec Montserrat (52 px Montserrat = 52 x scale).
POLICES = [
    {"id": "combo", "nom": "Ton combo", "desc": "Montserrat + Instrument Serif",
     "t1": {"font": "Montserrat.ttf", "weight": 700, "size": 66, "caps": True, "track": 1},
     "t2": {"font": "InstrumentSerif-Italic.ttf", "weight": 400, "size": 108, "italic": True},
     "sub": {"font": "Montserrat.ttf", "weight": 700, "caps": True, "track": 0.5, "scale": 1}},
    {"id": "condense", "nom": "Condensé géant", "desc": "Bebas Neue",
     "t1": {"font": "BebasNeue-Regular.ttf", "weight": 400, "size": 112, "track": 2},
     "t2": {"font": "BebasNeue-Regular.ttf", "weight": 400, "size": 112, "track": 2},
     "sub": {"font": "BebasNeue-Regular.ttf", "weight": 400, "caps": True, "track": 1.5, "scale": 1.42}},
    {"id": "fin-gras", "nom": "Fin + gras", "desc": "Outfit",
     "t1": {"font": "Outfit.ttf", "weight": 300, "size": 84},
     "t2": {"font": "Outfit.ttf", "weight": 800, "size": 92},
     "sub": {"font": "Outfit.ttf", "weight": 700, "caps": False, "scale": 1.08}},
    {"id": "large", "nom": "Large", "desc": "Archivo étiré",
     "t1": {"font": "Archivo.ttf", "weight": 800, "size": 64, "caps": True, "stretch": 125},
     "t2": {"font": "Archivo.ttf", "weight": 500, "size": 64, "caps": True, "stretch": 125},
     "sub": {"font": "Archivo.ttf", "weight": 700, "caps": True, "stretch": 112, "scale": 0.96}},
    {"id": "manuscrit", "nom": "Manuscrit", "desc": "Figtree + Caveat",
     "t1": {"font": "Figtree.ttf", "weight": 800, "size": 66, "caps": True, "track": 0.5},
     "t2": {"font": "Caveat.ttf", "weight": 700, "size": 130},
     "sub": {"font": "Figtree.ttf", "weight": 800, "caps": True, "track": 0.5, "scale": 1}},
    {"id": "tech", "nom": "Tech", "desc": "Space Grotesk + Space Mono",
     "t1": {"font": "SpaceGrotesk.ttf", "weight": 700, "size": 76},
     "t2": {"font": "SpaceMono-BoldItalic.ttf", "weight": 700, "size": 74, "italic": True},
     "sub": {"font": "SpaceGrotesk.ttf", "weight": 700, "caps": False, "scale": 1.04}},
]
TAILLES_TITRE = {"S": 0.85, "M": 1, "L": 1.15, "XL": 1.3}
TITRE_PLACES = {"haut": 280, "bas": 420}   # haut du bloc titre (zone interdite du haut = 270 px)
STYLE_DEFAUT = {"police": "combo", "titre": "M", "couleurs": {"t1": "#FFFFFF", "t2": "#FFFFFF", "sub": "#FFFFFF"},
                "titre_place": "haut", "align": "centre", "majuscules": None, "ombre": "douce", "mots": 4}


def style_actif():
    """Le style réglé dans le cockpit (complété par les valeurs par défaut) ; None = pas encore réglé (plan inchangé)."""
    st = ETAT.get("style")
    if not st:
        return None
    s = dict(STYLE_DEFAUT, **st)
    s["couleurs"] = dict(STYLE_DEFAUT["couleurs"], **(st.get("couleurs") or {}))
    if not any(x["id"] == s["police"] for x in POLICES):
        s["police"] = "combo"
    return s


def police(pid):
    return next(x for x in POLICES if x["id"] == pid)


def typo(s):
    """plan.typo pour build.mjs : police, graisse, taille, couleur de chaque ligne du titre et des sous-titres."""
    p, f = police(s["police"]), TAILLES_TITRE.get(s["titre"], 1)
    t1 = dict(p["t1"], size=round(p["t1"]["size"] * f), color=s["couleurs"]["t1"])
    t2 = dict(p["t2"], size=round(p["t2"]["size"] * f), color=s["couleurs"]["t2"])
    sub = dict(p["sub"], color=s["couleurs"]["sub"])
    if s.get("majuscules") is not None:
        sub["caps"] = bool(s["majuscules"])
    return {"t1": t1, "t2": t2, "sub": sub, "shadow": "forte" if s.get("ombre") == "forte" else "douce",
            "align": "left" if s.get("align") == "gauche" else "center"}


def ecrire_da_style(s):
    """DA du rendu : polices et couleurs du style (cartons, mots géants) ; jamais d'étalonnage."""
    p, da = police(s["police"]), da_base()
    fonts = dict(da.get("fonts") or {}, sans=p["sub"]["font"], sub=p["sub"]["font"])
    if p["t2"].get("italic"):
        fonts["serif"] = p["t2"]["font"]
    da["fonts"] = fonts
    da["colors"] = dict(da.get("colors") or {}, text=s["couleurs"]["sub"], serif=s["couleurs"]["t2"])
    da["_cockpit"] = f"Style « {p['nom']} » réglé dans le cockpit (polices, tailles, couleurs du texte, jamais d'étalonnage)"
    chemin = os.path.join(AP, "da-look.json")
    if lire(os.path.relpath(chemin, D)) != da:
        json.dump(da, open(chemin, "w"), ensure_ascii=False, indent=1)
    return chemin


def da_base():
    """La DA de base, choisie comme build.mjs : da/<client>.json, sinon Brain/00-Moi/reglages/da-montage.json, sinon da/exemple.json."""
    reg = os.path.join(os.environ.get("KIT_BRAIN") or os.path.join(HOME, "Documents", "Brain"), "00-Moi", "reglages")
    c = ""
    for p in (os.path.join(SKILL, "config.json"), os.path.join(reg, "supermonteur.json")):
        try:
            c = json.load(open(p)).get("client", c) or c
        except Exception:
            pass
    for p in ([os.path.join(SKILL, "da", c + ".json")] if c else []) + [os.path.join(reg, "da-montage.json"),
                                                                       os.path.join(SKILL, "da", "exemple.json")]:
        if os.path.exists(p):
            return json.load(open(p))
    return {"fonts": {}, "colors": {}}


def ecrire_da_look(lk):
    da = da_base()
    da["fonts"] = dict(da.get("fonts") or {}, sans=lk["sans"], serif=lk["serif"], sub=lk["sans"])
    da["colors"] = dict(da.get("colors") or {}, text=lk["texte"], serif=lk["serif_couleur"], accent=lk["accent"])
    da["zoomGap"] = RYTHMES.get(lk.get("rythme"), RYTHMES["pose"])
    da["_cockpit"] = f"Look « {lk['nom']} » choisi dans le cockpit (polices + couleur du texte + rythme, jamais d'étalonnage)"
    p = os.path.join(AP, "da-look.json")
    if lire(os.path.relpath(p, D)) != da:
        json.dump(da, open(p, "w"), ensure_ascii=False, indent=1)
    return p


# ---------- 23/10 étape 3 « Motion / B-roll » : les moments forts, la personne choisit pour chacun ----------
# Maquettes : passes-r1/r2-3b (moments forts) puis etape3-r1 r1-a (liste, un moment s'ouvre) + r2-a (3 idées de B-roll), validées 23/10.
# Claude les écrit dans cockpit.json "moments": [{id, t0, t1, texte, mot, reco, reglage?, carton?, brolls?}] (temps du reel), assez
# pour illustrer TOUTE la vidéo (retour n4 : « 3 moments, c'est pas suffisant ») : un toutes les ~4 s. Sans eux : les mots forts
# (keywords) puis les mots les plus longs, espacés d'au moins 3,5 s, après le titre.
# 6 effets (retour n3 : + « Carton plein ») et leurs réglages (retour n7) dans cockpit-etat.json "moments_reglages" {id: {...}} :
#   zoom "avant" | "arriere" ; mot "tete" (derrière la tête) | "sous" (en géant dans le sous-titre) ; carton {l1, l2, fond} ;
#   motion "coeur" | "entoure" | "souligne" (dessins faits par le code, jamais d'IA) ; broll = un plan de SA bibliothèque
#   (chemin relatif au dossier des B-rolls) ou "perso" (la vidéo envoyée). Jamais d'image ni de vidéo générée par IA.
# 23/10 (l'utilisateur, après test dans Chrome) : l'étape 3 ne propose plus que Zoom, Carton plein et Rien, POUR TOUT LE MONDE.
# Mot géant, Motion design et Ton B-roll sont CACHÉS, pas supprimés (build.mjs, matte.py, headtop.py, /api/biblio, /illus/ intacts) :
# pour les remettre, reprendre TOUS_EFFETS ici (la page lit la liste dans /api/etat "effets").
TOUS_EFFETS = ("zoom", "mot", "carton", "motion", "broll", "rien")
CHOIX_MOMENT = ("zoom", "carton", "rien")
REGLAGE_DEF = {"zoom": "avant", "mot": "tete", "motion": "chiffres"}
# Motion design (23/10, maquettes motion-r2 F + L validées par l'utilisateur après 5 rounds ; leçon Jun Yuh : pro, sans fond, coupe franche) :
#   "chiffres" = 1-2-3 géants derrière la tête (les moments « chiffres » de la vidéo sont numérotés dans l'ordre) ;
#   "trait" = une illustration au trait blanc (celles du skill Carrousel, art.py, dessinées, jamais d'IA) + son mot.
# Les anciens coeur / entoure / souligne (« dégueulasses ») deviennent "chiffres".
MOTIONS = ("chiffres", "trait")
ILLUS = {"camera": "Caméra", "script_long": "Script barré", "chat": "Message", "checklist": "Liste", "stairs": "Étapes",
         "chart_up": "Courbe qui monte", "copies": "Copies", "apples_grid": "Une parmi d'autres"}
ILLUS_MOTS = [("camera", "camera cam filme film tournage tourner video"), ("script_long", "script texte teleprompteur prompteur lire par coeur"),
              ("chat", "message dire parler dm conversation coeur"), ("checklist", "points liste etapes hook bullet"),
              ("stairs", "etape progresser monter niveau"), ("chart_up", "resultat chiffre vues croissance abonnes vente"),
              ("copies", "copier pareil meme tout le monde"), ("apples_grid", "different unique sortir lot")]
ILLUS_DIR = os.path.join(AP, "illus")


def illus_de(m):
    if m.get("illustration") in ILLUS:
        return m["illustration"]
    t = desaccent(m.get("texte", "") + " " + m.get("mot", ""))
    return max(ILLUS_MOTS, key=lambda x: sum(w in t for w in x[1].split()))[0] if any(w in t for _, ws in ILLUS_MOTS for w in ws.split()) else "checklist"


TRAIT_CSS = "<style>*{fill:none!important;stroke:#fff!important;stroke-width:9px!important;stroke-linecap:round;stroke-linejoin:round}</style>"


def illus_svg(nom):
    """Le SVG d'une illustration du skill Carrousel, SANS son cercle de fond. « <nom>-trait » = la même au trait blanc
    (aperçu et vignettes du cockpit ; build.mjs pose le même style sur le SVG d'origine)."""
    trait = nom.endswith("-trait")
    nom = nom[:-6] if trait else nom
    if nom not in ILLUS:
        return None
    if trait:
        p = os.path.join(ILLUS_DIR, nom + "-trait.svg")
        if not os.path.exists(p):
            src = open(illus_svg(nom)).read()
            open(p, "w").write(src.replace(">", ">" + TRAIT_CSS, 1))
        return p
    p = os.path.join(ILLUS_DIR, nom + ".svg")
    if not os.path.exists(p):
        sys.path.insert(0, os.path.expanduser("~/.claude/skills/carrousel/scripts"))
        import art
        art.frame = lambda inner, deco_items=(): f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 900">{inner}</svg>'
        os.makedirs(ILLUS_DIR, exist_ok=True)
        open(p, "w").write(art.ARTS[nom]())
    return p
# Fonds du carton plein : TOUJOURS un dégradé, jamais une couleur unie (l'utilisateur 23/10 : « une couleur unie, c'est dégueulasse »)
FONDS = {"nuit": "radial-gradient(85% 60% at 100% 0%,#2f74ff 0%,transparent 70%),radial-gradient(90% 65% at 0% 100%,#132b66 0%,transparent 75%),linear-gradient(165deg,#0d1836 0%,#060a1c 60%,#03050d 100%)",
         "noir": "radial-gradient(80% 55% at 100% 0%,#3a3f4a 0%,transparent 70%),radial-gradient(70% 50% at 0% 100%,#1a1d24 0%,transparent 75%),linear-gradient(165deg,#15171c 0%,#050506 70%)",
         "bleu": "radial-gradient(85% 60% at 100% 0%,#7fb2ff 0%,transparent 70%),radial-gradient(90% 65% at 0% 100%,#0a2a6b 0%,transparent 75%),linear-gradient(165deg,#2b6fff 0%,#0b3b8c 60%,#061f4d 100%)",
         "flou": "blur"}
BROLL_DIR = os.path.join(AP, "brolls")
EXT_VIDEO = (".mp4", ".mov", ".m4v")
ETAT.setdefault("moments_reglages", {})
PETITS = set("le la les un une des de du d l à au aux et ou mais donc car que qu qui quoi ce cet cette ces se sa son ses ma mon mes ta ton tes "
             "je tu il elle on nous vous ils elles me te lui leur y en ne pas plus très tout tous juste vraiment c est sont ai as a "
             "avec pour par sur dans sans comme faire fait être avoir".split())


def moments_auto():
    W = lire("words.json")["words"]
    fin_titre = max([h["title"].get("end", 0) for h in COCKPIT["hooks"] if h.get("title")] + [0])
    fin = W[-1]["end"] if W else 0
    ms = []
    def libre(t):
        return t > fin_titre + 0.5 and t < fin - 1.5 and all(abs(t - m["t0"]) >= 3.5 for m in ms)
    for k in COCKPIT.get("keywords", []):   # 1) les mots forts écrits par Claude
        p = [norm(x) for x in k.split()]
        for i in range(len(W) - len(p) + 1):
            if [norm(W[i + j]["text"]) for j in range(len(p))] == p and libre(W[i]["start"]):
                ms.append({"t0": W[i]["start"], "t1": W[i + len(p) - 1]["end"], "texte": " ".join(W[i + j]["text"] for j in range(len(p))),
                           "mot": max(k.split(), key=len)})
                break
    voulu = max(3, int((fin - fin_titre) / 4.5))   # 2) de quoi couvrir toute la vidéo : les mots les plus longs, espacés
    for i in sorted(range(len(W)), key=lambda i: -len(norm(W[i]["text"]))):
        if len(ms) >= voulu:
            break
        w = norm(W[i]["text"]).strip("'")
        if len(w) >= 5 and w not in PETITS and libre(W[i]["start"]):
            a = max(0, i - 2)
            ms.append({"t0": W[i]["start"], "t1": W[i]["end"], "texte": " ".join(x["text"] for x in W[a:i + 1]).replace(" '", "'"), "mot": W[i]["text"]})
    ms.sort(key=lambda m: m["t0"])
    cycle = [c for c in ["zoom", "mot", "carton", "broll", "zoom", "motion", "mot", "rien"] if c in CHOIX_MOMENT]
    for n, m in enumerate(ms):
        m.update(id=f"m{n + 1}", reco=cycle[n % len(cycle)])
    return ms


# ----- la bibliothèque de B-rolls de la personne (celle de broll.py : _INDEX.csv + le tri broll_tri.csv) -----
_BIBLIO = {"rows": None}


def biblio():
    if _BIBLIO["rows"] is None:
        rows = []
        try:
            import csv
            sys.path.insert(0, S)
            import reglages
            cfg = reglages.config()
            root, index = cfg.get("brolls_root"), cfg.get("brolls_index")
            tri_p = os.path.join(SKILL, "broll_tri.csv")
            tri = {r["fichier"]: r["rang"] for r in csv.DictReader(open(tri_p, encoding="utf-8"))} if os.path.exists(tri_p) else {}
            ex_p = os.path.join(SKILL, "broll_exclus.txt")
            exclus = {l.split("#")[0].strip() for l in open(ex_p, encoding="utf-8")} - {""} if os.path.exists(ex_p) else set()
            mini = cfg.get("brolls_min_date", "")
            for r in csv.DictReader(open(index, encoding="utf-8")):
                f = r.get("fichier", "")
                if not f.lower().endswith(EXT_VIDEO) or tri.get(f) in ("ecarte", "telephone") or r.get("action") in exclus \
                        or r.get("usage") == "souvenir" or (mini and r.get("date_tournage", "") < mini) or r.get("qualite", "ok") != "ok":
                    continue
                rows.append({"f": os.path.join(r["dossier"], f), "nom": r.get("action", "").replace("-", " "), "rang": tri.get(f, "ok"),
                             "duree": float(r.get("duree_s") or 0), "v": r.get("orientation") == "V",
                             "cle": desaccent(" ".join([r.get("theme", ""), r.get("action", ""), r.get("lieu", "")]))})
            rows.sort(key=lambda r: (r["rang"] != "beau", not r["v"], r["f"]))
            _BIBLIO["root"] = root
        except Exception as e:
            print("bibliothèque B-roll introuvable :", e)
        _BIBLIO["rows"] = rows
    return _BIBLIO["rows"]


def desaccent(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def chercher_biblio(q, n=60):
    mots = [m for m in re.split(r"[^a-z0-9]+", desaccent(q)) if len(m) >= 3 and m not in PETITS]
    rows = biblio()
    if not mots:
        return rows[:n]
    sc = [(sum(m[:5] in r["cle"] for m in mots), r) for r in rows]
    return [r for s, r in sorted((x for x in sc if x[0]), key=lambda x: (-x[0], not x[1]["v"], x[1]["rang"] != "beau"))][:n]


def chemin_biblio(rel):
    """Le chemin complet d'un plan de la bibliothèque, seulement s'il est dans l'index (jamais un fichier quelconque du disque)."""
    if rel and any(r["f"] == rel for r in biblio()):
        return os.path.join(_BIBLIO["root"], rel)
    return None


def idees_broll(m):
    """3 idées de B-roll pour ce moment : celles écrites par Claude dans cockpit.json, sinon une recherche sur ses mots."""
    if m.get("brolls"):
        return [x for x in m["brolls"] if chemin_biblio(x)][:3]
    out = [r["f"] for r in chercher_biblio(m.get("texte", "") + " " + m.get("mot", ""), 3)]
    for r in chercher_biblio("tournage camera parle bureau", 12):   # rien de proche : ses plans de tournage les plus beaux
        if len(out) >= 3:
            break
        if r["f"] not in out:
            out.append(r["f"])
    return out


def moments():
    ms = COCKPIT.get("moments") or moments_auto()
    out = []
    for m in ms:
        perso = broll_de(m["id"])
        r = {**REGLAGE_DEF, **(m.get("reglage") or {}), **ETAT["moments_reglages"].get(m["id"], {})}
        if r["motion"] not in MOTIONS:
            r["motion"] = "chiffres"
        r.setdefault("illus", illus_de(m))
        idees = idees_broll(m)
        if not r.get("broll") or (r["broll"] == "perso" and not perso):
            r["broll"] = "perso" if perso else (idees[0] if idees else None)
        mots = m.get("texte", "").split()
        r["carton"] = {"l1": " ".join(mots[:max(1, len(mots) // 2)]).upper(), "l2": " ".join(mots[max(1, len(mots) // 2):]).upper(),
                       "fond": "nuit", **(m.get("carton") or {}), **(r.get("carton") or {})}
        choix = effet_permis(ETAT["moments_choix"].get(m["id"]) or m.get("reco", "zoom"), r["carton"])
        if choix == "broll" and not (perso if r["broll"] == "perso" else chemin_biblio(r["broll"])):
            choix = "rien"
        out.append(dict(m, broll=bool(perso), idees=idees, reglage=r, choix=choix))
    return out


def effet_permis(c, carton):
    """Un choix ou un conseil d'effet caché (CHOIX_MOMENT) devient le plus proche permis : mot géant → carton plein si son texte
    tient sur 2 lignes (22 signes chacune, comme la page), sinon zoom ; motion design et B-roll → zoom."""
    if c in CHOIX_MOMENT:
        return c
    if c == "mot" and "carton" in CHOIX_MOMENT and all(0 < len((carton.get(k) or "").strip()) <= 22 for k in ("l1", "l2")):
        return "carton"
    return "zoom" if "zoom" in CHOIX_MOMENT else "rien"


def broll_de(mid):
    p = os.path.join(BROLL_DIR, re.sub(r"\W", "", mid) + ".mp4")
    return p if os.path.exists(p) else None


def ajouter_moments(plan):
    """Les choix de l'étape 3 dans le plan du reel. Zoom = plan.zooms (dir "out" = zoom arrière) ; mot géant = plan.bigwords
    (derrière la tête, matte.py) ou plan.subwords (en géant dans le sous-titre) ; carton plein = plan.mini type "card" ;
    motion design = plan.motions (build.mjs, dessins au code) ; B-roll = plan.brolls (son plan à elle, jamais d'IA).
    Étape sautée = plan inchangé. Depuis le 23/10, moments() ne rend que CHOIX_MOMENT (zoom, carton, rien) : mot géant,
    motion et B-roll des moments n'arrivent plus ici (le mot géant de l'OUVERTURE, lui, vient du hook et reste)."""
    if ETAT.get("passe3") == "sautee":
        return plan
    titre = plan.get("title") or {}
    serif = (lire(os.path.relpath(plan["da"], D)) if plan.get("da") and os.path.exists(plan["da"]) else {}) or {}
    for m in moments():
        c, r, t0, t1 = m["choix"], m["reglage"], m["t0"], m["t1"]
        if c == "zoom":
            z = {"start": round(max(0, t0 - 0.4), 3), "end": round(t1 + 1.6, 3)}
            plan.setdefault("zooms", []).append(dict(z, dir="out") if r["zoom"] == "arriere" else z)
        elif c == "mot" and m.get("mot"):
            if r["mot"] == "sous":
                plan.setdefault("subwords", []).append({"text": m["mot"], "start": round(t0 - 0.05, 3), "end": round(t1 + 0.05, 3)})
            elif t0 > titre.get("end", -1):
                plan.setdefault("bigwords", []).append({"text": m["mot"], "start": round(t0, 3), "end": round(max(t1 + 0.3, t0 + 1.6), 3)})
        elif c == "carton":
            k = r["carton"]
            lignes = [{"text": x} for x in (k.get("l1"), k.get("l2")) if x and x.strip()]
            if lignes:
                lignes[-1]["color"] = (serif.get("colors") or {}).get("serif") or "#F2D37A"
                plan.setdefault("mini", []).append({"type": "card", "start": round(max(0, t0 - 0.1), 3), "end": round(max(t1 + 0.6, t0 + 1.8), 3),
                                                    "bg": FONDS.get(k.get("fond"), FONDS["nuit"]), "lines": lignes[:2], "moment": m["id"]})
        elif c == "motion":
            mo = {"kind": r["motion"], "start": round(t0, 3), "end": round(max(t1 + 0.8, t0 + 1.8), 3), "mot": m.get("mot", ""), "moment": m["id"]}
            if r["motion"] == "trait":
                mo["svg"] = illus_svg(r["illus"])
            plan.setdefault("motions", []).append(mo)
        elif c == "broll":
            src = broll_de(m["id"]) if r["broll"] == "perso" else chemin_biblio(r["broll"])
            if src:
                b = {"src": src, "start": round(t0 - 0.1, 3), "end": round(max(t1 + 0.4, t0 + 2.2), 3), "moment": m["id"]}
                plan.setdefault("brolls", []).append(b if r["broll"] == "perso" else dict(b, **{"from": "auto"}))
    mos = sorted(plan.get("motions", []), key=lambda x: x["start"])   # un motion s'arrête quand le suivant arrive (jamais 2 à la fois)
    for a, b in zip(mos, mos[1:]):
        a["end"] = round(min(a["end"], b["start"] - 0.02), 3)
    ch = [x for x in plan.get("motions", []) if x["kind"] == "chiffres"]   # 1, 2, 3… dans l'ordre de la vidéo (4 au plus)
    for n, x in enumerate(ch, 1):
        x.update(n=min(n, 4), total=min(len(ch), 4))
    return plan


# ---------- 23/10 (retour n6) : l'aperçu imite le « derrière la tête » du rendu. headtop.py mesure le haut des cheveux sur la
#            silhouette détourée pour chaque mot géant (hook + moments), une fois, en tâche de fond ; la page pose le mot au même
#            endroit que build.mjs et cache la partie derrière la tête. Sans tête à l'image : le mot est devant (comme le rendu).
TETES_P = os.path.join(AP, "tetes.json")
TETES = {"clip_v": 0, "spans": {}}
_TETES_FIL = {"vivant": False}


def cle_tete(a, b):
    return f"{a:.2f}-{b:.2f}"


def spans_mots():
    out = [(b["start"], b["end"]) for h in COCKPIT["hooks"] for b in h.get("bigwords", [])]
    out += [(m["t0"], max(m["t1"] + 0.3, m["t0"] + 1.6)) for m in moments() if m.get("mot") and "mot" in CHOIX_MOMENT]   # mot géant caché : rien à mesurer
    out += [(m["t0"], max(m["t1"] + 0.8, m["t0"] + 1.8)) for m in moments() if m["choix"] == "motion"]   # motion design : même plage que build.mjs
    return out


def tetes():
    v = int(os.path.getmtime(os.path.join(D, "clip.mp4")))
    if TETES["clip_v"] != v:   # nouvelle coupe = nouvelle vidéo : on remesure
        old = lire(os.path.relpath(TETES_P, D)) or {}
        TETES.update(clip_v=v, spans=old.get("spans", {}) if old.get("clip_v") == v else {})
    manque = [s for s in spans_mots() if cle_tete(*s) not in TETES["spans"]]
    if manque and not _TETES_FIL["vivant"] and JOB["etat"] != "en cours":
        _TETES_FIL["vivant"] = True
        threading.Thread(target=_mesurer, args=(manque,), daemon=True).start()
    return TETES["spans"]


def _mesurer(spans):
    try:
        for a, b in spans:
            try:
                r = subprocess.run(["python3", os.path.join(S, "headtop.py"), os.path.join(D, "clip.mp4"), str(a), str(b), "--json"],
                                   capture_output=True, text=True, timeout=120)
                TETES["spans"][cle_tete(a, b)] = json.loads(r.stdout) if r.returncode == 0 else {"aucune": True}
            except Exception:
                TETES["spans"][cle_tete(a, b)] = {"aucune": True}
            ecrire(os.path.relpath(TETES_P, D), TETES)
    finally:
        _TETES_FIL["vivant"] = False


def plan_final(h=None, st=None, m="choisie"):
    principal = h is None   # les choix de l'étape 3 vont sur le reel (un reel d'essai a son propre hook et ses propres temps)
    plan = json.loads(json.dumps(BASE))
    for k in ("title", "bigwords", "keywords"):
        plan.pop(k, None)
    h = h or next(x for x in COCKPIT["hooks"] if x["id"] == ETAT["hook"])   # h = un reel d'essai (v2) : son propre hook
    st = st or {"taille": ETAT["taille"], "place": ETAT["place"]}               # st, m = son style de sous-titres, sa musique
    for k in ("title", "bigwords"):
        if k in h:   # copie : ajouter_moments ajoute ses mots géants au plan ; avant, il les ajoutait à la liste du hook
            plan[k] = json.loads(json.dumps(h[k]))   # lui-même (« script » x2, x3… à chaque calcul : retour n2 du 23/10)
    # mots forts : serif blanc géant (Style Lab : jamais en couleur), ignorés par le moteur s'il y a un titre
    if ETAT["mots_forts"] and "title" not in plan:
        geants = {norm(b["text"]) for b in plan.get("bigwords", [])}   # le mot géant sort déjà du sous-titre
        plan["keywords"] = [k for k in COCKPIT.get("keywords", []) if norm(k) not in geants]
    plan["subSize"] = max(44, min(58, int(st["taille"])))   # Style Lab : jamais de texte ≥ 60 px
    if BASE.get("subY"):
        plan["subY"] = max(560, min(1480 - round(53 * plan["subSize"] / 52), BASE["subY"] + PLACES[st["place"]]))
    if st.get("mots_max", 4) < 4:
        plan["subMax"] = st["mots_max"]
    m = musique_choisie() if m == "choisie" else m
    if m:
        plan["music"] = {"src": m["src"], "from": m.get("from", 0), "target": m.get("target", -29),
                         "emotion": f"{m['nom']} · {m['titre']} (choisi dans le cockpit)"}
    else:
        plan.pop("music", None)   # « Sans musique » : la personne l'ajoute dans Insta (mix.py : voix seule)
    plan["words"] = "words.json"
    lk, sty = look_actif(), style_actif()
    if sty:   # 23/10 : le style réglé (6 polices + 5 réglages) passe avant l'ancien look ; « style » dans le plan = refaire le rendu s'il change
        plan["typo"] = typo(sty)
        if "title" in plan:
            plan["title"] = dict(plan["title"], top=TITRE_PLACES.get(sty["titre_place"], 280))
        if sty["mots"] < 4 and "mots_max" not in st:   # un reel d'essai garde son propre découpage
            plan["subMax"] = sty["mots"]
        plan["da"] = ecrire_da_style(sty)
        plan["style"] = sty
    elif lk:   # sans look, le plan reste celui de Claude (rendu identique) ; « look » dans le plan = refaire le rendu s'il change
        plan["da"] = ecrire_da_look(lk)
        plan["look"] = {k: lk[k] for k in ("id", "sans", "serif", "texte", "serif_couleur", "accent", "rythme")}
    # 23/10 (l'utilisateur, après test) : étape 3 SUPPRIMÉE (zoom, carton, mot géant, motion, B-roll des moments) : ajouter_moments n'est plus appelé.
    if plan.get("keywords") and plan.get("bigwords"):   # un mot fort qui contient un mot géant (« piège du script » / SCRIPT) :
        geants = {norm(b["text"]) for b in plan["bigwords"]}   # le mot géant le remplace (avant : « piège du » seul en serif)
        plan["keywords"] = [k for k in plan["keywords"] if not geants & {norm(x) for x in k.split()}]
    return plan


# ---------- v2 (22/10) : l'Export fabrique les 6 contenus, un par un (Mac 8 Go), puis la demande de programmation ----------
HOME = os.path.expanduser("~")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CARROUSEL = os.path.join(HOME, ".claude", "skills", "carrousel", "scripts", "carrousel.py")
OPEN_CARRUSEL = os.path.join(HOME, "open-carrusel")
ENV = dict(os.environ, PATH=f"{HOME}/.local/bin:{HOME}/.local/node/bin:" + os.environ.get("PATH", ""))
RESEAUX = {"instagram": "Instagram", "tiktok": "TikTok", "youtube": "YouTube Shorts", "facebook": "Facebook"}
ORDRE = ["story", "carrousel", "reel"]   # les images d'abord (rapides), puis les vidéos (~2 min chacune), puis les essais


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def gardien_ok(d):
    p = os.path.join(d, "gardien.log")
    g = open(p).read() if os.path.exists(p) else ""
    return "❌" not in g and "GARDIEN" in g


def a_jour(d, plan):
    """Le final.mp4 de ce dossier a été fabriqué avec CE plan, après la dernière coupe, et le Gardien l'a passé : rien à refaire."""
    fin, p, clip = (os.path.join(d, f) for f in ("final.mp4", "plan.json", "clip.mp4"))
    if not all(os.path.exists(x) for x in (fin, p, clip)) or json.load(open(p)) != plan:
        return False
    return os.path.getmtime(fin) > max(os.path.getmtime(p), os.path.getmtime(clip)) and gardien_ok(d)


def video(d, plan, nom):
    """Le vrai moteur dans le dossier d : matte.py si mot géant, puis monte.sh (Gardien avant ET après le rendu)."""
    t = JOB["courante"]
    deja = a_jour(d, plan)
    if not deja:
        json.dump(plan, open(os.path.join(d, "plan.json"), "w"), ensure_ascii=False, indent=1)
        if plan.get("bigwords") and not commande(["python3", os.path.join(S, "matte.py"), "plan.json"], f"matte-{nom}.log", d):
            return False
        ok = commande(["bash", os.path.join(S, "monte.sh"), d], f"fabrication-{nom}.log", d)
        if not (ok and os.path.exists(os.path.join(d, "final.mp4")) and gardien_ok(d)):
            stop = [x for x in JOB["lignes"] if "⛔" in x or "❌" in x]
            t["detail"] = stop[-1] if stop else "le Gardien bloque"
            return False
    t["detail"] = ("déjà prêt · " if deja else "") + f"Gardien ✅ · {mmss(duree(os.path.join(d, 'final.mp4')))}"
    return True


def fusion(plages):
    out = []
    for a, b in sorted(plages):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def dernier_mot(d):
    w = json.load(open(os.path.join(d, "words.json")))["words"]
    return w[-1]["end"] if w else 0.0


def preparer_essai(e):
    """essais/<id>/ : même coupe que le reel (clip.mp4 en lien dur, 0 Mo de plus). Version courte (debut_mot = indice du mot du
    RUSH où l'essai démarre) : son propre dérush, corrections de texte comprises. Rien n'est écrit dans le dossier du reel."""
    d = os.path.join(D, "essais", e["id"])
    os.makedirs(d, exist_ok=True)
    clip = os.path.join(d, "clip.mp4")
    if e.get("debut_mot"):
        drop = fusion(lire("drop.json", []) + [[0, e["debut_mot"] - 1]])
        pl = [[max(a, RW[e["debut_mot"]]["start"] - 0.15), b] for a, b in lire("plages.json", []) if b > RW[e["debut_mot"]]["start"]]   # v5 : la timeline
        sig, sp = {"drop": drop, "garde": gardes(), "rush": RUSH, "plages": pl}, os.path.join(d, "source.json")
        if not (os.path.exists(clip) and os.path.exists(sp) and json.load(open(sp)) == sig):
            JOB["courante"]["detail"] = "Coupe de la version courte"
            json.dump(drop, open(os.path.join(d, "drop.json"), "w"))
            vf = (lire("cadre.json") or {}).get("vf")
            cmd = ["python3", os.path.join(S, "derush.py"), RUSH, os.path.join(D, "words_rush.json"), "cut.mp4", "--drop", "drop.json"]
            if pl:
                json.dump(pl, open(os.path.join(d, "plages.json"), "w"))
                cmd += ["--plages", "plages.json"]
            if vf:
                cmd += ["--vf", vf]
            if gardes():
                cmd += ["--garde", os.path.join(D, "garde.json")]
            if not commande(cmd, f"derush-{e['id']}.log", d) or not os.path.exists(os.path.join(d, "cut.mp4")):
                return None
            os.replace(os.path.join(d, "cut.mp4"), clip)
            appliquer_corrections(d, drop)
            json.dump(sig, open(sp, "w"))
    else:
        src = os.path.join(D, "clip.mp4")
        if not (os.path.exists(clip) and os.stat(clip).st_ino == os.stat(src).st_ino):   # Remettre / Couper = nouveau clip
            if os.path.exists(clip):
                os.remove(clip)
            os.link(src, clip)
        for f in ("words.json", "cut.segments.json", "cut.voice.json"):
            if os.path.exists(os.path.join(D, f)):
                shutil.copy(os.path.join(D, f), os.path.join(d, f))
    return d


def plan_essai(e, d):
    """Le plan du reel + le hook, le style de sous-titres et la musique de l'essai."""
    m = musique_essai(e)
    plan = plan_final(e, style_essai(e), m)
    if m and m["src"] == (musique_choisie() or {}).get("src") and os.path.exists(os.path.join(d, "words.json")):
        decal = dernier_mot(D) - dernier_mot(d)   # version courte, même musique : la montée tombe toujours sur la même phrase
        if abs(decal) > 0.01:
            plan["music"]["from"] = round(max(0.0, plan["music"].get("from", 0) + decal), 2)
    return plan


def fab_essai(e):
    d = preparer_essai(e)
    return bool(d) and video(d, plan_essai(e, d), e["id"])


def debut_essai(e):
    """Où l'essai démarre dans le clip du reel (aperçu de la carte) : 0 sauf version courte."""
    if not e.get("debut_mot"):
        return 0.0
    k, w = gardes_indices(lire("drop.json", [])), lire("words.json")["words"]
    j = next((n for n, i in enumerate(k) if i >= e["debut_mot"]), None)
    return round(max(0.0, w[j]["start"] - 0.1), 2) if j is not None and len(k) == len(w) else 0.0


def image_clip(t, out, largeur=None):
    vf = ["-vf", f"scale={largeur}:-2"] if largeur else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", os.path.join(D, "clip.mp4"), "-frames:v", "1", *vf,
                    "-q:v", "2", out], check=True)
    return out


def taille_image(p):
    o = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", p]).decode()
    return tuple(int(x) for x in o.strip().split(",")[:2])


def capture(html, png, l, h):
    """Chrome headless : profil à part + trousseau factice (jamais la fenêtre « mot de passe » du Mac)."""
    page = png[:-4] + ".html"
    open(page, "w").write(html)
    if os.path.exists(png):
        os.remove(png)
    subprocess.run([CHROME, "--headless=new", "--use-mock-keychain", "--disable-gpu", "--hide-scrollbars",
                    "--user-data-dir=" + os.path.join(AP, "chrome"), "--force-device-scale-factor=1", f"--window-size={l},{h}",
                    "--virtual-time-budget=3000", "--screenshot=" + png, "file://" + page], capture_output=True, timeout=120)
    return os.path.exists(png)


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


def esc_html(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# La story : une image du reel + le titre du reel (même style) + un sticker « Nouveau reel ». Texte hors des zones mortes
# des stories (haut ~250 px, bas ~340 px), sticker sous 60 px (règle Style Lab).
STORY = """<!doctype html><meta charset="utf-8"><style>
@font-face{font-family:MS;src:url(data:font/ttf;base64,@MS@)}
@font-face{font-family:IS;src:url(data:font/ttf;base64,@IS@)}
html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}
.bg{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover}
.ht{position:absolute;left:0;right:0;top:300px;text-align:center;color:#fff;text-shadow:0 3px 18px rgba(0,0,0,.55);padding:30px 60px 38px;
    background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.5) 22%,rgba(0,0,0,.5) 78%,rgba(0,0,0,0))}
.ht1{font-family:MS;font-weight:700;font-size:46px;letter-spacing:1px;text-transform:uppercase}
.ht2{font-family:IS;font-style:italic;font-size:104px;line-height:1.05}
.st{position:absolute;left:50%;top:1250px;transform:translateX(-50%) rotate(-3deg);background:#fff;color:#0E1621;border-radius:30px;
    padding:28px 46px;font-family:MS;font-weight:800;font-size:52px;display:flex;align-items:center;gap:18px;white-space:nowrap;
    box-shadow:0 18px 50px rgba(0,0,0,.35)}
</style><img class="bg" src="data:image/jpeg;base64,@IMG@">@TITRE@
<div class="st">@STICKER@<svg width="46" height="46" viewBox="0 0 24 24"><path d="M7 17L17 7M9 7h8v8" stroke="#0E1621"
stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>"""


def fab_story():
    s, d = COCKPIT.get("story", {}), os.path.join(D, "story")
    os.makedirs(d, exist_ok=True)
    img = image_clip(s.get("t", 2.6), os.path.join(d, "image.jpg"))
    T = next(x for x in COCKPIT["hooks"] if x["id"] == ETAT["hook"]).get("title")
    titre = f'<div class="ht"><div class="ht1">{esc_html(T["l1"])}</div><div class="ht2">{esc_html(T["l2"])}</div></div>' if T else ""
    sty = style_actif()
    lk = ({"sans": police(sty["police"])["t1"]["font"], "serif": police(sty["police"])["t2"]["font"]} if sty else
          look_actif() or {"sans": "Montserrat.ttf", "serif": "InstrumentSerif-Italic.ttf"})
    html = (STORY.replace("@MS@", b64(os.path.join(SKILL, "fonts", lk["sans"])))
            .replace("@IS@", b64(os.path.join(SKILL, "fonts", lk["serif"])))
            .replace("@IMG@", b64(img)).replace("@TITRE@", titre).replace("@STICKER@", esc_html(s.get("sticker", "Nouveau reel"))))
    png = os.path.join(d, "story.png")
    if not capture(html, png, 1080, 1920):
        JOB["courante"]["detail"] = "Chrome n'a pas fait l'image"
        return False
    l, h = taille_image(png)
    JOB["courante"]["detail"] = f"{l}x{h}"
    return (l, h) == (1080, 1920)


def oc_repond(delai=5):
    try:
        urllib.request.urlopen("http://localhost:3210/api/brand", timeout=delai).read()
        return True
    except Exception:
        return False


def fab_carrousel():
    """Le skill carrousel (modèle validé bleu-blanc, dessins SVG, jamais d'image IA) avec des images DU REEL (clip.mp4, sans
    sous-titres) et le texte écrit par Claude d'après ce que la personne dit (cockpit.json → carrousel)."""
    c, t = COCKPIT["carrousel"], JOB["courante"]
    d, tmp = os.path.join(D, "carrousel"), os.path.join(AP, "carrousel")
    os.makedirs(tmp, exist_ok=True)
    nom = re.sub(r"[^a-z0-9]+", "-", os.path.basename(D).lower()).strip("-")
    t["detail"] = "Images du reel"
    photos, noms = {}, {}
    for k, p in c["photos"].items():
        noms[k] = f"ck-{nom}-{k}"   # prep.py range les photos dans Open Carrusel : nom unique par reel
        photos[noms[k]] = dict({x: p[x] for x in ("fx", "fy", "zoom", "bright", "grad") if x in p},
                               src=image_clip(p["t"], os.path.join(tmp, f"{k}.jpg")))
    slides = [dict(s, photo=noms[s["photo"]]) if s.get("photo") else s for s in c["slides"]]
    spec = {"name": f"{COCKPIT.get('titre', nom)} (cockpit)", "out": d, "photos": photos, "slides": slides,
            "caption": c.get("caption", ""), "hashtags": c.get("hashtags", [])}
    lance = None
    if not oc_repond():
        t["detail"] = "J'ouvre Open Carrusel (~30 s)"
        lance = subprocess.Popen(["npm", "run", "dev", "--", "-p", "3210"], cwd=OPEN_CARRUSEL, env=ENV, start_new_session=True,
                                 stdout=open(os.path.join(AP, "open-carrusel.log"), "w"), stderr=subprocess.STDOUT)
        fin = time.time() + 180
        while time.time() < fin and not oc_repond(30):
            time.sleep(2)
    try:
        ancien = os.path.join(d, "spec.json")
        if os.path.exists(ancien):   # même carrousel dans Open Carrusel qu'au dernier passage (pas un doublon par essai)
            cid = json.load(open(ancien)).get("id")
            try:
                urllib.request.urlopen(f"http://localhost:3210/api/carousels/{cid}", timeout=30).read()
                spec["id"] = cid
            except Exception:
                pass
        sp = os.path.join(tmp, "spec.json")
        json.dump(spec, open(sp, "w"), ensure_ascii=False, indent=1)
        t["detail"] = f"Montage des {len(slides)} slides (~1 min)"
        if not commande(["python3", CARROUSEL, sp], "carrousel.log", tmp):
            t["detail"] = "le carrousel a échoué (voir _cockpit/carrousel.log)"
            return False
    finally:
        if lance:   # ouvert pour l'occasion : refermé (Mac 8 Go, les rendus vidéo arrivent)
            try:
                os.killpg(lance.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    pngs = [os.path.join(d, f"slide-{i}.png") for i in range(1, len(slides) + 1)]
    ok = all(os.path.exists(p) and taille_image(p) == (1080, 1440) for p in pngs)
    t["detail"] = f"{len(slides)} slides 1080x1440" if ok else "slides manquantes ou de travers"
    return ok


def sortie(cid):
    if cid == "reel":
        return os.path.join(D, "final.mp4")
    if cid == "story":
        return os.path.join(D, "story", "story.png")
    if cid == "carrousel":
        return os.path.join(D, "carrousel", "slide-1.png")
    return os.path.join(D, "essais", cid, "final.mp4")


def demain_midi():
    return (dt.datetime.now() + dt.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)


def calendrier():
    """Le reel à l'heure choisie (défaut demain 12h) ; la story 15 min après ; le carrousel le lendemain à 12h ; les reels
    d'essai 1 par jour à 18h dès le lendemain (Instagram ne les montre d'abord qu'aux non-abonnés)."""
    p = ETAT["prog"]
    try:
        r = dt.datetime.fromisoformat(p.get("quand") or "")
    except ValueError:
        r = None
    if not r or r < dt.datetime.now() + dt.timedelta(minutes=10):
        r = demain_midi()
        p["quand"] = r.strftime("%Y-%m-%dT%H:%M")
    hh, mm = (int(x) for x in (p.get("essais_heure") or "18:00").split(":"))
    lend = (r + dt.timedelta(days=1)).replace(hour=0, minute=0)
    cal = {"reel": r, "story": r + dt.timedelta(minutes=15), "carrousel": lend.replace(hour=12)}
    for i, e in enumerate(ESSAIS):
        cal[e["id"]] = (lend + dt.timedelta(days=i)).replace(hour=hh, minute=mm)
    return {k: v.strftime("%Y-%m-%dT%H:%M") for k, v in cal.items()}


def fuseau():
    try:
        out = subprocess.check_output(["python3", "-E", os.path.join(HOME, ".claude", "skills", "publieur", "scripts", "_config.py")],
                                      stderr=subprocess.DEVNULL, timeout=20)
        return json.loads(out).get("timezone") or "Europe/Paris"
    except Exception:
        return "Europe/Paris"


def ecrire_publication(ids):
    """Une DEMANDE pour le Publieur (rien n'est publié ici) : chaque contenu, ses fichiers, ses réseaux, son heure et les
    données Metricool à envoyer. Reel d'essai = instagramData.type TRIAL_REEL (vérifié dans createScheduledPost le 22/10)."""
    cal, p, titre = calendrier(), ETAT["prog"], COCKPIT.get("titre", "")
    contenus, alertes = [], []
    for cid in [c for c in NOMS_C if c in ids]:
        f = sortie(cid)
        x = {"id": cid, "nom": NOMS_C[cid], "quand": cal[cid], "fichiers": [f]}
        if cid == "reel":
            res = [r for r in p["reseaux"] if r in RESEAUX]
            md = {"instagram": {"instagramData": {"type": "REEL", "showReelOnFeed": True}},
                  "facebook": {"facebookData": {"type": "REEL", "title": titre}},
                  "tiktok": {"tiktokData": {"privacyOption": "PUBLIC_TO_EVERYONE", "title": titre}},
                  "youtube": {"youtubeData": {"title": titre, "type": "short", "privacy": "public", "madeForKids": False,
                                              "notifySubscribers": False}}}
            x.update(reseaux=res, legende=COCKPIT.get("legende", ""), duree=round(duree(f), 1),
                     gardien="✅" if gardien_ok(D) else "❌", metricool={r: md[r] for r in res})
            if "tiktok" in res and duree(f) < 60:
                alertes.append(f"TikTok : le reel dure {mmss(duree(f))}. Ta règle du 20/10 : plus de 60 s pour être payé par TikTok.")
        elif cid == "story":
            x.update(reseaux=["instagram"], metricool={"instagram": {"instagramData": {"type": "STORY"}}})
        elif cid == "carrousel":
            n = len(COCKPIT["carrousel"]["slides"])
            x.update(reseaux=["instagram"], fichiers=[os.path.join(D, "carrousel", f"slide-{i}.png") for i in range(1, n + 1)],
                     legende=COCKPIT["carrousel"].get("caption", ""), metricool={"instagram": {"instagramData": {"type": "POST"}}})
            cta = next((s["cta"] for s in COCKPIT["carrousel"]["slides"] if s.get("cta")), None)
            if cta:
                alertes.append(f"Carrousel : le mot {cta} doit répondre en DM (ManyChat) avant la publication.")
        else:
            e = next(e for e in ESSAIS if e["id"] == cid)
            x.update(reseaux=["instagram"], legende=e.get("legende") or COCKPIT.get("legende", ""), duree=round(duree(f), 1),
                     gardien="✅" if gardien_ok(os.path.dirname(f)) else "❌", hook=e.get("title"),
                     musique=(musique_essai(e) or {}).get("titre", "sans musique"), sous_titres=style_essai(e)["nom"],
                     metricool={"instagram": {"instagramData": {"type": "TRIAL_REEL"}}})
        contenus.append(x)
    ecrire("publication.json", {
        "_doc": "Demande du cockpit : RIEN n'est programmé. Claude la fait passer par le Publieur (Metricool) seulement après un OK "
                "dans le chat. metricool = les données réseau à envoyer à createScheduledPost pour chaque réseau.",
        "statut": "à valider dans le chat", "demande_le": time.strftime("%Y-%m-%d %H:%M"), "fuseau": fuseau(),
        "dossier": D, "contenus": contenus, "alertes": alertes,
        "note_claude": "Le Publieur dit « trial reel jamais par défaut » (règle d'avant le 22/10) : les reels d'essai du cockpit sont le "
                       "choix de l'utilisateur du 22/10, son OK sur ce lot vaut exception. 3 reels par jour max (essais compris)."})


def tout(ids, programmer):
    JOB["taches"] = [{"id": c, "nom": NOMS_C[c], "etat": "attente", "detail": "", "debut": 0, "fin": 0} for c in ids]
    fab = {"reel": lambda: video(D, plan_final(), "reel"), "story": fab_story, "carrousel": fab_carrousel}
    fab.update({e["id"]: (lambda e=e: fab_essai(e)) for e in ESSAIS})
    for t in JOB["taches"]:   # un par un : le Mac a 8 Go, deux rendus en même temps le font ramer
        t.update(etat="en cours", debut=time.time())
        JOB["courante"] = t
        try:
            ok = fab[t["id"]]()
        except Exception as ex:
            JOB["lignes"].append(f"⛔ {t['nom']} : {ex}")
            t["detail"], ok = str(ex)[:160], False
        t.update(etat="fini" if ok else "erreur", fin=time.time())
    JOB["courante"] = None
    if not all(t["etat"] == "fini" for t in JOB["taches"]):
        return False
    if programmer:
        ecrire_publication(ids)
    return True


# ---------- aperçu du rush (le rush original est souvent en HEVC 4K : le navigateur ne le lit pas partout) ----------
def apercu_rush():
    out = os.path.join(AP, "rush.mp4")
    if os.path.exists(out) or not RUSH:
        return
    vf = (lire("cadre.json") or {}).get("vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", RUSH, "-vf", vf + ",scale=540:960", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "27", "-c:a", "aac", "-b:a", "96k", out + ".part.mp4"])
    if os.path.exists(out + ".part.mp4"):
        os.replace(out + ".part.mp4", out)


def notes():
    """cockpit-notes.json : {id, quand, t (instant du reel, None = vidéo en lecture), texte, statut "à faire" | "corrigé", reponse}.
    Claude les lit dans le chat, corrige, puis écrit statut "corrigé" + reponse : la page affiche sa réponse."""
    out = []
    for i, n in enumerate(lire("cockpit-notes.json", [])):
        out.append(dict({"id": f"n{i + 1}", "t": None, "statut": "à faire", "reponse": ""}, **n))
    return out


def _sur(f, defaut):
    """Derush Lab : sans plan.json, ce qui sert au Style / à l'Export peut manquer ; la timeline n'en a pas besoin."""
    if not LAB:
        return f()
    try:
        return f()
    except Exception:
        return defaut


def etat_page():
    if JOB["etat"] != "en cours":
        relire_cockpit()
    fin = os.path.join(D, "final.mp4")
    gardien = ""
    if os.path.exists(os.path.join(D, "gardien.log")):
        gardien = open(os.path.join(D, "gardien.log")).read()
    return {
        "projet": {"titre": COCKPIT.get("titre", os.path.basename(D)), "rush": round(RUSH_DUREE, 1),
                   "reel": round(duree(os.path.join(D, "clip.mp4")), 1),
                   "clip_v": int(os.path.getmtime(os.path.join(D, "clip.mp4")))},
        "coupes": coupes(),
        "hooks": [{k: v for k, v in h.items()} for h in COCKPIT["hooks"]],
        "musiques": [{k: v for k, v in m.items() if k != "src"} for m in _sur(musiques, [])],
        "looks": _sur(looks, []), "look": _sur(look_actif, None), "polices": POLICES, "style": _sur(style_actif, None), "noms_polices": NOMS_POLICES, "noms_couleurs": NOMS_COULEURS,
        "notes": notes(), "moments": _sur(moments, []), "tetes": _sur(tetes, {}), "illus": ILLUS, "effets": CHOIX_MOMENT,
        "lab": lab_etat() if LAB else None,
        "reco": {"hook": COCKPIT.get("reco_hook"), "musique": COCKPIT.get("reco_musique")},
        "keywords": COCKPIT.get("keywords", []), "legende": COCKPIT.get("legende", ""),
        "base": {"subY": BASE.get("subY", 1340), "subSize": BASE.get("subSize", 52), "fixes": BASE.get("fixes", {}),
                 "zoom": BASE.get("zoom", True) is not False},
        "words": lire("words.json")["words"],
        "rush_mots": mots_rush(), "phrases": phrases_rush(), "segs": lire("cut.segments.json", []), "derush": derush_choix(),
        "planche": planche_rush()[1] if os.path.exists(os.path.join(AP, "planche.jpg")) else None,
        "choix": ETAT, "job": JOB, "rush_pret": os.path.exists(os.path.join(AP, "rush.mp4")),
        "final": {"existe": os.path.exists(fin), "v": int(os.path.getmtime(fin)) if os.path.exists(fin) else 0,
                  "duree": round(duree(fin), 1) if os.path.exists(fin) else 0,
                  "gardien_ok": "❌" not in gardien and "GARDIEN" in gardien},
        "publication": lire("publication.json"),
        "contenus": _sur(contenus_etat, []), "cal": _sur(calendrier, {}), "reseaux": RESEAUX,
    }


def contenus_etat():
    """Les cartes de l'écran Export : ce qu'on montre avant (aperçu) et après (le vrai fichier)."""
    out = []
    for cid, nom in NOMS_C.items():
        f = sortie(cid)
        x = {"id": cid, "nom": nom, "existe": os.path.exists(f), "v": int(os.path.getmtime(f)) if os.path.exists(f) else 0}
        if cid == "reel":
            x.update(type="video", gardien=gardien_ok(D), duree=round(duree(f), 1) if x["existe"] else 0, pret=a_jour(D, plan_final()))
        elif cid == "story":
            s = COCKPIT.get("story", {})
            x.update(type="story", t=s.get("t", 2.6), sticker=s.get("sticker", "Nouveau reel"))
        elif cid == "carrousel":
            cv = next((s for s in COCKPIT["carrousel"]["slides"] if s["type"] == "cover"), {})
            x.update(type="carrousel", t=COCKPIT["carrousel"]["photos"].get(cv.get("photo"), {}).get("t", 2.6),
                     mot=cv.get("word", ""), slides=len(COCKPIT["carrousel"]["slides"]))
        else:
            e, d = next(e for e in ESSAIS if e["id"] == cid), os.path.dirname(f)
            m = musique_essai(e) or {}
            x.update(type="video", essai=True, hook={k: e[k] for k in ("title", "bigwords") if k in e}, detail=e.get("detail", ""),
                     decal=debut_essai(e), gardien=gardien_ok(d), duree=round(duree(f), 1) if x["existe"] else 0,
                     st=style_essai(e), musique={"nom": m.get("nom", ""), "titre": m.get("titre", ""), "from": m.get("from", 0)},
                     pret=os.path.isdir(d) and a_jour(d, plan_essai(e, d)))
        out.append(x)
    return out


TYPES = {".mp4": "video/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac", ".ttf": "font/ttf",
         ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".html": "text/html; charset=utf-8"}


class Page(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def json(self, v, code=200):
        b = json.dumps(v, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def fichier(self, p):
        if not p or not os.path.isfile(p):
            return self.send_error(404)
        taille = os.path.getsize(p)
        a, b = 0, taille - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                a = int(m.group(1))
                b = min(int(m.group(2)), taille - 1) if m.group(2) else taille - 1
            else:
                a = max(0, taille - int(m.group(2)))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {a}-{b}/{taille}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", TYPES.get(os.path.splitext(p)[1].lower(), "application/octet-stream"))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(b - a + 1))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(p, "rb") as f:
                f.seek(a)
                reste = b - a + 1
                while reste > 0:
                    bout = f.read(min(1 << 16, reste))
                    if not bout:
                        break
                    self.wfile.write(bout)
                    reste -= len(bout)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        u = urlparse(self.path).path
        if u == "/":
            return self.fichier(os.path.join(ICI, "cockpit.html"))
        if u == "/api/etat":
            return self.json(etat_page())
        if u == "/api/onde":
            return self.json(onde())
        if u == "/api/planche":   # v5 : les images du rush (timeline)
            return self.fichier(planche_rush()[0])
        if u == "/video/clip":
            return self.fichier(os.path.join(D, "clip.mp4"))
        if u == "/video/rush":
            return self.fichier(os.path.join(AP, "rush.mp4"))
        if u == "/video/final":
            return self.fichier(os.path.join(D, "final.mp4"))
        if u.startswith("/image/"):   # une image du clip (cartes de l'Export), gardée en cache
            try:
                t = round(float(u.split("/")[-1]), 2)
            except ValueError:
                return self.send_error(404)
            p = os.path.join(AP, "images", f"{t}.jpg")
            if not os.path.exists(p):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                image_clip(t, p, 540)
            return self.fichier(p)
        if u == "/sortie/carrousel/planche":
            return self.fichier(os.path.join(D, "carrousel", "00-planche.png"))
        if re.fullmatch(r"/sortie/carrousel/\d+", u):
            return self.fichier(os.path.join(D, "carrousel", f"slide-{u.split('/')[-1]}.png"))
        if u.startswith("/sortie/") and u.split("/")[-1] in NOMS_C:
            return self.fichier(sortie(u.split("/")[-1]))
        if u.startswith("/musique/"):
            cle = u.split("/")[-1]   # un id de l'étape Musique, ou l'id d'un reel d'essai (sa musique à lui)
            m = next((x for x in musiques() if x["id"] == cle), None) or \
                next((musique_essai(e) for e in ESSAIS if e["id"] == cle), None)
            return self.fichier(m and os.path.expanduser(m["src"]))
        if u.startswith("/broll/"):   # le B-roll envoyé par la personne pour un moment (étape 3)
            return self.fichier(broll_de(u.split("/")[-1]))
        if u.startswith("/polices/"):
            return self.fichier(os.path.join(SKILL, "fonts", os.path.basename(u)))
        if u == "/api/biblio":   # étape 3 « Ma bibliothèque » : ses B-rolls (recherche ?q=), jamais d'IA
            from urllib.parse import parse_qs
            q = (parse_qs(urlparse(self.path).query).get("q") or [""])[0]
            return self.json([{k: r[k] for k in ("f", "nom", "duree")} for r in chercher_biblio(q, 60)])
        if u in ("/biblio/vignette", "/biblio/apercu"):   # une image (vignette) ou 3 s légères (aperçu dans le téléphone) d'un plan
            from urllib.parse import parse_qs
            import hashlib
            src = chemin_biblio((parse_qs(urlparse(self.path).query).get("f") or [""])[0])
            if not src or not os.path.exists(src):
                return self.send_error(404)
            img = u.endswith("vignette")
            out = os.path.join(AP, "vignettes", hashlib.md5(src.encode()).hexdigest() + (".jpg" if img else ".mp4"))
            if not os.path.exists(out):
                os.makedirs(os.path.dirname(out), exist_ok=True)
                vf = "scale=270:480:force_original_aspect_ratio=increase,crop=270:480" if img else \
                     "scale=540:960:force_original_aspect_ratio=increase,crop=540:960,fps=30"
                cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", "1", "-i", src, "-vf", vf]
                cmd += ["-frames:v", "1", "-q:v", "4"] if img else ["-t", "3", "-an", "-c:v", "libx264", "-crf", "26", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
                subprocess.run(cmd + [out + (".part.jpg" if img else ".part.mp4")])
                if os.path.exists(out + (".part.jpg" if img else ".part.mp4")):
                    os.replace(out + (".part.jpg" if img else ".part.mp4"), out)
            return self.fichier(out)
        if u.startswith("/illus/"):   # une illustration du Carrousel (motion design au trait)
            return self.fichier(illus_svg(os.path.splitext(os.path.basename(u))[0]))
        if u == "/api/plan":   # pour Claude : le plan que « Fabriquer » enverrait au moteur (look, musique, hook)
            return self.json(plan_final())
        if u == "/logo.png":
            return self.fichier(os.path.join(ICI, "logo-stratosphere.png"))   # 23/10 : logo Stratosphère (avant : logo perso)
        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        if u == "/api/musique":   # « Ajoute ta musique » : le fichier brut (pas du JSON), son nom dans l'en-tête X-Nom
            from urllib.parse import unquote
            nom = unquote(self.headers.get("X-Nom") or "musique.mp3")
            ext = os.path.splitext(nom)[1].lower()
            if ext not in EXT_AUDIO or not n or n > 60 << 20:
                self.rfile.read(n)
                return self.json({"ok": False, "erreur": "Un fichier MP3, M4A, WAV ou AAC de moins de 60 Mo."})
            for e in EXT_AUDIO:
                if os.path.exists(MUS_PERSO + e):
                    os.remove(MUS_PERSO + e)
            with open(MUS_PERSO + ext + ".part", "wb") as f:
                reste = n
                while reste > 0:
                    bout = self.rfile.read(min(1 << 16, reste))
                    if not bout:
                        break
                    f.write(bout)
                    reste -= len(bout)
            os.replace(MUS_PERSO + ext + ".part", MUS_PERSO + ext)
            if duree(MUS_PERSO + ext) < 1:
                os.remove(MUS_PERSO + ext)
                return self.json({"ok": False, "erreur": "Je n'arrive pas à lire ce fichier audio."})
            ETAT.update(musique="perso", musique_perso_nom=os.path.splitext(os.path.basename(nom))[0][:60])
            sauver_etat()
            return self.json({"ok": True})
        if u == "/api/broll":   # étape 3 « Ton B-roll » : la vidéo brute, son moment dans l'en-tête X-Moment
            from urllib.parse import unquote
            mid = re.sub(r"\W", "", self.headers.get("X-Moment") or "")
            ext = os.path.splitext(unquote(self.headers.get("X-Nom") or ""))[1].lower()
            if not mid or ext not in EXT_VIDEO or not n or n > 500 << 20:
                self.rfile.read(n)
                return self.json({"ok": False, "erreur": "Une vidéo MP4 ou MOV de moins de 500 Mo."})
            os.makedirs(BROLL_DIR, exist_ok=True)
            brut = os.path.join(BROLL_DIR, mid + "-brut" + ext)
            with open(brut, "wb") as f:
                reste = n
                while reste > 0:
                    bout = self.rfile.read(min(1 << 16, reste))
                    if not bout:
                        break
                    f.write(bout)
                    reste -= len(bout)
            sortie_b = os.path.join(BROLL_DIR, mid + ".mp4")
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", brut, "-t", "8", "-an",
                                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                                "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", sortie_b + ".part.mp4"])
            os.remove(brut)
            if r.returncode or duree(sortie_b + ".part.mp4") < 1:
                if os.path.exists(sortie_b + ".part.mp4"):
                    os.remove(sortie_b + ".part.mp4")
                return self.json({"ok": False, "erreur": "Je n'arrive pas à lire cette vidéo."})
            os.replace(sortie_b + ".part.mp4", sortie_b)
            ETAT["moments_choix"][mid] = "broll"
            ETAT["moments_reglages"].setdefault(mid, {})["broll"] = "perso"
            sauver_etat()
            return self.json({"ok": True})
        q = json.loads(self.rfile.read(n) or b"{}")
        if u == "/api/valider":   # Derush Lab : « ✓ Valider le dérush »
            pl = plages_propres(q.get("plages", []))
            if not pl:
                return self.json({"ok": False, "vide": True})
            d = {"plages": pl, "applique": derush_choix().get("applique", "")}
            ETAT["derush"] = d
            sauver_etat()
            return self.json({"ok": lancer("Je coupe ta vidéo et le Gardien la contrôle", lambda: valider(d))})
        if u == "/api/derush":   # v5 : les plages gardées de la timeline ; "appliquer" = le moteur recoupe
            pl = plages_propres(q.get("plages", []))
            if not pl:
                return self.json({"ok": False, "vide": True})
            d = {"plages": pl}
            sig = sig_plages(pl)
            d["applique"] = derush_choix().get("applique", "")
            if q.get("appliquer") and sig != d["applique"]:
                if JOB["etat"] == "en cours":
                    return self.json({"ok": False})
                derush_ecrire(d)
                d["applique"] = sig
                ETAT["derush"] = d
                sauver_etat()
                return self.json({"ok": lancer("Je coupe ta vidéo", derush), "recoupe": True})
            ETAT["derush"] = d
            sauver_etat()
            return self.json({"ok": True, "recoupe": False})
        if u == "/api/remettre":
            return self.json({"ok": remettre(q.get("id"))})
        if u == "/api/couper":
            return self.json({"ok": recouper(q.get("id"))})
        if u == "/api/choix":
            for k in ("etape", "hook", "taille", "place", "mots_forts", "musique", "coches", "prog", "look", "affine", "style", "coupes_ok", "passe", "moments_choix", "moments_reglages", "passe3", "extras"):
                if k in q:
                    ETAT[k] = q[k]
            sauver_etat()
            return self.json({"ok": True})
        if u == "/api/tout":
            # « Tout fabriquer et programmer » : les contenus cochés, un par un, puis publication.json (une demande)
            if JOB["etat"] != "en cours":
                relire_cockpit()
            # "ids" (v3) = fabriquer seulement ceux-là (ex. le reel seul) sans toucher aux interrupteurs de la planche
            if q.get("ids") is None:
                ETAT["coches"] = [c for c in q.get("coches", ETAT["coches"]) if c in NOMS_C]
            ETAT["prog"].update(q.get("prog", {}))
            sauver_etat()
            dem = q["ids"] if q.get("ids") is not None else ETAT["coches"]
            ids = [c for c in ORDRE + [e["id"] for e in ESSAIS] if c in dem]
            return self.json({"ok": bool(ids) and lancer("Tout fabriquer", lambda: tout(ids, q.get("programmer", True)))})
        if u == "/api/changer":
            # « Changer quelque chose » : la demande de programmation est mise de côté (rien n'était parti)
            if os.path.exists(os.path.join(D, "publication.json")):
                os.replace(os.path.join(D, "publication.json"), os.path.join(AP, "publication-annulee.json"))
            return self.json({"ok": True})
        if u == "/api/note":
            texte = str(q.get("texte", "")).strip()[:500]
            if not texte:
                return self.json({"ok": False})
            ns = lire("cockpit-notes.json", [])
            t = q.get("t")
            ns.append({"id": f"n{len(ns) + 1}", "quand": time.strftime("%Y-%m-%d %H:%M"),
                       "t": round(float(t), 2) if isinstance(t, (int, float)) else None,
                       "texte": texte, "statut": "à faire", "reponse": ""})
            ecrire("cockpit-notes.json", ns)
            return self.json({"ok": True})
        self.send_error(404)


if __name__ == "__main__":
    threading.Thread(target=lambda: (apercu_rush(), planche_rush()), daemon=True).start()
    print(f"Cockpit : http://127.0.0.1:{PORT}  ({D})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Page).serve_forever()
