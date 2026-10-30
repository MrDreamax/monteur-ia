"""SuperVeille : ce que le serveur (serveur.py) et Claude (sv.py) partagent. Fichiers, réglages, anti-doublon, Brain."""
import contextlib
import copy
import fcntl
import glob
import html
import json
import os
import re
import time
import unicodedata
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
VEILLES = os.path.join(ICI, "veilles")
TOURNAGE = os.path.join(ICI, "tournage.json")    # code -> {statut: a_tourner | tourne, ...} toutes veilles confondues
JOUR = os.path.join(ICI, "tournage-jour.json")  # 29/10 : Tournage du jour, format n° -> [idées : un script ou une phrase]
REGLAGES_APP = os.path.join(ICI, "reglages.json")  # derniers choix par personne (1 clic au prochain lancement)
ENREG = os.path.join(ICI, "enregistres.json")  # {comptes: {id: {lu, items}}, retires: [codes]} : les enregistrés Instagram de l’utilisateur
ENREG_MINI = os.path.join(ICI, "enregistres")  # leurs miniatures (les liens Instagram expirent)
BRAIN = os.path.join(ICI, "mes-notes")  # copies des veilles (anti-doublon + scripts) : restent sur ce Mac
for _d in ("04-Audits", "06-Contenu", "07-Clients"):
    os.makedirs(os.path.join(BRAIN, _d), exist_ok=True)
REGLAGES_BRAIN = os.path.join(BRAIN, "07-Clients", "veille-reglages.md")
LIVRABLES = os.path.join(BRAIN, "livrables")
YTDLP = os.path.expanduser("~/.local/bin/yt-dlp")

MARCHES = ["en", "es", "fr"]  # ordre fixe : anglophone, espagnol, français
NOMS_MARCHES = {"en": "anglophone", "es": "espagnol", "fr": "français"}
PERIODES = [15, 45, 90]
LIKES = [10000, 50000, 100000]  # jamais moins de 10 000 (l’utilisateur)
REPARTITION = {3: [5, 3, 2], 2: [6, 4], 1: [10]}
STARS = ["danmartell", "codiesanchez", "hormozi", "garyvee", "grantcardone", "leilahormozi", "alexhormozi",
         "patrickbetdavid", "tonyrobbins", "mrbeast", "imangadzhi", "iman_gadzhi", "russellbrunson"]
UA = "facebookexternalhit/1.1"  # Instagram ne sert og:image qu'aux robots de partage


def lire(p, defaut=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return copy.deepcopy(defaut)


def ecrire(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp%d" % os.getpid()
    json.dump(data, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


@contextlib.contextmanager
def verrou(p):
    """Serveur et Claude écrivent le même fichier : un seul à la fois (sinon une mise à jour en écrase une autre)."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def chemin(vid, *a):
    return os.path.join(VEILLES, vid, *a)


def veille(vid):
    return lire(chemin(vid, "veille.json"), {})


def maj_veille(vid, fn=None, **champs):
    """Lit, modifie (fn(v) et/ou champs), réécrit, sous verrou. Renvoie la veille à jour."""
    p = chemin(vid, "veille.json")
    with verrou(p):
        v = lire(p, {})
        if fn:
            fn(v)
        v.update(champs)
        v["maj"] = time.time()
        ecrire(p, v)
    return v


def maj_reel(vid, code, **champs):
    def f(v):
        for r in v.get("reels", []):
            if r["code"] == code:
                r.update(champs)
    return maj_veille(vid, f)


def toutes_veilles():
    if not os.path.isdir(VEILLES):
        return []
    return sorted([d for d in os.listdir(VEILLES) if os.path.isfile(chemin(d, "veille.json"))], reverse=True)


def norm(s):
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower().strip()


# ---------------------------------------------------------------- réglages par personne

def personnes():
    """Lignes du tableau Brain 07-Clients/veille-reglages.md : Personne | fichier | Cible | Marchés | Likes min | Réglé le."""
    try:
        lignes = open(REGLAGES_BRAIN, encoding="utf-8").read().splitlines()
    except OSError:
        return []
    out, tete = [], None
    for l in lignes:
        if not l.startswith("|"):
            tete = None if out else tete
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if tete is None:
            tete = [norm(c) for c in cells]
            continue
        if set(cells[0]) <= set("-: "):
            continue
        d = dict(zip(tete, cells))
        marches = [m for m, nom in NOMS_MARCHES.items() if norm(nom) in norm(d.get("marches (dans l'ordre)", d.get("marches", "")))]
        likes = int(re.sub(r"\D", "", d.get("likes min", "")) or 10000)
        nom = d.get("personne", "")
        out.append({"fichier": d.get("fichier", ""), "personne": nom, "court": nom.split("(")[0].strip(),
                    "cible": d.get("cible", ""), "marches": marches or MARCHES[:], "likes_min": max(likes, 10000)})
    return [p for p in out if p["fichier"]]


def reglages(fichier):
    """Réglages pour l'écran : ceux du Brain, remplacés par les derniers choix faits dans l'appli."""
    p = next((x for x in personnes() if x["fichier"] == fichier), None)
    if not p:
        return None
    r = {"marches": p["marches"], "periode": 45, "likes_min": p["likes_min"]}
    r.update({k: v for k, v in lire(REGLAGES_APP, {}).get(fichier, {}).items() if k in r})
    return dict(p, **r)


def garder_reglages(fichier, marches, periode, likes_min):
    with verrou(REGLAGES_APP):
        tout = lire(REGLAGES_APP, {})
        tout[fichier] = {"marches": marches, "periode": periode, "likes_min": likes_min, "quand": time.strftime("%Y-%m-%d %H:%M")}
        ecrire(REGLAGES_APP, tout)


# ---------------------------------------------------------------- anti-doublon

def deja_livres(fichier):
    """Codes et créateurs déjà livrés à cette personne : copies Brain, anciennes pages, et veilles de l'appli."""
    codes, createurs = set(), set()
    fichiers = glob.glob(os.path.join(BRAIN, "04-Audits", f"*veille-{fichier}*.md"))
    fichiers += glob.glob(os.path.join(LIVRABLES, f"*veille-{fichier}*", "*.html"))
    fichiers += glob.glob(os.path.join(LIVRABLES, f"*veille-{fichier}*", "*.md"))
    for f in fichiers:
        t = open(f, encoding="utf-8", errors="ignore").read()
        codes.update(re.findall(r"instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)", t))
        createurs.update(m.lower() for m in re.findall(r"\|\s*@([A-Za-z0-9_.]+)\s*\|", t))
    for vid in toutes_veilles():
        v = veille(vid)
        if v.get("pour") == fichier:
            for r in v.get("reels", []):
                codes.add(r["code"])
                createurs.add(r["createur"].lower())
    return sorted(codes), sorted(createurs)


# ---------------------------------------------------------------- couverture

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def url_couverture(code):
    """Adresse de l'image de couverture (og:image), 0 crédit. None si Instagram ne répond pas."""
    for essai in range(2):
        for kind in ("reel", "p"):
            try:
                page = _get(f"https://www.instagram.com/{kind}/{code}/").decode("utf-8", "ignore")
                m = re.search(r'property="og:image" content="([^"]+)"', page)
                if m:
                    return html.unescape(m.group(1))
            except Exception:
                pass
        time.sleep(1.5)
    return None


def telecharger_couverture(url, dest):
    try:
        img = _get(url)
        if img[:3] == b"\xff\xd8\xff":
            open(dest, "wb").write(img)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------- copie Brain (anti-doublon + Scripteur)

def court(n):
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} M".replace(".", ",").replace(",0 M", " M")
    if n >= 1_000:
        return f"{round(n / 1_000)} k"
    return str(n)


def milliers(n):
    return f"{int(n or 0):,}".replace(",", " ")


def ecrire_brain(vid):
    """Copie .md de la veille dans 04-Audits (tableau lu par l'anti-doublon et par miniatures.py) + 1 ligne dans log.md."""
    v = veille(vid)
    if v.get("source") == "transposes":
        return ecrire_brain_transposes(v)
    v["reels"] = [dict(r, n=i) for i, r in enumerate((r for r in v.get("reels", []) if r["statut"] != "ecarte"), 1)]
    jour = time.strftime("%Y-%m-%d", time.localtime(v.get("debut", time.time())))
    enreg = v.get("source") == "enregistres"
    base = os.path.join(BRAIN, "04-Audits", f"{jour}-veille-{v['pour']}" + ("-enregistres" if enreg else ""))
    p, i = base + ".md", 2
    while os.path.exists(p) and f"superveille: {vid}" not in open(p, encoding="utf-8").read():
        p, i = f"{base}-{i}.md", i + 1
    marches = " > ".join(m.upper() for m in v["marches"])
    if enreg:  # l’utilisateur a fait la veille lui-même (vidéos enregistrées sur Instagram) : pas de filtre
        marches = "enregistrés Insta"
        l = ["---", f'description: "SuperVeille {jour[8:]}/{jour[5:7]} : {len(v["reels"])} reels enregistrés sur Instagram par '
             f'{v["personne"]}, script mot pour mot traduit en français."', "type: audit", "statut: actif",
             "sujets: [contenu, veille]", f"date: {jour}", f"superveille: {vid}", "---",
             f"# SuperVeille enregistrés {v['personne']} ({jour[8:]}/{jour[5:7]}/{jour[:4]})", "",
             f"- {len(v['reels'])} reels choisis par {v['personne']} dans ses enregistrés Instagram.",
             "- Scripts mot pour mot (original | français) : appli SuperVeille, http://localhost:8811.", "",
             "| # | Langue | Créateur | Likes | Vues | Date | Lien | Hook en français | Format |",
             "|---|---|---|---|---|---|---|---|---|"]
    else:
        l = ["---", f'description: "SuperVeille {jour[8:]}/{jour[5:7]} pour {v["personne"]} : {len(v["reels"])} reels à reprendre, '
             f'{marches}, {v["periode"]} j, {court(v["likes_min"])} likes min."', "type: audit", "statut: actif",
             "sujets: [contenu, veille]", f"date: {jour}", f"superveille: {vid}", "---",
             f"# SuperVeille {v['personne']} ({jour[8:]}/{jour[5:7]}/{jour[:4]})", "",
             f"- Filtre : {marches} · {v['periode']} derniers jours · {milliers(v['likes_min'])} likes minimum"
             + (f" · sujet « {v['sujet']} »" if v.get("sujet") else "") + ".",
             f"- {len(v['reels'])} reels passent" + (f" ; il en manque {10 - len(v['reels'])} : {v['manque']}" if v.get("manque") else "") + ".",
             "- Scripts mot pour mot (original | français) : appli SuperVeille, http://localhost:8811.", "",
         "| # | Marché | Créateur | Likes | Vues | Date | Lien | Hook en français | Format |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in v["reels"]:
        hook = (r.get("hook") or "").replace("|", "/")
        l.append(f"| {r['n']} | {r['marche'].upper()} | @{r['createur']} | {milliers(r['likes'])} | {milliers(r.get('vues'))} "
                 f"| {r.get('date', '')[8:10]}/{r.get('date', '')[5:7]} | [lien]({r['lien']}) | « {hook} » | {r.get('format', '')} |")
    l += ["", "## Scripts", ""]
    for r in v["reels"]:
        l.append(f"### {r['n']}. @{r['createur']} ({r['marche'].upper()}) · {r['lien']}")
        for ph in r.get("phrases") or []:
            l.append(f"- {ph['o']}" + (f" → {ph['f']}" if ph.get("f") and ph["f"] != ph["o"] else ""))
        l.append("")
    nouveau = not os.path.exists(p)
    open(p, "w", encoding="utf-8").write("\n".join(l))
    if not nouveau:  # veille complétée : la copie est réécrite, la ligne de log existe déjà
        return p
    log = os.path.join(BRAIN, "log.md")
    fin = open(log, "rb").read()[-1:] if os.path.exists(log) else b"\n"
    with open(log, "a", encoding="utf-8") as f:
        f.write(("" if fin == b"\n" else "\n") + f"- {time.strftime('%Y-%m-%d')} · SuperVeille {v['personne']} : {len(v['reels'])} reels à reprendre "
                f"({marches}" + ("" if enreg else f", {v['periode']} j") + f") → 04-Audits/{os.path.basename(p)}\n")
    return p


def ecrire_brain_transposes(v):
    """Scripts transposés du jour (lien collé, format repris dans la niche de l’utilisateur) : 06-Contenu, lus par le Scripteur.
    Réécrite à chaque lien ; 1 ligne dans log.md la 1re fois."""
    reels = [r for r in v.get("reels", []) if r["statut"] == "pret" and r.get("script")]
    jour = time.strftime("%Y-%m-%d", time.localtime(v.get("debut", time.time())))
    p = os.path.join(BRAIN, "06-Contenu", f"{jour}-scripts-transposes.md")
    l = ["---", f'description: "Scripts transposés le {jour[8:]}/{jour[5:7]} dans SuperVeille : format d\'un reel repris, '
         f'script de l’utilisateur dans sa niche ({len(reels)})."', "type: scripts", "statut: actif", "sujets: [contenu, scripts]",
         f"date: {jour}", f"superveille: {v['id']}", "---", f"# Scripts transposés ({jour[8:]}/{jour[5:7]}/{jour[:4]})", "",
         "Format repris d'un reel collé dans SuperVeille (http://localhost:8811), réécrit pour la cible de l’utilisateur.", ""]
    for r in reels:
        l += [f"## {r.get('format_repris', '')} · @{r['createur']}", "", f"**Vidéo inspiration :** {r['lien']}", "",
              "**Plan :** " + " → ".join(r.get("plan") or []), ""]
        if r.get("sujet"):
            l += [f"**Sujet demandé :** {r['sujet']}", ""]
        l += [f"**Hook :** {r['hook']}", "", "**Script :**", r["script"], ""]
    nouveau = not os.path.exists(p)
    open(p, "w", encoding="utf-8").write("\n".join(l))
    if nouveau:
        log = os.path.join(BRAIN, "log.md")
        fin = open(log, "rb").read()[-1:] if os.path.exists(log) else b"\n"
        with open(log, "a", encoding="utf-8") as f:
            f.write(("" if fin == b"\n" else "\n") + f"- {time.strftime('%Y-%m-%d')} · SuperVeille Transposer : scripts au format "
                    f"d'un reel collé, dans la niche de l’utilisateur → 06-Contenu/{os.path.basename(p)}\n")
    return p
