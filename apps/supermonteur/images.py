"""SuperMonteur : l'écran « Tes images pour ce reel » (29/10/2026, maquettes reprise-r1 A + reprise-r2 B validées).

l’utilisateur : « lorsqu'on veut reprendre le montage de quelqu'un, on est d'abord fidèle à son concept, son style, et nous on vient
juste mettre notre police. Tu peux me proposer ou me demander quelles sont les images ou les b-rolls à mettre. »
Entre la préparation de ref/ (monter.preparer_ref) et le montage par Claude (monter.pousser_ref) :

  choisir(D, e)       découpe la référence en plans, Claude (Sonnet) propose 3 de ses b-rolls par plan à illustrer
                      -> images.json + statut "images" (l'écran attend l’utilisateur). False = rien à choisir : on monte direct.
  perso(D, n, chemin) sa vidéo glissée sur le plan n : ajoutée aux choix et choisie.
  consigne(D)         les images choisies, en texte, pour le retour automatique que Claude suit au montage.
"""
import csv, glob, hashlib, json, os, re, subprocess, sys

APP = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.expanduser("~/.claude/skills/supermonteur/scripts")
PLANS_MAX = 10      # au-delà, les plans voisins les plus courts sont fusionnés (une liste qu'on lit d'un coup d'œil)
PLAN_MIN = 0.5      # s : un plan plus court se colle au précédent
CLIP_S = 3          # s : extrait joué dans l'aperçu


def lire(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def ecrire(p, o):
    t = p + ".tmp"
    json.dump(o, open(t, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(t, p)


def duree(p):
    try:
        return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], text=True))
    except Exception:
        return 0.0


def ref_video(D, e):
    ref = e.get("reference") or {}
    return os.path.join(D, "ref", ref["fichier"] if ref.get("fichier") else "reference.mp4")


def plans_ref(D, src):
    """Les plans de la référence : coupes mesurées par analyse_ref.py (ref/*.analyse.json), sinon un seul plan."""
    d = duree(src)
    an = next((lire(p) for p in glob.glob(os.path.join(D, "ref", "*.analyse.json"))), None) or {}
    bornes = [0.0] + [t for t in sorted((an.get("coupes") or {}).get("temps") or []) if 0 < t < d] + [d]
    P = []
    for a, b in zip(bornes, bornes[1:]):
        if P and b - a < PLAN_MIN: P[-1][1] = b
        else: P.append([a, b])
    while len(P) > PLANS_MAX:   # fusionne le plan le plus court avec son voisin le plus court
        i = min(range(len(P)), key=lambda k: P[k][1] - P[k][0])
        j = i - 1 if i == len(P) - 1 or (i > 0 and P[i - 1][1] - P[i - 1][0] < P[i + 1][1] - P[i + 1][0]) else i + 1
        a, b = min(i, j), max(i, j)
        P[a:b + 1] = [[P[a][0], P[b][1]]]
    return [(round(a, 2), round(b, 2)) for a, b in P if b > a]


def catalogue():
    """Ses b-rolls vidéo filmables (mêmes filtres que broll.py search : date, exclus, écartés, souvenirs, qualité)."""
    sys.path.insert(0, SCRIPTS)
    import reglages   # (pas broll.py : il lance sa ligne de commande dès l'import)
    cfg = reglages.config()
    idx, root = cfg.get("brolls_index"), cfg.get("brolls_root")
    if not idx or not os.path.exists(idx): return []
    ex = os.path.join(os.path.dirname(SCRIPTS), "broll_exclus.txt")
    exclus = {l.split("#")[0].strip() for l in open(ex, encoding="utf-8")} - {""} if os.path.exists(ex) else set()
    t = os.path.join(os.path.dirname(SCRIPTS), "broll_tri.csv")   # tremble / flou / refusé = « ecarte » (scripts/broll_tri.py)
    tri = {r["fichier"]: r["rang"] for r in csv.DictReader(open(t, encoding="utf-8"))} if os.path.exists(t) else {}
    mini = cfg.get("brolls_min_date", "")
    L = []
    for r in csv.DictReader(open(idx, encoding="utf-8")):
        if r.get("action") in exclus or tri.get(r.get("fichier"), "ok") == "ecarte": continue
        if mini and r.get("date_tournage", "") < mini: continue
        if r.get("usage") == "souvenir" or r.get("qualite", "ok") != "ok": continue
        if float(r.get("duree_s") or 0) < 1.5: continue   # photos et plans trop courts : pas un plan de reel
        p = os.path.join(root, r.get("dossier", ""), r["fichier"])
        if os.path.exists(p): L.append(dict(r, src=p))
    return L


def apercus(D, src, depuis=None):
    """Vignette + extrait de 3 s (270 px, muet) d'un plan, faits une fois dans images/."""
    I = os.path.join(D, "images")
    os.makedirs(I, exist_ok=True)
    h = hashlib.md5(src.encode()).hexdigest()[:10]
    d = duree(src)
    f = depuis if depuis is not None else (1.0 if d > CLIP_S + 1.5 else 0.0)
    jpg, mp4 = os.path.join(I, f"c-{h}.jpg"), os.path.join(I, f"c-{h}.mp4")
    if not os.path.exists(mp4):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f:.2f}", "-t", str(CLIP_S), "-i", src, "-vf", "scale=270:-2,fps=30",
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4],
                       timeout=120, check=True)
    if not os.path.exists(jpg):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", mp4, "-frames:v", "1", jpg], timeout=30, check=True)
    return {"src": src, "from": round(f, 2), "img": f"images/c-{h}.jpg", "clip": f"images/c-{h}.mp4"}


def demander_claude(D, plans, cat, muet):
    sortie = os.path.join(D, "images", "claude.json")   # un fichier : ouvrier_claude.lancer ne rend que la fin de la réponse
    if os.path.exists(sortie): os.remove(sortie)
    lignes = "\n".join(f"{i} | {r.get('theme', '')} | {r.get('action', '')} | {r.get('lieu', '')} | {r.get('tenue', '')} | "
                       f"{r.get('orientation', '')} {r.get('duree_s', '')} s" for i, r in enumerate(cat, 1))
    pl = "\n".join(f"Plan {n} : {a:.1f} s -> {b:.1f} s, image : {os.path.join(D, 'images', f'ref-{n:02d}.jpg')}"
                   for n, (a, b) in enumerate(plans, 1))
    prompt = (
        "l’utilisateur reprend le montage d'un reel qui marche. Règle : on est FIDÈLE à son concept et son style ; seule la police change. "
        f"Voici les plans de ce reel (regarde chaque image avec Read, et la planche {os.path.join(D, 'ref', 'planche.jpg')}) :\n{pl}\n\n"
        + ("La vidéo de l’utilisateur est un B-roll muet (n° 0 = SA vidéo de ce reel, à proposer en premier au plan qui lui ressemble le plus).\n"
           if muet else "La vidéo de l’utilisateur est face caméra : les plans où le créateur parle face caméra seront SA vidéo.\n")
        + f"Sa bibliothèque de B-rolls (n° | thème | geste | lieu | tenue | format durée) :\n{lignes}\n\n"
        "Pour chaque plan, dis son type :\n"
        + ("" if muet else "- \"cam\" : le créateur parle face caméra (rien à choisir, ce sera l’utilisateur) ;\n")
        + "- \"carton\" : texte ou graphisme plein écran sans personne ni décor (rien à choisir, on le refait) ;\n"
        "- \"image\" : un plan à illustrer avec SES b-rolls. Donne 3 numéros, le meilleur d'abord : même idée, même cadrage "
        "(serré / large), même mouvement, même ambiance de lumière que le plan de la référence. Varie : pas 3 fois le même geste, "
        "pas le même b-roll dans 2 plans si possible.\n"
        "  \"exact\": true si le 1er colle vraiment, false s'il n'a pas ce plan ; si false, \"consigne\" = 1 phrase pour qu'il le filme "
        "lui-même (« filme-toi … », cadrage, caméra fixe ou non, durée en s, tenue qui va avec ses autres plans).\n"
        "  \"desc\" = ce qu'on voit dans la référence, 6 mots max, en français simple. \"pourquoi\" = 4 mots max sur le 1er choix.\n"
        f"Écris ta réponse avec l'outil Write dans {sortie} : ce JSON seul, un objet par plan :\n"
        "{\"plans\": [{\"n\": 1, \"type\": \"image\", \"desc\": \"...\", \"choix\": [12, 40, 7], \"exact\": true, \"consigne\": \"\", \"pourquoi\": \"...\"}]}\n"
        "Puis réponds « fait ».")
    sys.path.insert(0, os.path.dirname(APP))
    import ouvrier_claude
    ouvrier_claude.lancer(prompt, D, ["Read", "Write"], delai=420, modele="sonnet")
    try:
        return lire(sortie)["plans"]
    except Exception:
        return None


def choisir(D, e, dire=lambda t: None):
    src = ref_video(D, e)
    if not os.path.exists(src): return False
    muet = bool(e.get("muet"))
    dire("Je découpe la référence en plans…")
    plans = plans_ref(D, src)
    os.makedirs(os.path.join(D, "images"), exist_ok=True)
    for n, (a, b) in enumerate(plans, 1):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(a + b) / 2:.2f}", "-i", src, "-frames:v", "1", "-vf", "scale=240:-2",
                        os.path.join(D, "images", f"ref-{n:02d}.jpg")], timeout=30)
    cat = catalogue()
    if not cat:
        dire("Bibliothèque de b-rolls introuvable : je monte sans te demander les images.")
        return False
    if muet: cat = [{"src": e["rush"], "action": "ta vidéo de ce reel", "theme": "TOI", "duree_s": str(round(duree(e["rush"]), 1))}] + cat
    dire("Je cherche tes b-rolls qui collent à chaque plan…")
    rep = demander_claude(D, plans, cat if not muet else cat[1:], muet)
    if not rep: return False
    dire("Je prépare les aperçus de tes b-rolls…")
    out = []
    for n, (a, b) in enumerate(plans, 1):
        r = next((x for x in rep if int(x.get("n", 0)) == n), {}) or {}
        typ = r.get("type") if r.get("type") in ("cam", "carton", "image") else "image"
        if muet and typ == "cam": typ = "image"
        p = {"n": n, "de": a, "a": b, "ref_img": f"images/ref-{n:02d}.jpg", "type": typ, "desc": (r.get("desc") or "")[:60],
             "exact": bool(r.get("exact", True)), "consigne": (r.get("consigne") or "")[:220], "pourquoi": (r.get("pourquoi") or "")[:40],
             "choix": [], "pris": 0}
        if typ == "image":
            ids = [int(i) for i in r.get("choix") or [] if str(i).isdigit()]
            ids = [i for i in ids if (0 if muet else 1) <= i <= len(cat) - (1 if muet else 0)]
            for i in ids[:3]:
                row = cat[i] if muet else cat[i - 1]
                try:
                    c = apercus(D, row["src"], 0.0 if row["src"] == e["rush"] else None)
                except Exception:
                    continue
                c["nom"] = "Ta vidéo de ce reel" if row["src"] == e["rush"] else (row.get("action") or "").replace("-", " ").capitalize()
                p["choix"].append(c)
        out.append(p)
    if not any(p["type"] == "image" and p["choix"] for p in out): return False
    ecrire(os.path.join(D, "images.json"), {"plans": out, "ref": os.path.relpath(src, D)})
    return True


def perso(D, n, chemin):
    I = lire(os.path.join(D, "images.json"))
    p = next(x for x in I["plans"] if x["n"] == n)
    c = apercus(D, chemin, 0.0)
    c.update(nom="Ta vidéo", perso=True)
    p["choix"] = [x for x in p["choix"] if x["src"] != chemin] + [c]
    p["pris"] = len(p["choix"]) - 1
    ecrire(os.path.join(D, "images.json"), I)


def prendre(D, pris):
    """pris = {"<n>": index du choix} : ce que l’utilisateur a cliqué sur l'écran."""
    I = lire(os.path.join(D, "images.json"))
    for p in I["plans"]:
        k = pris.get(str(p["n"]))
        if isinstance(k, int) and 0 <= k < len(p["choix"]): p["pris"] = k
    ecrire(os.path.join(D, "images.json"), I)


def tc(s):
    return f"{int(s // 60)}:{int(s % 60):02d}"


def consigne(D):
    I = lire(os.path.join(D, "images.json"))
    if not I: return ""
    L = []
    for p in I["plans"]:
        quand = f"plan {p['n']} ({tc(p['de'])} -> {tc(p['a'])} de la référence{', ' + p['desc'] if p['desc'] else ''})"
        if p["type"] == "cam": L.append(f"- {quand} : l’utilisateur face caméra (son rush).")
        elif p["type"] == "carton": L.append(f"- {quand} : carton / graphisme de la référence, refait à l'identique, police de la DA.")
        elif p["choix"]:
            c = p["choix"][p["pris"]]
            L.append(f"- {quand} : {c['src']} (à partir de {c['from']} s){' = SA vidéo filmée pour ce plan' if c.get('perso') else ''}.")
    return ("\n\nImages choisies par l’utilisateur sur l'écran « Tes images » (images.json) : une par plan de la référence, dans le même ordre, "
            "même durée de plan, même cadrage, même mouvement et mêmes transitions que la référence (si son reel est plus long, garde "
            "l'ordre et le rythme). Aucune autre image.\n" + "\n".join(L))
