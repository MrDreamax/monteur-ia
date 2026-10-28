"""Renomme le rush d'un reel pour le retrouver d'un coup d'œil (28/10/2026, l'utilisateur : « renomme les rushes pour qu'ils
soient plus facilement trouvables »).

    CAM20058.MP4  ->  2026-10-28 Tourner sans téléprompteur - CAM20058.MP4

Date du tournage + titre du reel + nom d'origine (on retrouve toujours le fichier par son numéro caméra).
Le rush n'est ni copié ni modifié : seul son nom change, sur place. Toutes les fiches qui pointaient vers l'ancien
chemin (etat.json, rush.txt… des montages et de SuperMonteur) sont mises à jour.

    python3 renommer_rush.py <dossier du reel>            # rush et titre lus dans le dossier
    python3 renommer_rush.py <dossier> --rush <chemin>    # rush donné à la main
"""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import reglages_apps  # noqa: E402
MONTAGES = reglages_apps.chemin("montages")
REELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reels")
VIDEO = r"\.(mp4|mov|m4v)$"


def lire(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


PAS_UN_RUSH = re.compile(r"/montages/|/reels/|Biblioth|B-rolls|/Musique/|/Sons/|/skills/")


def trouver_rushs(dossier):
    """Les rushs du reel : etat.json, sinon les chemins de vidéo cités dans les journaux du montage (hors B-rolls,
    musiques et fichiers du montage lui-même). Un reel fait de 2 rushs (cam20056-57) en rend 2."""
    r = (lire(os.path.join(dossier, "etat.json"), {}) or {}).get("rush")
    if r and os.path.isfile(r):
        return [r]
    vus = []
    for f in sorted(os.listdir(dossier)):
        if not re.search(r"\.(log|json|txt)$", f) or os.path.getsize(os.path.join(dossier, f)) > 2_000_000:
            continue
        for c in re.findall(r"(/(?:Volumes|Users)/[^\"'\n]*?\.(?:MP4|mp4|MOV|mov|M4V|m4v))", open(os.path.join(dossier, f), errors="ignore").read()):
            if c not in vus and os.path.isfile(c) and not PAS_UN_RUSH.search(c):
                vus.append(c)
    return vus[:3]


def titre(dossier):
    t = (lire(os.path.join(dossier, "plan.json"), {}) or {}).get("title") or {}
    s = " ".join(x for x in (t.get("l1"), t.get("l2")) if x) if isinstance(t, dict) else str(t)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", s)          # interdits sur la carte de la caméra (exFAT)
    s = re.sub(r"\s+", " ", s).strip(" .-")
    return s[:1].upper() + s[1:].lower() if s.isupper() else s[:1].upper() + s[1:]


def nouveau_nom(rush, dossier):
    base, ext = os.path.splitext(os.path.basename(rush))
    if re.match(r"\d{4}-\d{2}-\d{2} ", base):
        return None                                        # déjà renommé
    t = titre(dossier)
    if not t:
        return None
    st = os.stat(rush)
    jour = datetime.date.fromtimestamp(min(getattr(st, "st_birthtime", st.st_mtime), st.st_mtime))  # jour du tournage
    return f"{jour:%Y-%m-%d} {t[:60].rstrip()} - {base}{ext}"


def fiches():
    """Les petits fichiers texte des montages et de SuperMonteur qui peuvent citer le chemin du rush."""
    for racine in (MONTAGES, REELS):
        if not os.path.isdir(racine):
            continue
        for d in os.listdir(racine):
            dd = os.path.join(racine, d)
            if os.path.islink(dd) or not os.path.isdir(dd):
                continue                                   # un reel importé = raccourci vers montages/ : déjà parcouru
            for f in os.listdir(dd):
                p = os.path.join(dd, f)
                if re.search(r"\.(json|txt)$", f) and os.path.isfile(p) and os.path.getsize(p) < 5_000_000:
                    yield p


def renommer(dossier, rush=None):
    dossier = os.path.abspath(dossier)
    rushs = [rush] if rush else trouver_rushs(dossier)
    if not rushs:
        print("rush introuvable (carte de la caméra débranchée ?) : rien renommé")
        return []
    return [un_rush(dossier, r) for r in rushs]


def un_rush(dossier, rush):
    nom = nouveau_nom(rush, dossier)
    if not nom:
        print("déjà renommé ou pas de titre :", os.path.basename(rush))
        return rush
    neuf = os.path.join(os.path.dirname(rush), nom)
    if os.path.exists(neuf):
        print("existe déjà :", neuf)
        return rush
    os.rename(rush, neuf)
    vieux_json, neuf_json = json.dumps(rush)[1:-1], json.dumps(neuf)[1:-1]
    n = 0
    for p in fiches():
        s = open(p, errors="ignore").read()
        if rush in s or vieux_json in s:
            open(p, "w").write(s.replace(vieux_json, neuf_json).replace(rush, neuf))
            n += 1
    print(f"{os.path.basename(rush)} -> {nom} ({n} fiche{'s' if n > 1 else ''} mise{'s' if n > 1 else ''} à jour)")
    return neuf


if __name__ == "__main__":
    a = sys.argv[1:]
    r = a[a.index("--rush") + 1] if "--rush" in a else None
    renommer(a[0], r)
