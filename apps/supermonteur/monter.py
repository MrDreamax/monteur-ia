"""SuperMonteur : la partie machine derrière l'écran (28/10/2026). Ne réécrit PAS le moteur : il enchaîne les scripts du
skill supermonteur (transcription, dérush, plan.json, monte.sh) et tient à jour etat.json, que la page lit.

    python3 monter.py regarder <dossier du reel>    écran 0 : transcription + devine_format -> style conseillé
    python3 monter.py monter   <dossier du reel>    « Monter le reel » : dérush + plan.json + monte.sh -> versions/v1.mp4
    python3 monter.py suite    <dossier du reel>    après le Derush Lab, si le monter.py qui attendait est mort (29/10)
    python3 monter.py remonter <dossier du reel>    après les retours corrigés par Claude dans plan.json -> version N+1

Un seul montage à la fois sur le Mac (8 Go) : on attend qu'aucun autre rendu HyperFrames ne tourne.
"""
import datetime, fcntl, json, os, re, shutil, subprocess, sys, threading, time, unicodedata

APP = os.path.dirname(os.path.abspath(__file__))
SK = os.path.expanduser("~/.claude/skills/supermonteur")
S = os.path.join(SK, "scripts")
ENV = dict(os.environ, PATH=os.path.expanduser("~/.local/bin") + ":" + os.path.expanduser("~/.local/node/bin") + ":" + os.environ.get("PATH", ""))
sys.path.insert(0, APP)
import da as DA
import reglages_apps

STYLES = ["Dynamique", "Minimaliste", "Comparatif", "Interview", "Inspiration"]
# recette de devine_format.py -> un des 4 styles de base (devine-format.md, tableau 4 ; 29/10 : « Autre » devient Inspiration,
# qu'on ne conseille pas : il faut un reel à reprendre, donc voix off / green screen / B-roll texte -> Dynamique)
RECETTE = {"face-cam": "Dynamique", "raw": "Minimaliste", "montage-viral": "Comparatif", "a-plusieurs": "Interview",
           "podcast": "Interview", "voix-off": "Dynamique", "green-screen": "Dynamique", "broll-texte": "Dynamique"}


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
        if r.returncode == 3 and fin and fin[-1].startswith("ElevenLabs"):   # 29/10 : montage bloqué sans ElevenLabs
            raise RuntimeError(fin[-1])
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
def a_du_son(p):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p],
                               capture_output=True, text=True).stdout.strip())


def regarder(D):
    """29/10 : une panne ici laissait l'écran sur « Je regarde ta vidéo… » pour toujours : elle s'affiche maintenant."""
    try:
        _regarder(D)
    except Exception as x:
        etat(D, statut="erreur", etape="", erreur=str(x)[:600])
        log_erreur(f"SuperMonteur {os.path.basename(D)} : regarder bloqué : {str(x)[:200]}")
        raise


def _regarder(D):
    e = lire(os.path.join(D, "etat.json"), {})
    rush = e["rush"]
    etat(D, statut="regarde", etape="Je regarde ta vidéo…")
    if not a_du_son(rush):   # 29/10 : B-roll muet = B-roll + texte (la transcription plantait et l'écran restait bloqué)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{duree(rush) / 3:.2f}", "-i", rush, "-frames:v", "1",
                        "-vf", "scale=540:-2", os.path.join(D, "apercu.jpg")], env=ENV)
        return etat(D, statut="choix", etape="", conseil="Inspiration", muet=True, duree_rush=round(duree(rush), 1),
                    pourquoi="vidéo sans voix : B-roll + texte, colle le reel à reprendre")
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
    # 28/10 (l’utilisateur, CAM20047 : « enlève les "euh" quand tu dérush ») : chaque « euh / heu / hum » seul saute
    gardes = {i for a, b in drop for i in range(a, b + 1)}
    drop += [[i, i] for i, w in enumerate(words) if i not in gardes and norm(w["text"]) in {"euh", "heu", "hum", "euhm", "bah"}]
    return sorted(drop)


def suspect(words, i):
    """Mot mal calé par la transcription du rush entier : il dure plus d'1 s, ou une pause d'1 s le suit en pleine phrase."""
    w, t = words[i], words[i]["text"].strip()
    if not re.search(r"\w", t): return False
    pause = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 0
    return w["end"] - w["start"] > 1.0 or (pause > 1.0 and not re.search(r"[.!?…,;:]\s*$", t))


def recaler(D, rush, words):
    """29/10 (CAM20062 : « la » de 1,85 s cachait une 2e prise entière, « portes » fantôme après une pause d'1,5 s) : chaque
    passage suspect est retranscrit seul (3 mots de chaque côté, fenêtres fusionnées). Sur 4 s de son, les mots tombent juste."""
    from concurrent.futures import ThreadPoolExecutor
    F = []
    def blanc(k):   # silence entre words[k-1] et words[k]
        return 9 if k <= 0 or k >= len(words) else words[k]["start"] - words[k - 1]["end"]
    for i in (k for k in range(len(words)) if suspect(words, k)):
        a, b = max(0, i - 3), min(len(words) - 1, i + 3)
        for _ in range(6):   # bords posés dans un vrai blanc, jamais au milieu d'un mot voisin (« parce Parce »)
            if blanc(a) >= .15: break
            a -= 1
        for _ in range(6):
            if blanc(b + 1) >= .15: break
            b += 1
        a, b = max(0, a), min(len(words) - 1, b)
        if F and a <= F[-1][1] + 1: F[-1][1] = max(F[-1][1], b)
        else: F.append([a, b])
    if not F: return words, 0

    def un(f):
        a, b = f
        t0 = max(0, (words[a - 1]["end"] + words[a]["start"]) / 2 if a else words[a]["start"] - .05)
        t1 = (words[b]["end"] + words[b + 1]["start"]) / 2 if b + 1 < len(words) else words[b]["end"] + .3
        wav = os.path.join(D, f"_recale_{a}.wav")
        js = wav[:-4] + ".json"
        try:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", rush, "-vn", "-ac", "1",
                            "-ar", "16000", wav], env=ENV, check=True)
            subprocess.run(["python3", os.path.join(S, "transcribe.py"), wav, js], env=ENV, capture_output=True, timeout=180)
            new = [{"text": x["text"], "start": round(x["start"] + t0, 3), "end": round(x["end"] + t0, 3)}
                   for x in (lire(js, {}) or {}).get("words", [])]
        except Exception:
            new = []
        finally:
            for p in (wav, js):
                if os.path.exists(p): os.remove(p)
        if len(new) < .3 * (b - a + 1): return None   # retranscription ratée = on garde l'ancienne
        # la fin de phrase compte pour le dérush (il ne coupe qu'après . , ! ?) : une phrase qui repart en majuscule après un
        # blanc prend un point, et la ponctuation du dernier mot d'avant est gardée
        for k in range(len(new) - 1):
            if not re.search(r"[.!?…,;:]$", new[k]["text"]) and new[k + 1]["start"] - new[k]["end"] > .3 and new[k + 1]["text"][:1].isupper():
                new[k]["text"] += "."
        p = re.search(r"[.!?…,;:]+$", words[b]["text"].strip())
        if p and not re.search(r"[.!?…,;:]$", new[-1]["text"]): new[-1]["text"] += p.group()
        return new

    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(un, F))
    out, k, n = [], 0, 0
    for (a, b), new in zip(F, res):
        out += words[k:a] + (new or words[a:b + 1])
        k, n = b + 1, n + bool(new)
    return out + words[k:], n


def fragments(words):
    """Morceaux de parole séparés par plus de 0,5 s de silence (une prise, ou un bout de prise)."""
    F, a = [], 0
    for i in range(1, len(words) + 1):
        if i == len(words) or words[i]["start"] - words[i - 1]["end"] > .5:
            F.append((a, i - 1))
            a = i
    return F


def reprises_restantes(words, gardes):
    """29/10 (CAM20065, vu en réécoutant clip.mp4) : Claude gardait encore une prise abandonnée juste avant sa reprise.
    A : « Mais le 2e coach lui aussi il a eu un prospect. » puis « Mais le 2e coach lui aussi il a eu un prospect en appel… »
        = le 1er morceau est le début du suivant -> tout le 1er saute.
    B : « …avec ses enfants et que même les médecins. » puis « que même les médecins lui disent… »
        = la fin du 1er (4 mots ou plus) = le début du suivant -> cette fin saute.
    Mots comparés sans ponctuation ni majuscules. -> indices de mots à retirer."""
    def mots(a, b): return [norm(words[i]["text"]) for i in range(a, b + 1)]
    out = set()
    for (a, b), (c, d) in zip(gardes, gardes[1:]):
        p, q = mots(a, b), mots(c, d)
        if 3 <= len(p) < len(q) and q[:len(p)] == p:
            out |= set(range(a, b + 1))
            continue
        for k in range(min(len(p) - 1, len(q)), 3, -1):   # 4 mots mini : « …vers le premier coach. Le premier coach le prend » est voulu
            if p[-k:] == q[:k]:
                out |= set(range(b - k + 1, b + 1))
                break
    return out


def prises_par_claude(D, words):
    """29/10 (CAM20062 : 13 min, ~40 reprises, drop_auto gardait des bouts ratés -> Gardien bloquant 2 fois) : Claude (Sonnet)
    lit les morceaux numérotés et garde la dernière prise réussie de chaque idée, comme au dérush à la main. None = repli drop_auto."""
    F = fragments(words)
    if len(F) < 3: return None
    liste = "\n".join(f"{n}. {texte(words, a, b)}" for n, (a, b) in enumerate(F, 1))
    prompt = ("l’utilisateur a filmé un reel face caméra en refaisant ses phrases plusieurs fois. Voici sa transcription, coupée en morceaux "
              f"numérotés, dans l'ordre du tournage :\n{liste}\n\nChoisis les morceaux à GARDER pour la vidéo finale :\n"
              "- pour chaque idée, garde la DERNIÈRE prise complète et fluide, jamais une prise abandonnée (qui finit par « ... », "
              "coupée, bafouillée ou reprise juste après) ;\n"
              "- tu peux enchaîner 2 ou 3 morceaux voisins quand une phrase réussie est coupée par une pause "
              "(ex. « c'est là qu » + « on lui annonce le prix… ») ;\n"
              "- garde toutes les idées de la vidéo, dans l'ordre, et chaque phrase une seule fois ;\n"
              "- après l'appel à l'action final (abonne-toi…), enlève « merci » et ce qui suit.\n"
              "Réponds SEULEMENT par les numéros gardés, dans l'ordre, séparés par des virgules. Rien d'autre.")
    try:
        sys.path.insert(0, os.path.dirname(APP))
        import ouvrier_claude
        ok, sortie = ouvrier_claude.lancer(prompt, D, ["Read"], delai=300, modele="sonnet")
    except Exception:
        return None
    lignes = [l for l in (sortie or "").strip().splitlines() if re.fullmatch(r"[\d,\s]+", l.strip())] if ok else []
    nums = sorted({int(x) for x in re.findall(r"\d+", lignes[-1])} & set(range(1, len(F) + 1))) if lignes else []
    if not nums: return None
    garde = {i for n in nums for i in range(F[n - 1][0], F[n - 1][1] + 1)}
    garde -= reprises_restantes(words, [F[n - 1] for n in nums])
    drop, a = [], None
    for i in range(len(words) + 1):
        if i < len(words) and i not in garde:
            a = i if a is None else a
        elif a is not None:
            drop.append([a, i - 1])
            a = None
    # les « euh » seuls sautent aussi dans les prises gardées (28/10)
    drop += [[i, i] for i in sorted(garde) if norm(words[i]["text"]) in {"euh", "heu", "hum", "euhm", "bah"}]
    return sorted(drop)


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
    # 29/10 : plus de découpe à la colonne 39 (un nom de reel long y collait « 0047-xxx) » devant le morceau -> mix.py planté)
    fics = sorted(os.listdir(dossier), key=len, reverse=True) if dossier and os.path.isdir(dossier) else []
    nom = lambda l: next((f for f in fics if l.endswith(" " + f)), None)
    neuves = [nom(l) for l in L if l.startswith("jamais utilisée") and nom(l)]
    vieilles = [nom(l) for l in L if l.startswith("utilisée le") and nom(l)]
    pool = (neuves or vieilles)[:6]
    if not pool or not dossier: raise RuntimeError("pas de musique : mets des musiques dans ~/Documents/Montage/MUSIQUE (music_reels du config.json du skill supermonteur)")
    src = os.path.join(dossier, pool[sum(map(ord, rid)) % len(pool)])
    att = subprocess.run(["python3", os.path.join(S, "attaque.py"), src, "0", "60"], capture_output=True, text=True, env=ENV).stdout
    m = re.search(r"^\s*([\d.]+) s", att, re.M)
    return {"src": src, "from": float(m.group(1)) if m else 0.0,
            "emotion": f"choisie par SuperMonteur dans REELS INSTA (jamais utilisée d'abord), part sur son temps fort (attaque.py)"}


# ------------------------------------------------------------------------------------------------------- le montage
def attendre_le_mac(D, dire=None):
    """Mac 8 Go : un rendu à la fois. Un autre chat rend déjà ? On attend (le dire à l'écran)."""
    dire = dire or (lambda t: etat(D, etape=t))
    verrou = open(os.path.join(APP, ".rendu.lock"), "w")
    while True:
        autres = subprocess.run(["pgrep", "-f", "hyperframes.*render"], capture_output=True, text=True).stdout.split()
        if not autres:
            try:
                fcntl.flock(verrou, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return verrou
            except BlockingIOError:
                pass
        dire("J'attends que l'autre rendu du Mac finisse (un seul à la fois)…")
        time.sleep(10)


def monte_sh(D, ici, dire):
    """monte.sh dans le dossier ici : un rendu à la fois sur le Mac.
    29/10 (l’utilisateur : « je demande juste un sous-titre et un titre ») : titre + sous-titres seuls = express.py d'abord (~1 min au
    lieu de 6, sans rendu Chrome) ; il sort en code 2 dès que le plan a autre chose (B-roll, mots géants…) -> monte.sh."""
    verrou = attendre_le_mac(D, dire)
    try:
        dire("Je monte en express : titre + sous-titres (~1 min)…")
        r = subprocess.run(["python3", os.path.join(S, "express.py"), "."], cwd=ici, env=ENV, capture_output=True, text=True)
        if r.returncode == 2:
            dire("Je monte : composition, Gardien, rendu, son (~4 min)…")
            r = subprocess.run(["bash", os.path.join(S, "monte.sh"), "."], cwd=ici, env=ENV, capture_output=True, text=True)
        open(os.path.join(ici, "monte.log"), "w").write(r.stdout + r.stderr)
        if r.returncode or not os.path.exists(os.path.join(ici, "final.mp4")):
            stop = [l for l in (r.stdout + r.stderr).splitlines() if "⛔" in l or "❌" in l]
            raise RuntimeError(" / ".join(stop[-4:]) or "monte.sh a échoué (voir monte.log)")
    finally:
        verrou.close()


def monte(D):
    """monte.sh = B-rolls, composition, Gardien AVANT, rendu, mix, Gardien final, planche. Puis versions/vN.mp4."""
    e = lire(os.path.join(D, "etat.json"), {})
    # reel monté dans un chat (importer_montages) : pas de plan.json, son propre monte.py = sa recette, qu'on relance
    recette = "plan.json" if os.path.exists(os.path.join(D, "plan.json")) else "monte.py"
    # 29/10 (test-images : face cam + b-rolls choisis à l'écran « Tes images » partait dans brolltexte.py) : B-roll + texte = pas de cam
    p = lire(os.path.join(D, "plan.json"), {}) or {}
    if recette == "plan.json" and (p.get("famille") == "broll-texte" or ("brolls" in p and not p.get("cam"))):
        verrou = attendre_le_mac(D, lambda t: etat(D, etape=t))
        try:
            etat(D, etape="Je monte le B-roll + texte (~30 s)…")
            run(D, ["python3", os.path.join(S, "brolltexte.py"), "plan.json"], "monte.log")
        finally:
            verrou.close()
        zones = "brolltexte : zone sûre contrôlée"
    elif recette == "plan.json":
        monte_sh(D, D, lambda t: etat(D, etape=t))
        zones = subprocess.run(["node", os.path.join(S, "zones.mjs"), "."], cwd=D, env=ENV, capture_output=True, text=True)
        zones = (zones.stdout.strip().splitlines() or ["?"])[-1]
    else:
        verrou = attendre_le_mac(D, lambda t: etat(D, etape=t))
        try:
            etat(D, etape="Je monte (recette du chat, monte.py)…")
            os.replace(os.path.join(D, "final.mp4"), os.path.join(D, "final.mp4.avant"))   # lien dur vers vN : ne pas l'écraser
            try:
                run(D, ["python3", "monte.py"], "monte.log")
            except Exception:
                os.replace(os.path.join(D, "final.mp4.avant"), os.path.join(D, "final.mp4"))
                raise
            os.remove(os.path.join(D, "final.mp4.avant"))
        finally:
            verrou.close()
        zones = "?"
    n = len(e.get("versions", [])) + 1
    os.makedirs(os.path.join(D, "versions"), exist_ok=True)
    shutil.copy2(os.path.join(D, "final.mp4"), os.path.join(D, "versions", f"v{n}.mp4"))
    shutil.copy2(os.path.join(D, recette), os.path.join(D, "versions", f"v{n}.{recette}"))
    v = e.get("versions", []) + [{"n": n, "fichier": f"versions/v{n}.mp4", "date": datetime.datetime.now().isoformat(timespec="seconds"),
                                   "duree": round(duree(os.path.join(D, "final.mp4")), 2), "zones": zones}]
    etat(D, statut="retours", etape="", version=n, versions=v, erreur=None)


DERUSH_LAB = False


def attendre_derush(D, rush, vf, e):
    """29/10 (l’utilisateur : « pourquoi tu passes pas par Derush Lab avant de monter la version finale ? ») : après le 1er dérush de
    Claude, l'écran montre le DERUSH LAB (skill outils/cockpit, cockpit.py --lab, lancé par serveur.py) ; l’utilisateur retouche au
    pixel, « ✓ Valider le dérush » (clip.mp4 recoupé + Gardien du dérush), puis « Monter le reel » (serveur : derush_ok).
    Pour tous les reels, clients compris. On attend ici (le fil de la référence continue). False = projet supprimé."""
    # un nouveau 1er dérush (reel remonté dans un autre style) : le Lab repart de lui, pas des plages d'avant
    shutil.rmtree(os.path.join(D, "_cockpit"), ignore_errors=True)
    for f in ("cockpit-etat.json", "plages.json", "gardien-derush.json", "bords.json"):
        if os.path.exists(os.path.join(D, f)): os.remove(os.path.join(D, f))
    shutil.copy2(os.path.join(D, "words.rush.json"), os.path.join(D, "words_rush.json"))   # nom lu par cockpit.py
    cadre = lire(os.path.join(D, "cadre.json"), {}) or {}
    if cadre.get("vf") != vf:   # Minimaliste : pas de cadre.py, le Lab doit recouper avec le même vf que le 1er dérush
        ecrire(os.path.join(D, "cadre.json"), dict(cadre, vf=vf, source=rush))
    ecrire(os.path.join(D, "cockpit.json"), {"rush": rush, "titre": e.get("nom", e["id"]), "hooks": [{"id": "lab", "texte": ""}]})
    etat(D, statut="derush", etape="", derush_ok=False, erreur=None, pid_derush=os.getpid())
    while True:
        time.sleep(2)
        x = lire(os.path.join(D, "etat.json"), {}) or {}
        if x.get("cache"): return False
        if x.get("derush_ok"): return True


def monter(D):
    e = lire(os.path.join(D, "etat.json"), {})
    rid, rush, style, cases = e["id"], e["rush"], e.get("style", "Dynamique"), e.get("cases", {})
    if e.get("muet") or not a_du_son(rush):
        return monter_broll(D, e)
    ref = {}
    if e.get("reference"):   # 29/10 : téléchargement + planche + mesures pendant la transcription et le dérush (avant : après la v1)
        ref["fil"] = threading.Thread(target=lambda: ref.update(erreur=preparer_ref(D, e)), daemon=True)
        ref["fil"].start()
    try:
        if not os.path.exists(os.path.join(D, "words.rush.json")):
            etat(D, etape="Je transcris ta vidéo…")
            run(D, ["python3", os.path.join(S, "transcribe.py"), rush, "words.rush.json"], "transcribe.log")
        W = lire(os.path.join(D, "words.rush.json"))["words"]
        if not os.path.exists(os.path.join(D, "words.rush.brut.json")):   # une seule fois : passages mal calés retranscrits seuls
            etat(D, etape="Je vérifie chaque mot de ta vidéo…")
            shutil.copy2(os.path.join(D, "words.rush.json"), os.path.join(D, "words.rush.brut.json"))
            W, n = recaler(D, rush, W)
            if n: ecrire(os.path.join(D, "words.rush.json"), dict(lire(os.path.join(D, "words.rush.json")), words=W))
        etat(D, etape="Je dérushe : dernière prise gardée, blancs coupés…")
        ecrire(os.path.join(D, "drop.json"), prises_par_claude(D, W) or drop_auto(W))
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
        # 29/10 21h32 (l’utilisateur : « enlève le Derush Lab de SuperMonteur et reviens comme c'était avant, c'était ça le problème ») :
        # plus d'attente sous le Lab, le dérush de Claude part direct au montage. Pour le remettre : DERUSH_LAB = True.
        if DERUSH_LAB and not attendre_derush(D, rush, vf, e):
            return
    except Exception as x:
        etat(D, statut="erreur", etape="", erreur=str(x)[:600])
        log_erreur(f"SuperMonteur {rid} : montage v1 bloqué : {str(x)[:200]}")
        raise
    suite(D, ref)


def suite(D, ref=None):
    """Après « Monter le reel » sous le Derush Lab : plan.json, montage v1 (ou la référence), rush renommé.
    Lancé seul (`monter.py suite`) par le serveur si le monter.py qui attendait n'existe plus (Mac redémarré)."""
    e = lire(os.path.join(D, "etat.json"), {})
    rid, style, cases = e["id"], e.get("style", "Dynamique"), e.get("cases", {})
    try:
        etat(D, statut="montage", etape="J'écris le plan : titre, sous-titres, musique…")
        plan = plan_auto(D, rid, style, cases, lire(os.path.join(D, "words.json"))["words"])
        ecrire(os.path.join(D, "plan.json"), plan)
        if ref is None:
            ref = {"erreur": preparer_ref(D, e)} if e.get("reference") else {}
        if ref:
            etat(D, etape="Je finis de regarder le montage à reprendre…")
            if ref.get("fil"): ref["fil"].join()
            if ref.get("erreur"):
                etat(D, reference=dict(e["reference"], erreur="Je n'ai pas pu lire la vidéo à reprendre (lien privé ou supprimé ?). "
                                                             "Ta v1 est montée dans ton style : dis-moi tes retours."))
        if not ref or ref.get("erreur"):
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
    if ref and not ref.get("erreur") and not demander_images(D):
        pousser_ref(D)   # Claude écrit le plan au style de la référence et monte la v1 : UN seul rendu (avant : v1 puis v2)


def images_choisies(D):
    try:
        import images
        return images.consigne(D)
    except Exception:
        return ""


def monter_broll(D, e):
    """29/10 : vidéo sans voix = B-roll + texte (styles/broll-texte.md, brolltexte.py). Pas de transcription ni de dérush :
    le plan entier, la musique, la DA ; Claude écrit le texte (repris de la référence, adapté à la cible) puis monte la v1."""
    rid, rush = e["id"], e["rush"]
    try:
        if not e.get("reference"):
            raise RuntimeError("vidéo sans voix : choisis Inspiration et colle le reel B-roll + texte à reprendre.")
        etat(D, etape="Je regarde le montage à reprendre…")
        err = preparer_ref(D, e)
        if err: raise RuntimeError("je n'ai pas pu lire la vidéo à reprendre (lien privé ou supprimé ?)")
        plan = {"famille": "broll-texte", "brolls": [{"src": rush, "from": 0, "dur": round(min(duree(rush), 12) - 0.05, 2)}],
                "style": "da", "music": musique_auto(D, rid),
                "_note": f"{datetime.date.today():%d/%m} SuperMonteur : B-roll + texte, Claude écrit \"text\" d'après ref/ (styles/broll-texte.md)"}
        dm = DA.pour_moteur()
        if dm:
            ecrire(os.path.join(D, "da-supermonteur.json"), dm)
            plan["da"] = os.path.join(D, "da-supermonteur.json")
        ecrire(os.path.join(D, "plan.json"), plan)
    except Exception as x:
        etat(D, statut="erreur", etape="", erreur=str(x)[:600])
        log_erreur(f"SuperMonteur {rid} : B-roll + texte bloqué : {str(x)[:200]}")
        raise
    t = ("Reprends ce B-roll + texte pour ma vidéo : même mise en page (ex. tableau titre + 2 colonnes, ou 2-3 lignes), "
                         "texte réécrit en français pour ma cible (styles/broll-texte.md, voix Brain 00-Moi/voix-contenu.md, faits vrais seulement). "
                         "Écris \"text\" dans plan.json (et \"brolls\" = les images choisies plus bas, une par plan, s'il y en a ; rien d'autre), "
                         "puis monter.py remonter. Seule la police change : celle de ma DA.")
    if not demander_images(D, t):
        pousser_ref(D, texte=t)


def preparer_ref(D, e):
    """29/10 : montage à reprendre (lien ou vidéo glissée à l'écran 0), pour CE reel seulement : la vidéo dans ref/, sa planche
    (1 image/s) et ses mesures (analyse_ref.py). Tourne en parallèle du dérush (n'écrit pas etat.json). Renvoie l'erreur ou None."""
    ref, R = e["reference"], os.path.join(D, "ref")
    os.makedirs(R, exist_ok=True)
    src = os.path.join(R, ref["fichier"] if ref.get("fichier") else "reference.mp4")
    try:
        if ref.get("lien") and not os.path.exists(src):
            run(D, [os.path.expanduser("~/.local/bin/yt-dlp"), "-q", "--no-warnings", "--no-playlist", "-f", "bv*+ba/b",
                    "--merge-output-format", "mp4", "-o", src, ref["lien"]], "ref.log")
        d = duree(src)
        n = min(48, max(1, int(d)))   # 1 image/s, 48 max : une planche que Claude lit d'un coup
        run(D, ["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"fps={n / d:.4f},scale=180:-2,tile=8x{-(-n // 8)}", "-frames:v", "1",
                os.path.join(R, "planche.jpg")], "ref-planche.log")
    except Exception as x:
        log_erreur(f"SuperMonteur {e['id']} : montage à reprendre illisible : {str(x)[:200]}")
        return str(x)[:300]
    try:
        run(D, ["python3", os.path.join(S, "analyse_ref.py"), src, R, "--lang", "auto"], "ref-analyse.log")
    except Exception as x:   # sans mesures, la planche suffit pour reprendre le montage
        log_erreur(f"SuperMonteur {e['id']} : analyse de la référence ratée : {str(x)[:200]}")
    return None


def demander_images(D, texte=None):
    """29/10 : écran « Tes images pour ce reel » (images.py) : 3 de ses b-rolls proposés par plan de la référence, l’utilisateur clique,
    puis « Monter avec ces images » (serveur.py) appelle pousser_ref. False = rien à choisir (ou panne) : on monte direct."""
    e = lire(os.path.join(D, "etat.json"), {})
    try:
        import images
        if images.choisir(D, e, lambda t: etat(D, etape=t)):
            etat(D, statut="images", etape="", images_texte=texte)   # texte du retour automatique, gardé pour le clic « Monter »
            return True
    except Exception as x:
        log_erreur(f"SuperMonteur {e.get('id')} : écran des images sauté : {str(x)[:200]}")
    return False


def pousser_ref(D, texte=None):
    """Le 1er retour automatique (à 0:00) que l'ouvrier de serveur.py donne à Claude : plan.json au montage de la référence,
    police de la DA gardée, puis `monter.py remonter` = la v1. Aucune version avant : rien à regarder dans final.mp4."""
    e = lire(os.path.join(D, "etat.json"), {})
    ref = e["reference"]
    quoi = ref.get("lien") or f"la vidéo {ref['fichier']}"
    Rt = lire(os.path.join(D, "retours.json"), []) or []
    Rt.append({"id": max([x["id"] for x in Rt] or [0]) + 1, "t": 0, "statut": "a_faire", "version": e.get("version", 1), "reponse": "",
               "auto": "reference", "date": datetime.datetime.now().isoformat(timespec="seconds"),
               "texte": (texte or f"Reprends le montage de {quoi} pour cette vidéo, FIDÈLE à son concept et son style : mise en page, couleurs, "
                        "rythme, zooms, sous-titres, cartons, motion, transitions, musique, bruitages. Seule la police change : celle de ma DA. "
                        "(Aucune version montée encore : pars de plan.json et de ref/, pas de final.mp4.)") + images_choisies(D)})
    ecrire(os.path.join(D, "retours.json"), Rt)
    dem = {"reel": e["id"], "dossier": D, "version": e.get("version"), "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "retours": [x for x in Rt if x["statut"] == "a_faire"],
           "a_faire": "Lire CLAUDE.md : reprendre le montage de ref/ (planche.jpg, *.analyse.json) dans plan.json, police de la DA gardée, "
                      "puis python3 monter.py remonter <dossier>, puis statut corrige + reponse dans retours.json"}
    ecrire(os.path.join(D, "demande.json"), dem)
    boite = [x for x in lire(os.path.join(APP, "a-corriger.json"), []) or [] if x.get("reel") != e["id"]] + [dem]
    ecrire(os.path.join(APP, "a-corriger.json"), boite)
    etat(D, statut="correction", etape="Claude copie le montage de ta référence et monte ton reel (~5 min)…")


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
    # signature finale (« … avec le cœur. [temps] Mr Dreamax ») : son temps naturel est gardé (SKILL, Gardien pause_signature)
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


def texte(words, a, b):
    return " ".join(words[k]["text"].strip() for k in range(a, b + 1)).strip()


def log_erreur(t):
    reglages_apps.erreur(t)


if __name__ == "__main__":
    action, D = sys.argv[1], os.path.abspath(sys.argv[2])
    {"regarder": regarder, "monter": monter, "remonter": remonter, "suite": suite}[action](D)
