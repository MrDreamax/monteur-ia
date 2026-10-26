"""Réglages du Monteur et DA de la personne, communs à tous les scripts.

config() = config.json du skill (défauts du kit) écrasé clé par clé par ~/Documents/Brain/00-Moi/reglages/supermonteur.json
           (les réglages de CETTE machine, jamais écrasés par une mise à jour). MONTEUR_CONFIG = un fichier seul, pour un test.
da_perso() = DA de montage de l'utilisateur : ~/Documents/Brain/00-Moi/reglages/da-montage.json, sinon da/exemple.json du kit.
"""
import json, os

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(os.path.expanduser(os.environ.get("KIT_BRAIN", "~/Documents/Brain")), "00-Moi", "reglages")


def _x(v):
    return os.path.expanduser(v) if isinstance(v, str) and v.startswith("~") else v


def config():
    p = os.environ.get("MONTEUR_CONFIG")
    c = json.load(open(os.path.expanduser(p) if p else os.path.join(SKILL, "config.json"), encoding="utf-8"))
    perso = os.path.join(REG, "supermonteur.json")
    if not p and os.path.exists(perso):
        c.update(json.load(open(perso, encoding="utf-8")))
    c = {k: _x(v) for k, v in c.items()}
    for s in (c.get("sfx") or {}).values():
        if isinstance(s, dict):
            s["src"] = _x(s.get("src", ""))
    return c


def da_perso():
    p = os.path.join(REG, "da-montage.json")
    return p if os.path.exists(p) else os.path.join(SKILL, "da", "exemple.json")


def colonne_visible(cfg=None):
    """Colonne « la personne est visible » de l'_INDEX.csv des B-rolls."""
    return (cfg or config()).get("colonne_visible", "personne_visible")


def sorties():
    """Où ranger ce que l'employé fabrique : « sorties » de 00-Moi/marque.json, sinon ~/Documents/Contenu."""
    try:
        s = json.load(open(os.path.join(os.path.dirname(REG), "marque.json"), encoding="utf-8")).get("sorties")
    except (OSError, ValueError):
        s = ""
    return os.path.expanduser(s or "~/Documents/Contenu")


if __name__ == "__main__":  # affiche les réglages de cette machine (défauts du kit + Brain) et la DA utilisée
    print(json.dumps(dict(config(), _da=da_perso(), _sorties=sorties()), ensure_ascii=False, indent=2))
