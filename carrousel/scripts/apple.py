"""Style « Apple » des carrousels (validé par l'utilisateur le 22/10/2026, 2 rounds), appelé par carrousel.py quand
la description contient "style": "apple". Rendu en local avec Chrome (pas besoin d'Open Carrusel).
  Fond blanc, titres SF Pro gras serrés, sous-titre gris, notes manuscrites Kalam couleur principale.
  Photo BORD À BORD (touche les bords gauche et droit) ; la personne détourée dépasse au-dessus : seulement les cheveux.
  Dessins sur le cercle clair d'art.py. Dernière slide : 3 bulles de message (question / MOT / réponse).
Types de slide :
  cover : "kicker" (petit titre), "title", "photo", "note" facultative
  photo : "photo", "title", "body" | "steps" ; "pop": false = photo sans dépassement (sujet petit dans l'image)
  art   : "art" (art.py) ou "svg", "title", "body" | "steps" | "cta" (+ "cta_q", "cta_line")
Commun : "note" + "note_pos" ({"top":..,"left"|"right":..}) pour une note manuscrite de 3 à 5 mots.
"""
import os
import subprocess

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps
from scipy import ndimage

from art import ARTS, BLUE

W, H = 1080, 1440
MODEL = os.path.expanduser("~/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx")  # modèle du skill supermonteur
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HAIR = 110  # pixels de cheveux qui dépassent au-dessus de la photo (choix de l'utilisateur : « jusqu'aux cheveux »)
INK, MUTE, GRAY = "#1D1D1F", "#6E6E73", "#E9E9EB"

CSS = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Kalam:wght@400;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0}}
body{{margin:0;background:#fff;font-family:-apple-system,"SF Pro Display",system-ui,sans-serif;-webkit-font-smoothing:antialiased;color:{INK}}}
.s{{width:{W}px;height:{H}px;position:relative;overflow:hidden;background:#fff}}
.t{{font-weight:700;letter-spacing:-.035em;line-height:1.02}}
.k{{font-size:34px;font-weight:600;color:{BLUE}}}
.sub{{font-size:40px;color:{MUTE};margin-top:24px;letter-spacing:-.01em;line-height:1.3}}
.ctr{{text-align:center}}
.note{{position:absolute;font-family:Kalam,cursive;color:{BLUE};font-size:44px;transform:rotate(-4deg);z-index:5;white-space:nowrap}}
.arrow{{position:absolute;right:56px;bottom:52px;font-size:44px;color:#86868B}}
.card{{position:absolute;left:0;width:{W}px;background-repeat:no-repeat;background-size:{W}px {H}px}}
.pop{{position:absolute;left:0;top:0;width:{W}px;overflow:hidden}}
.pop img{{position:absolute;left:0;width:{W}px;height:{H}px}}
.art{{display:block;width:{W}px;height:900px}}
.steps{{display:inline-flex;flex-direction:column;gap:22px;text-align:left;margin-top:30px}}
.step{{display:flex;gap:24px;align-items:center;font-size:40px;letter-spacing:-.01em}}
.n{{flex:0 0 60px;height:60px;border-radius:50%;background:{BLUE};color:#fff;font-weight:700;font-size:30px;display:flex;align-items:center;justify-content:center}}
.chat{{position:absolute;left:90px;right:90px;display:flex;flex-direction:column;gap:22px;font-size:42px;line-height:1.25}}
.b{{padding:22px 38px;max-width:780px}}
.them{{align-self:flex-start;background:{GRAY};border-radius:40px 40px 40px 12px}}
.me{{align-self:flex-end;background:#0A84FF;color:#fff;font-weight:600;border-radius:40px 40px 12px 40px}}
</style></head><body>"""


def prep_photo(p, name, work):
    """Recadrage 3:4 aux teintes naturelles + détourage local (RVM). Renvoie le haut de la tête (px)."""
    im = ImageOps.exif_transpose(Image.open(p["src"])).convert("RGB")
    iw, ih = im.size
    cw = min(iw, ih * 3 / 4) / p.get("zoom", 1.0)
    ch = cw * 4 / 3
    cx = min(max(p.get("fx", 0.5) * iw, cw / 2), iw - cw / 2)
    cy = min(max(p.get("fy", 0.45) * ih, ch / 2), ih - ch / 2)
    im = im.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.LANCZOS)
    im.save(f"{work}/{name}.jpg", quality=92)
    rgb = np.asarray(im, np.float32) / 255
    sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    x = rgb.transpose(2, 0, 1)[None]
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
    for _ in range(4):  # même image 4 fois pour stabiliser l'état récurrent de RVM
        _, pha, *rec = sess.run(None, {"src": x, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                       "downsample_ratio": np.array([0.25], np.float32)})
    alpha = np.where(pha[0, 0] < 0.15, 0, pha[0, 0])  # coupe le voile de bruit autour du sujet
    lab, n = ndimage.label(alpha > 0.5)
    if n > 1:  # ne garde que la plus grande tache (la personne) : pas de traînées isolées au-dessus de la photo
        keep = np.argmax(ndimage.sum(np.ones_like(alpha), lab, range(1, n + 1))) + 1
        alpha = alpha * ndimage.binary_dilation(lab == keep, iterations=6)
    ys = np.where(alpha > 0.5)[0]
    head = int(ys.min()) if len(ys) else 0
    # au-dessus de la photo, seule la tête dépasse : on garde la tache qui part du haut du crâne et on efface
    # mains, doigts et bruit qui ne la touchent pas (sans couper les côtés des cheveux)
    cut = head + HAIR + 5
    lab, _ = ndimage.label(alpha[:cut] > 0.5)
    top = lab[head][alpha[head] > 0.5]
    if len(top):
        alpha[:cut] *= ndimage.binary_dilation(lab == np.bincount(top).argmax(), iterations=4)
    Image.fromarray((np.dstack([rgb, alpha]) * 255).astype(np.uint8)).save(f"{work}/{name}-fg.png")
    return head


def photo_block(name, head, top, h, pop=True):
    """Photo bord à bord de `top` à `top+h` ; si pop, les cheveux détourés dépassent de HAIR px au-dessus."""
    off = min(max(head + HAIR, 0), H - h) if pop else max(0, min(H - h, int(head - 120)))
    html = f'<div class="card" style="top:{top}px;height:{h}px;background-image:url({name}.jpg);background-position:0 {-off}px"></div>'
    if pop:  # le détourage ne sert qu'AU-DESSUS de la photo : dedans, la vraie photo reste intacte
        html += f'<div class="pop" style="height:{top}px"><img src="{name}-fg.png" style="top:{top - off}px"></div>'
    return html


def text(s, size):
    out = f'<h2 class="t" style="font-size:{s.get("title_size", size)}px">{s["title"]}</h2>'
    if s.get("body"):
        out += f'<p class="sub">{s["body"]}</p>'
    if s.get("steps"):
        out += '<div class="steps">' + "".join(f'<div class="step"><div class="n">{i}</div><div>{t}</div></div>'
                                              for i, t in enumerate(s["steps"], 1)) + "</div>"
    return out


def note(s):
    if not s.get("note"):
        return ""
    pos = ";".join(f"{k}:{v}px" for k, v in s.get("note_pos", {"top": 470, "right": 60}).items())
    return f'<div class="note" style="{pos}">{s["note"]}</div>'


def slide(s, last, heads, spec_dir):
    arrow = "" if last else '<div class="arrow">→</div>'
    t = s["type"]
    if t == "cover":
        p = s["photo"]
        kicker = f'<div class="k">{s["kicker"]}</div>' if s.get("kicker") else ""
        inner = (f'<div class="ctr" style="padding-top:110px">{kicker}'
                 f'<h1 class="t" style="font-size:{s.get("title_size", 112)}px;margin-top:18px">{s["title"]}</h1></div>'
                 + photo_block(p, heads[p], s.get("photo_top", 620), 700))
    elif t == "photo":
        p = s["photo"]
        pop = s.get("pop", True)  # sans dépassement (sujet petit dans l'image) : la photo part du haut de la slide
        inner = (photo_block(p, heads[p], 300 if pop else 0, 700 if pop else 1000, pop)
                 + f'<div class="ctr" style="position:absolute;left:60px;right:60px;top:{1050 if pop else 1060}px">{text(s, 92)}</div>')
    elif t == "art":
        if s.get("svg"):
            art = open(os.path.join(spec_dir, os.path.expanduser(s["svg"]))).read()
        else:
            art = ARTS[s["art"]](**s.get("args", {}))
        if s.get("cta"):  # dernière slide : dessin plus petit + 3 bulles de message
            art = art.replace('<svg class="art"', '<svg class="art" style="height:660px"', 1)
            q = s.get("cta_q", "Tu veux la ressource ?")
            inner = (art + f'<div class="ctr">{text(s, 84)}</div>'
                     f'<div class="chat" style="top:930px"><div class="b them">{q}</div><div class="b me">{s["cta"].upper()}</div>'
                     f'<div class="b them">{s.get("cta_line", "Envoyé en DM. Bonne lecture.")}</div></div>'
                     f'<div class="note" style="top:1070px;left:110px">écris ça en commentaire →</div>')
        else:
            inner = art + f'<div class="ctr" style="padding:0 60px">{text(s, 104)}</div>'
    else:
        raise ValueError(f"type de slide inconnu : {t}")
    return f'<div class="s">{inner}{note(s)}{arrow}</div>'


def build(spec, spec_dir, out):
    work = os.path.join(out, "_sources")
    os.makedirs(work, exist_ok=True)
    heads = {n: prep_photo(p, n, work) for n, p in spec.get("photos", {}).items()}
    slides = spec["slides"]
    for i, s in enumerate(slides, 1):
        page = os.path.join(work, f"slide-{i}.html")
        with open(page, "w") as f:
            f.write(CSS + slide(s, i == len(slides), heads, spec_dir) + "</body></html>")
        subprocess.run([CHROME, "--headless=new", "--use-mock-keychain", "--disable-gpu", "--hide-scrollbars",
                        "--virtual-time-budget=8000", f"--window-size={W},{H}", f"--screenshot={out}/slide-{i}.png",
                        f"file://{page}"], stderr=subprocess.DEVNULL, check=True)
    return len(slides)
