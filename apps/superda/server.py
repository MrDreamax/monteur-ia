#!/usr/bin/env python3
"""SuperDA : petit serveur local qui sert l'appli et lit / écrit da.json.

Lancer : python3 server.py  (port 8781)
API :
  GET  /api/da          la DA (da.json)
  POST /api/da          enregistre la DA envoyée (normalisée, ancienne version gardée dans historique/)
  GET  /api/catalogue   les choix proposés (catalogue.json)
  POST /api/claude      {onglet, section, demande, da} -> claude -p modifie la DA, enregistrée
  POST /api/inspiration {source | fichier(base64) + nom, onglet, da} -> DA proposée (pas enregistrée)
"""
import base64
import copy
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ICI = os.path.dirname(os.path.abspath(__file__))
DA = os.path.join(ICI, "da.json")
CATALOGUE = os.path.join(ICI, "catalogue.json")
SCHEMA = os.path.join(ICI, "da-schema.json")
HISTO = os.path.join(ICI, "historique")
INSPI = os.path.join(ICI, "inspiration")
PORT = int(os.environ.get("SUPERDA_PORT", "8781"))


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def cat():
    return lire(CATALOGUE)


def par_id(liste, i):
    for x in liste:
        if x.get("id") == i:
            return x
    return None


def borne(v, lo, hi, defaut):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        return defaut
    return max(lo, min(hi, v))


def nom_couleur(hexa, c):
    if hexa is None:
        return "aucune"
    hexa = hexa.upper()
    for groupe in c["couleurs"].values():
        for x in groupe:
            if x["hex"].upper() == hexa:
                return x["nom"]
    for groupe in c["cartons"].values():
        for x in groupe:
            if x["hex"].upper() == hexa:
                return x["nom"]
    return "perso"


def normaliser(da):
    """Remet la DA dans le contrat : valeurs bornées, champs calculés (_y, _resume, couleurs du motion)."""
    c = cat()
    zi = c["zone_interdite"]
    da = copy.deepcopy(da)
    da["version"] = 1
    da.setdefault("nom", "")
    co = da.setdefault("commun", {})
    duo = co.setdefault("duo", {})
    if duo.get("id") != "perso":
        ref = par_id(c["duos"], duo.get("id")) or c["duos"][0]
        duo.update({"id": ref["id"], "nom": ref["nom"],
                    "principale": copy.deepcopy(ref["principale"]), "secondaire": copy.deepcopy(ref["secondaire"])})
    else:
        duo["nom"] = "Mon combo perso"
        duo.setdefault("principale", copy.deepcopy(c["duos"][0]["principale"]))
        duo.setdefault("secondaire", copy.deepcopy(c["duos"][0]["secondaire"]))
    cl = co.setdefault("couleurs", {})
    for k, d in (("titre", "#FFFFFF"), ("ligne2", "#FFFFFF"), ("sous_titres", "#FFFFFF"), ("texte", "#FFFFFF")):
        cl.setdefault(k, d)
    cl.setdefault("accent", "#4F9BFF")
    cl["touches"] = None  # petites touches supprimées le 28/10 (« ça pollue le design »)

    m = da.setdefault("montage", {})
    t = m.setdefault("titre", {})
    t["taille"] = borne(t.get("taille"), 40, 200, 104)
    if t.get("position") not in ("haut", "milieu", "bas"):
        t["position"] = "haut"
    t["decalage"] = borne(t.get("decalage"), -600, 600, 0)
    hauteur_titre = int(round(t["taille"] * 0.5 * 1.05 + t["taille"] * 1.1))
    y = c["positions"]["titre"][t["position"]] + t["decalage"]
    t["_y"] = max(zi["haut"], min(zi["bas"] - hauteur_titre, y))
    s = m.setdefault("sous_titres", {})
    s["taille"] = borne(s.get("taille"), 24, 120, 52)
    if s.get("position") not in ("col", "poitrine", "bas"):
        s["position"] = "col"
    s["decalage"] = borne(s.get("decalage"), -600, 600, 0)
    y = c["positions"]["sous_titres"][s["position"]] + s["decalage"]
    demi = int(s["taille"] * 0.7)
    s["_y"] = max(zi["haut"] + demi, min(zi["bas"] - demi, y))
    m["alignement"] = "centre"
    m["mots_par_ligne"] = borne(m.get("mots_par_ligne"), 1, 5, 3)
    m["texte_entree"] = "net"
    m["texte_sortie"] = "fondu"
    ca = m.setdefault("cartons", {})
    ca.setdefault("depart", "#0E1220")
    ca.setdefault("arrivee", "#1F3A66")
    if not par_id(c["univers"], m.get("univers")):
        m["univers"] = "futuriste"
    mo = m.setdefault("motion", {})
    if mo.get("mode") not in ("sombre", "clair"):
        mo["mode"] = "sombre"
    if mo.get("palette") != "perso" and not par_id(c["palettes"], mo.get("palette")):
        mo["palette"] = "glacier"
    if mo["palette"] != "perso":
        mo["couleurs"] = copy.deepcopy(par_id(c["palettes"], mo["palette"])[mo["mode"]])
    else:
        mo.setdefault("couleurs", copy.deepcopy(c["palettes"][0][mo["mode"]]))
    if mo.get("trait") not in ("fin", "moyen", "epais"):
        mo["trait"] = "fin"
    if mo.get("formes") not in ("arrondies", "carrees"):
        mo["formes"] = "carrees"
    if mo.get("rythme") not in ("pose", "normal", "nerveux"):
        mo["rythme"] = "normal"
    m["zone_interdite"] = copy.deepcopy(zi)

    k = da.setdefault("carrousels", {})
    if not par_id(c["modeles"], k.get("modele")):
        k["modele"] = "cinema"
    cv = k.setdefault("couverture", {})
    if cv.get("place_titre") not in ("haut", "bas", "derriere_tete"):
        cv["place_titre"] = "bas"
    cv["taille_titre"] = borne(cv.get("taille_titre"), 40, 200, 84)
    cv["petite_ligne"] = bool(cv.get("petite_ligne", True))
    cv["fleche_glisse"] = bool(cv.get("fleche_glisse", False))
    sp = k.setdefault("slides_photo", {})
    if sp.get("photos") not in ("sombres", "naturelles", "noir_blanc"):
        sp["photos"] = "sombres"
    if sp.get("texte") not in ("phrase", "liste"):
        sp["texte"] = "phrase"
    sp["taille_texte"] = borne(sp.get("taille_texte"), 24, 120, 40)
    de = k.setdefault("dessins", {})
    if de.get("fond") not in ("nuit", "jour"):
        de["fond"] = "nuit"
    if de.get("style") not in ("comme_motion", "autre"):
        de["style"] = "comme_motion"
    if de["style"] == "comme_motion" or not par_id(c["univers"], de.get("univers")):
        de["univers"] = m["univers"]
    ds = k.setdefault("derniere_slide", {})
    ds["active"] = bool(ds.get("active", True))
    if ds.get("forme") not in ("bulles", "mot_geant", "bouton"):
        ds["forme"] = "bulles"
    ds["photo"] = bool(ds.get("photo", True))
    ds["contour"] = borne(ds.get("contour"), 0, 20, 8)  # épaisseur du contour blanc de la photo ronde, en px (slide 1080)
    ca = ds.setdefault("cadrage", {})  # photo ronde : zoom en %, position du visage en % (50 = centre)
    ca["zoom"] = borne(ca.get("zoom"), 100, 400, 180)
    ca["x"] = borne(ca.get("x"), 0, 100, 50)
    ca["y"] = borne(ca.get("y"), 0, 100, 20)
    da.setdefault("photo_ref", "img/frame.jpg")
    da["_resume"] = resume(da, c)
    da["maj"] = datetime.now().astimezone().isoformat(timespec="seconds")
    ordre = ["version", "maj", "nom", "commun", "montage", "carrousels", "photo_ref", "inspiration", "_resume"]
    return {**{x: da[x] for x in ordre if x in da}, **{x: v for x, v in da.items() if x not in ordre}}


POS = {"haut": "Haut", "milieu": "Milieu", "bas": "Bas", "col": "Col", "poitrine": "Poitrine"}


def resume(da, c):
    co, m, k = da["commun"], da["montage"], da["carrousels"]
    cl = co["couleurs"]
    duo = co["duo"]["nom"] if co["duo"]["id"] != "perso" else "Perso"
    uni = par_id(c["univers"], m["univers"])["nom"]
    mo = m["motion"]
    pal = "Perso" if mo["palette"] == "perso" else par_id(c["palettes"], mo["palette"])["nom"]
    acc = nom_couleur(cl.get("accent"), c)
    dep = nom_couleur(m["cartons"]["depart"], c)
    arr = nom_couleur(m["cartons"]["arrivee"], c)
    mod = par_id(c["modeles"], k["modele"])["nom"]
    cv = k["couverture"]
    place = {"haut": "Titre en haut", "bas": "Titre en bas", "derriere_tete": "Derrière la tête"}[cv["place_titre"]]
    photos = {"sombres": "Sombres", "naturelles": "Naturelles", "noir_blanc": "Noir et blanc"}[k["slides_photo"]["photos"]]
    ds = k["derniere_slide"]
    forme = {"bulles": "3 bulles", "mot_geant": "Mot en géant", "bouton": "Bouton"}[ds["forme"]] if ds["active"] else "Aucune"
    marque = acc.capitalize() if acc != "aucune" else "Aucune"
    return {
        "montage": [
            {"cle": "duo", "ligne": "Duo de polices", "valeur": duo},
            {"cle": "tailles", "ligne": "Tailles et position", "valeur": "%d · %d px" % (m["titre"]["taille"], m["sous_titres"]["taille"])},
            {"cle": "mots", "ligne": "Mots par ligne", "valeur": str(m["mots_par_ligne"])},
            {"cle": "couleurs", "ligne": "Couleur de marque", "valeur": marque},
            {"cle": "texte", "ligne": "Couleurs du texte", "valeur": nom_couleur(cl["titre"], c).capitalize()},
            {"cle": "cartons", "ligne": "Cartons", "valeur": "%s → %s" % (dep, arr)},
            {"cle": "univers", "ligne": "Univers du motion", "valeur": uni},
            {"cle": "motion", "ligne": "Réglages du motion", "valeur": "%s · %s" % (pal, mo["mode"].capitalize())},
        ],
        "carrousels": [
            {"cle": "duo", "ligne": "Duo de polices", "valeur": duo},
            {"cle": "couleurs", "ligne": "Couleur de marque", "valeur": marque},
            {"cle": "texte", "ligne": "Couleur du texte", "valeur": nom_couleur(cl["texte"], c).capitalize()},
            {"cle": "modele", "ligne": "Modèle", "valeur": mod},
            {"cle": "couverture", "ligne": "Couverture", "valeur": place},
            {"cle": "photos", "ligne": "Slides photo", "valeur": photos},
            {"cle": "dessins", "ligne": "Dessins", "valeur": k["dessins"]["fond"].capitalize()},
            {"cle": "derniere", "ligne": "Dernière slide", "valeur": forme},
        ],
    }


def ecrire(da):
    da = normaliser(da)
    os.makedirs(HISTO, exist_ok=True)
    if os.path.exists(DA):
        avant = lire(DA)
        avant.pop("maj", None)
        apres = dict(da)
        apres.pop("maj", None)
        if avant == apres:
            return lire(DA)
        shutil.copy2(DA, os.path.join(HISTO, "da-%s.json" % time.strftime("%Y%m%d-%H%M%S")))
    fd, tmp = tempfile.mkstemp(dir=ICI, suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(da, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, DA)
    return da


def trouver_claude():
    p = shutil.which("claude")
    if p:
        return p
    for c in [os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"),
              "/opt/homebrew/bin/claude", "/usr/local/bin/claude"]:
        if os.path.exists(c):
            return c
    base = os.path.expanduser("~/Library/Application Support/Claude/claude-code")
    trouves = glob.glob(os.path.join(base, "*", "*", "claude.app", "Contents", "MacOS", "claude"))

    def cle(chemin):
        v = chemin[len(base) + 1:].split(os.sep)[0]
        return [int(x) if x.isdigit() else 0 for x in v.split(".")]
    trouves.sort(key=cle)
    return trouves[-1] if trouves else None


def premier_json(texte):
    texte = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.M)
    debut = texte.find("{")
    if debut < 0:
        raise ValueError("pas de JSON dans la réponse")
    prof = 0
    dans_chaine = False
    echap = False
    for i in range(debut, len(texte)):
        ch = texte[i]
        if dans_chaine:
            if echap:
                echap = False
            elif ch == "\\":
                echap = True
            elif ch == '"':
                dans_chaine = False
            continue
        if ch == '"':
            dans_chaine = True
        elif ch == "{":
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0:
                return json.loads(texte[debut:i + 1])
    raise ValueError("JSON incomplet")


def fusion(base, patch):
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            fusion(base[k], v)
        else:
            base[k] = v
    return base


def sans_calcule(da):
    da = copy.deepcopy(da)
    da.pop("_resume", None)
    return da


REGLES = """Règles de la DA (à respecter TOUJOURS) :
- Texte toujours centré. Jamais d'animation du texte (il apparaît net, sort en fondu). Mots par ligne de 1 à 5.
- Zone interdite Instagram sur 1080x1920 : rien au-dessus de 270 px, sous 1480 px, à moins de 65 px des côtés, ni à moins de 120 px à droite sous 1100 px.
- Cartons = dégradé (départ / arrivée), jamais une couleur unie (départ != arrivée).
- Univers du motion = une ambiance parmi : elegant, epure, futuriste, magazine, fait_main, impact.
- Carrousels : vraies photos, jamais d'image IA. Couleurs en hex #RRGGBB. accent peut être null (= aucune). Couleur de marque = accent seul, partagée reels + carrousels. touches = toujours null (supprimées).
- Photo ronde de la dernière slide : carrousels.derniere_slide.cadrage = {zoom 100-400 (%), x 0-100, y 0-100}. « Recentrer » = x 50 ; monter le visage = y plus grand ; plus gros = zoom plus grand.
- N'invente pas de nouvelles clés. Garde les noms de clés existants.
- Pour un duo perso : commun.duo.id = "perso" et principale / secondaire = {famille, fichier, graisse, ...} pris dans le catalogue."""


def appeler_claude(prompt, outils=None, delai=240, modele="sonnet", dossier=None, edition=False):
    exe = trouver_claude()
    if not exe:
        raise RuntimeError("Je ne trouve pas Claude Code sur ce Mac.")
    cmd = [exe, "-p", prompt, "--model", modele, "--output-format", "text"]
    if edition:  # mode « modifier l'appli » : lire et écrire des fichiers, jamais de commande
        cmd += ["--allowedTools", ",".join(outils), "--disallowedTools", "Bash,WebFetch,WebSearch,Agent,NotebookEdit",
                "--permission-mode", "acceptEdits"]
    elif outils:
        cmd += ["--allowedTools", ",".join(outils)]
    else:
        cmd += ["--disallowedTools", "Bash,Edit,Write,WebFetch,WebSearch,Read,Glob,Grep,Agent,NotebookEdit"]
    # Sans les variables de la session Claude qui a lancé le serveur : Claude utilise le compte connecté sur le Mac.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "ANTHROPIC")) and k not in ("AI_AGENT", "BAGGAGE")}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=delai, cwd=dossier or ICI, env=env, stdin=subprocess.DEVNULL)
    sortie = (r.stdout or "") + (r.stderr or "")
    if "Not logged in" in sortie or "/login" in sortie:
        raise RuntimeError("Claude n'est pas encore connecté sur ce Mac. Double-clique une fois sur connecter-claude.command (dossier apps/superda), puis réessaie.")
    if r.returncode != 0:
        raise RuntimeError(sortie.strip()[-400:] or "Claude n'a pas répondu")
    return r.stdout


def demande_claude(corps):
    da = sans_calcule(corps.get("da") or lire(DA))
    onglet = corps.get("onglet", "montage")
    section = corps.get("section", "")
    demande = (corps.get("demande") or "").strip()
    if not demande:
        raise ValueError("Demande vide")
    prompt = """Tu modifies la direction artistique (DA) d'un créateur de contenu dans l'appli SuperDA.
Onglet : %s. Section ouverte : %s.
Sa demande (en français, peut-être dictée) : « %s »

%s

Catalogue des choix possibles :
%s

DA actuelle (JSON) :
%s

Réponds UNIQUEMENT par un objet JSON, sans texte autour, de la forme :
{"patch": { ... seulement les clés à changer, même structure que la DA ... }, "explication": "1 phrase simple en français, tutoiement, ce que tu as changé"}
Si la demande a besoin d'un réglage qui n'existe pas encore dans la DA ou d'une modif de l'appli (nouveau bouton, nouvel élément, autre placement, autre comportement), réponds {"patch": {}, "code": true, "explication": "ce que tu vas ajouter, 1 phrase"} : un second Claude ajoutera le réglage.
Si la demande va contre les règles ci-dessus, patch = {} et explique pourquoi en 1 phrase.""" % (
        onglet, section, demande, REGLES,
        json.dumps(cat(), ensure_ascii=False), json.dumps(da, ensure_ascii=False))
    rep = premier_json(appeler_claude(prompt))
    if rep.get("code") and not rep.get("patch"):
        return modifier_appli(onglet, section, demande)
    patch = rep.get("patch") or {}
    for interdit in ("_resume", "version", "maj"):
        patch.pop(interdit, None)
    nouvelle = ecrire(fusion(da, patch))
    noter(onglet, section, demande, rep.get("explication", ""), patch)
    return {"da": nouvelle, "explication": rep.get("explication", ""), "patch": patch}


APPS = os.path.dirname(ICI)
ZONES = ("superda", "supercarrousel", "supermonteur")
EXT_CODE = (".py", ".js", ".mjs", ".css", ".html", ".json", ".md", ".sh")
SAUTE = {"historique", "preuves", "projets", "reels", "fonts", "img", "inspiration", "node_modules", "final", "rendus", "__pycache__", ".git"}
SERVEURS = {"supercarrousel": 8797, "supermonteur": 8801}
EXCLUS = {"a-corriger.json", "metricool.json", "config.json"}  # état vivant des applis (retours en cours) : jamais remis en arrière

CONSIGNES_CODE = """Tu es dans le dossier des 3 applis de l'utilisateur (créateur de contenu, pas développeur). Elles se parlent :
- superda/ : la DA. server.py (normaliser() = bornes et valeurs par défaut de chaque réglage, resume()), app.js (SECTIONS, panneau() = les réglages de chaque section avec les aides pm / seg / inter / dots, et les aperçus reel() / slides()), catalogue.json, da-schema.json, da.json (la DA en cours).
- supercarrousel/ : fabrique les carrousels avec la DA (modeles.py, moteur.py, README.md).
- supermonteur/ : monte les reels avec la DA (lis d'abord supermonteur/CLAUDE.md).

Sa demande dans SuperDA (onglet %s, section %s) : « %s »
Le réglage n'existe pas encore : ajoute-le pour de vrai.
1. Une clé dans da.json + sa borne et sa valeur par défaut dans normaliser() (server.py) + da-schema.json.
2. Le contrôle dans panneau() d'app.js, dans la bonne section, avec les mêmes aides et le même style que les autres réglages (sinon ajoute les bornes dans le gestionnaire data-pas).
3. L'aperçu d'app.js qui suit le réglage.
4. Le vrai rendu : supercarrousel pour un carrousel, supermonteur pour un reel. Sinon le réglage ne sert à rien.
5. Mets dans da.json la valeur que l'utilisateur demande.

%s
- Change le moins de lignes possible. Ne casse rien de ce qui marche. Garde les noms et le style du code autour.
- Interface en français simple, tutoiement, zéro jargon. Texte toujours centré dans les reels.
- Ne touche jamais aux dossiers historique, preuves, projets, reels, fonts, img. Aucune nouvelle dépendance, aucun appel Internet, aucune clé.
- Tu ne peux pas lancer de commande : relis bien ton code (accolades, virgules, guillemets).

À la fin, réponds UNIQUEMENT par un objet JSON : {"explication": "1 à 2 phrases simples, tutoiement : ce que tu as ajouté et où le trouver"}"""


def photo_code():
    """Le contenu des fichiers de code des 3 applis, pour revenir en arrière si Claude casse quelque chose."""
    out = {}
    for z in ZONES:
        for racine, dossiers, fichiers in os.walk(os.path.join(APPS, z)):
            dossiers[:] = [d for d in dossiers if d not in SAUTE]
            for f in fichiers:
                ch = os.path.join(racine, f)
                if f.endswith(EXT_CODE) and f not in EXCLUS and os.path.getsize(ch) < 2_000_000:
                    with open(ch, "rb") as h:
                        out[ch] = h.read()
    return out


def verifier(chemins):
    """Contrôle chaque fichier modifié + que la DA se charge encore. Renvoie l'erreur, ou None."""
    for ch in chemins:
        if not os.path.exists(ch):
            continue
        if ch.endswith((".js", ".mjs")):
            r = subprocess.run(["node", "--check", ch], capture_output=True, text=True)
        elif ch.endswith(".py"):
            r = subprocess.run([sys.executable, "-m", "py_compile", ch], capture_output=True, text=True)
        elif ch.endswith(".json"):
            try:
                json.load(open(ch, encoding="utf-8"))
                continue
            except Exception as e:
                return "%s : %s" % (os.path.basename(ch), e)
        else:
            continue
        if r.returncode != 0:
            return "%s : %s" % (os.path.basename(ch), (r.stderr or r.stdout).strip()[-300:])
    r = subprocess.run([sys.executable, "-c", "import server; server.normaliser(server.lire(server.DA))"],
                       capture_output=True, text=True, cwd=ICI)
    if r.returncode != 0:
        return "la DA ne se charge plus : " + (r.stderr or "").strip()[-300:]
    return None


def relancer(zone):
    """Relance SuperCarrousel ou SuperMonteur pour qu'ils lisent le nouveau code."""
    port = SERVEURS[zone]
    pids = subprocess.run(["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    for pid in pids:
        subprocess.run(["kill", pid])
    time.sleep(1)
    subprocess.Popen(["bash", os.path.join(APPS, zone, "lancer.sh")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def modifier_appli(onglet, section, demande):
    """Claude ajoute le réglage qui manque, dans le code des applis. Sauvegarde avant, contrôle après, retour arrière si ça casse."""
    avant = photo_code()
    prompt = CONSIGNES_CODE % (onglet, section, demande, REGLES)
    try:
        sortie = appeler_claude(prompt, outils=["Read", "Edit", "Write", "Glob", "Grep"], delai=900, modele="opus",
                                dossier=APPS, edition=True)
        rep = premier_json(sortie)
    except Exception as e:
        rep, sortie = {"explication": ""}, "ERREUR " + str(e)
    apres = photo_code()
    changes = [ch for ch in set(avant) | set(apres) if avant.get(ch) != apres.get(ch)]
    erreur = verifier(changes) if changes else "Claude n'a rien changé (" + sortie.strip()[-200:] + ")"
    if erreur:
        for ch in changes:  # retour arrière : tout redevient comme avant
            if ch in avant:
                with open(ch, "wb") as h:
                    h.write(avant[ch])
            elif os.path.exists(ch):
                os.remove(ch)
        noter(onglet, section, demande, "RETOUR ARRIÈRE : " + erreur, {})
        raise RuntimeError("j'ai essayé d'ajouter ce réglage mais ça cassait l'appli, j'ai tout remis comme avant. Claude Code le fera à la main.")
    sauve = os.path.join(HISTO, "code-" + datetime.now().strftime("%Y%m%d-%H%M%S"))  # anciennes versions, pour annuler
    for ch in changes:
        if ch in avant:
            cible = os.path.join(sauve, os.path.relpath(ch, APPS))
            os.makedirs(os.path.dirname(cible), exist_ok=True)
            with open(cible, "wb") as h:
                h.write(avant[ch])
    explication = rep.get("explication") or "J'ai ajouté le réglage."
    noter(onglet, section, demande, explication + " | fichiers : " + ", ".join(os.path.relpath(c, APPS) for c in changes), {"code": 1})
    for zone in SERVEURS:
        if any(c.startswith(os.path.join(APPS, zone) + os.sep) and c.endswith(".py") for c in changes):
            relancer(zone)
    if os.path.join(ICI, "server.py") in changes:  # SuperDA se relance lui-même juste après avoir répondu
        threading.Timer(1.5, lambda: os.execv(sys.executable, [sys.executable] + sys.argv)).start()
    return {"da": ecrire(lire(DA)) if os.path.join(ICI, "server.py") not in changes else lire(DA),
            "explication": explication, "recharger": True}


def noter(onglet, section, demande, explication, patch):
    """Garde chaque demande à Claude dans demandes.jsonl : Claude Code relit celles qu'il n'a pas pu faire (patch vide)."""
    ligne = {"quand": datetime.now().astimezone().isoformat(timespec="seconds"), "onglet": onglet, "section": section,
             "demande": demande, "explication": explication, "fait": bool(patch)}
    with open(os.path.join(ICI, "demandes.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def inspiration(corps):
    da = sans_calcule(corps.get("da") or lire(DA))
    onglet = corps.get("onglet", "montage")
    source = (corps.get("source") or "").strip()
    outils = ["WebFetch", "WebSearch", "Read"]
    if corps.get("fichier"):
        os.makedirs(INSPI, exist_ok=True)
        nom = re.sub(r"[^\w.\-]", "_", corps.get("nom") or "ressource")
        chemin = os.path.join(INSPI, time.strftime("%Y%m%d-%H%M%S-") + nom)
        with open(chemin, "wb") as f:
            f.write(base64.b64decode(corps["fichier"].split(",")[-1]))
        source = "fichier local : " + chemin
    if not source:
        raise ValueError("Colle un lien ou dépose une ressource")
    prompt = """Tu es directeur artistique. Analyse cette inspiration (lien ou fichier) : %s
Regarde le style visuel (polices, couleurs, taille et place du texte, rythme, type de graphiques). Si tu ne peux pas ouvrir le lien, déduis au mieux du nom du créateur ou de la marque.
Puis propose une DA complète pour l'onglet « %s » de SuperDA, qui s'en inspire, en choisissant UNIQUEMENT dans le catalogue.

%s

Catalogue :
%s

DA actuelle (même structure attendue) :
%s

Réponds UNIQUEMENT par un objet JSON, sans texte autour :
{"da": { ...la DA proposée complète, même structure... }, "resume": "1 phrase simple : Inspirée de X : duo « … », palette …, univers « … »."}""" % (
        source, onglet, REGLES, json.dumps(cat(), ensure_ascii=False), json.dumps(da, ensure_ascii=False))
    rep = premier_json(appeler_claude(prompt, outils=outils, delai=300))
    proposee = normaliser(fusion(copy.deepcopy(da), rep.get("da") or {}))
    return {"proposee": proposee, "resume": rep.get("resume", ""), "source": source}


class Gestion(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ICI, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("[superda] " + (fmt % args) + "\n")

    def end_headers(self):
        statique = self.path.startswith("/fonts/") or self.path.startswith("/img/")
        self.send_header("Cache-Control", "max-age=86400" if statique else "no-store")
        super().end_headers()

    def json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/api/da":
            return self.json(200, lire(DA))
        if p == "/api/catalogue":
            return self.json(200, cat())
        if p == "/api/schema":
            return self.json(200, lire(SCHEMA))
        if p.startswith("/historique") or p.startswith("/inspiration") or p.endswith(".py"):
            return self.json(404, {"erreur": "introuvable"})
        return super().do_GET()

    def do_POST(self):
        p = urlparse(self.path).path
        origine = self.headers.get("Origin")
        if origine and origine not in ("http://localhost:%d" % PORT, "http://127.0.0.1:%d" % PORT):
            return self.json(403, {"erreur": "refusé"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 60 * 1024 * 1024:
                return self.json(413, {"erreur": "Fichier trop lourd (60 Mo max)"})
            corps = json.loads(self.rfile.read(n) or b"{}")
            if p == "/api/da":
                return self.json(200, ecrire(corps))
            if p == "/api/claude":
                return self.json(200, demande_claude(corps))
            if p == "/api/inspiration":
                return self.json(200, inspiration(corps))
            return self.json(404, {"erreur": "introuvable"})
        except subprocess.TimeoutExpired:
            return self.json(504, {"erreur": "Claude a mis trop de temps. Réessaie avec une demande plus courte."})
        except Exception as e:  # message lisible pour la page
            return self.json(400, {"erreur": str(e)})


if __name__ == "__main__":
    if not os.path.exists(DA):
        sys.exit("da.json manquant")
    ecrire(lire(DA))  # remet à jour les champs calculés au démarrage
    print("SuperDA : http://localhost:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Gestion).serve_forever()
