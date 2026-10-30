"""Réglages communs des applis de Super (chez l'utilisateur, jamais dans le code).

    config.json (à côté de ce fichier) : créé par install.sh, rempli au 1er lancement, jamais écrasé par une mise à jour.
    Metricool (id de marque, compte Instagram attendu) : lus dans les réglages du skill publieur (~/.claude/skills/publieur/config.json).
"""
import datetime
import json
import os

ICI = os.path.dirname(os.path.abspath(__file__))
PUBLIEUR = os.path.expanduser("~/.claude/skills/publieur/config.json")
DEFAUT = {
    "nom": "",                                                 # prénom de l'utilisateur (les consignes de Claude)
    "montages": "~/Documents/Montage/MONTAGES",                # reels montés dans un chat : ils apparaissent dans « Tes reels »
    "registre": "~/Documents/Montage/PUBLICATION/registre.md",  # 1 ligne par publication (évite de publier 2 fois)
    "erreurs": os.path.join(ICI, "erreurs.log"),
    "ports": {"superveille": 8811, "superda": 8781, "supermonteur": 8801, "supercarrousel": 8797},
}


def _lire(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def config():
    c = json.loads(json.dumps(DEFAUT))
    for k, v in _lire(os.path.join(ICI, "config.json")).items():
        if isinstance(v, dict) and isinstance(c.get(k), dict):
            c[k].update(v)
        elif v not in ("", None):
            c[k] = v
    return c


def chemin(cle):
    return os.path.expanduser(config()[cle])


def port(appli):
    return int(config()["ports"][appli])


def nom():
    return config()["nom"] or "l'utilisateur"


def mode_essai(appli_dir):
    """true (défaut) = le bouton Publier ne publie rien. Se change dans <appli>/config.json, par l'utilisateur lui-même."""
    return _lire(os.path.join(appli_dir, "config.json")).get("mode_essai", True) is not False


def publieur():
    """Réglages Metricool du skill publieur. Vides tant que le 1er lancement du Publieur n'est pas fait."""
    p = _lire(PUBLIEUR)
    return {"brand": str(p.get("metricool_brand_id") or "").strip(),
            "instagram": str(p.get("instagram_attendu") or "").strip().lstrip("@"),
            "registre": os.path.expanduser(p.get("registre") or config()["registre"]),
            "carnet": os.path.expanduser(p.get("carnet") or "~/.claude/skills/publieur/retours-client.md")}


def erreur(texte):
    try:
        with open(chemin("erreurs"), "a", encoding="utf-8") as f:
            f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} {texte}\n")
    except OSError:
        pass
