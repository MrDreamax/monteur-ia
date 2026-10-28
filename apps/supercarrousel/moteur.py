"""SuperCarrousel : la couche entre l'écran et le moteur du skill carrousel (style Apple, apple.py).
Ne réécrit PAS le moteur : il appelle apple.prep_photo / apple.slide, une slide à la fois, et pose la DA de SuperDA
par-dessus (polices du duo, couleur d'accent, petites touches, traitement des photos, flèche, fond des dessins).

Un projet = projets/<id>/ :
  demande.json            ce que l'utilisateur a choisi sur l'écran 0 (départ, vidéo, lien, idée, images)
  _reel/                  images + texte.txt sortis du reel (reel2frames.py du skill)
  _modele/                images du carrousel à reprendre
  etat.json               où on en est (statut, version, slide en cours)
  retours.json            les retours tapés sur l'écran 2
  v1/, v2/…               une version = description.json (écrite par Claude) + slide-N.png + legendes.txt
"""
import copy
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
PROJETS = os.path.join(ICI, "projets")
SKILL = os.path.expanduser("~/.claude/skills/carrousel/scripts")
SUPERDA = os.path.join(os.path.dirname(ICI), "superda")
DA_FICHIER = os.path.join(SUPERDA, "da.json")
sys.path.insert(0, SKILL)
import apple  # noqa: E402  (moteur style Apple du skill carrousel)
from art import BLUE, MIST, PALE, SKY, YELLOW  # noqa: E402
import modeles  # noqa: E402  (modèles que le moteur ne fait pas encore : Cinéma)

W, H = apple.W, apple.H
RESEAUX = ["instagram", "tiktok", "facebook", "linkedin"]  # jamais YouTube (pas de carrousel)
NOMS_RESEAUX = {"instagram": "Instagram", "tiktok": "TikTok (mode photos)", "facebook": "Facebook", "linkedin": "LinkedIn (document)"}

# ---------------------------------------------------------------- DA

# En attendant da.json de SuperDA : la DA actuelle du skill carrousel (style Apple validé le 22/10), au format du contrat
DA_SKILL = {
    "version": 1,
    "_source": "skill carrousel (style Apple du 22/10), en attendant SuperDA",
    "commun": {
        "duo": {"id": "moderne", "nom": "Apple",
                "principale": {"famille": "-apple-system", "graisse": 700, "majuscules": False},
                "secondaire": {"famille": "Kalam", "italique": False}},
        "couleurs": {"accent": BLUE, "touches": None, "texte": apple.INK},
    },
    "carrousels": {
        "modele": "epure",
        "couverture": {"place_titre": "haut", "taille_titre": 112, "petite_ligne": True, "fleche_glisse": True},
        "slides_photo": {"photos": "naturelles", "texte": "phrase", "taille_texte": 40},
        "dessins": {"fond": "jour", "style": "comme_motion", "univers": "epure"},
        "derniere_slide": {"active": True, "forme": "bulles", "photo": False},
    },
}

MODELES = {"epure": "Épuré", "cinema": "Cinéma", "collage": "Collage", "carnet": "Carnet", "impact": "Impact",
           "post_texte": "Post texte"}


def _fusion(base, haut):
    out = copy.deepcopy(base)
    for k, v in (haut or {}).items():
        out[k] = _fusion(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def lire_da():
    """DA de SuperDA (apps/superda/da.json : clés commun + carrousels), complétée par la DA du skill si une clé manque."""
    try:
        da = json.load(open(DA_FICHIER))
        out = _fusion(DA_SKILL, {"commun": da.get("commun", {}), "carrousels": da.get("carrousels", {})})
        out["_source"] = "SuperDA"
        out["maj"] = da.get("maj", "")
        return out
    except (OSError, ValueError):
        return copy.deepcopy(DA_SKILL)


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(round(ra[i] * (1 - t) + rb[i] * t) for i in range(3))


def nom_couleur(h):
    """Nom simple d'une couleur pour la pastille (« Bleu », « Jaune »…)."""
    if not h:
        return ""
    r, g, b = [x / 255 for x in _rgb(h)]
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 0.12:
        return "Noir" if mx < 0.3 else ("Blanc" if mx > 0.85 else "Gris")
    if mx == r:
        hue = ((g - b) / (mx - mn)) % 6
    elif mx == g:
        hue = (b - r) / (mx - mn) + 2
    else:
        hue = (r - g) / (mx - mn) + 4
    hue *= 60
    for fin, nom in ((15, "Rouge"), (40, "Orange"), (70, "Jaune"), (165, "Vert"), (200, "Turquoise"), (255, "Bleu"),
                     (290, "Violet"), (335, "Rose"), (361, "Rouge")):
        if hue < fin:
            return nom


def resume_da(da=None):
    """Ce que l'écran affiche : pastille « Épuré · Élégant · Bleu + jaune » et les 7 lignes du tiroir."""
    da = da or lire_da()
    c, car = da["commun"]["couleurs"], da["carrousels"]
    acc, tou = nom_couleur(c.get("accent")), nom_couleur(c.get("touches"))
    couleurs = acc or "Aucune"  # petites touches supprimées le 28/10
    duo = da["commun"]["duo"].get("nom", "")
    cov = {"haut": "Titre en haut", "bas": "Titre en bas", "derriere_tete": "Mot derrière la tête"}
    photos = {"sombres": "Sombres", "naturelles": "Naturelles", "noir_blanc": "Noir et blanc"}
    der = car["derniere_slide"]
    formes = {"bulles": "3 bulles", "mot_geant": "Mot en géant", "bouton": "Bouton"}
    modele = car.get("modele", "epure")
    return {
        "source": da.get("_source", ""),
        "duo": duo, "modele": MODELES.get(modele, modele), "modele_id": modele, "couleurs": couleurs,
        "pastille": f"{MODELES.get(modele, modele)} · {duo} · {couleurs}",
        "lignes": [
            ["Duo de polices", duo, True],
            ["Couleurs", couleurs, True],
            ["Modèle", MODELES.get(modele, modele), False],
            ["Couverture", cov.get(car["couverture"].get("place_titre"), "Titre en haut"), False],
            ["Slides photo", "Bord à bord · " + photos.get(car["slides_photo"].get("photos"), "Naturelles"), False],
            ["Dessins", "Nuit" if car["dessins"].get("fond") == "nuit" else "Jour", False],
            ["Dernière slide", formes.get(der.get("forme"), "3 bulles") if der.get("active", True) else "Aucune", False],
        ],
        "empreinte": hashlib.md5(json.dumps([da["commun"], da["carrousels"]], sort_keys=True).encode()).hexdigest()[:10],
    }


MODELES_CODES = {"epure", "cinema"}  # les autres (Collage, Carnet, Impact, Post texte) sortent en Épuré pour l'instant


def modele_rendu(da):
    m = da["carrousels"].get("modele", "epure")
    return m if m in MODELES_CODES else "epure"


def _clair(h):
    r, g, b = _rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.8


def css_da(da):
    """CSS posé APRÈS celui du moteur : la DA de SuperDA gagne, le reste du style Apple reste tel quel."""
    duo, c, car = da["commun"]["duo"], da["commun"]["couleurs"], da["carrousels"]
    p, s = duo.get("principale", {}), duo.get("secondaire", {})
    out = []
    for pol in (p, s):
        if pol.get("fichier"):
            f = os.path.join(SUPERDA, "fonts", pol["fichier"])
            if os.path.exists(f):
                style = "italic" if pol.get("italique") else "normal"
                out.append(f'@font-face{{font-family:"{pol["famille"]}";src:url("file://{f}");font-style:{style}}}')
    fam = p.get("famille", "-apple-system")
    if fam != "-apple-system":
        out.append(f'.t,.k,.sub,.step,.chat{{font-family:"{fam}",-apple-system,system-ui,sans-serif}}')
        out.append(".t{letter-spacing:-.02em}")
    out.append(f'.t{{font-weight:{p.get("graisse", 700)}}}')
    if p.get("majuscules"):
        out.append(".t{text-transform:uppercase}")
    if s.get("famille"):
        out.append(f'.t em{{font-family:"{s["famille"]}",serif;font-style:{"italic" if s.get("italique") else "normal"};'
                   f'font-weight:{s.get("graisse", 400)};letter-spacing:0}}')
    texte = c.get("texte") or apple.INK
    if _clair(texte):  # Épuré = fond blanc : un texte blanc (pensé pour Cinéma) deviendrait invisible
        texte = apple.INK
    out.append(f"body,.t{{color:{texte}}}")
    taille = car["slides_photo"].get("taille_texte")
    if taille:
        out.append(f".sub,.step{{font-size:{int(taille)}px}}")
    ph = car["slides_photo"].get("photos", "naturelles")
    filtre = {"sombres": "brightness(.78) contrast(1.06)", "noir_blanc": "grayscale(1) contrast(1.05)"}.get(ph)
    if filtre:
        out.append(f".card,.pop img{{filter:{filtre}}}")
    if not car["couverture"].get("fleche_glisse", True):
        out.append(".arrow{display:none}")
    if not car["couverture"].get("petite_ligne", True):
        out.append(".k{display:none}")
    if car["dessins"].get("fond") == "nuit":
        out.append(".s.nuit{background:#0B1424}.s.nuit .t{color:#fff}.s.nuit .sub,.s.nuit .step{color:#B8C2D6}")
    return "<style>" + "".join(out) + "</style>"


def couleurs_da(page, da):
    """Remplace la couleur principale du moteur (et ses déclinaisons) par l'accent de la DA, l'appoint par les touches."""
    c = da["commun"]["couleurs"]
    acc = c.get("accent") or (c.get("texte") or apple.INK)
    rep = {BLUE: acc, SKY: _mix(acc, "#FFFFFF", .35), PALE: _mix(acc, "#FFFFFF", .8), MIST: _mix(acc, "#FFFFFF", .92)}
    if c.get("touches", YELLOW) != YELLOW:
        rep[YELLOW] = c.get("touches") or _mix(acc, "#FFFFFF", .5)
    for a, b in rep.items():
        if a.upper() != b.upper():
            page = re.sub(re.escape(a), b, page, flags=re.I)
    return page


# Ajustement des titres dans la page (avant la capture) : un titre tient sur autant de lignes que de morceaux
# séparés par <br> (jamais 3 lignes pour 2 morceaux, jamais un mot seul) ; sinon il rétrécit, 64 px minimum.
AJUSTE = """<script>
document.querySelectorAll('.t').forEach(function (t) {
  var max = (t.innerHTML.match(/<br\\s*\\/?>/gi) || []).length + 1;
  var cs = getComputedStyle(t), taille = parseFloat(cs.fontSize);
  function lignes() { return Math.round(t.getBoundingClientRect().height / (parseFloat(getComputedStyle(t).lineHeight) || taille * 1.02)); }
  while (taille > 64 && (lignes() > max || t.scrollWidth > t.clientWidth + 2)) { taille -= 4; t.style.fontSize = taille + 'px'; }
});
</script>"""


# ---------------------------------------------------------------- typo : jamais de ponctuation seule en fin de ligne

_TAG = re.compile(r"(<[^>]+>|&[a-z#0-9]+;)")


def typo(txt):
    """Espaces insécables avant ? ! : ; » et après «, et les 2 derniers mots de chaque ligne collés (pas de mot seul)."""
    if not isinstance(txt, str) or not txt:
        return txt
    lignes = re.split(r"(<br\s*/?>)", txt)
    out = []
    for seg in lignes:
        if re.fullmatch(r"<br\s*/?>", seg):
            out.append(seg)
            continue
        seg = re.sub(r"\s+([?!:;»%])", "&nbsp;\\1", seg.strip())
        seg = re.sub(r"«\s+", "«&nbsp;", seg)
        seg = re.sub(r"(\d)\s+(?=\d{3}\b)", "\\1&nbsp;", seg)
        morceaux = _TAG.split(seg)
        if len(re.sub(r"<[^>]+>", " ", seg).split()) >= 3:  # colle les 2 derniers mots (dernier espace hors balises)
            for i in range(len(morceaux) - 1, -1, -1):
                m = morceaux[i]
                if _TAG.fullmatch(m or "") or not m.strip():
                    continue
                j = m.rfind(" ")
                if j >= 0:
                    morceaux[i] = m[:j] + "&nbsp;" + m[j + 1:]
                    break
        out.append("".join(morceaux))
    return "".join(out)


def typo_slide(s):
    s = dict(s)
    for k in ("title", "body", "kicker", "cta_q", "cta_line"):
        if k in s:
            s[k] = typo(s[k])
    if s.get("title"):
        s["title"] = modeles.propre(s["title"])  # vaut aussi pour le modèle Épuré
    if s.get("steps"):
        s["steps"] = [typo(x) for x in s["steps"]]
    return s


# ---------------------------------------------------------------- projets

def chemin(pid, *a):
    return os.path.join(PROJETS, pid, *a)


def lire(p, defaut=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return copy.deepcopy(defaut)


def ecrire(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(data, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def etat(pid):
    return lire(chemin(pid, "etat.json"), {})


def maj_etat(pid, **kw):
    e = etat(pid)
    e.update(kw, maj=time.time())
    ecrire(chemin(pid, "etat.json"), e)
    return e


def versions(pid):
    d = chemin(pid)
    vs = [int(n[1:]) for n in os.listdir(d) if re.fullmatch(r"v\d+", n)] if os.path.isdir(d) else []
    return sorted(vs)


def version_rendue(pid):
    vs = [v for v in versions(pid) if os.path.exists(chemin(pid, f"v{v}", "rendu.json"))]
    return vs[-1] if vs else 0


# ---------------------------------------------------------------- rendu

def da_photo_fin(da):
    der = da["carrousels"]["derniere_slide"]
    return der.get("active", True) and der.get("photo")


def _photo(p, nom, projet_dir, work):
    """Prépare une photo (recadrage + détourage du moteur) une seule fois par projet, puis la copie dans la version."""
    src = p["src"] if os.path.isabs(os.path.expanduser(p["src"])) else os.path.join(projet_dir, p["src"])
    p = dict(p, src=os.path.expanduser(src))
    cle = hashlib.md5(json.dumps(p, sort_keys=True).encode()).hexdigest()[:12]
    cache = os.path.join(projet_dir, "_cache")
    os.makedirs(cache, exist_ok=True)
    if not os.path.exists(os.path.join(cache, cle + ".json")):
        head = apple.prep_photo(p, cle, cache)
        ecrire(os.path.join(cache, cle + ".json"), {"head": head})
    shutil.copy(os.path.join(cache, cle + ".jpg"), os.path.join(work, nom + ".jpg"))
    shutil.copy(os.path.join(cache, cle + "-fg.png"), os.path.join(work, nom + "-fg.png"))
    return lire(os.path.join(cache, cle + ".json"))["head"]


def visage(work, nom):
    """Rond de la dernière slide (28/10, photo « mal centrée ») : trouve le visage de la personne détourée avec Vision (intégré
    à macOS, visage.swift compilé une fois) -> [cx, cy, D] en px sur la photo préparée (1080 x 1440), D = rond tête + épaules.
    None si aucun visage : le rond garde alors le cadrage de SuperDA."""
    exe = os.path.join(ICI, "_outils", "visage")
    if not os.path.exists(exe):
        os.makedirs(os.path.dirname(exe), exist_ok=True)
        subprocess.run(["swiftc", "-O", os.path.join(ICI, "visage.swift"), "-o", exe], capture_output=True, timeout=300)
    jpg = os.path.join(work, nom + ".jpg")
    try:
        sortie = subprocess.run([exe, jpg], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return None
    faces = [[float(v) for v in l.split()] for l in sortie.splitlines() if len(l.split()) == 4]
    if not faces:
        return None
    from PIL import Image
    im = Image.open(os.path.join(work, nom + "-fg.png"))
    wi, hi = im.size
    alpha = im.split()[-1]

    def sur_la_personne(f):  # le visage de la personne détourée, pas celui d'une affiche ou de l'écran derrière
        return alpha.getpixel((min(int((f[0] + f[2] / 2) * wi), wi - 1), min(int((f[1] + f[3] / 2) * hi), hi - 1))) > 128
    x, y, w, h = max(faces, key=lambda f: (sur_la_personne(f), f[2]))
    fw = w * wi
    return [round((x + w / 2) * wi, 1), round((y + h / 2) * hi + 0.3 * fw, 1), round(2.6 * fw, 1)]


def capture(page, png):
    """Chrome sans fenêtre. Son code de sortie ment parfois (2 alors que l'image est écrite) : on juge sur l'image."""
    for _ in range(2):
        if os.path.exists(png):
            os.remove(png)
        subprocess.run([apple.CHROME, "--headless=new", "--use-mock-keychain", "--disable-gpu", "--hide-scrollbars",
                        "--virtual-time-budget=6000", f"--window-size={W},{H}", f"--screenshot={png}", f"file://{page}"],
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=120)
        if os.path.exists(png) and os.path.getsize(png) > 10000:
            return
    raise RuntimeError(f"Chrome n'a pas produit {os.path.basename(png)}")


def rendre(pid, v, sur_slide=None):
    """Rend la version v slide par slide avec le vrai moteur. sur_slide(i, n) après chaque PNG."""
    pdir, vdir = chemin(pid), chemin(pid, f"v{v}")
    desc = lire(os.path.join(vdir, "description.json"))
    da = lire_da()
    work = os.path.join(vdir, "_sources")
    os.makedirs(work, exist_ok=True)
    slides = desc["slides"]
    n = len(slides)
    for f in os.listdir(vdir):
        if re.fullmatch(r"slide-\d+\.png", f):
            os.remove(os.path.join(vdir, f))
    heads = {nom: _photo(p, nom, pdir, work) for nom, p in desc.get("photos", {}).items()}
    fin = slides[-1] if slides else {}
    visages = ({nom: visage(work, nom) for nom in heads}
               if fin.get("cta") and da_photo_fin(da) and modele_rendu(da) == "cinema" else {})
    modele = modele_rendu(da)
    extra = css_da(da)
    nuit = da["carrousels"]["dessins"].get("fond") == "nuit"
    for i, s in enumerate(slides, 1):
        if modele == "cinema":
            page = (modeles.css_cinema(da, SUPERDA) + modeles.slide_cinema(typo_slide(s), i == n, {k: k for k in heads}, da, pdir, visages)
                    + "</body></html>")
        else:  # Épuré = le moteur Apple du skill tel quel, DA posée par-dessus
            corps = apple.slide(typo_slide(s), i == n, heads, pdir)
            if nuit and s["type"] == "art":
                corps = corps.replace('<div class="s">', '<div class="s nuit">', 1)
            page = apple.CSS + extra + corps + "</body></html>"
        page = couleurs_da(page.replace("</body></html>", AJUSTE + "</body></html>"), da)
        hp = os.path.join(work, f"slide-{i}.html")
        open(hp, "w").write(page)
        capture(hp, os.path.join(vdir, f"slide-{i}.png"))
        if sur_slide:
            sur_slide(i, n)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-start_number", "1", "-i", os.path.join(vdir, "slide-%d.png"),
                    "-vf", f"scale=540:720,pad=556:736:8:8:color=0xDDDDDD,tile={min(n, 4)}x{(n + 3) // 4}",
                    "-frames:v", "1", os.path.join(vdir, "00-planche.png")], check=True)
    leg = legendes(desc)
    with open(os.path.join(vdir, "legendes.txt"), "w") as f:
        for r in RESEAUX:
            f.write(f"{NOMS_RESEAUX[r]}\n{leg[r]}\n\n")
    ecrire(os.path.join(vdir, "rendu.json"), {"slides": n, "da": resume_da(da)["empreinte"], "modele": modele, "fini": time.time()})
    return n


def legendes(desc):
    """Une légende par réseau (1-2 phrases, 0 hashtag : règle legende-courte). Repli : la légende commune."""
    base = desc.get("caption", "")
    leg = desc.get("legendes") or {}
    return {r: (leg.get(r) or base).strip() for r in RESEAUX}


def livraison(pid):
    """Zip des images + 4 légendes de la dernière version, rangé dans le projet puis copié dans Téléchargements."""
    v = version_rendue(pid)
    vdir = chemin(pid, f"v{v}")
    titre = re.sub(r"[^\w-]+", "-", (etat(pid).get("titre") or pid)).strip("-").lower()
    nom = f"carrousel-{titre}-v{v}.zip"
    z = chemin(pid, nom)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        n = lire(os.path.join(vdir, "rendu.json"))["slides"]
        for i in range(1, n + 1):
            zf.write(os.path.join(vdir, f"slide-{i}.png"), f"slide-{i:02d}.png")
        zf.write(os.path.join(vdir, "legendes.txt"), "legendes.txt")
    dl = os.path.expanduser("~/Downloads")
    shutil.copy(z, os.path.join(dl, nom))
    return os.path.join(dl, nom)


def texte_html(t):
    return html.unescape(re.sub(r"<[^>]+>", " ", t or "")).replace("\xa0", " ").strip()
