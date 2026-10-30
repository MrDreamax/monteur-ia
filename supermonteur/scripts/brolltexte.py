"""FAMILLE « B-ROLL + TEXTE » (16/10/2026) : 1 plan (2 max) de 5-7 s, du texte AU-DESSUS DE LA TÊTE, musique, zéro voix.
  python3 brolltexte.py plan.json            -> final.mp4 + legende.txt (+ text.png pour contrôle)
plan.json :
  "brolls": [{"src": "<chemin absolu>", "from": 1.33 | "auto", "dur": 6}]   1 ou 2 plans, total 5-7 s
  "text": {"lines": ["Tu n'es pas nul en vidéo.", "Ton message est flou."], "strong": "flou", "cta": "Commente POSITION"}
           2 lignes (3 MAX), chacune tient sur UNE ligne ; "strong" = mot fort en serif italique ; "cta" FACULTATIF
  OU (29/10, mode TABLEAU, repris d'un reel « No digas / Mejor di ») :
  "text": {"title": "Parle mieux pour vendre", "head": ["Ne dis pas", "Dis plutôt"], "rows": [["Je pense que", "Je sais que"], ...]}
           3 à 9 lignes ; colonne gauche fine, flèche, colonne droite en gras ; posé en haut de la zone sûre, voile auto
           "accent": "#FFD60A" facultatif = titre + colonne droite (en-tête compris) en couleur (29/10 : jaune demandé par l’utilisateur)
  OU (29/10, mode NUAGE, repris d'un reel « I'm a business owner but I'm also a… » + 20 métiers autour) :
  "text": {"lines": ["Tu es coach", "mais aussi"], "strong": "coach", "words": ["Monteur", "Vendeur", ...], "accent": "#FFD60A"}
           lines = le texte AU CENTRE (MAJUSCULES, gras, TOUT en couleur "accent", défaut jaune #FFD60A ; "strong" ignoré) ;
           words = 8 à 30 mots courts (MAJUSCULES, éparpillés au hasard sur tout l'écran) qui APPARAISSENT UN PAR UN autour (de plus en plus vite), jamais sur le visage
           ni sur le texte du centre, dans la zone sûre (scripts/nuage.mjs) ; "start" / "end" facultatifs = fenêtre
           d'apparition en part de la durée (défaut 0.35 -> 0.85) ; sans visage, texte du centre au milieu de l'écran
           "slots": "ref/reference.mp4" facultatif = place + instant de chaque mot repris d'un reel de référence
           (nuage_ref.py) : même disposition (resserrée dans la zone Insta), même ordre, même rythme, à partir de "at"
           "at": 4.1 facultatif = TOUS les mots apparaissent d'un coup à cette seconde (sur un temps fort de la musique)
  "music": {..., "tempo": 1.06}   facultatif : accélère la musique (hauteur gardée) ; un temps fort à m s du morceau
           tombe à (m - from) / tempo dans la vidéo
  "sombre": 0.3     facultatif (0 à 0.6) : assombrit tout le plan (29/10 : « assombris le tout »)
  "style": "da" (défaut, VALIDÉ : police de la DA en majuscules blanches + mot fort serif italique, ombre douce)
           | "natif" (bandeau blanc arrondi, texte noir, casse mixte = l'outil texte d'Instagram)
  "y": 470          facultatif : force le centre du bloc texte (sinon calculé au-dessus de la tête)
  "music": {"src": "<wav Epidemic coupé à la durée, loopable>", "from": 0}   "from" facultatif : départ dans le morceau (s)
  "caption": "..."  la légende du post (écrite par l'étape Copywriter)
  "da": "da/<client>.json"   facultatif (défaut : config.json « client », sinon la DA de l'utilisateur : Brain/00-Moi/reglages/da-montage.json, sinon da/exemple.json)
Règles 16/10 :
- Texte TOUJOURS au-dessus de la tête. Le script mesure le haut de la tête sur tout le plan (5e centile = quand elle est
  la plus haute) ; pas assez de place -> le plan descend et le haut de l'image est prolongé en fondu (« place rajoutée »
  validée en montage viral). Pas de visage (de dos, mains, lieu) -> texte en haut de la zone sûre.
- CTA facultatif ; s'il y en a un : EN BAS, séparé du texte (bloc bas à 1 420 px max).
- Jamais de ponctuation en fin de texte ni de CTA (retirée toute seule, l'emoji final reste).
- Fond trop clair ou trop chargé sous le texte -> voile noir léger en haut (comme les titres-questions), tout seul ;
  "veil": true / false dans plan.json pour forcer.
- Zones mortes Insta : 270-1480 px en hauteur, 120-960 px en largeur.
"""
import json, os, subprocess, sys
import numpy as np

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "scripts" \
    else os.path.expanduser("~/.claude/skills/supermonteur")
plan_p = sys.argv[1]
here = os.path.dirname(os.path.abspath(plan_p))
plan = json.load(open(plan_p))
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import reglages  # config.json du skill + réglages de cette machine (Brain)
from sdr import sdr, BT709
CFG = reglages.config()
_da = os.path.expanduser(plan.get("da") or (CFG.get("client") and f"da/{CFG['client']}.json") or reglages.da_perso())
DA = json.load(open(_da if os.path.isabs(_da) else os.path.join(SKILL, _da)))
W, H, FPS = 1080, 1920, 30
TOP, BOTTOM, LEFT, RIGHT = 270, 1480, 120, 960      # zones mortes Instagram (16/10)
AIR, SMAX, FADE = 70, 480, 260                     # air entre texte et tête ; descente max du plan ; fondu (viral.py)
run = lambda *a: subprocess.run(a, check=True)
P = lambda n: os.path.join(here, n)

# --- 1. plans : coupés, recadrés 1080x1920, bruts, enchaînés en coupe franche ---
parts = []
for i, b in enumerate(plan["brolls"]):
    b["src"] = sdr(b["src"], here)   # 25/10 : plan iPhone HDR -> SDR avant la coupe
    start = b.get("from", 0)
    if start == "auto":
        out = subprocess.check_output(["python3", os.path.join(SKILL, "scripts/broll.py"), "steady", b["src"], str(b["dur"])]).decode()
        start = float(out.split("from ")[1].split("s")[0])
    p = P(f"_b{i}.mp4")
    run("ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", b["src"], "-t", str(b["dur"]), "-map", "0:v:0", "-an",
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-crf", "14", "-preset", "slow", *BT709, p)
    parts.append(p)
open(P("_list.txt"), "w").write("".join(f"file '{p}'\n" for p in parts))
run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", P("_list.txt"), "-c", "copy", P("_broll.mp4"))
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", P("_broll.mp4")]))


def head_top(src):
    """Haut de la tête (cheveux compris, px) au moment où elle est la plus haute ; None si aucun visage."""
    b = face_box(src)
    return b and b[1]


def face_box(src, t0=0.0):
    """29/10 : boîte du visage sur tout le plan [x0, haut de tête, x1, menton] (px 1080x1920) ; None si aucun visage."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    w, h = 540, 960
    raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vf", f"fps=4,scale={w}:{h}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)[int(t0 * 4):]   # t0 : seulement à partir de cette seconde
    det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=os.path.join(SKILL, "models", "face_landmarker.task")),
        running_mode=vision.RunningMode.IMAGE))
    bx = []
    for f in fr:
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)))
        if r.face_landmarks:
            L = r.face_landmarks[0]; xs = [q.x for q in L]
            bx.append((min(xs) * W, L[10].y * H - 0.45 * (L[152].y - L[10].y) * H, max(xs) * W, L[152].y * H))
    if len(bx) < len(fr) * 0.3: return None
    a = np.array(bx)
    return [int(np.percentile(a[:, 0], 5)), int(np.percentile(a[:, 1], 5)), int(np.percentile(a[:, 2], 95)), int(np.percentile(a[:, 3], 95))]


# --- 2. texte : HTML -> PNG transparent 1080x1920 (vraies polices, emoji Apple) ---
t = plan["text"]; style = plan.get("style", "da")
import re
def nopunct(x):
    """16/10 : pas de ponctuation à la fin d'un texte (l'emoji final reste)."""
    emo = re.search(r"[\s\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F]*$", x).group(0)
    core = x[:len(x) - len(emo)] if emo else x
    return re.sub(r"[\s.,;:!?…«»\"']+$", "", core) + (" " + emo.strip() if emo.strip() else "")
table = "rows" in t
cloud = bool(t.get("words"))
if cloud and not 8 <= len(t["words"]) <= 30: sys.exit(f"!! nuage de {len(t['words'])} mots : 8 à 30.")
lines, cta = [nopunct(l) for l in t.get("lines", [])], nopunct(t.get("cta", ""))
if cloud:                                           # 29/10 (l’utilisateur : « Tu es coach mais tu es aussi... ») : les points de suspension restent
    lines = [re.sub(r"\.{3}$", "…", l.strip()) if l.strip().endswith(("...", "…")) else nopunct(l) for l in t["lines"]]
if table and not 3 <= len(t["rows"]) <= 9: sys.exit(f"!! tableau de {len(t['rows'])} lignes : 3 à 9.")
if len(lines) > 3: sys.exit(f"!! {len(lines)} lignes de texte : 2 conseillées, 3 MAX. Raccourcir.")
fonts = os.path.join(SKILL, "fonts")
strong = t.get("strong", "")
isemo = lambda c: ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF or ord(c) == 0xFE0F


def row_html(s):
    if cloud:                                       # nuage (29/10, comme la réf) : casse normale, tout en couleur, pas de mot fort à part
        return f'<div class="row"><span class="l">{s.upper()}</span></div>'
    if style == "da" and strong and strong in s:
        a, z = s.split(strong, 1)
        txt = "".join(c for c in z if not isemo(c)).strip(); emo = "".join(c for c in z if isemo(c))
        glue = txt if txt and not txt[0].isalnum() else ""          # ponctuation collée au mot fort
        rest = txt[len(glue):].strip() if glue else txt              # des mots après le mot fort = police normale
        mixed = bool(a.strip() or rest)
        h = (f'<span class="l">{a.strip().upper()} </span>' if a.strip() else "") + \
            f'<span class="s{" m" if mixed else ""}">{strong}{glue}</span>' + \
            (f'<span class="l"> {rest.upper()}</span>' if rest else "")
        return f'<div class="row">{h}' + (f'<span class="e">{emo}</span>' if emo else "") + "</div>"
    return f'<div class="row"><span class="l">{s.upper() if style == "da" else s}</span></div>'


def rows_html():
    h = [row_html(s) for s in lines]
    if cloud: h = [x.replace('<div class="row">', '<div class="row acc">', 1) for x in h]   # nuage : tout le texte du centre en couleur (29/10)
    return "".join(h)


css = f"""
@font-face{{font-family:Mont;src:url("file://{fonts}/{DA['fonts']['sans']}");font-weight:100 900}}
@font-face{{font-family:Serif;src:url("file://{fonts}/{DA['fonts']['serif']}");font-style:italic}}
html,body{{margin:0;width:{W}px;height:{H}px;background:transparent}}
.blk{{position:absolute;left:{LEFT}px;width:{RIGHT-LEFT}px;text-align:center}}
.row,.cta{{display:block;white-space:nowrap}}
"""
if style == "natif":
    css += """
.l,.c{font-family:Mont,'Apple Color Emoji';font-weight:600;font-size:50px;line-height:1.32;color:#111;background:#fff;
   padding:4px 22px 6px;border-radius:14px}
.row{margin:0 0 -2px}
"""
else:
    acc = DA["colors"].get("text", "#fff")
    sh = "text-shadow:0 2px 6px rgba(0,0,0,.55),0 0 28px rgba(0,0,0,.45)"
    css += f"""
.l{{font-family:Mont,'Apple Color Emoji';font-weight:700;font-size:56px;letter-spacing:.5px;line-height:1.18;color:{acc};{sh}}}
.s{{font-family:Serif;font-style:italic;font-size:124px;line-height:1.0;color:{acc};{sh}}}
.s.m{{font-size:96px}}
.e{{font-family:'Apple Color Emoji';font-size:64px;margin-left:10px;vertical-align:12px}}
.c{{font-family:Mont,'Apple Color Emoji';font-weight:600;font-size:42px;letter-spacing:.5px;color:{acc};{sh}}}
.row{{margin:0 0 6px}}
.acc .l,.acc .s{{color:{t.get("accent") or "#FFD60A"}}}
.acc .l{{font-weight:800;font-size:78px;letter-spacing:0;line-height:1.08}}
.w{{position:absolute;white-space:nowrap;font-family:Mont,'Apple Color Emoji';font-weight:800;letter-spacing:-.5px;color:{acc};{sh};visibility:hidden}}
"""


def table_html():
    """29/10 : titre + 2 colonnes (« ne dis pas » -> « dis plutôt »), police de la DA, couleur texte de la DA."""
    esc = lambda x: x.replace("&", "&amp;").replace("<", "&lt;")
    hd = t.get("head", ["Ne dis pas", "Dis plutôt"])
    h = (f'<div class="tt">{esc(nopunct(t["title"])).upper()}</div>' if t.get("title") else "") + \
        f'<div class="tr th"><span>{esc(hd[0]).upper()}</span><i></i><span class="d">{esc(hd[1]).upper()}</span></div>'
    for a, z in t["rows"]:
        h += f'<div class="tr"><span class="g">{esc(nopunct(a))}</span><i>→</i><span class="d">{esc(nopunct(z))}</span></div>'
    return h


if table:
    acc = DA["colors"].get("text", "#fff"); acc2 = t.get("accent") or acc
    sh = "text-shadow:0 2px 6px rgba(0,0,0,.6),0 0 24px rgba(0,0,0,.45)"
    css += f"""
.tt{{font-family:Mont;font-weight:800;font-size:58px;line-height:1.1;color:{acc2};margin:0 0 90px;{sh}}}
.tr{{display:grid;grid-template-columns:1fr 84px 1fr;align-items:center;margin:0 0 22px;font-family:Mont;color:{acc};{sh}}}
.tr span{{font-size:38px;line-height:1.12}}
.tr i{{font-family:-apple-system,'Helvetica Neue',sans-serif;font-style:normal;font-size:46px;font-weight:700;opacity:.9}}
.th span{{font-weight:800;font-size:36px;letter-spacing:1px}}
.th{{margin-bottom:30px}}
.g{{font-weight:400;opacity:.82}}
.d{{font-weight:700;color:{acc2}}}
"""


def render(ytop, veil=0):
    """Écrit le HTML (bloc texte dont le HAUT est à ytop ; CTA en bas ; voile noir jusqu'à veil px), capture le PNG,
    rend [haut, bas, ok, cta_haut, cta_bas]."""
    vl = (f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{veil + 170}px;background:linear-gradient(180deg,'
          f'rgba(0,0,0,.5) 0,rgba(0,0,0,.45) {veil}px,rgba(0,0,0,0) {veil + 170}px)"></div>') if veil else ""
    html = f"<!doctype html><meta charset=utf-8><style>{css}</style>" + vl + \
           f'<div id=b class=blk style="top:{ytop}px">' + (table_html() if table else rows_html()) + "</div>" + \
           (f'<div id=c class="blk cta" style="bottom:{H - (BOTTOM - 60)}px"><span class="c">{cta}</span></div>' if cta else "")
    open(P("_text.html"), "w").write(html)
    js = f"""
import {{ createRequire }} from "node:module";
import {{ existsSync, readdirSync }} from "node:fs";
import {{ join }} from "node:path";
import {{ homedir }} from "node:os";
// puppeteer-core + Chrome installés par HyperFrames (même recherche que zones.mjs) ; secours : Google Chrome
const NPX = join(homedir(), ".npm", "_npx"), CH = [join(homedir(), ".cache", "hyperframes", "chrome", "chrome-headless-shell"), join(homedir(), ".cache", "puppeteer", "chrome-headless-shell")];   // 0.8 range Chrome dans ~/.cache/hyperframes, 0.6 dans ~/.cache/puppeteer (25/10)
const mod = existsSync(NPX) && readdirSync(NPX).map(d => join(NPX, d, "node_modules")).find(d => existsSync(join(d, "puppeteer-core")));
if (!mod) {{ console.log("puppeteer-core introuvable : lancer une fois « npx --yes hyperframes@0.8.149 browser ensure »"); process.exit(1); }}
const puppeteer = createRequire(mod + "/")("puppeteer-core");
const hs = CH.filter(existsSync).flatMap(c => readdirSync(c).sort().reverse().map(v => join(c, v))).flatMap(v => readdirSync(v).map(x => join(v, x, "chrome-headless-shell"))).find(existsSync);
const gc = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
let exe = hs || (existsSync(gc) && gc);
if (!exe) {{ try {{ exe = (await import("node:child_process")).execSync("npx --yes hyperframes@0.8.149 browser path", {{encoding: "utf8"}}).trim().split("\\n").pop(); }} catch (e) {{}} }}
if (!exe) {{ console.log("Chrome introuvable (ni chrome-headless-shell ni Google Chrome)"); process.exit(1); }}
const b = await puppeteer.launch({{executablePath: exe, headless: "new", args: ["--allow-file-access-from-files", "--no-sandbox"]}});
const p = await b.newPage(); await p.setViewport({{width: {W}, height: {H}, deviceScaleFactor: 1}});
await p.goto("file://{P('_text.html')}"); await p.evaluate(() => document.fonts.ready);
// chaque ligne doit tenir dans {RIGHT-LEFT} px : la police rétrécit (min 44 px pour le texte, 34 px pour le CTA)
const ok = await p.evaluate((maxW) => {{
  let ok = true;
  for (const row of document.querySelectorAll(".row,.cta")) {{
    const els = [...row.querySelectorAll("span")];
    const min = row.classList.contains("cta") ? 34 : 44;
    let k = 1;
    while (row.scrollWidth > maxW && k > 0.5) {{
      k -= 0.02;
      for (const e of els) {{ e.dataset.fs ||= parseFloat(getComputedStyle(e).fontSize); e.style.fontSize = (e.dataset.fs * k) + "px"; }}
    }}
    const l = els.find(e => e.classList.contains("l") || e.classList.contains("c"));
    if (row.scrollWidth > maxW || (l && parseFloat(getComputedStyle(l).fontSize) < min)) ok = false;
  }}
  const blk = document.getElementById("b");
  if (blk && document.querySelector(".tr")) {{
    let k = 1; const els = [...blk.querySelectorAll(".tt,.tr span,.tr i")];
    for (const e of els) e.dataset.fs = parseFloat(getComputedStyle(e).fontSize);
    while (blk.getBoundingClientRect().bottom > {BOTTOM} && k > 0.6) {{ k -= 0.02; for (const e of els) e.style.fontSize = (e.dataset.fs * k) + "px"; }}
    if (blk.getBoundingClientRect().bottom > {BOTTOM}) ok = false;
  }}
  return ok;
}}, {RIGHT-LEFT});
const r = await p.evaluate(() => {{ const f = id => {{ const e = document.getElementById(id); if (!e) return [0, 0];
  const q = e.getBoundingClientRect(); return [Math.round(q.top), Math.round(q.bottom)]; }}; return [...f("b"), ...f("c")]; }});
console.log(JSON.stringify([r[0], r[1], ok, r[2], r[3]]));
await p.screenshot({{path: "{P('text.png')}", omitBackground: true}}); await b.close();
"""
    open(P("_shot.mjs"), "w").write(js)
    return json.loads(subprocess.check_output(["node", P("_shot.mjs")]).decode().strip().splitlines()[-1])


top0, bot0, ok, _, _ = render(TOP + 30)
if not ok: sys.exit("!! une ligne ne tient pas sur une ligne même en petit : raccourcir la phrase.")
hb = bot0 - top0                                   # hauteur du bloc texte

# --- 3. place au-dessus de la tête ---
S, head = 0, None
if table:
    ytop = TOP + 30
    print("tableau : en haut de la zone sûre")
elif "y" in plan:
    ytop = int(plan["y"] - hb / 2)
    print(f"texte forcé : centre à {plan['y']} px")
else:
    fbox = face_box(P("_broll.mp4"))
    head = fbox and fbox[1]
    if head is None and cloud:
        ytop = int((TOP + BOTTOM) / 2 - hb / 2)
        print("pas de visage dans le plan : texte au centre de l'écran (nuage)")
    elif cloud and max(fbox[3] + 70, (TOP + BOTTOM - hb) // 2) + hb < BOTTOM - 150:
        ytop = int(max(fbox[3] + 70, (TOP + BOTTOM - hb) // 2))   # nuage : texte au centre, sous le menton (jamais sur le visage)
        print(f"nuage : texte du centre sous le visage (menton {fbox[3]} px)")
    elif head is None:
        ytop = TOP + 30
        print("pas de visage dans le plan : texte en haut de la zone sûre")
    else:
        room = head - AIR - (TOP + 30)             # place entre la zone sûre et la tête
        S = int(min(SMAX, max(0, hb - room)))
        ytop = int(TOP + 30 + max(0, (room + S - hb) / 2))
        print(f"haut de tête {head} px · bloc texte {hb} px · place {room} px -> plan descendu de {S} px")
        if hb - room > SMAX:
            print(f"!! même descendu de {SMAX} px, le texte touche la tête : prendre un plan plus large (tête plus basse)")
cam = P("_broll.mp4")
if S > 0:                                          # fondu « place rajoutée » (même recette que viral.py, validé 16/10)
    from PIL import Image
    ramp = np.ones((H, W), np.float32); x = np.linspace(0, 1, FADE)
    ramp[:FADE] = (x * x * (3 - 2 * x))[:, None]
    Image.fromarray((ramp * 255).astype(np.uint8)).save(P("_mask.png"))
    band = max(120, min((head or 420) - 60, 360))  # haut de l'image (mur, ciel), sans la tête (comme viral.py)
    fc = (f"[0:v]split[a][b];[a]crop={W}:{band}:0:0,scale={W}:{S + FADE},boxblur=28:2,eq=brightness=-0.05,pad={W}:{H}:0:0:black[bg];"
          f"[b]format=rgba[c];[1:v]format=gray,scale={W}:{H}[m];[c][m]alphamerge[fg];[bg][fg]overlay=0:{S}:shortest=1,format=yuv420p[v]")
    run("ffmpeg", "-nostdin", "-v", "error", "-y", "-i", cam, "-loop", "1", "-framerate", str(FPS), "-i", P("_mask.png"),
        "-filter_complex", fc, "-map", "[v]", "-t", str(dur), "-c:v", "libx264", "-crf", "14", "-preset", "fast", P("_place.mp4"))
    os.remove(P("_mask.png")); cam = P("_place.mp4")
top, bot, ok, ctop, cbot = render(ytop)
# contraste sous le texte (16/10 : « fond légèrement noir en haut » quand le contraste n'est pas bon)
x0, x1 = LEFT - 20, RIGHT + 20
ch, cy = (bot - top) // 2 * 2, top // 2 * 2          # ffmpeg arrondit le crop au pair sur du 4:2:0 : on le fait nous-mêmes
raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-i", cam, "-vf",
                               f"fps=2,crop={x1 - x0}:{ch}:{x0}:{cy},format=gray", "-f", "rawvideo", "-"])
g = np.frombuffer(raw, np.uint8).reshape(-1, ch, x1 - x0).astype(np.float32)
clair, charge = float(np.percentile(g, 85)), float(np.mean([f.std() for f in g]))
veil = plan.get("veil", (clair > 140 or charge > 45) and not cloud)   # nuage : tout le plan s'assombrit ("sombre")
print(f"fond sous le texte : clair {clair:.0f}/255, chargé {charge:.0f} -> " + ("voile noir en haut" if veil else "pas de voile"))
if veil:
    top, bot, ok, ctop, cbot = render(ytop, veil=bot + 20)
print(f"bloc texte {top} -> {bot} px" + (f" · CTA {ctop} -> {cbot} px" if cta else ""))
if top < TOP or bot > BOTTOM or (cta and cbot > BOTTOM): print(f"!! hors zone Insta (autorisé {TOP}-{BOTTOM})")

# --- 3 bis. NUAGE (29/10) : les mots se posent autour (jamais sur le visage ni sur le texte du centre), 1 PNG par mot ---
words = []
if cloud:
    fb = None
    if not table and "y" not in plan and head is not None:
        t0 = float(t["at"]) if "at" in t else float(t.get("start", 0.35)) * dur
        fbox = face_box(P("_broll.mp4"), t0) or fbox   # 29/10 : le visage seulement quand les mots sont là (il bouge : sinon zone interdite trop large)
        fb = [fbox[0] - 25, fbox[1] + S - 15, fbox[2] + 25, fbox[3] + S + 30]   # visage (plan descendu de S) + marge
        print(f"nuage : visage {fb}")
    js = open(P("_shot.mjs")).read()
    ws = json.dumps([nopunct(w).upper() for w in t["words"]], ensure_ascii=False)   # 29/10 : tout en majuscules
    # 29/10 : "slots" = places + instants des mots d'un reel de référence (nuage_ref.py), resserrés dans la zone Insta
    sl, st = t.get("slots"), None
    if isinstance(sl, str):
        import nuage_ref
        sl = nuage_ref.detecter(sl if os.path.isabs(sl) else os.path.join(here, sl))
    if sl:
        sl = sl[:len(t["words"])]
        ZL, ZR, ZT, ZB = 90, W - 90, TOP + 20, BOTTOM - 20
        x0, x1 = min(q["x"] - q["w"] / 2 for q in sl), max(q["x"] + q["w"] / 2 for q in sl)
        y0, y1 = min(q["y"] - q["h"] / 2 for q in sl), max(q["y"] + q["h"] / 2 for q in sl)
        kx, ky = min(1, (ZR - ZL) / (x1 - x0)), min(1, (ZB - ZT) / (y1 - y0))
        ox, oy = (ZL + ZR) / 2 - kx * (x0 + x1) / 2, (ZT + ZB) / 2 - ky * (y0 + y1) / 2
        st = [q["t"] for q in sl]
        sl = [[round(ox + kx * q["x"]), round(oy + ky * q["y"]), q["h"], q["w"] * kx] for q in sl] + [None] * (len(t["words"]) - len(sl))
        print(f"nuage : {len(st)} places reprises de la référence (resserrées x{kx:.2f} / y{ky:.2f})")
    shot = 'await p.screenshot({path: "' + P("text.png") + '", omitBackground: true}); await b.close();'
    place = (open(os.path.join(SKILL, "scripts", "nuage.mjs")).read()
             .replace("__WORDS__", ws).replace("__SLOTS__", json.dumps(sl or None)).replace("__FB__", json.dumps(fb)).replace("__W__", str(W))
             .replace("__TOP__", str(TOP)).replace("__BOTTOM__", str(BOTTOM)).replace("__DIR__", here))
    if shot not in js: sys.exit("!! nuage : capture introuvable dans _shot.mjs")
    open(P("_shot.mjs"), "w").write(js.replace(shot, place + "\nawait b.close();"))
    words = json.loads(subprocess.check_output(["node", P("_shot.mjs")]).decode().strip().splitlines()[-1])
    lost = [t["words"][i] for i in range(len(t["words"])) if i not in {w[0] for w in words}]
    print(f"nuage : {len(words)} mots posés" + (f" · pas de place pour : {', '.join(lost)}" if lost else ""))
    # contrôle zone Insta sur l'ENCRE réelle (alpha > 50 %, l'ombre douce peut déborder) : 29/10, valable pour tous les nuages
    from PIL import Image
    al = np.array(Image.open(P("text-nuage.png")))[:, :, 3] > 128
    ys, xs = np.nonzero(al)
    bad = int(((ys < TOP) | (ys > BOTTOM) | (xs < 65) | (xs > W - 65) | ((ys > 1100) & (xs > W - 120))).sum())
    print(f"zones Insta (encre) : " + ("OK : 0 pixel dehors" if not bad else f"!! {bad} pixels dehors"))
    a0, a1 = float(t.get("start", 0.35)) * dur, float(t.get("end", 0.85)) * dur
    n = len(words)
    if st:                                          # rythme de la référence : chaque mot à son instant, décalé sur "at" (ou "start")
        t0 = float(t["at"]) if "at" in t else float(t.get("start", 0.35)) * dur
        when = {w[0]: t0 + st[w[0]] - st[0] if w[0] < len(st) else t0 + st[-1] - st[0] for w in words}
        words = [(when[w[0]], P(f"_w{w[0]}.png")) for w in words]
    elif "at" in t: a0 = a1 = float(t["at"])          # 29/10 : "at" = tous les mots d'un coup à cette seconde (ex. 2e coup de violon)
    if not st: words = [(a0 + (a1 - a0) * (k / max(1, n - 1)) ** 0.6, P(f"_w{w[0]}.png")) for k, w in enumerate(words)]   # de plus en plus vite

# --- 4. image + son ---
fin = P("final.mp4")
m = plan.get("music")
cmd = ["ffmpeg", "-v", "error", "-y", "-i", cam, "-loop", "1", "-i", P("text.png")]
k = max(0.0, min(0.6, float(plan.get("sombre", 0))))
fc = (f"[0:v]colorchannelmixer=rr={1-k:.3f}:gg={1-k:.3f}:bb={1-k:.3f}[d];[d]" if k else "[0:v]") + "[1:v]overlay=0:0:shortest=1"
for j, (tj, wp) in enumerate(words):                 # nuage : chaque mot entre en fondu de 0,12 s à son heure
    cmd += ["-loop", "1", "-i", wp]
    fc += f"[o{j}];[{j + 2}:v]format=rgba,fade=in:st={tj:.2f}:d=0.12:alpha=1[w{j}];[o{j}][w{j}]overlay=0:0:shortest=1"
fc += ",format=yuv420p[v]"
ia = len(words) + 2                                  # index de l'entrée musique
if m:
    cmd += ["-ss", str(m.get("from", 0)), "-i", m["src"]]
    # musique seule à -14 LUFS (pas de voix) : gain mesuré (loudnorm en 1 passe rate la cible sur 6 s) ;
    # fondus très courts pour que la boucle Instagram ne claque pas
    meas = subprocess.run(["ffmpeg", "-nostats", "-ss", str(m.get("from", 0)), "-t", str(dur), "-i", m["src"], "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    I = float([l for l in meas.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    tempo = float(m.get("tempo", 1))                # 29/10 : "tempo": 1.06 = musique accélérée de 6 % (hauteur gardée)
    fc += f";[{ia}:a]" + (f"atempo={tempo:.3f}," if tempo != 1 else "") + f"atrim=0:{dur},asetpts=N/SR/TB,volume={-14 - I:.2f}dB,alimiter=limit=0.79:attack=1:release=50:level=false," \
          f"afade=t=in:d=0.05,afade=t=out:st={dur-0.12}:d=0.12[a]"
cmd += ["-filter_complex", fc, "-map", "[v]"] + (["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if m else []) + \
       ["-t", str(dur), "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-r", str(FPS), "-movflags", "+faststart", fin]
run(*cmd)
if plan.get("caption"):
    open(P("legende.txt"), "w").write(plan["caption"].strip() + "\n")
for f in parts + [w for _, w in words] + [P("_list.txt"), P("_broll.mp4"), P("_shot.mjs"), P("_place.mp4"), P("_text.html")]:
    if os.path.exists(f): os.remove(f)
print("OK", fin, f"{dur:.1f} s")
