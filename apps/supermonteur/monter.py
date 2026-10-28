"""SuperMonteur : la partie machine derrière l'écran (28/10/2026). Ne réécrit PAS le moteur : il enchaîne les scripts du
skill supermonteur (transcription, dérush, plan.json, monte.sh) et tient à jour etat.json, que la page lit.

    python3 monter.py regarder <dossier du reel>    écran 0 : transcription + devine_format -> style conseillé
    python3 monter.py monter   <dossier du reel>    « Monter le reel » : dérush + plan.json + monte.sh -> versions/v1.mp4
    python3 monter.py remonter <dossier du reel>    après les retours corrigés par Claude dans plan.json -> version N+1

Un seul montage à la fois sur le Mac (8 Go) : on attend qu'aucun autre rendu HyperFrames ne tourne.
"""
import datetime, fcntl, json, os, re, shutil, subprocess, sys, time, unicodedata

APP = os.path.dirname(os.path.abspath(__file__))
SK = os.path.expanduser("~/.claude/skills/supermonteur")
S = os.path.join(SK, "scripts")
ENV = dict(os.environ, PATH=os.path.expanduser("~/.local/bin") + ":" + os.path.expanduser("~/.local/node/bin") + ":" + os.environ.get("PATH", ""))
sys.path.insert(0, APP)
import da as DA
import reglages_apps

STYLES = ["Dynamique", "Minimaliste", "Comparatif", "Interview", "Autre"]
# recette de devine_format.py -> un des 5 styles (devine-format.md, tableau 4)
RECETTE = {"face-cam": "Dynamique", "raw": "Minimaliste", "montage-viral": "Comparatif", "a-plusieurs": "Interview",
           "podcast": "Interview", "voix-off": "Autre", "green-screen": "Autre", "broll-texte": "Autre"}


def lire(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def ecrire(p, o):
    t = p + ".tmp"
    json.dump(o, open(t, "w"), ensure_ascii=False, indent=1)
    os.replace(t, p)


def etat(D, **k):
    e = lire(os.path.join(D, "etat.json"), {})
    e.update(k)
    ecrire(os.path.join(D, "etat.json"), e)
    return e


def run(D, cmd, log):
    with open(os.path.join(D, log), "w") as f:
        r = subprocess.run(cmd, cwd=D, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        fin = open(os.path.join(D, log)).read().strip().splitlines()[-6:]
        raise RuntimeError(f"{os.path.basename(cmd[1]) if len(cmd) > 1 else cmd[0]} : " + " / ".join(fin))


def duree(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip() or 0)


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9' ]", "", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def phrases(words):
    """[(i0, i1)] : indices des mots de chaque phrase (fin = . ! ? …)."""
    P, i0 = [], 0
    for i, w in enumerate(words):
        if re.search(r"[.!?…]\s*$", w["text"].strip()):
            P.append((i0, i))
            i0 = i + 1
    if i0 < len(words): P.append((i0, len(words) - 1))
    return P


# ---------------------------------------------------------------------------------------------------- écran 0 : regarder
def regarder(D):
    e = lire(os.path.join(D, "etat.json"), {})
    rush = e["rush"]
    etat(D, statut="regarde", etape="Je regarde ta vidéo…")
    d = duree(rush)
    # une image du rush pour les aperçus des 5 styles (vraie image, pas un dessin)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d / 3:.2f}", "-i", rush, "-frames:v", "1",
                    "-vf", "scale=540:-2", os.path.join(D, "apercu.jpg")], env=ENV)
    if not os.path.exists(os.path.join(D, "words.rush.json")):
        run(D, ["python3", os.path.join(S, "transcribe.py"), rush, "words.rush.json"], "transcribe.log")
    conseil, pourquoi = "Dynamique", "toi seul face caméra"
    try:
        run(D, ["python3", os.path.join(S, "devine_format.py"), rush, "--words", "words.rush.json", "--out", "."], "devine.log")
        dv = lire(os.path.join(D, "devine.json"), {})
        p = (dv.get("propositions") or [{}])[0]
        conseil = RECETTE.get(p.get("recette"), "Dynamique")
        pourquoi = ", ".join(p.get("pourquoi", [])) or pourquoi
    except Exception as x:
        pourquoi = f"devine_format indisponible ({x})"
    W = (lire(os.path.join(D, "words.rush.json"), {}) or {}).get("words", [])
    P = phrases(W)
    # une question posée en 1re phrase, vidéo courte = FAQ = Minimaliste (devine-format.md : « FAQ = Minimaliste »)
    if conseil == "Dynamique" and P and W[P[0][1]]["text"].strip().endswith("?") and d < 90:
        conseil, pourquoi = "Minimaliste", "tu poses une question au début : format FAQ"
    etat(D, statut="choix", etape="", conseil=conseil, pourquoi=pourquoi, duree_rush=round(d, 1))


# ------------------------------------------------------------------------------------------------- le dérush automatique
def drop_auto(words):
    """Dernière prise gardée (SKILL étape 3) : une phrase reprise juste après (mêmes 3 premiers mots) = l'ancienne saute.
    Coupe toujours sur une fin de phrase (jamais au milieu, règle du 23/10)."""
    P = phrases(words)
    drop = []
    for k, (a, b) in enumerate(P):
        tete = " ".join(norm(words[i]["text"]) for i in range(a, min(a + 3, b + 1)))
        if len(tete.split()) < 3: continue
        for a2, b2 in P[k + 1:k + 4]:
            if " ".join(norm(words[i]["text"]) for i in range(a2, min(a2 + 3, b2 + 1))) == tete:
                drop.append([a, b])
                break
    return drop


def titre_auto(words):
    """Titre = 1re phrase (la question du hook), 2 lignes équilibrées, sans , . : (build.mjs les retire de toute façon)."""
    P = phrases(words)
    if not P: return None
    a, b = P[0]
    mots = [re.sub(r"[,.:;…?!]", "", words[i]["text"].strip()) for i in range(a, b + 1)]
    mots = [m for m in mots if m]
    if len(mots) > 9: mots = mots[:7]
    q = words[b]["text"].strip().endswith("?") and len(mots) <= 9
    if mots: mots[0] = mots[0][:1].upper() + mots[0][1:]
    best, cut = 9e9, 1
    for c in range(1, len(mots)):
        g = abs(len(" ".join(mots[:c])) - len(" ".join(mots[c:])))
        if g < best: best, cut = g, c
    l1, l2 = " ".join(mots[:cut]), " ".join(mots[cut:])
    return {"l1": l1, "l2": l2 + (" ?" if q else "")}


def musique_auto(D, rid):
    """Dossier REELS INSTA seulement (28/10) : jamais utilisées d'abord, jamais une des 3 derniers reels, tirage propre au reel."""
    out = subprocess.run(["python3", os.path.join(S, "musiques.py")], capture_output=True, text=True, env=ENV).stdout
    dossier = None
    try:
        sys.path.insert(0, S)
        import reglages
        dossier = reglages.config().get("music_reels") or reglages.config().get("music_epidemic")
    except Exception:
        pass
    L = [l for l in out.splitlines() if l.strip()]
    neuves = [l[39:].strip() for l in L if l.startswith("jamais utilisée")]
    vieilles = [l[39:].strip() for l in L if l.startswith("utilisée le")]
    pool = (neuves or vieilles)[:6]
    if not pool or not dossier: raise RuntimeError("pas de musique : mets des musiques dans ~/Documents/Montage/MUSIQUE (music_reels du config.json du skill supermonteur)")
    src = os.path.join(dossier, pool[sum(map(ord, rid)) % len(pool)])
    att = subprocess.run(["python3", os.path.join(S, "attaque.py"), src, "0", "60"], capture_output=True, text=True, env=ENV).stdout
    m = re.search(r"^\s*([\d.]+) s", att, re.M)
    return {"src": src, "from": float(m.group(1)) if m else 0.0,
            "emotion": f"choisie par SuperMonteur dans REELS INSTA (jamais utilisée d'abord), part sur son temps fort (attaque.py)"}


# ------------------------------------------------------------------------------------------------------- le montage
def attendre_le_mac(D):
    """Mac 8 Go : un rendu à la fois. Un autre chat rend déjà ? On attend (le dire à l'écran)."""
    verrou = open(os.path.join(APP, ".rendu.lock"), "w")
    while True:
        autres = subprocess.run(["pgrep", "-f", "hyperframes.*render"], capture_output=True, text=True).stdout.split()
        if not autres:
            try:
                fcntl.flock(verrou, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return verrou
            except BlockingIOError:
                pass
        etat(D, etape="J'attends que l'autre rendu du Mac finisse (un seul à la fois)…")
        time.sleep(10)


def monte(D):
    """monte.sh = B-rolls, composition, Gardien AVANT, rendu, mix, Gardien final, planche. Puis versions/vN.mp4."""
    e = lire(os.path.join(D, "etat.json"), {})
    verrou = attendre_le_mac(D)
    try:
        etat(D, etape="Je monte : composition, Gardien, rendu, son (~4 min)…")
        r = subprocess.run(["bash", os.path.join(S, "monte.sh"), "."], cwd=D, env=ENV, capture_output=True, text=True)
        open(os.path.join(D, "monte.log"), "w").write(r.stdout + r.stderr)
        if r.returncode or not os.path.exists(os.path.join(D, "final.mp4")):
            stop = [l for l in (r.stdout + r.stderr).splitlines() if "⛔" in l or "❌" in l]
            raise RuntimeError(" / ".join(stop[-4:]) or "monte.sh a échoué (voir monte.log)")
    finally:
        verrou.close()
    zones = subprocess.run(["node", os.path.join(S, "zones.mjs"), "."], cwd=D, env=ENV, capture_output=True, text=True)
    n = len(e.get("versions", [])) + 1
    os.makedirs(os.path.join(D, "versions"), exist_ok=True)
    shutil.copy2(os.path.join(D, "final.mp4"), os.path.join(D, "versions", f"v{n}.mp4"))
    shutil.copy2(os.path.join(D, "plan.json"), os.path.join(D, "versions", f"v{n}.plan.json"))
    v = e.get("versions", []) + [{"n": n, "fichier": f"versions/v{n}.mp4", "date": datetime.datetime.now().isoformat(timespec="seconds"),
                                   "duree": round(duree(os.path.join(D, "final.mp4")), 2),
                                   "zones": (zones.stdout.strip().splitlines() or ["?"])[-1]}]
    etat(D, statut="retours", etape="", version=n, versions=v, erreur=None)


def monter(D):
    e = lire(os.path.join(D, "etat.json"), {})
    rid, rush, style, cases = e["id"], e["rush"], e.get("style", "Dynamique"), e.get("cases", {})
    try:
        if not os.path.exists(os.path.join(D, "words.rush.json")):
            etat(D, etape="Je transcris ta vidéo…")
            run(D, ["python3", os.path.join(S, "transcribe.py"), rush, "words.rush.json"], "transcribe.log")
        W = lire(os.path.join(D, "words.rush.json"))["words"]
        etat(D, etape="Je dérushe : dernière prise gardée, blancs coupés…")
        ecrire(os.path.join(D, "drop.json"), drop_auto(W))
        # Minimaliste = cadre d'origine (styles/raw.md : le cadre serré met les cheveux dans le titre) ; sinon cadre.py
        st = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", rush]))["streams"][0]
        w, h = st["width"], st["height"]
        if any(abs(int(sd.get("rotation", 0))) == 90 for sd in st.get("side_data_list", [])): w, h = h, w
        if style == "Minimaliste" and h > w:
            vf = "scale=1080:1920:flags=lanczos,fps=30"
        else:
            run(D, ["python3", os.path.join(S, "cadre.py"), rush], "cadre.log")
            vf = lire(os.path.join(D, "cadre.json"))["vf"]
        run(D, ["python3", os.path.join(S, "derush.py"), rush, "words.rush.json", "cut.mp4", "--drop", "drop.json", "--vf", vf], "derush.log")
        os.replace(os.path.join(D, "cut.mp4"), os.path.join(D, "clip.mp4"))
        shutil.copy2(os.path.join(D, "cut.words.json"), os.path.join(D, "words.json"))
        etat(D, etape="J'écris le plan : titre, sous-titres, musique…")
        plan = plan_auto(D, rid, style, cases, lire(os.path.join(D, "words.json"))["words"])
        ecrire(os.path.join(D, "plan.json"), plan)
        monte(D)
    except Exception as x:
        etat(D, statut="erreur", etape="", erreur=str(x)[:600])
        log_erreur(f"SuperMonteur {rid} : montage v1 bloqué : {str(x)[:200]}")
        raise
    try:  # rush renommé « date titre - CAM20058.MP4 » pour le retrouver (28/10) ; jamais bloquant pour le reel
        import renommer_rush
        renommer_rush.renommer(D)
    except Exception as x:
        log_erreur(f"SuperMonteur {rid} : rush pas renommé : {str(x)[:200]}")


def plan_auto(D, rid, style, cases, words):
    dur = duree(os.path.join(D, "clip.mp4"))
    plan = {"cam": "clip.mp4", "words": "words.json", "zoom": False, "fixes": {}, "keywords": [], "sfx": [],
            "cases": cases, "style_supermonteur": style}
    T = titre_auto(words) if cases.get("titre", True) else None
    if T:
        # Minimaliste : le titre reste toute la vidéo ; les autres : pendant le hook (SKILL : title 0-4 s)
        T.update({"start": 0, "end": 999 if style == "Minimaliste" else 4.0, "top": 280})
        plan["title"] = T
    plan["music"] = musique_auto(D, rid)
    # signature finale (« … avec le cœur. [temps] la signature ») : son temps naturel est gardé (SKILL, Gardien pause_signature)
    P = phrases(words)
    if len(P) > 1:
        a, b = P[-1]
        if b - a <= 2 and words[a]["start"] - words[a - 1]["end"] <= 0.8 and dur - words[a]["start"] <= 3.0:
            plan["pause_signature"] = True
    # DA de SuperDA (da.json) traduite dans le format du moteur ; absente = DA du moteur (Brain da-montage.json)
    dm = DA.pour_moteur()
    if dm:
        ecrire(os.path.join(D, "da-supermonteur.json"), dm)
        plan["da"] = os.path.join(D, "da-supermonteur.json")
        if dm.get("subMax"): plan["subMax"] = dm["subMax"]
    if dur < 58:
        plan["duree_min"] = 0     # rush trop court pour passer 60 s sans rallonge visible : on le dit, on ne bloque pas
        plan["_court"] = f"{dur:.1f} s : sous 1 min (pas de monétisation TikTok)"
    plan["_note"] = (f"{datetime.date.today():%d/%m} SuperMonteur v1 auto, style {style} : dernière prise gardée, titre = 1re phrase, "
                     "musique REELS INSTA. Claude enrichit (mots forts, cartons, animations) au tour des retours.")
    return plan


def remonter(D):
    e = lire(os.path.join(D, "etat.json"), {})
    try:
        etat(D, statut="montage", etape="Je remonte la version suivante…")
        monte(D)
    except Exception as x:
        etat(D, statut="erreur", etape="", erreur=str(x)[:600])
        log_erreur(f"SuperMonteur {e.get('id')} : version {e.get('version', 0) + 1} bloquée : {str(x)[:200]}")
        raise


def log_erreur(t):
    reglages_apps.erreur(t)


if __name__ == "__main__":
    action, D = sys.argv[1], os.path.abspath(sys.argv[2])
    {"regarder": regarder, "monter": monter, "remonter": remonter}[action](D)
