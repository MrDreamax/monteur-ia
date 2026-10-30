"""La DA vue par SuperMonteur (28/10/2026). Source unique = SuperDA : ~/Documents/SuperApps/superda/da.json
(clés commun + montage, contrat da-schema.json). Tant que SuperDA n'a rien écrit : repli sur la DA du moteur
(Brain 00-Moi/reglages/da-montage.json, sinon le da/exemple.json du skill), lue en lecture seule.
"""
import json, os

SUPERDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "superda")
import sys
sys.path.insert(0, os.path.dirname(SUPERDA))
import reglages_apps  # noqa: E402
SK = os.path.expanduser("~/.claude/skills/supermonteur")
REPLI = [os.path.join(SK, "da", "exemple.json")]
DUOS = {("Montserrat.ttf", "InstrumentSerif-Italic.ttf"): "Élégant", ("BebasNeue-Regular.ttf", "BebasNeue-Regular.ttf"): "Impact"}
NOMS = {"#FFFFFF": "Blanc", "#4F9BFF": "Bleu", "#4F7CFF": "Bleu", "#0071E3": "Bleu", "#000000": "Noir", "#FFD60A": "Jaune"}
UNIVERS = {"elegant": "Élégant", "epure": "Épuré", "futuriste": "Futuriste", "magazine": "Magazine", "fait_main": "Fait main", "impact": "Impact"}


def _lire(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def superda():
    """da.json de SuperDA, ou None."""
    d = _lire(os.path.join(SUPERDA, "da.json"))
    return d if isinstance(d, dict) and d.get("montage") else None


def _couleur(h):
    return NOMS.get((h or "").upper(), h or "?")


def resume():
    """Les 7 lignes du tiroir « Ma DA » + le nom du duo (bouton du haut) + d'où vient la DA."""
    d = superda()
    if d:
        c, m = d.get("commun", {}), d.get("montage", {})
        duo = c.get("duo", {}).get("nom", "?")
        lignes = (d.get("_resume") or {}).get("montage")
        if lignes:
            lignes = [{"ligne": l.get("ligne"), "valeur": l.get("valeur")} for l in lignes]
        else:
            co, mo = c.get("couleurs", {}), m.get("motion", {})
            lignes = [
                {"ligne": "Duo de polices", "valeur": duo},
                {"ligne": "Tailles et position", "valeur": f"{m.get('titre', {}).get('taille', '?')} · {m.get('sous_titres', {}).get('taille', '?')} px"},
                {"ligne": "Mots par ligne", "valeur": str(m.get("mots_par_ligne", "?"))},
                {"ligne": "Couleurs", "valeur": f"{_couleur(co.get('titre'))} · {_couleur(co.get('accent') or co.get('titre'))}"},
                {"ligne": "Cartons", "valeur": f"{_couleur(m.get('cartons', {}).get('depart'))} → {_couleur(m.get('cartons', {}).get('arrivee'))}"},
                {"ligne": "Univers du motion", "valeur": UNIVERS.get(m.get("univers"), m.get("univers", "?"))},
                {"ligne": "Réglages du motion", "valeur": (mo.get("mode") or "?").capitalize()},
            ]
        return {"source": "superda", "duo": duo, "lignes": lignes}
    for p in REPLI:
        r = _lire(p)
        if not r: continue
        f, c, ty = r.get("fonts", {}), r.get("colors", {}), r.get("typo") or {}
        duo = DUOS.get((f.get("sans"), f.get("serif")), "Mon combo perso")
        ts = r.get("titleSize") or [ty.get("t1", {}).get("size", 97), ty.get("t2", {}).get("size", 106)]
        lst = c.get("list") or ["#161D2F", "#0B0B0D"]
        lignes = [
            {"ligne": "Duo de polices", "valeur": duo},
            {"ligne": "Tailles et position", "valeur": f"{ts[0] if isinstance(ts, list) else ts} · {r.get('subSize', 52)} px"},
            {"ligne": "Mots par ligne", "valeur": str(r.get("subMax", 4))},
            {"ligne": "Couleurs", "valeur": f"{_couleur(c.get('text'))} · {_couleur(c.get('accent'))}"},
            {"ligne": "Cartons", "valeur": "Nuit → bleu" if lst else "?"},
            {"ligne": "Univers du motion", "valeur": "Élégant"},
            {"ligne": "Réglages du motion", "valeur": "Sombre"},
        ]
        return {"source": os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p), "duo": duo, "lignes": lignes}
    return {"source": "aucune", "duo": "?", "lignes": []}


def pour_moteur():
    """da.json de SuperDA traduit au format du moteur (fonts, colors, typo, subSize, subMax) pour plan.da. None = rien à
    traduire (le moteur prend alors sa DA habituelle)."""
    d = superda()
    if not d: return None
    c, m = d.get("commun", {}), d.get("montage", {})
    p, s, co = c.get("duo", {}).get("principale", {}), c.get("duo", {}).get("secondaire", {}), c.get("couleurs", {})
    fonts_dir = os.path.join(SK, "fonts")
    fp = p.get("fichier") if p.get("fichier") and os.path.exists(os.path.join(fonts_dir, p["fichier"])) else "Montserrat.ttf"
    fs = s.get("fichier") if s.get("fichier") and os.path.exists(os.path.join(fonts_dir, s["fichier"])) else "InstrumentSerif-Italic.ttf"
    # contrat SuperDA (note du 28/10 01:50) : titre.taille = ligne 2 (police secondaire) ; ligne 1 = taille x 0,5
    t2 = int(m.get("titre", {}).get("taille") or 120)
    t1 = round(t2 * 0.5)
    sub = int(m.get("sous_titres", {}).get("taille") or 52)
    accent = co.get("accent") or co.get("titre") or "#FFFFFF"
    car = m.get("cartons", {})
    out = {
        "_doc": "Traduit de apps/superda/da.json par SuperMonteur (da.py). Ne pas éditer : changer la DA dans SuperDA.",
        "fonts": {"sans": fp, "serif": fs, "sub": fp},
        "colors": {"text": co.get("sous_titres") or "#FFFFFF", "accent": accent, "serif": co.get("ligne2") or "#FFFFFF",
                   "list": [car.get("depart") or "#161D2F", car.get("arrivee") or "#0B0B0D"]},
        "subSize": sub,
        "typo": {
            "t1": {"font": fp, "weight": p.get("graisse", 700), "size": t1, "color": co.get("titre") or "#FFFFFF", "caps": bool(p.get("majuscules", True))},
            "t2": {"font": fs, "weight": s.get("graisse", 400), "size": t2, "color": co.get("ligne2") or "#FFFFFF",
                   "italic": bool(s.get("italique", True)), "caps": bool(s.get("majuscules", False))},
            "sub": {"font": fp, "weight": p.get("graisse", 700), "caps": bool(m.get("sous_titres", {}).get("majuscules", True)), "scale": 1, "color": co.get("sous_titres") or "#FFFFFF",
                    "track": 0.5},   # sous-titres du moteur : majuscules, 0,5 px (moteur.md, Style Lab 13/10)
            "shadow": "douce", "align": "center"},
        "subMax": max(1, min(4, int(m.get("mots_par_ligne") or 4))),   # le moteur plafonne à 4 mots (plan.subMax)
    }
    return out


def superda_url():
    """Port du serveur SuperDA : launch.json du projet (entrée « superda »), sinon 8765 (contrat da-schema.json)."""
    return f"http://localhost:{reglages_apps.port('superda')}"
