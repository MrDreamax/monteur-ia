"""SuperMonteur : le petit serveur local (28/10/2026).  python3 serveur.py [port]  ->  http://localhost:8801

Écrans : 0 style · 1 retours · 2 Ma DA (tiroir SuperDA) · 3 publier. Les reels vivent dans reels/<id>/ (etat.json,
retours.json, versions/). « Suivant : corrige mes retours » écrit reels/<id>/demande.json + a-corriger.json (la boîte
que Claude lit, mode d'emploi : CLAUDE.md). Publication réelle depuis le 28/10 (clic confirmé de l’utilisateur, apps/publier.py).
"""
import datetime, io, json, mimetypes, os, re, shutil, subprocess, sys, threading, time, urllib.parse, urllib.request, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP = os.path.dirname(os.path.abspath(__file__))
REELS = os.path.join(APP, "reels")
WEB = os.path.join(APP, "web")
sys.path.insert(0, APP)
import da as DA
from monter import lire, ecrire, etat, pousser_ref
import images
sys.path.insert(0, os.path.dirname(APP))
import ouvrier_claude
import publier
import reglages_apps

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
os.makedirs(REELS, exist_ok=True)
CASES = {  # devine-format.md 3 bis (B-rolls décochés par défaut, maquette 0-style validée)
    "Dynamique": [["titre", "titre"], ["sous_titres", "sous-titres"], ["ecran_coupe", "écran coupé"], ["cartons", "cartons"],
                  ["animations", "animations"], ["mots_geants", "mots géants"], ["brolls", "B-rolls"], ["bruitages", "bruitages"]],
    "Minimaliste": [["titre", "titre"], ["sous_titres", "sous-titres"]],
    "Comparatif": [["titre", "titre"], ["tableau", "tableau"], ["sous_titres", "sous-titres"], ["bruitages", "bruitages"]],
    "Interview": [["titre", "titre"], ["sous_titres", "sous-titres"], ["ecran_coupe", "écran coupé"], ["plein_ecran", "plein écran sur qui parle"]],
    "Inspiration": [],   # 29/10 : remplace « Autre » = le montage d'un reel à reprendre (lien ou vidéo)
}
RESEAUX = ["Instagram", "TikTok", "YouTube Shorts", "Facebook", "LinkedIn"]
LIEN_REF = re.compile(r"https?://([\w-]+\.)?(instagram\.com|tiktok\.com|youtube\.com|youtu\.be)/\S+$")


def D(rid):
    if not re.fullmatch(r"[\w-]+", rid or ""): raise KeyError(rid)
    d = os.path.join(REELS, rid)
    if not os.path.isdir(d): raise KeyError(rid)
    return d


def lancer(action, rid):
    log = open(os.path.join(D(rid), f"_{action}.log"), "a")
    subprocess.Popen([sys.executable, os.path.join(APP, "monter.py"), action, D(rid)], stdout=log, stderr=log, cwd=APP,
                     start_new_session=True)


# 29/10 : le DERUSH LAB (skill outils/cockpit, cockpit.py --lab) dans l'écran, entre le 1er dérush de Claude et le montage.
# Un petit serveur par reel en statut « derush », sur un port libre à partir de 8830 ; arrêté à « Monter le reel ».
COCKPIT = os.path.expanduser("~/.claude/skills/supermonteur/outils/cockpit/cockpit.py")
LABS = {}   # rid -> (process ou None si repris d'un ancien serveur, pid, port)
VERROU_LAB = threading.Lock()
# 29/10 : serveur redémarré = LABS vide = 2e Lab lancé sur le même reel (+ son aperçu ffmpeg) -> derush de 15 min.
# Le pid et le port du Lab sont écrits dans le dossier du reel ; un Lab vivant est repris, jamais doublé.
LAB_PID = "_derushlab.pid"


def lab_vivant(pid, port):
    try:
        os.kill(pid, 0)
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/etat", timeout=2)
        return True
    except Exception:
        return False


def port_libre():
    import socket
    pris = {p for _, _, p in LABS.values()}
    for p in range(8830, 8900):
        if p in pris: continue
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)): return p
    raise RuntimeError("aucun port libre pour le Derush Lab")


def lab(rid):
    """Le port du Derush Lab de ce reel (lancé s'il ne tourne pas : 1re ouverture, ou serveur redémarré)."""
    with VERROU_LAB:
        pr, pid, port = LABS.get(rid, (None, None, None))
        if pr and pr.poll() is None: return port
        if not pr and pid and lab_vivant(pid, port): return port
        try:
            pid, port = map(int, open(os.path.join(D(rid), LAB_PID)).read().split())
            if lab_vivant(pid, port):
                LABS[rid] = (None, pid, port)
                return port
        except (OSError, ValueError):
            pass
        port = port_libre()
        log = open(os.path.join(D(rid), "_derushlab.log"), "a")
        pr = subprocess.Popen([sys.executable, COCKPIT, D(rid), "--port", str(port), "--lab"], stdout=log, stderr=log,
                              cwd=D(rid), start_new_session=True)
        LABS[rid] = (pr, pr.pid, port)
        with open(os.path.join(D(rid), LAB_PID), "w") as f:
            f.write(f"{pr.pid} {port}")
        for _ in range(40):   # la page répond en ~1 s ; l'aperçu du rush se fait ensuite dans son coin
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/etat", timeout=1)
                break
            except Exception:
                if pr.poll() is not None: break
                time.sleep(.25)
        return port


def arreter_lab(rid):
    with VERROU_LAB:
        pr, pid, _ = LABS.pop(rid, (None, None, None))
        if pr and pr.poll() is None: pr.terminate()
        if not pr and pid:
            try: os.kill(pid, 15)
            except OSError: pass
        try: os.remove(os.path.join(D(rid), LAB_PID))
        except OSError: pass


def lab_valide(d):
    """Le Derush Lab a validé ce dérush (« ✓ Valider le dérush », aucune retouche depuis = mêmes plages) :
    "ok" = Gardien du dérush vert, "rouge" = il voit un point (l’utilisateur peut monter quand même : faux positifs), None = pas validé."""
    C = lire(os.path.join(d, "cockpit-etat.json"), {}) or {}
    L, pl = C.get("lab") or {}, (C.get("derush") or {}).get("plages")
    r2 = lambda x: [[round(a, 2), round(b, 2)] for a, b in (x or [])]
    if not pl or r2(L.get("plages")) != r2(pl): return None
    return "ok" if L.get("ok") else "rouge"


CONSIGNE = """Tu es Claude, DANS l'appli SuperMonteur de l’utilisateur (dossier actuel). Ne publie rien.
l’utilisateur a cliqué « Suivant : corrige mes retours » pour le reel %s (dossier %s, version %s). Ses retours :
%s
Suis la section « Quand l’utilisateur dit corrige mes retours » de CLAUDE.md (lis-le d'abord) et les règles du skill
~/.claude/skills/supermonteur/ (SKILL.md, feedback.md, fichier du style). Regarde l'image au temps de chaque retour
(`ffmpeg -ss <t> -i <dossier>/final.mp4 -frames:v 1 <dossier>/_retour-<n>.jpg` puis Read), corrige plan.json,
lance `python3 monter.py remonter <dossier>`, passe chaque retour traité en "statut": "corrige" + "reponse" (1 ligne) dans retours.json,
retire ce reel de a-corriger.json, et note 1 ligne datée par retour dans feedback-retours.md (ici).
Montage à reprendre (dossier <dossier>/ref/ : la vidéo, planche.jpg = 1 image par seconde, *.analyse.json = coupes, débit, musique, SFX) :
copie son montage pour CE reel seulement, FIDÈLE à son concept et son style (mise en page, couleurs, rythme, zooms, sous-titres,
cartons, motion, transitions, musique, bruitages) : seule la police change, celle de la DA (plan.json "da"). Les images de chaque
plan = celles que l’utilisateur a choisies (liste dans le retour, détail dans images.json), aucune autre. Regarde planche.jpg (Read) et d'autres images au besoin (`ffmpeg -ss <t> -i <vidéo de ref/>`).
Réponds en 1 ligne quand la nouvelle version est montée."""
ESSAIS = {}  # (reel, version) -> nombre d'essais


def ouvrier():
    """Dès qu'un reel arrive dans a-corriger.json, Claude corrige et remonte la version suivante tout seul."""
    while True:
        try:
            for dem in lire(os.path.join(APP, "a-corriger.json"), []) or []:
                rid, d = dem.get("reel"), dem.get("dossier")
                if not rid or not d or not os.path.isdir(d):
                    continue
                cle = (rid, dem.get("version"))
                ESSAIS[cle] = ESSAIS.get(cle, 0) + 1
                if ESSAIS[cle] > 2:
                    if lire(os.path.join(d, "etat.json"), {}).get("statut") == "correction":
                        etat(d, statut="erreur", etape="", erreur="Claude n'a pas réussi à corriger tes retours (détails : supermonteur/_claude.log). "
                                                                 "Demande « corrige mes retours » dans un chat Claude.")
                    continue
                retours = "\n".join(f"- à {r.get('t')} s : {r.get('texte')}" for r in dem.get("retours", []))
                ouvrier_claude.lancer(CONSIGNE % (rid, d, dem.get("version"), retours), APP,
                                      ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python3 monter.py remonter:*)", "Bash(ffmpeg -ss:*)"],
                                      delai=2400)
                break  # un reel à la fois, puis on relit la boîte
        except Exception as x:
            print("ouvrier :", x, flush=True)
        time.sleep(3)


def metricool():
    """Lecture seule. Le serveur ne parle pas à Metricool (c'est Claude, par le connecteur, getBrandSettings) : il lit
    metricool.json, écrit par Claude. Absent ou « branche: false » = mode Télécharger."""
    m = lire(os.path.join(APP, "metricool.json"), {}) or {}
    return {"branche": bool(m.get("branche")), "compte": m.get("compte", ""), "verifie": m.get("verifie", ""),
            "essai": reglages_apps.mode_essai(APP)}  # config.json "mode_essai": false = le bouton Publier publie pour de vrai


def legendes(d):
    """Une légende par réseau (legende-courte : 1-2 phrases, 0 hashtag). Claude les écrit dans legendes.json ; sinon brouillon
    tiré du titre, à relire."""
    L = lire(os.path.join(d, "legendes.json"))
    if L: return L
    p = lire(os.path.join(d, "plan.json"), {}) or {}
    t = p.get("title") or {}
    sujet = (t.get("l1", "") + " " + t.get("l2", "")).strip() or "Nouveau reel"
    return {r: sujet for r in RESEAUX} | {"_brouillon": True}


MONTAGES = reglages_apps.chemin("montages")
PAS_UN_REEL = re.compile(r"test|cockpit|essai|video-use", re.I)


def importer_montages():
    """Les reels montés dans un chat (montages/<date>-<nom>/) apparaissent aussi dans « Tes reels » : reels/<id> devient
    un raccourci vers leur dossier (même format que le moteur), avec un etat.json et ses versions (_v1, _v2… puis final.mp4)
    rangées en versions/vN.mp4 par lien dur (aucune copie, l'ancienne image reste si final.mp4 est refait)."""
    if not os.path.isdir(MONTAGES):
        return
    for nom in os.listdir(MONTAGES):
        src = os.path.join(MONTAGES, nom)
        if (not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[\w-]+", nom) or PAS_UN_REEL.search(nom)
                or os.path.lexists(os.path.join(REELS, nom)) or not os.path.isfile(os.path.join(src, "final.mp4"))):
            continue
        try:
            anciennes = sorted((x for x in os.listdir(src) if re.fullmatch(r"_v\d+", x) and os.path.isfile(os.path.join(src, x, "final.mp4"))),
                               key=lambda x: int(x[2:]))
            os.makedirs(os.path.join(src, "versions"), exist_ok=True)
            versions = []
            for n, f in enumerate([os.path.join(x, "final.mp4") for x in anciennes] + ["final.mp4"], 1):
                cible = os.path.join(src, "versions", f"v{n}.mp4")
                if not os.path.exists(cible):
                    os.link(os.path.join(src, f), cible)
                dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", cible],
                                     capture_output=True, text=True).stdout.strip()
                versions.append({"n": n, "fichier": f"versions/v{n}.mp4", "duree": round(float(dur or 0), 2),
                                 "date": datetime.datetime.fromtimestamp(os.path.getmtime(cible)).isoformat(timespec="seconds")})
            if not os.path.exists(os.path.join(src, "etat.json")):
                ecrire(os.path.join(src, "etat.json"), {
                    "id": nom, "nom": nom[11:].upper(), "importe": "monté dans un chat", "statut": "retours", "etape": "",
                    "cree": datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(src, "final.mp4"))).isoformat(timespec="seconds"),
                    "version": len(versions), "versions": versions})
            if not os.path.exists(os.path.join(src, "retours.json")):
                ecrire(os.path.join(src, "retours.json"), [])
            os.symlink(src, os.path.join(REELS, nom))
        except Exception as x:
            print("import", nom, x, file=sys.stderr)


def carte(rid):
    """Une ligne de « Tes reels » : l'état + le titre du reel + une vignette (image à 1,5 s de la dernière version,
    faite une fois puis gardée ; refaite si une nouvelle version sort)."""
    d = os.path.join(REELS, rid)
    e = lire(os.path.join(d, "etat.json"), {})
    if not e or e.get("cache"):   # 29/10 : projet supprimé depuis l'accueil = caché, aucun fichier effacé
        return None
    t = (lire(os.path.join(d, "plan.json"), {}) or {}).get("title") or {}
    e["titre"] = re.sub(r"<[^>]+>", "", " ".join(x for x in (t.get("l1"), t.get("l2")) if x) if isinstance(t, dict) else str(t)).strip()
    v = (e.get("versions") or [{}])[-1].get("fichier")
    vig = os.path.join(d, "vignette.jpg")
    if v and os.path.isfile(os.path.join(d, v)):
        if not os.path.exists(vig) or os.path.getmtime(vig) < os.path.getmtime(os.path.join(d, v)):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.5", "-i", os.path.join(d, v), "-frames:v", "1",
                            "-vf", "scale=180:-2", vig], timeout=20)
        if os.path.exists(vig):
            e["vignette"] = f"/media/{rid}/vignette.jpg?t={int(os.path.getmtime(vig))}"
    return e


def titre_reel(d):
    t = (lire(os.path.join(d, "plan.json"), {}) or {}).get("title") or {}
    return re.sub(r"<[^>]+>", "", " ".join(x for x in (t.get("l1"), t.get("l2")) if x) if isinstance(t, dict) else str(t)).strip()


def publieur():
    """Dès qu'un reel a un publication.json « a_faire » (clic confirmé de l’utilisateur), Claude l'envoie à Metricool."""
    for r in os.listdir(REELS):   # un envoi coupé par un redémarrage du serveur : on ne sait pas ce qui est parti
        d = os.path.join(REELS, r)
        if os.path.isdir(d) and publier.etat(d).get("statut") == "en_cours":
            publier._maj(d, statut="erreur", etape="", message="Envoi coupé (serveur relancé) : vérifie le planner Metricool avant de relancer.")
    while True:
        try:
            for r in sorted(os.listdir(REELS)):
                d = os.path.join(REELS, r)
                if os.path.isdir(d) and publier.etat(d).get("statut") == "a_faire":
                    e = lire(os.path.join(d, "etat.json"), {})
                    publier.lancer(d, "SuperMonteur", {"video": os.path.join(d, e["versions"][-1]["fichier"]), "legendes": legendes(d)})
        except Exception as x:
            print("publieur :", x, flush=True)
        time.sleep(3)


def fiche(rid):
    d = D(rid)
    e = lire(os.path.join(d, "etat.json"), {})
    r = lire(os.path.join(d, "retours.json"), []) or []
    e["retours"] = r
    e["cases_du_style"] = CASES
    e["images"] = lire(os.path.join(d, "images.json")) if e.get("statut") == "images" else None   # 29/10 écran « Tes images »
    if e["images"]:   # le titre du reel, montré dans le brouillon avec sa police
        t = (lire(os.path.join(d, "plan.json"), {}) or {}).get("title") or {}
        e["images"]["titre"] = re.sub(r"<[^>]+>", "", " ".join(x for x in (t.get("l1"), t.get("l2")) if x) if isinstance(t, dict) else str(t)).strip()
    if e.get("statut") == "derush" and not e.get("derush_ok"):   # 29/10 : l'écran montre le Derush Lab de ce reel
        try:
            v = lab_valide(d)
            rouge = [x["controle"] + " : " + x["detail"] for x in lire(os.path.join(d, "gardien-derush.json"), []) or [] if x.get("ok") is False]
            e["lab"] = {"port": lab(rid), "valide": v, "rouge": rouge[0] if v == "rouge" and rouge else ""}
        except Exception as x:
            e["lab"] = {"erreur": str(x)[:200]}
    e["publication"] = publier.etat(d)
    e["deja_publie"] = publier.deja_publie(rid)
    ty = (lire(os.path.join(d, "plan.json"), {}) or {}).get("typo") or {}
    if ty.get("t1", {}).get("size") and ty.get("t2", {}).get("size"):  # tailles propres à CE reel (un retour les a changées)
        e["tailles_reel"] = f'{ty["t2"]["size"]} · {ty["t1"]["size"]} px'
    return e


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def envoyer(self, code, corps, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(corps, (dict, list)): corps = json.dumps(corps, ensure_ascii=False).encode()
        elif isinstance(corps, str): corps = corps.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corps)

    def fichier(self, p):
        """Avec Range : la vidéo se déplace image par image dans le lecteur."""
        if not os.path.isfile(p): return self.envoyer(404, {"erreur": "introuvable"})
        taille = os.path.getsize(p)
        ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
        rg = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        a, b = 0, taille - 1
        if rg:
            a = int(rg.group(1) or 0)
            b = min(int(rg.group(2)) if rg.group(2) else taille - 1, taille - 1)
        self.send_response(206 if rg else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(b - a + 1))
        self.send_header("Cache-Control", "no-store")
        if rg: self.send_header("Content-Range", f"bytes {a}-{b}/{taille}")
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(a)
            reste = b - a + 1
            try:
                while reste > 0:
                    bloc = f.read(min(1 << 20, reste))
                    if not bloc: break
                    self.wfile.write(bloc)
                    reste -= len(bloc)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def corps(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    # ------------------------------------------------------------------------------------------------------- GET
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path
        try:
            if p in ("/", "/index.html"): return self.fichier(os.path.join(WEB, "index.html"))
            if p.startswith("/web/"): return self.fichier(os.path.join(WEB, os.path.basename(p)))
            if p.startswith("/fonts/"): return self.fichier(os.path.join(WEB, "fonts", os.path.basename(p)))
            if p == "/api/alerte":   # 29/10 : ElevenLabs refuse (mots.py) -> bandeau rouge en haut de l'écran
                f = os.path.expanduser("~/.claude/skills/supermonteur/.alerte-elevenlabs.json")
                return self.envoyer(200, json.load(open(f)) if os.path.exists(f) else {})
            if p == "/api/reels":
                importer_montages()
                L = [carte(r) for r in sorted(os.listdir(REELS), reverse=True) if os.path.isdir(os.path.join(REELS, r))]
                return self.envoyer(200, [x for x in L if x])
            m = re.fullmatch(r"/api/reel/([\w-]+)", p)
            if m: return self.envoyer(200, fiche(m.group(1)))
            if p == "/api/da": return self.envoyer(200, DA.resume())
            if p == "/api/superda":
                url = DA.superda_url()
                try:
                    urllib.request.urlopen(url + "/api/da", timeout=1.5)
                    ok = True
                except Exception:
                    ok = False
                return self.envoyer(200, {"url": url, "en_marche": ok})
            if p == "/api/metricool": return self.envoyer(200, metricool())
            m = re.fullmatch(r"/media/([\w-]+)/(.+)", p)
            if m:
                d = D(m.group(1))
                f = os.path.normpath(os.path.join(d, urllib.parse.unquote(m.group(2))))
                if not f.startswith(d + os.sep): return self.envoyer(403, {"erreur": "non"})
                return self.fichier(f)
            m = re.fullmatch(r"/api/telecharger/([\w-]+)", p)
            if m: return self.telecharger(m.group(1))
            return self.envoyer(404, {"erreur": "introuvable"})
        except KeyError:
            return self.envoyer(404, {"erreur": "reel introuvable"})

    def telecharger(self, rid):
        """Mode Télécharger : la vidéo + ses 5 légendes (une par réseau), dans un zip."""
        d = D(rid)
        e = lire(os.path.join(d, "etat.json"), {})
        v = os.path.join(d, e["versions"][-1]["fichier"])
        L = legendes(d)
        txt = "\n\n".join(f"{r}\n{L.get(r, '')}" for r in RESEAUX)
        if L.get("_brouillon"): txt = "Brouillon tiré du titre : demande à Claude d'écrire les vraies légendes.\n\n" + txt
        nom = f"{e.get('nom', rid)}-v{e.get('version')}"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            z.write(v, f"{nom}.mp4")
            z.writestr("legendes.txt", txt)
        self.envoyer(200, buf.getvalue(), "application/zip", {"Content-Disposition": f'attachment; filename="{nom}.zip"'})

    # ------------------------------------------------------------------------------------------------------ POST
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        o = self.headers.get("Origin")  # serrure : seule la page SuperMonteur peut envoyer des ordres, pas un autre site
        if o and o not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.envoyer(403, {"erreur": "refusé"})
        try:
            if p == "/api/upload": return self.upload()
            m = re.fullmatch(r"/api/ref-fichier/([\w-]+)", p)
            if m: return self.ref_fichier(m.group(1))
            m = re.fullmatch(r"/api/image-fichier/([\w-]+)/(\d+)", p)
            if m: return self.image_fichier(m.group(1), int(m.group(2)))
            b = self.corps()
            if p == "/api/nouveau": return self.nouveau(b.get("rush", ""))
            if p == "/api/demande-da":   # « Demande à Claude » du tiroir quand SuperDA ne tourne pas : Claude la lit
                L = lire(os.path.join(APP, "demandes-da.json"), []) or []
                L.append({"date": datetime.datetime.now().isoformat(timespec="seconds"), "reel": b.get("reel"), "texte": b.get("texte", "")})
                ecrire(os.path.join(APP, "demandes-da.json"), L)
                return self.envoyer(200, {"ok": True})
            m = re.fullmatch(r"/api/(\w+)/([\w-]+)", p)
            if not m: return self.envoyer(404, {"erreur": "introuvable"})
            act, rid = m.groups()
            d = D(rid)
            e = lire(os.path.join(d, "etat.json"), {})
            if act == "monter":
                if e.get("statut") in ("montage",): return self.envoyer(409, {"erreur": "déjà en cours"})
                style = b.get("style") if b.get("style") in CASES else e.get("conseil", "Dynamique")
                # 29/10 : montage à reprendre pour CE reel (lien Instagram / TikTok / YouTube, ou vidéo glissée) ; la police reste la DA
                ref, lien, fic = None, (b.get("lien") or "").strip(), os.path.basename(b.get("fichier") or "")
                if lien:
                    if not LIEN_REF.match(lien): return self.envoyer(400, {"erreur": "colle un lien Instagram, TikTok ou YouTube"})
                    ref = {"lien": lien}
                elif fic:
                    if not os.path.isfile(os.path.join(d, "ref", fic)): return self.envoyer(400, {"erreur": "vidéo à reprendre introuvable : glisse-la à nouveau"})
                    ref = {"fichier": fic}
                if style == "Inspiration" and not ref: return self.envoyer(400, {"erreur": "colle le lien ou glisse la vidéo à reprendre"})
                etat(d, statut="montage", style=style, cases=b.get("cases", {}), reference=ref, etape="Je prépare le montage…", erreur=None)
                lancer("monter", rid)
                return self.envoyer(200, fiche(rid))
            if act == "derush_ok":  # 29/10 « Monter le reel » sous le Derush Lab : monter.py attend ce feu vert
                if e.get("statut") != "derush": return self.envoyer(409, {"erreur": "le dérush est déjà validé"})
                v = lab_valide(d)
                if not v: return self.envoyer(409, {"erreur": "clique d'abord « ✓ Valider le dérush » en bas"})
                if v == "rouge" and not b.get("forcer"): return self.envoyer(409, {"erreur": "le Gardien voit un point à régler"})
                arreter_lab(rid)
                etat(d, derush_ok=True, etape="Je prends ton dérush…")
                try:   # le monter.py qui attendait est toujours là ? (Mac redémarré = non : on relance la suite)
                    os.kill(int(e.get("pid_derush") or 0), 0)
                    vivant = int(e.get("pid_derush") or 0) > 0 and "monter.py" in subprocess.run(
                        ["ps", "-o", "command=", "-p", str(e["pid_derush"])], capture_output=True, text=True).stdout
                except Exception:
                    vivant = False
                if not vivant:
                    etat(d, statut="montage")
                    lancer("suite", rid)
                return self.envoyer(200, fiche(rid))
            if act == "images":     # 29/10 « Monter avec ces images » : ses choix, puis Claude monte au style de la référence
                if e.get("statut") != "images": return self.envoyer(409, {"erreur": "les images sont déjà envoyées"})
                images.prendre(d, b.get("pris") or {})
                pousser_ref(d, texte=e.get("images_texte"))
                return self.envoyer(200, fiche(rid))
            if act == "retour":
                R = lire(os.path.join(d, "retours.json"), []) or []
                texte = (b.get("texte") or "").strip()
                if not texte: return self.envoyer(400, {"erreur": "retour vide"})
                R.append({"id": max([x["id"] for x in R] or [0]) + 1, "t": round(float(b.get("t", 0)), 2), "texte": texte,
                          "statut": "a_faire", "version": e.get("version", 1), "reponse": "",
                          "date": datetime.datetime.now().isoformat(timespec="seconds")})
                ecrire(os.path.join(d, "retours.json"), R)
                return self.envoyer(200, fiche(rid))
            if act == "effacer":     # retirer un retour pas encore envoyé (faute de frappe)
                R = [x for x in lire(os.path.join(d, "retours.json"), []) if not (x["id"] == b.get("id") and x["statut"] == "a_faire")]
                ecrire(os.path.join(d, "retours.json"), R)
                return self.envoyer(200, fiche(rid))
            if act == "suivant":
                R = lire(os.path.join(d, "retours.json"), []) or []
                a_faire = [x for x in R if x["statut"] == "a_faire"]
                if not a_faire: return self.envoyer(400, {"erreur": "aucun retour à corriger"})
                dem = {"reel": rid, "dossier": d, "version": e.get("version"), "date": datetime.datetime.now().isoformat(timespec="seconds"),
                       "retours": a_faire, "a_faire": "Lire CLAUDE.md : corriger plan.json pour chaque retour, puis python3 monter.py remonter <dossier>, puis statut corrige + reponse dans retours.json"}
                ecrire(os.path.join(d, "demande.json"), dem)
                boite = lire(os.path.join(APP, "a-corriger.json"), []) or []
                boite = [x for x in boite if x.get("reel") != rid] + [dem]
                ecrire(os.path.join(APP, "a-corriger.json"), boite)
                etat(d, statut="correction", etape="Retours envoyés : Claude corrige et remonte la version suivante.")
                return self.envoyer(200, fiche(rid))
            if act == "valider":
                etat(d, statut="valide", valide_le=datetime.datetime.now().isoformat(timespec="seconds"))
                return self.envoyer(200, fiche(rid))
            if act == "rouvrir":
                etat(d, statut="retours")
                return self.envoyer(200, fiche(rid))
            if act == "cacher":      # 29/10 « Supprimer » de l'accueil (2 clics) : le projet disparaît, ses fichiers et le rush restent
                etat(d, cache=datetime.datetime.now().isoformat(timespec="seconds"))
                return self.envoyer(200, {"ok": True})
            if act == "publier":
                if reglages_apps.mode_essai(APP):
                    return self.envoyer(400, {"ok": False, "message": "Mode essai : rien n'est publié. Pour publier pour de vrai : "
                                                                      "supermonteur/config.json, \"mode_essai\": false."})
                # 28/10 : vraie publication. Le clic confirmé = le OK de l’utilisateur pour CE reel ; Claude envoie (apps/publier.py).
                reseaux, quand = [r for r in (b.get("reseaux") or []) if r in RESEAUX], b.get("quand") or ""
                if not reseaux:
                    return self.envoyer(400, {"ok": False, "message": "Choisis au moins un réseau."})
                ok, msg = publier.demander(d, "reel", reseaux, quand, titre_reel(d) or e.get("nom", rid), cles_registre=(rid,),
                                           forcer=bool(b.get("forcer")))
                if msg.startswith("DEJA:"): return self.envoyer(409, {"deja": msg[5:]})
                if not ok: return self.envoyer(400, {"ok": False, "message": msg})
                return self.envoyer(200, {"ok": True, "message": msg, "publication": publier.etat(d)})
            return self.envoyer(404, {"erreur": "action inconnue"})
        except KeyError:
            return self.envoyer(404, {"erreur": "reel introuvable"})

    def nouveau(self, rush):
        rush = os.path.expanduser(rush.strip().strip("'\""))
        if not os.path.isfile(rush): return self.envoyer(400, {"erreur": f"vidéo introuvable : {rush}"})
        base = re.sub(r"[^\w-]", "", os.path.splitext(os.path.basename(rush))[0]).lower() or "reel"
        rid = f"{datetime.date.today():%Y-%m-%d}-{base}"
        k = 2
        while True:   # 29/10 : deux imports dans la même seconde plantaient (FileExistsError)
            try: os.makedirs(os.path.join(REELS, rid)); break
            except FileExistsError:
                rid = f"{datetime.date.today():%Y-%m-%d}-{base}-{k}"
                k += 1
        d = os.path.join(REELS, rid)
        ecrire(os.path.join(d, "etat.json"), {"id": rid, "nom": os.path.splitext(os.path.basename(rush))[0], "rush": rush,
                                              "cree": datetime.datetime.now().isoformat(timespec="seconds"), "statut": "regarde",
                                              "etape": "Je regarde ta vidéo…", "version": 0, "versions": []})
        ecrire(os.path.join(d, "retours.json"), [])
        lancer("regarder", rid)
        return self.envoyer(200, fiche(rid))

    def upload(self):
        """Vidéo glissée sur la page : copiée dans reels/_rushs/ (pas de copie si elle vient déjà du Mac par son chemin)."""
        nom = os.path.basename(urllib.parse.unquote(self.headers.get("X-Nom", "rush.mp4")))
        dst = os.path.join(REELS, "_rushs")
        os.makedirs(dst, exist_ok=True)
        p = os.path.join(dst, re.sub(r"[^\w.-]", "_", nom))
        n = int(self.headers.get("Content-Length") or 0)
        # 29/10 (CAM20062 : copie arrêtée à 5,8 / 6,4 Go, vidéo illisible) : copie dans .part, gardée seulement si complète
        part = p + ".part"
        with open(part, "wb") as f:
            while n > 0:
                bloc = self.rfile.read(min(1 << 20, n))
                if not bloc: break
                f.write(bloc)
                n -= len(bloc)
        if n > 0:
            os.remove(part)   # copie partielle faite par ce serveur, jamais la vidéo d'origine
            return self.envoyer(400, {"erreur": "import coupé en route : colle plutôt le chemin de la vidéo"})
        os.replace(part, p)
        return self.nouveau(p)

    def image_fichier(self, rid, n):
        """29/10 : sa vidéo glissée sur un plan de l'écran « Tes images » (il l'a filmée pour ce plan) : copiée dans
        reels/<id>/images/, ajoutée aux choix du plan et choisie."""
        dst = os.path.join(D(rid), "images")
        os.makedirs(dst, exist_ok=True)
        nom = re.sub(r"[^\w.-]", "_", os.path.basename(urllib.parse.unquote(self.headers.get("X-Nom", "video.mp4"))))
        p = os.path.join(dst, f"perso-{n}-{nom}")
        reste = int(self.headers.get("Content-Length") or 0)
        with open(p + ".part", "wb") as f:
            while reste > 0:
                bloc = self.rfile.read(min(1 << 20, reste))
                if not bloc: break
                f.write(bloc)
                reste -= len(bloc)
        if reste > 0:
            os.remove(p + ".part")
            return self.envoyer(400, {"erreur": "import coupé en route : glisse-la à nouveau"})
        os.replace(p + ".part", p)
        try:
            images.perso(D(rid), n, p)
        except Exception as x:
            return self.envoyer(400, {"erreur": f"vidéo illisible : {str(x)[:120]}"})
        return self.envoyer(200, fiche(rid))

    def ref_fichier(self, rid):
        """Vidéo à reprendre glissée sur l'écran 0 : copiée dans reels/<id>/ref/ (lue par monter.py après la v1)."""
        dst = os.path.join(D(rid), "ref")
        os.makedirs(dst, exist_ok=True)
        nom = re.sub(r"[^\w.-]", "_", os.path.basename(urllib.parse.unquote(self.headers.get("X-Nom", "reference.mp4"))))
        n = int(self.headers.get("Content-Length") or 0)
        with open(os.path.join(dst, nom), "wb") as f:
            while n > 0:
                bloc = self.rfile.read(min(1 << 20, n))
                if not bloc: break
                f.write(bloc)
                n -= len(bloc)
        return self.envoyer(200, {"fichier": nom})


if __name__ == "__main__":
    print(f"SuperMonteur : http://localhost:{PORT}")
    threading.Thread(target=ouvrier, daemon=True).start()
    threading.Thread(target=publieur, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
