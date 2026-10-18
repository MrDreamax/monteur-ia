"""Réglages du Publieur (config.json du skill, ou PUBLIEUR_CONFIG pour un test) + DA de la cover."""
import json, os

ICI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(ICI)
MONTEUR = os.path.expanduser("~/.claude/skills/supermonteur")


def _x(v):
    return os.path.expanduser(v) if isinstance(v, str) else v


def config():
    p = os.environ.get("PUBLIEUR_CONFIG", os.path.join(SKILL, "config.json"))
    if not os.path.exists(p):
        raise SystemExit(f"Réglages introuvables : {p} (chez un client : copier config.exemple-client.json en config.json)")
    c = json.load(open(p))
    return {k: _x(v) for k, v in c.items()}


def config_monteur():
    p = _x(os.environ.get("MONTEUR_CONFIG", os.path.join(MONTEUR, "config.json")))
    c = json.load(open(p))
    return {k: _x(v) for k, v in c.items()}


def da_cover():
    """Polices et couleurs de la cover. DA vide = celle de Cyril."""
    d = {"sans": os.path.join(SKILL, "assets", "Montserrat.ttf"),
         "serif": os.path.join(SKILL, "assets", "InstrumentSerif-Italic.ttf"),
         "texte": "#FFFFFF", "accent": "#D9BC82"}
    chemin = config().get("da", "")
    if chemin:
        if not os.path.exists(chemin):
            raise SystemExit(f"DA du client introuvable : {chemin}")
        da = json.load(open(chemin))
        for cle in ("sans", "serif"):
            f = da.get("fonts", {}).get(cle)
            if f:
                src = f if os.path.isabs(f) else os.path.join(MONTEUR, "fonts", f)
                if os.path.exists(src):
                    d[cle] = src
        col = da.get("colors", {})
        if col.get("text", "").startswith("#"):
            d["texte"] = col["text"]
        if col.get("accent", "").startswith("#"):
            d["accent"] = col["accent"]
    return d
