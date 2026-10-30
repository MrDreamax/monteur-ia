"""Monte un carrousel Instagram 1080x1440 (3:4) au modèle validé le 16/10 (v4 « Quand tous les coachs se ressemblent »)
à partir d'un fichier de description, via Open Carrusel (localhost:3210), puis exporte les PNG + planche + légende.
  python3 carrousel.py spec.json
Le fichier spec : voir ../exemples/exemple-v4.json. Types de slide :
  cover : photo + mot géant derrière la tête + 1 ligne en majuscules (couverture validée)
  photo : vraie photo étalonnée (prep.py) + titre serif + 1 phrase
  art   : illustration 2D (art.py "art" ou fichier "svg") + titre + 1 phrase | "steps" (liste 1-2-3) | "cta" (mot-clé)
"style": "apple" (validé le 22/10/2026) : rendu local par apple.py, sans Open Carrusel. Voir ../exemples/exemple-apple.json.
Pas de numéro de slide, pas de @, flèche « swipe » sur toutes sauf la dernière.
"""
import io
import json
import os
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from art import ARTS, BLUE, NAVY, WHITE  # noqa: E402
import apple  # noqa: E402

API = "http://localhost:3210/api"

BASE = f"""<style>
.s{{position:relative;width:1080px;height:1440px;overflow:hidden;font-family:"Montserrat";}}
.light{{background:{WHITE};color:{NAVY};}}
.dark{{background:#0B162B;color:{WHITE};}}
.ph{{position:absolute;inset:0;width:1080px;height:1440px;object-fit:cover;}}
.veil{{position:absolute;left:0;right:0;bottom:0;height:640px;background:linear-gradient(180deg,rgba(11,22,43,0) 0%,rgba(11,22,43,.82) 45%,rgba(11,22,43,.95) 100%);z-index:2;}}
.swp{{position:absolute;right:84px;bottom:84px;width:64px;height:2px;background:{BLUE};z-index:5;}}
.swp:after{{content:"";position:absolute;right:0;top:-6px;width:12px;height:12px;border-top:2px solid {BLUE};border-right:2px solid {BLUE};transform:rotate(45deg);}}
.dark .swp{{background:{WHITE};}} .dark .swp:after{{border-color:{WHITE};}}
.txt{{position:absolute;left:84px;right:84px;bottom:150px;z-index:4;}}
.serif{{font-family:"Instrument Serif";font-style:italic;font-weight:400;line-height:1;letter-spacing:-1px;}}
.caps{{font-weight:700;text-transform:uppercase;letter-spacing:5px;line-height:1.1;}}
.body{{font-weight:500;font-size:42px;line-height:1.38;margin-top:26px;}}
.light .body{{color:rgba(19,37,63,.82);}} .dark .body{{color:rgba(255,255,255,.9);}}
.rule{{width:64px;height:3px;background:{BLUE};margin-bottom:32px;}}
.dark .rule{{background:#6FB1E3;}}
.shadow{{text-shadow:0 4px 28px rgba(0,0,0,.45);}}
.art{{position:absolute;left:0;top:0;width:1080px;height:900px;}}
</style>"""

SWIPE = '<div class="swp"></div>'


def steps_html(items):
    return "".join(f'<div style="display:flex;gap:24px;align-items:baseline;margin-top:18px"><div class="serif" style="font-size:64px;color:{BLUE};min-width:40px">{i}</div>'
                   f'<div class="body" style="margin-top:0">{t}</div></div>' for i, t in enumerate(items, start=1))


def cta_html(word, line):
    return (f'<div style="display:flex;align-items:center;gap:26px;margin-top:36px"><div class="caps" style="font-size:40px">Commente</div>'
            f'<div style="background:{BLUE};padding:18px 32px 14px;border-radius:12px"><div class="caps" style="font-size:62px;font-weight:800;letter-spacing:8px;line-height:1;color:#fff">{word}</div></div></div>'
            f'<div class="body" style="margin-top:22px">{line}</div>')


def text_block(s):
    body = f'<div class="body">{s["body"]}</div>' if s.get("body") else ""
    if s.get("steps"):
        body += steps_html(s["steps"])
    if s.get("cta"):
        body += cta_html(s["cta"], s.get("cta_line", "Je t’envoie mon doc."))
    return f'<div class="rule"></div><div class="serif" style="font-size:{s.get("title_size", 96)}px">{s["title"]}</div>{body}'


def render(s, last, spec_dir):
    arrow = "" if last else SWIPE
    if s["type"] == "cover":
        p = s["photo"]
        return (f'{BASE}<div class="s dark"><img class="ph" src="/uploads/{p}-bg.jpg"><div class="veil" style="height:520px"></div>'
                f'<div class="serif shadow" style="position:absolute;left:0;right:0;top:{s.get("word_top", 182)}px;text-align:center;font-size:{s.get("word_size", 270)}px;color:#fff;z-index:2">{s["word"]}</div>'
                f'<img class="ph" src="/uploads/{p}-fg.png" style="z-index:3">'
                f'<div class="caps shadow" style="position:absolute;left:72px;right:72px;bottom:170px;text-align:center;font-size:{s.get("caps_size", 54)}px;z-index:4">{s["caps"]}</div>'
                f'{arrow}</div>')
    if s["type"] == "photo":
        return (f'{BASE}<div class="s dark"><img class="ph" src="/uploads/{s["photo"]}-bg.jpg"><div class="veil"></div>'
                f'<div class="txt shadow">{text_block(s)}</div>{arrow}</div>')
    if s["type"] == "art":
        if s.get("svg"):
            art = open(os.path.join(spec_dir, os.path.expanduser(s["svg"]))).read()
        else:
            art = ARTS[s["art"]](**s.get("args", {}))
        return f'{BASE}<div class="s light">{art}<div class="txt">{text_block(s)}</div>{arrow}</div>'
    raise ValueError(f"type de slide inconnu : {s['type']}")


def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = r.read()
    return out if raw else json.loads(out.decode())


def main():
    spec_path = os.path.abspath(sys.argv[1])
    spec, spec_dir = json.load(open(spec_path)), os.path.dirname(spec_path)
    if spec.get("style") == "apple":  # style Apple (22/10/2026) : rendu local, sans Open Carrusel
        return finish(spec, apple.build(spec, spec_dir, os.path.expanduser(spec["out"])))
    try:
        call("GET", "/brand")
    except Exception:
        sys.exit("Open Carrusel ne répond pas sur localhost:3210. Lance-le : preview_start « open-carrusel » "
                 "(.claude/launch.json du dossier de travail) ou, en dernier recours, `cd ~/open-carrusel && npm run dev -- -p 3210` en arrière-plan.")
    here = os.path.dirname(os.path.abspath(__file__))
    for name, p in spec.get("photos", {}).items():  # vraies photos : recadrage + étalonnage + détourage
        args = [sys.executable, os.path.join(here, "prep.py"), p["src"], name]
        for k in ("fx", "fy", "zoom", "bright", "grad"):
            if k in p:
                args += [f"--{k}", str(p[k])]
        subprocess.run(args, check=True)
    slides = spec["slides"]
    htmls = [render(s, i == len(slides) - 1, spec_dir) for i, s in enumerate(slides)]
    cid = spec.get("id")
    if cid:
        car = call("GET", f"/carousels/{cid}")
        for sl in car["slides"]:
            call("DELETE", f"/carousels/{cid}/slides/{sl['id']}")
    else:
        cid = call("POST", "/carousels", {"name": spec["name"], "aspectRatio": "3:4"})["id"]
    for h in htmls:
        call("POST", f"/carousels/{cid}/slides", {"html": h})
    call("PUT", f"/carousels/{cid}/caption", {"caption": spec.get("caption", ""), "hashtags": spec.get("hashtags", [])})

    out = os.path.expanduser(spec["out"])
    os.makedirs(out, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(call("POST", f"/carousels/{cid}/export", raw=True))).extractall(out)
    spec["id"] = cid
    finish(spec, len(slides))


def finish(spec, n):
    """Planche + légende + copie de la description dans le dossier de sortie."""
    out = os.path.expanduser(spec["out"])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-start_number", "1", "-i", os.path.join(out, "slide-%d.png"),
                    "-vf", f"scale=540:720,pad=556:736:8:8:color=0x888888,tile=4x{(n + 3) // 4}",
                    "-frames:v", "1", os.path.join(out, "00-planche.png")], check=True)
    with open(os.path.join(out, "legende.txt"), "w") as f:
        f.write(spec.get("caption", "") + "\n\n" + " ".join("#" + h for h in spec.get("hashtags", [])) + "\n")
    json.dump(spec, open(os.path.join(out, "spec.json"), "w"), ensure_ascii=False, indent=1)
    print(spec.get("id", "local"), "->", out)


if __name__ == "__main__":
    main()
