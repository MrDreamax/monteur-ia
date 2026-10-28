"""Modèles de carrousel que le moteur du skill (style Apple = « Épuré ») ne sait pas encore faire.
Ils réutilisent la préparation photo du moteur (apple.prep_photo : recadrage 3:4 + détourage) et les dessins
d'art.py : seule la mise en page change. Jamais d'image IA.

Cinéma (SuperDA, 26/10/2026) : photo plein cadre assombrie vers le bas, petite ligne en majuscules (police principale),
titre en police secondaire (ex. Instrument Serif italique) en blanc, mot fort <em> en couleur d'accent ;
slides dessin sur fond nuit en dégradé ; dernière slide : photo ronde + 3 bulles de message.
"""
import os
import re

import apple
from art import ARTS, MIST, NAVY

W, H = apple.W, apple.H


def _font_faces(da, superda):
    out = ""
    duo = da["commun"]["duo"]
    for pol in (duo.get("principale", {}), duo.get("secondaire", {})):
        f = os.path.join(superda, "fonts", pol.get("fichier", ""))
        if pol.get("fichier") and os.path.exists(f):
            out += (f'@font-face{{font-family:"{pol["famille"]}";src:url("file://{f}");'
                    f'font-style:{"italic" if pol.get("italique") else "normal"}}}')
    return out


def css_cinema(da, superda):
    duo, c, car = da["commun"]["duo"], da["commun"]["couleurs"], da["carrousels"]
    p, s = duo.get("principale", {}), duo.get("secondaire", {})
    fp = f'"{p.get("famille", "Montserrat")}",-apple-system,sans-serif'
    fs = f'"{s.get("famille", "Instrument Serif")}",Georgia,serif'
    acc = c.get("accent") or "#FFFFFF"
    txt = c.get("texte") or "#FFFFFF"
    ital = "italic" if s.get("italique", True) else "normal"
    ph = car["slides_photo"].get("photos", "sombres")
    filtre = {"sombres": "brightness(.82) contrast(1.05)", "noir_blanc": "grayscale(1) contrast(1.05)"}.get(ph, "none")
    voile = ".2,.92" if ph == "sombres" else ".05,.85"
    a, b = voile.split(",")
    corps = car["slides_photo"].get("taille_texte", 40)
    cad = car["derniere_slide"].get("cadrage") or {}  # cadrage de la photo ronde, réglé dans SuperDA
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<style>{_font_faces(da, superda)}
*{{box-sizing:border-box;margin:0}}
body{{margin:0;background:#000;-webkit-font-smoothing:antialiased;color:{txt}}}
.s{{width:{W}px;height:{H}px;position:relative;overflow:hidden;background:#0B0B0D}}
.nuit{{background:linear-gradient(160deg,#0B0B0D 0%,#161D2F 100%)}}
.ph{{position:absolute;inset:0;width:{W}px;height:{H}px;object-fit:cover;filter:{filtre}}}
.voile{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,{a}) 0%,rgba(0,0,0,.15) 35%,rgba(0,0,0,{b}) 78%,rgba(0,0,0,.96) 100%)}}
.voile.haut{{background:linear-gradient(0deg,rgba(0,0,0,{a}) 0%,rgba(0,0,0,.15) 45%,rgba(0,0,0,{b}) 82%,rgba(0,0,0,.96) 100%)}}
.txt{{position:absolute;left:84px;right:84px;z-index:4}}
.k{{font:{p.get("graisse", 700)} 34px {fp};letter-spacing:.16em;text-transform:uppercase;opacity:.85;margin-bottom:22px}}
.t{{font-family:{fs};font-style:{ital};font-weight:{s.get("graisse", 400)};line-height:.98;letter-spacing:-.01em;color:{txt}}}
.t em{{font-style:{ital};color:{acc}}}
.sub{{font:500 {corps}px/1.4 {fp};opacity:.88;margin-top:28px}}
.steps{{display:flex;flex-direction:column;gap:22px;margin-top:34px}}
.step{{display:flex;gap:26px;align-items:center;font:500 {corps}px/1.3 {fp}}}
.n{{flex:0 0 64px;height:64px;border-radius:50%;border:2px solid {acc};color:{acc};font:700 30px {fp};display:flex;align-items:center;justify-content:center}}
.glisse{{display:inline-block;margin-top:34px;background:{acc};color:#fff;font:700 30px {fp};padding:20px 34px;border-radius:60px}}
.arrow{{position:absolute;right:60px;bottom:54px;font:500 44px {fp};opacity:.6;z-index:5}}
.art{{display:block;width:{W}px;height:820px}}
.chat{{display:flex;flex-direction:column;gap:24px;font:500 42px/1.25 -apple-system,system-ui,sans-serif;margin-top:60px}}
.b{{padding:24px 40px;max-width:800px}}
.them{{align-self:flex-start;background:#2C2C2E;color:#fff;border-radius:42px 42px 42px 12px}}
.me{{align-self:flex-end;background:{acc};color:#fff;font-weight:700;border-radius:42px 42px 12px 42px}}
.rond{{width:200px;height:200px;border-radius:50%;background-size:{cad.get("zoom", 180)}%;background-position:{cad.get("x", 50)}% {cad.get("y", 20)}%;border:{car["derniere_slide"].get("contour", 8)}px solid #fff;margin-bottom:44px}}
.fin{{font:500 36px {fp};opacity:.85;margin-top:48px}}
.fin b{{color:{acc};font-weight:700}}
.fin-bloc{{top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;padding-bottom:40px}}
</style></head><body>"""


def propre(t):
    """Titre propre : pas de point qui traîne en fin de ligne (« ? », « ! » et « … » restent),
    et « n°1 » collé (le ° de la police serif laisse un trou)."""
    lignes = re.split(r"(<br\s*/?>)", t or "")
    lignes = [x if x.startswith("<br") else re.sub(r"(?<![.…])\.(\s*(?:</\w+>)?\s*)$", r"\1", x) for x in lignes]
    return re.sub(r"\b([nN])\s*°\s*(\d)", r'\1<span style="margin-left:-.18em">°</span>\2', "".join(lignes))


def _titre(s, taille):
    out = f'<div class="k">{s["kicker"]}</div>' if s.get("kicker") else ""
    out += f'<h2 class="t" style="font-size:{s.get("title_size", taille)}px">{propre(s["title"])}</h2>'
    if s.get("body"):
        out += f'<p class="sub">{s["body"]}</p>'
    if s.get("steps"):
        out += '<div class="steps">' + "".join(f'<div class="step"><div class="n">{i}</div><div>{t}</div></div>'
                                               for i, t in enumerate(s["steps"], 1)) + "</div>"
    return out


def _art_nuit(svg):
    """Dessins d'art.py posés sur la nuit : le grand cercle clair devient bleu nuit, le trait foncé devient clair."""
    svg = svg.replace(f'fill="{MIST}"', 'fill="#1A2440"')
    # traits et formes foncés -> clairs ; mais un chiffre ou un mot (<text>) posé sur une forme claire garde son encre foncée
    morceaux = re.split(r"(<text[^>]*>.*?</text>)", svg, flags=re.S)
    return "".join(x if x.startswith("<text") else x.replace(NAVY, "#DCE6F5") for x in morceaux)


def photo_ronde(photos, s, visages, cad):
    """La photo ronde : centrée sur le visage trouvé par Vision ; le cadrage de SuperDA (zoom, flèches) l'ajuste autour.
    Sans visage trouvé : le cadrage de SuperDA seul, comme avant."""
    nom = s.get("photo") or max(photos, key=lambda k: (visages.get(k) or [0, 0, 0])[2])  # sinon : la photo où le visage est le plus grand
    v = visages.get(nom)
    if not v:
        return f'<div class="rond" style="background-image:url({photos[nom]}.jpg)"></div>'
    cx, cy, d = v
    d = d * 180 / max(cad.get("zoom", 180), 1)                      # zoom SuperDA : 180 = réglage de base
    cx += (cad.get("x", 50) - 50) / 100 * d                          # flèches SuperDA : ← → et ↑ ↓
    cy += (cad.get("y", 20) - 20) / 100 * d
    k = 200 / d                                                      # le rond fait 200 px
    return (f'<div class="rond" style="background-image:url({photos[nom]}.jpg);background-size:{1080 * k:.0f}px {1440 * k:.0f}px;'
            f'background-position:{100 - cx * k:.0f}px {100 - cy * k:.0f}px"></div>')


def slide_cinema(s, last, photos, da, spec_dir, visages=None):
    car = da["carrousels"]
    cov = car["couverture"]
    fleche = "" if last or not cov.get("fleche_glisse", True) else '<div class="arrow">→</div>'
    t = s["type"]
    if t == "cover":
        img = photos[s["photo"]]
        place = cov.get("place_titre", "bas")
        taille = int(cov.get("taille_titre", 120))  # px sur 1080 (contrat SuperDA) ; le script AJUSTE le rétrécit s'il déborde
        glisse = '<div class="glisse">Glisse pour voir →</div>' if cov.get("fleche_glisse", True) else ""
        if place == "derriere_tete":  # mot géant derrière la tête : le détourage du moteur repasse par-dessus
            inner = (f'<img class="ph" src="{img}.jpg"><div class="voile"></div>'
                     f'<div class="txt" style="top:150px;text-align:center;z-index:2"><h2 class="t" style="font-size:{int(taille * 1.5)}px">{propre(s["title"])}</h2></div>'
                     f'<img class="ph" src="{img}-fg.png" style="z-index:3">'
                     f'<div class="txt" style="bottom:110px;text-align:center">{"<div class=k>" + s["kicker"] + "</div>" if s.get("kicker") else ""}{glisse}</div>')
        else:
            pos = "top:130px" if place == "haut" else "bottom:120px"
            inner = (f'<img class="ph" src="{img}.jpg"><div class="voile{" haut" if place == "haut" else ""}"></div>'
                     f'<div class="txt" style="{pos}">{_titre(s, taille)}{glisse}</div>')
        return f'<div class="s">{inner}</div>'  # pas de flèche en plus : la couverture a son bouton « Glisse »
    if t == "photo":
        img = photos[s["photo"]]
        return (f'<div class="s"><img class="ph" src="{img}.jpg"><div class="voile"></div>'
                f'<div class="txt" style="bottom:130px">{_titre(s, 104)}</div>{fleche}</div>')
    if t == "art":
        if s.get("cta"):
            der = car["derniere_slide"]
            rond = ""
            if der.get("photo") and photos:
                rond = photo_ronde(photos, s, visages or {}, der.get("cadrage") or {})
            q = s.get("cta_q", "Tu veux la ressource ?")
            # bloc centré en hauteur (plus de grand vide en bas), le mot à écrire répété en clair
            return (f'<div class="s nuit"><div class="txt fin-bloc">{rond}{_titre(dict(s, body=None), 110)}'
                    f'<div class="chat"><div class="b them">{q}</div><div class="b me">{s["cta"].upper()}</div>'
                    f'<div class="b them">{s.get("cta_line", "Envoyé en DM. Bonne lecture.")}</div></div>'
                    f'<div class="fin">Écris <b>{s["cta"].upper()}</b> en commentaire</div></div></div>')
        if s.get("svg"):
            art = open(os.path.join(spec_dir, os.path.expanduser(s["svg"]))).read()
        else:
            art = ARTS[s["art"]](**s.get("args", {}))
        titre = f'<div class="txt" style="top:120px"><h2 class="t" style="font-size:{s.get("title_size", 104)}px">{propre(s["title"])}</h2></div>'
        bas = dict(s, title="")
        corps = ""
        if s.get("body"):
            corps += f'<p class="sub" style="margin-top:0">{s["body"]}</p>'
        if s.get("steps"):
            corps += _titre(dict(bas, body=None), 10).split("</h2>", 1)[1]
        haut = "560" if s.get("steps") else "700"
        art = _art_nuit(art).replace('<svg class="art"', f'<svg class="art" style="height:{haut}px"', 1)
        return (f'<div class="s nuit">{titre}<div style="position:absolute;left:0;top:{330 if s.get("steps") else 380}px">'
                f'{art}</div>'
                f'<div class="txt" style="bottom:130px">{corps}</div>{fleche}</div>')
    raise ValueError(f"type de slide inconnu : {t}")
