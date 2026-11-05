"""Écrans de code façon Ayo Omolewa pour IMG_7042 : PNG 1080x1920 transparents (bandeau haut) ou pleins (plein écran),
une image par état de surlignage, + filtre ffmpeg qui les pose sur clip.mp4 -> cam_code.mp4."""
import json, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont

D = os.path.abspath(sys.argv[1])
OUT = os.path.join(D, "codes"); os.makedirs(OUT, exist_ok=True)
BG = (13, 11, 18, 255)
TXT = (228, 228, 232)
COM = (128, 128, 140)
HL = (37, 243, 230)
HLT = (0, 23, 42)
BAND = 560            # bas du bandeau au-dessus de la tête (tête de l’utilisateur à ~560 px)
X0 = 70
XF = 65   # plein écran : 30 px par lettre comme la réf (mesuré), marge = zone Insta
MONO = "/System/Library/Fonts/SFNSMono.ttf"
OUTFIT = os.path.expanduser("~/.claude/skills/supermonteur/fonts/Outfit.ttf")
INSTA = sys.argv[2]


def mono(sz, w="Regular"):
    f = ImageFont.truetype(MONO, sz)
    try: f.set_variation_by_name(w)
    except Exception: pass
    return f


def outfit(sz):
    f = ImageFont.truetype(OUTFIT, sz)
    try: f.set_variation_by_name("Bold")
    except Exception: pass
    return f


def code(lines, hl, y0, sz=None, lh=None, full=True):
    """lines : liste de chaînes ; hl : jetons à surligner (texte exact dans la ligne)."""
    sz = sz or (48 if full else 40); lh = lh or (74 if full else 70)
    im = Image.new("RGBA", (1080, 1920), BG if full else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if not full: d.rectangle([0, 0, 1080, BAND], fill=BG)
    f = mono(sz)
    X0 = XF if full else globals()["X0"]
    y = y0
    for ln in lines:
        col = COM if ln.strip().startswith("//") else TXT
        for tok in hl:
            i = ln.find(tok)
            if i >= 0:
                x = X0 + d.textlength(ln[:i], font=f)
                w = d.textlength(tok, font=f)
                d.rectangle([x - 4, y - 6, x + w + 4, y + sz + 8], fill=HL)
        x = X0
        # texte posé caractère par segment : le jeton surligné passe en sombre
        segs, rest = [], ln
        while rest:
            pos = [(rest.find(t), t) for t in hl if rest.find(t) >= 0]
            if not pos:
                segs.append((rest, col)); break
            i, t = min(pos)
            if i: segs.append((rest[:i], col))
            segs.append((t, HLT)); rest = rest[i + len(t):]
        for s, c in segs:
            d.text((x, y), s, font=f, fill=c)
            x += d.textlength(s, font=f)
        y += lh
    return im


def grand(nombre, mot, colonnes, hl, y0=300):
    im = Image.new("RGBA", (1080, 1920), BG)
    d = ImageDraw.Draw(im)
    fn, fm = outfit(120), outfit(46)
    d.text((X0, y0), nombre, font=fn, fill=HL)
    wn = d.textlength(nombre, font=fn)
    d.text((X0 + wn + 22, y0 + 62), mot, font=fm, fill=(255, 255, 255))
    f = mono(33)
    y = y0 + 200
    for row in list(zip(*colonnes))[:12]:
        for k, cell in enumerate(row):
            x = X0 + k * 480
            if cell in hl:
                w = d.textlength(cell, font=f)
                d.rectangle([x - 3, y - 5, x + w + 3, y + 40], fill=HL)
                d.text((x, y), cell, font=f, fill=HLT)
            else:
                d.text((x, y), cell, font=f, fill=COM if k else TXT)
        y += 54
    return im


def carte():
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1080, BAND], fill=(0, 0, 0, 255))
    c = Image.open(INSTA).convert("RGBA")
    bb = c.convert("L").point(lambda v: 255 if v > 30 else 0).getbbox()
    c = c.crop((max(bb[0] - 40, 0), max(bb[1] - 30, 0), min(bb[2] + 40, c.width), min(bb[3] + 30, c.height)))
    w = 900; h = round(c.height * w / c.width)
    if h > BAND - 280: h = BAND - 280; w = round(c.width * h / c.height)
    c = c.resize((w, h), Image.LANCZOS)
    im.alpha_composite(c, ((1080 - w) // 2, 272 + (BAND - 272 - h) // 2))
    return im


MODELES = [["feed_rank_v3_2610", "clips_skip_predict", "har_predict_v2", "playtime_ml", "comment_intent_v1",
            "reopen_predict", "drowsy_detect_v1", "scroll_speed_v4", "like_prob_cvr", "follow_prob_v2",
            "share_prob_v1", "live_pull_focus", "prerender_reels"],
           ["dwell_time_v5", "story_tray_rank", "explore_rank_v8", "audio_on_predict", "battery_ctx_v1",
            "typing_intent_v2", "lost_focus_v3", "push_timing_v2", "keep_warm_v1", "reels_tray_ml",
            "ad_slot_predict", "session_end_v4", "rewatch_prob_v1"]]
VARS = [["battery_pct", "battery_temp", "is_charging", "screen_brightness", "is_mute", "volume_level",
         "headphones_on", "net_type", "wifi_signal", "cpu_usage", "memory_avail", "disk_free", "orientation"],
        ["locale", "timezone", "last_touch_ms", "scroll_speed", "time_since_open", "app_bg_count",
         "low_power_mode", "dark_mode", "font_scale", "motion_state", "lie_down_pct", "session_len", "feed_depth"]]

P = []   # (début, fin, nom, image)
def ajoute(a, b, nom, im):
    p = os.path.join(OUT, nom + ".png"); im.save(p); P.append((a, b, p))

ajoute(0.7, 2.25, "01-carte", carte())   # réf : visage d'abord, la carte arrive sur le nom de l'appli
ajoute(2.25, 4.1, "02-fichiers", code(["// Instagram.app/Frameworks/", "FeedRankingServiceImpl.swift",
                                        "ClipsPrefetchServiceImpl.swift", "FeedLoadMoreServiceImpl.swift"], [], 285, full=False))
for k, n in enumerate(range(19, 26)):   # le nombre compte jusqu'à 25, comme la réf (26 -> 31)
    ajoute(5.75 + k * 0.07, 5.75 + (k + 1) * 0.07 if n < 25 else 7.0, f"03-modeles-n{n}", grand(str(n), "MODÈLES IA", MODELES, []))
ajoute(7.0, 11.2, "03-modeles-b", grand("25", "MODÈLES IA", MODELES, ["har_predict_v2", "playtime_ml", "reopen_predict"]))
META = ["// une vidéo Reels en cache", "video.meta {", '  "rec_skip": 0.7412,', '  "rec_finish": 0.1873,',
        '  "rec_like": 0.0061,', '  "rec_comment": 0.0129,', '  "rec_follow": 0.0000917,', '  "rec_share": 0.0024,',
        "  …", "}"]
for k, (a, b, h) in enumerate([(14.2, 15.55, []), (15.55, 19.15, ["video.meta"]), (19.15, 20.35, ['"rec_skip"']),
                               (20.35, 21.55, ['"rec_finish"']), (21.55, 22.25, ['"rec_like"']),
                               (22.25, 22.95, ['"rec_comment"']), (22.95, 23.55, ['"rec_follow"']),
                               (23.55, 24.4, ['"rec_share"'])]):
    ajoute(a, b, f"04-meta-{k}", code(META, h, 310))
ajoute(28.35, 29.45, "05-dossiers-a", code(["// mon téléphone : client_ai/", "feed_rank_hot/", "playtime_ml/", "reels_prerender/"], [], 285, full=False))
ajoute(29.45, 31.65, "05-dossiers-b", code(["// mon téléphone : client_ai/", "feed_rank_hot/", "playtime_ml/", "reels_prerender/"],
                                           ["feed_rank_hot/", "playtime_ml/", "reels_prerender/"], 285, full=False))
HAR = ["// Instagram iOS · fil Reels", "client_info_v2 {", "  device_info {", "    har_predict {",
       "      static_percent", "      walking_percent", "      lie_down_percent", "      by_car_percent", "    }",
       "    play_time_predict", "  …"]
for k, (a, b, h) in enumerate([(31.55, 34.85, []), (34.85, 37.95, ["har_predict"]), (37.95, 38.65, ["walking_percent"]),
                               (38.65, 39.65, ["lie_down_percent"]), (39.65, 40.35, ["by_car_percent"])]):
    ajoute(a, b, f"06-har-{k}", code(HAR, h, 310))
DEV = ["// requête du fil · device_info", "POST /api/v1/feed/reels_tray/", "device_info {", '  "battery_pct": 100.0,',
       '  "is_charging": true,', '  "screen_brightness": 0.1843,', '  "is_mute": 1,', "  …", "}"]
for k, (a, b, h) in enumerate([(40.3, 41.65, []), (41.65, 43.15, ["/api/v1/feed/reels_tray/"]), (43.15, 43.95, ['"battery_pct"']),
                               (43.95, 45.95, ['"screen_brightness"']), (45.95, 46.6, ['"is_mute"'])]):
    ajoute(a, b, f"07-device-{k}", code(DEV, h, 310))
for k, n in enumerate(range(43, 51)):
    ajoute(46.6 + k * 0.07, 46.6 + (k + 1) * 0.07 if n < 50 else 50.7, f"08-vars-n{n}", grand(str(n), "AUTRES PARAMÈTRES", VARS, ["battery_pct", "screen_brightness", "is_mute"]))
ajoute(50.7, 52.35, "08-vars-b", grand("50", "AUTRES PARAMÈTRES", VARS, ["battery_pct", "screen_brightness", "is_mute", "motion_state", "lie_down_pct"]))
COMM = ["// Comments.onTextChanged", "// CommentDraftLogger.swift", 'log("comment_draft_typed")', "logDraft(",
        '  "draft_text" String str,', '  "media_id" String str2,', '  "is_sent" Boolean bool,', '  "to_userid" String str5,', "  …)"]
BANDE = ["// Comments.onTextChanged", 'log("comment_draft_typed")', '  "draft_text": "Franchement…"']
ajoute(52.35, 54.25, "09-commentaire-0", code(BANDE, [], 285, full=False))   # visage au milieu : 26 s de code d'affilée sinon (réf : 23 s max)
ajoute(54.25, 55.7, "09-commentaire-1", code(BANDE, ['log("comment_draft_typed")'], 285, full=False))
ajoute(55.7, 58.35, "09-commentaire-2", code(COMM, ['"is_sent"'], 310))
ajoute(63.45, 64.55, "10-allonge-a", code(["// requête du fil · iOS", "har_predict {", "  lie_down_percent", "}"], [], 285, full=False))
ajoute(64.55, 65.85, "10-allonge-b", code(["// requête du fil · iOS", "har_predict {", "  lie_down_percent", "}"], ["lie_down_percent"], 285, full=False))
KW = ["// AppStartPredictor", "getFeature(producer,", '  "app_start_predict_list",', "  null,",
      '  "prefetch_keep_warm")', "…", "getLong(", '  "app_start_prediction_at")', "…", "// lifecycle/task/", "KeepWarmJobService"]
for k, (a, b, h) in enumerate([(65.85, 67.25, []), (67.25, 69.75, ['"app_start_prediction_at"']), (69.75, 71.35, ['"prefetch_keep_warm"'])]):
    ajoute(a, b, f"11-keepwarm-{k}", code(KW, h, 310))

# 05/11 : bords des écrans calés sur les coupes du dérush (sinon plan éclair < 0,1 s vu par le Gardien)
seg = json.load(open(os.path.join(D, "cut.segments.json")))
coupes, t = [], 0.0
for a, b in seg:
    t += b - a; coupes.append(round(t, 3))
snap = lambda x: min(coupes, key=lambda c: abs(c - x)) if min(abs(c - x) for c in coupes) <= 0.2 else x
P = [(snap(a), snap(b), p) for a, b, p in sorted(P)]
FIN = float(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
# 1 seule entrée (concat d'images) au lieu d'une entrée par image : 31 s au lieu de >10 min
vide = os.path.join(OUT, "vide.png"); Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(vide)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(D, "clip.mp4")]))
L, t = [], 0.0
for a, b, p in P:
    if a > t + 0.001: L.append((vide, a - t))
    L.append((p, b - a)); t = b
L.append((vide, dur - t + 0.5))
with open(os.path.join(OUT, "liste.txt"), "w") as f:
    for p, d in L: f.write(f"file '{p}'\nduration {d:.3f}\n")
    f.write(f"file '{vide}'\n")
args = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", os.path.join(D, "clip.mp4"), "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "liste.txt"),
        "-filter_complex", "[1:v]fps=30,format=rgba[o];[0:v][o]overlay=0:0:shortest=1:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-c:a", "aac", "-b:a", "256k"]
if FIN: args += ["-t", str(FIN)]
args += [os.path.join(D, "cam_code.mp4")]
json.dump([[a, b, os.path.basename(p)] for a, b, p in P], open(os.path.join(OUT, "temps.json"), "w"), indent=1)
if "--rendu" in sys.argv:
    subprocess.check_call(args)
print(len(P), "images")
