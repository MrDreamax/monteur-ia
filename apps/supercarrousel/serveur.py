"""SuperCarrousel : petit serveur local (port 8797). Sert l'écran (static/) et fait tourner le moteur.
  python3 serveur.py [port]
Ce que le serveur fait seul : lire le reel (images + texte), rendre chaque version slide par slide, ranger les retours,
préparer le Télécharger. Ce que Claude fait (lancé par le serveur lui-même, ouvrier_claude.py, via sc.py) : écrire le
texte des slides (description.json) et corriger les retours. Le serveur ne publie RIEN : la publication passe par Claude, avec le OK de l'utilisateur.
"""
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import moteur as m
import sc

sys.path.insert(0, os.path.dirname(m.ICI))
import ouvrier_claude
import publier
import reglages_apps

ICI = m.ICI
STATIC = os.path.join(ICI, "static")
CONFIG = os.path.join(ICI, "config.json")
VERROU = threading.Lock()  # Mac 8 Go : un seul rendu (ou une seule lecture de reel) à la fois
EN_COURS = set()


def port_superda():
    """Port de SuperDA : celui de son entrée dans .claude/launch.json, sinon celui du contrat (8765)."""
    return reglages_apps.port("superda")
    return 8765


def config():
    c = m.lire(CONFIG, {})
    return {"mode_essai": c.get("mode_essai", True) is not False, "superda_port": c.get("superda_port") or port_superda(),
            "claude_auto": c.get("claude_auto", True)}  # false = c'est un chat Claude qui écrit (sc.py attendre)


# ---------------------------------------------------------------- préparation (avant l'écriture du texte)

def _mots_a_cote(video):
    d = os.path.dirname(video)
    for n in ("words.json", "rush.words.json", "words_rush.json"):
        p = os.path.join(d, n)
        if os.path.exists(p):
            return p
    return None


def _telecharger_lien(lien, dest):
    out = os.path.join(dest, "source.%(ext)s")
    r = subprocess.run([os.path.expanduser("~/.local/bin/yt-dlp"), "-q", "--no-playlist", "-f", "mp4/best", "-o", out, lien],
                       capture_output=True, text=True, timeout=300)
    vids = [f for f in os.listdir(dest) if f.startswith("source.")]
    if r.returncode or not vids:
        raise RuntimeError((r.stderr or r.stdout or "lien illisible").strip().splitlines()[-1][:200])
    return os.path.join(dest, vids[0])


def _images_carrousel(lien, dest):
    """29/10 : yt-dlp ne prend que les vidéos (« No video formats found » sur un carrousel photo). On lit les slides
    avec la session Instagram déjà ouverte dans Chrome (module insta de SuperVeille, lecture seule). Renvoie le nombre."""
    code = re.search(r"instagram\.com/(?:[^/?#]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", lien)
    if not code:
        raise RuntimeError("pas un lien de post Instagram")
    sys.path.insert(0, os.path.join(os.path.dirname(ICI), "superveille"))
    import insta
    n = 0
    for ch in code.group(1)[:11]:  # le code du lien = le numéro du post en base 64 d'Instagram
        n = n * 64 + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_".index(ch)
    for p in insta.profils():
        try:
            op, _ = insta.session(p)
            if not op:
                continue
            it = (json.load(op.open(f"https://www.instagram.com/api/v1/media/{n}/info/", timeout=20)).get("items") or [{}])[0]
        except Exception:
            continue
        slides = [c for c in (it.get("carousel_media") or [it]) if (c.get("image_versions2") or {}).get("candidates")]
        for i, c in enumerate(slides, 1):
            with open(os.path.join(dest, f"modele-{i:02d}.jpg"), "wb") as f:
                f.write(op.open(c["image_versions2"]["candidates"][0]["url"], timeout=30).read())
        if slides:
            return len(slides)
    raise RuntimeError("Instagram n'a rien rendu (session Chrome fermée ?)")


def preparer(pid):
    d = m.lire(m.chemin(pid, "demande.json"))
    try:
        with VERROU:
            if d["depart"] == "reel":
                m.maj_etat(pid, statut="prepa", message="Je regarde ton reel…")
                video = d.get("video")
                if not video:
                    video = _telecharger_lien(d["lien"], m.chemin(pid))
                reel = m.chemin(pid, "_reel")
                os.makedirs(reel, exist_ok=True)
                mots = _mots_a_cote(video)
                if not mots:  # pas de transcription à côté : celle du Monteur (ElevenLabs, Whisper du Mac en secours)
                    m.maj_etat(pid, message="J'écoute ton reel…")
                    sys.path.insert(0, os.path.expanduser("~/.claude/skills/supermonteur/scripts"))
                    from mots import transcrire
                    words, _ = transcrire(video, langue="fr", secours=True)   # 29/10 : le blocage ElevenLabs vise le montage seul
                    mots = os.path.join(reel, "words.json")
                    m.ecrire(mots, {"words": words})
                m.maj_etat(pid, message="Je choisis les meilleures images…")
                subprocess.run([sys.executable, os.path.join(m.SKILL, "reel2frames.py"), video, reel, "--words", mots],
                               check=True, capture_output=True, timeout=600)
            elif d["depart"] == "reprendre":
                mod = m.chemin(pid, "_modele")
                os.makedirs(mod, exist_ok=True)
                if d.get("images"):
                    for i, p in enumerate(d["images"], 1):
                        shutil.copy(p, os.path.join(mod, f"modele-{i:02d}{os.path.splitext(p)[1].lower()}"))
                else:
                    m.maj_etat(pid, statut="prepa", message="Je récupère le carrousel…")
                    try:
                        try:
                            _images_carrousel(d["lien"], mod)
                        except Exception:
                            _telecharger_lien(d["lien"], mod)
                    except Exception as e:
                        m.maj_etat(pid, statut="besoin_images", message="Je n'arrive pas à lire ce lien. Dépose les captures "
                                   "du carrousel (une image par slide) dans la zone de dépôt.", detail=str(e))
                        return
        m.maj_etat(pid, statut="attente_texte", message="J'écris ton carrousel…", depuis=time.time())
    except Exception as e:
        traceback.print_exc()
        m.maj_etat(pid, statut="erreur", message="La lecture a planté. Réessaie ou change de vidéo.", detail=str(e)[:300])


# ---------------------------------------------------------------- rendu (boucle de fond)

def appliquer_corrections(pid, v):
    desc = m.lire(m.chemin(pid, f"v{v}", "description.json"), {})
    faites = {int(c["retour"]): c for c in desc.get("corrections", [])}
    rs = m.lire(m.chemin(pid, "retours.json"), [])
    for r in rs:
        if r["statut"] == "envoye":
            if r["id"] in faites:
                c = faites[r["id"]]
                r.update(statut="corrige", reponse=c.get("ligne", "corrigé"), version=v, slide=int(c.get("slide", r["slide"])))
            else:
                r["statut"] = "a_faire"  # pas traité : il revient dans la liste, rien ne se perd
    m.ecrire(m.chemin(pid, "retours.json"), rs)


def rendre(pid, v):
    def avance(i, n):
        m.maj_etat(pid, fab={"faites": i, "total": n})
    try:
        n = len(m.lire(m.chemin(pid, f"v{v}", "description.json"))["slides"])
        m.maj_etat(pid, statut="fabrication", version_en_cours=v, fab={"faites": 0, "total": n},
                   message=("J'écris" if v == 1 else "Je corrige"))
        m.rendre(pid, v, avance)
        appliquer_corrections(pid, v)
        desc = m.lire(m.chemin(pid, f"v{v}", "description.json"))
        m.maj_etat(pid, statut="retours", version=v, titre=desc.get("name") or m.etat(pid).get("titre"), message="")
    except Exception as e:
        traceback.print_exc()
        m.ecrire(m.chemin(pid, f"v{v}", "erreur.json"), {"erreur": str(e)[:500]})
        m.maj_etat(pid, statut="erreur", message="Le rendu a planté. Claude doit corriger la description.", detail=str(e)[:300])


def boucle():
    while True:
        try:
            for pid in sorted(os.listdir(m.PROJETS)) if os.path.isdir(m.PROJETS) else []:
                for v in m.versions(pid):
                    vd = m.chemin(pid, f"v{v}")
                    if (os.path.exists(os.path.join(vd, "description.json")) and not os.path.exists(os.path.join(vd, "rendu.json"))
                            and not os.path.exists(os.path.join(vd, "erreur.json")) and (pid, v) not in EN_COURS):
                        EN_COURS.add((pid, v))
                        with VERROU:
                            rendre(pid, v)
                        EN_COURS.discard((pid, v))
        except Exception:
            traceback.print_exc()
        time.sleep(1)


CONSIGNE = """Tu es Claude, DANS l'appli SuperCarrousel de l’utilisateur (dossier actuel). N'ouvre rien, ne lance aucun serveur, ne publie rien.
L'écran attend que tu fasses ceci pour le projet %s : %s.
1. Lance `python3 sc.py a-faire` : il dit tout (départ, idée ou lien, images du reel, texte, DA, retours à corriger).
2. Lis le skill carrousel (~/.claude/skills/carrousel/SKILL.md et les fichiers qu'il cite) et suis sa méthode pour écrire la description
   (étapes 1-2 et 3 bis), au format du README.md d'ici et de `python3 sc.py --aide`. Regarde les images avec Read.
   Ajoute "name", "legendes" {instagram, tiktok, facebook, linkedin} (1-2 phrases, 0 hashtag) et, pour des retours, "corrections".
3. Écris le fichier dans projets/%s/brouillon.json puis lance `python3 sc.py ecrire %s projets/%s/brouillon.json`.
   S'il refuse, corrige le fichier et recommence. Jamais d'image IA. Ne touche qu'au dossier projets/%s.
   Photos : regarde chaque photo avant de la prendre ; évite celles où un grand texte se lit derrière l’utilisateur (écran,
   slide projetée, panneau) : il se bat avec le titre. Titres sans point final (« ? » et « ! » ok).
Réponds en 1 ligne quand c'est posé."""
TENTATIVES = {}  # (projet, quoi, version) -> nombre d'essais


def ouvrier():
    """Fait écrire Claude dès que l'écran attend un texte ou des corrections : plus besoin d'un chat ouvert."""
    while True:
        try:
            if config().get("claude_auto", True):
                for quoi, pid in sc.demandes():
                    if quoi == "da":
                        continue  # les demandes de DA vont à SuperDA
                    cle = (pid, quoi, m.version_rendue(pid))
                    TENTATIVES[cle] = TENTATIVES.get(cle, 0) + 1
                    if TENTATIVES[cle] > 2:
                        if m.etat(pid).get("statut") != "erreur":
                            m.maj_etat(pid, statut="erreur", message="Claude n'a pas réussi à écrire ce carrousel.",
                                       detail="Détails dans supercarrousel/_claude.log. Réessaie, ou demande-le dans un chat Claude.")
                        continue
                    tache = "écrire la version 1" if quoi == "texte" else "corriger ses retours (version suivante)"
                    ouvrier_claude.lancer(CONSIGNE % (pid, tache, pid, pid, pid, pid), m.ICI,
                                          ["Read", "Write", "Edit", "Glob", "Grep", "Skill", "Bash(python3 sc.py:*)"])
                    break  # une demande à la fois, puis on relit la liste
        except Exception:
            traceback.print_exc()
        time.sleep(3)


# ---------------------------------------------------------------- vues

def metricool():
    """Lecture seule : Claude écrit metricool.json après avoir vérifié le compte (getBrandSettings), sans rien publier."""
    mc = m.lire(os.path.join(ICI, "metricool.json"), {})
    frais = time.time() - mc.get("verifie_ts", 0) < 7 * 86400
    return {"branche": bool(mc.get("branche")) and frais, "compte": mc.get("compte", ""), "verifie_le": mc.get("verifie_le", "")}


def superda():
    port = config()["superda_port"]
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/da", timeout=0.6):
            en_ligne = True
    except Exception:
        en_ligne = False
    return {"port": port, "en_ligne": en_ligne, "url": f"http://localhost:{port}/?tiroir=carrousels"}


def mes_carrousels(n=8):
    """Les derniers carrousels déjà fabriqués, pour les rouvrir depuis l'accueil (le plus récent d'abord)."""
    out = []
    for pid in sorted(os.listdir(m.PROJETS), reverse=True):
        if pid.startswith("_") or not os.path.isdir(m.chemin(pid)):
            continue
        v = m.version_rendue(pid)
        if not v:
            continue
        e = m.etat(pid)
        out.append({"id": pid, "titre": e.get("titre", pid), "version": v, "valide": e.get("statut") == "valide",
                    "vignette": f"/p/{pid}/v{v}/slide-1.png"})
        if len(out) == n:
            break
    return out


def publieur():
    """Dès qu'un carrousel a un publication.json « a_faire » (clic confirmé de l’utilisateur), Claude l'envoie à Metricool."""
    for pid in os.listdir(m.PROJETS):   # envoi coupé par un redémarrage : on ne sait pas ce qui est parti
        if os.path.isdir(m.chemin(pid)) and publier.etat(m.chemin(pid)).get("statut") == "en_cours":
            publier._maj(m.chemin(pid), statut="erreur", etape="", message="Envoi coupé (serveur relancé) : vérifie le planner Metricool avant de relancer.")
    while True:
        try:
            for pid in sorted(os.listdir(m.PROJETS)):
                if pid.startswith("_") or publier.etat(m.chemin(pid)).get("statut") != "a_faire":
                    continue
                v = m.version_rendue(pid)
                n = m.lire(m.chemin(pid, f"v{v}", "rendu.json"))["slides"]
                publier.lancer(m.chemin(pid), "SuperCarrousel",
                               {"slides": [m.chemin(pid, f"v{v}", f"slide-{i}.png") for i in range(1, n + 1)],
                                "legendes": m.legendes(m.lire(m.chemin(pid, f"v{v}", "description.json")))})
        except Exception:
            traceback.print_exc()
        time.sleep(3)


def vue_projet(pid):
    e = m.etat(pid)
    v = m.version_rendue(pid)
    out = {"id": pid, "etat": e, "version": v, "slides": [], "retours": m.lire(m.chemin(pid, "retours.json"), []),
           "demande": m.lire(m.chemin(pid, "demande.json"), {})}
    if e.get("statut") in ("attente_texte", "attente_corrections") and e.get("depuis"):
        out["attente_s"] = int(time.time() - e["depuis"])
    if v:
        r = m.lire(m.chemin(pid, f"v{v}", "rendu.json"))
        stamp = int(r.get("fini", 0))
        out["slides"] = [f"/p/{pid}/v{v}/slide-{i}.png?t={stamp}" for i in range(1, r["slides"] + 1)]
        out["modele_rendu"] = r.get("modele", "epure")
        out["da_rendue"] = r.get("da")
    out["publication"] = publier.etat(m.chemin(pid))
    out["deja_publie"] = publier.deja_publie(pid)
    vc = e.get("version_en_cours")
    if e.get("statut") == "fabrication" and vc:
        fab = e.get("fab", {})
        out["en_cours"] = [f"/p/{pid}/v{vc}/slide-{i}.png?t={int(e.get('maj', 0))}" for i in range(1, fab.get("faites", 0) + 1)]
    return out


def nouveau_projet(d):
    base = time.strftime("%Y-%m-%d-%H%M%S")
    pid = base
    os.makedirs(m.chemin(pid), exist_ok=True)
    titre = {"reel": "Depuis un reel", "reprendre": "Carrousel à reprendre", "idee": (d.get("idee") or "Une idée")[:60]}[d["depart"]]
    d["cree"] = time.strftime("%Y-%m-%d %H:%M")
    m.ecrire(m.chemin(pid, "demande.json"), d)
    m.ecrire(m.chemin(pid, "retours.json"), [])
    m.maj_etat(pid, statut="prepa", titre=titre, version=0, message="Je prépare…", depuis=time.time())
    threading.Thread(target=preparer, args=(pid,), daemon=True).start()
    return pid


def videos():
    out = []
    for dossier, racine in (("reels", os.path.join(os.path.dirname(ICI), "supermonteur", "reels")), ("montages", reglages_apps.chemin("montages"))):
        if not os.path.isdir(racine):
            continue
        for n in sorted(os.listdir(racine), reverse=True):
            v = os.path.join(racine, n, "clip.mp4")
            if os.path.exists(v):
                out.append({"nom": n, "dossier": dossier, "video": v,
                            "vignette": "/api/vignette?c=" + urllib.parse.quote(v)})
    return out


def vignette(video):
    cache = os.path.join(m.PROJETS, "_vignettes")
    os.makedirs(cache, exist_ok=True)
    f = os.path.join(cache, hashlib.md5(video.encode()).hexdigest()[:12] + ".jpg")
    if not os.path.exists(f):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", video, "-frames:v", "1",
                        "-vf", "scale=180:-2", f], timeout=60)
    return f


# ---------------------------------------------------------------- HTTP

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        b = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _fichier(self, p):
        if not os.path.isfile(p):
            return self._json({"erreur": "introuvable"}, 404)
        ct = mimetypes.guess_type(p)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ct + ("; charset=utf-8" if ct.startswith("text/") else ""))
        self.send_header("Content-Length", str(os.path.getsize(p)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(p, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def _corps(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        if p == "/":
            return self._fichier(os.path.join(STATIC, "index.html"))
        if p.startswith("/static/"):
            f = os.path.normpath(os.path.join(STATIC, p[8:]))
            return self._fichier(f) if f.startswith(STATIC) else self._json({}, 403)
        if p.startswith("/p/"):
            f = os.path.normpath(os.path.join(m.PROJETS, urllib.parse.unquote(p[3:])))
            return self._fichier(f) if f.startswith(m.PROJETS) else self._json({}, 403)
        if p == "/api/accueil":
            return self._json({"da": m.resume_da(), "superda": superda(), "metricool": metricool(),
                               "mode_essai": config()["mode_essai"], "projets": mes_carrousels()})
        if p == "/api/videos":
            return self._json(videos())
        if p == "/api/vignette":
            v = os.path.normpath(q.get("c", [""])[0])
            return self._fichier(vignette(v)) if v.startswith((os.path.dirname(ICI), reglages_apps.chemin("montages"))) and v.endswith(".mp4") else self._json({}, 403)
        mo = re.fullmatch(r"/api/projet/([\w-]+)", p)
        if mo and os.path.isdir(m.chemin(mo.group(1))):
            return self._json(vue_projet(mo.group(1)))
        return self._json({"erreur": "introuvable"}, 404)

    def _autre_site(self):
        """Serrure : seule la page SuperCarrousel elle-même peut envoyer des ordres (pas un autre site ouvert dans le navigateur)."""
        o = self.headers.get("Origin")
        port = self.server.server_address[1]
        if o and o not in ("http://localhost:%d" % port, "http://127.0.0.1:%d" % port):
            self._json({"erreur": "refusé"}, 403)
            return True
        return False

    def do_PUT(self):  # dépôt d'un fichier (vidéo ou captures d'un carrousel), en flux pour les grosses vidéos
        if self._autre_site():
            return
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/depot":
            return self._json({}, 404)
        nom = re.sub(r"[^\w.-]+", "-", urllib.parse.parse_qs(u.query).get("nom", ["fichier"])[0])[-80:]
        d = os.path.join(m.PROJETS, "_depots")
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, time.strftime("%H%M%S-") + nom)
        reste = int(self.headers.get("Content-Length") or 0)
        with open(f, "wb") as out:
            while reste > 0:
                b = self.rfile.read(min(reste, 1 << 20))
                if not b:
                    break
                out.write(b)
                reste -= len(b)
        return self._json({"chemin": f})

    def do_POST(self):
        if self._autre_site():
            return
        p = urllib.parse.urlparse(self.path).path
        d = self._corps()
        if p == "/api/fabriquer":
            if d.get("depart") not in ("reel", "reprendre", "idee"):
                return self._json({"erreur": "départ inconnu"}, 400)
            if d["depart"] == "idee" and not (d.get("idee") or "").strip():
                return self._json({"erreur": "Écris ton idée d'abord."}, 400)
            if d["depart"] == "reel" and not (d.get("video") or d.get("lien")):
                return self._json({"erreur": "Dépose une vidéo ou colle un lien."}, 400)
            if d["depart"] == "reprendre" and not (d.get("images") or d.get("lien")):
                return self._json({"erreur": "Colle le lien du carrousel ou dépose ses captures."}, 400)
            return self._json({"id": nouveau_projet(d)})
        if p == "/api/da/demande":
            f = os.path.join(m.PROJETS, "_demandes-da.json")
            dem = m.lire(f, [])
            dem.append({"texte": d.get("texte", ""), "quand": time.strftime("%Y-%m-%d %H:%M"), "faite": False})
            m.ecrire(f, dem)
            return self._json({"ok": True})
        mo = re.fullmatch(r"/api/projet/([\w-]+)/(\w+)", p)
        if not mo or not os.path.isdir(m.chemin(mo.group(1))):
            return self._json({"erreur": "introuvable"}, 404)
        pid, action = mo.groups()
        rs = m.lire(m.chemin(pid, "retours.json"), [])
        v = m.version_rendue(pid)
        if action == "retour":
            texte = (d.get("texte") or "").strip()
            if not texte:
                return self._json({"erreur": "vide"}, 400)
            rs.append({"id": max([r["id"] for r in rs] or [0]) + 1, "slide": int(d.get("slide", 1)), "texte": texte,
                       "version_vue": v, "statut": "a_faire", "quand": time.strftime("%H:%M")})
            m.ecrire(m.chemin(pid, "retours.json"), rs)
            return self._json(vue_projet(pid))
        if action == "suivant":
            a_faire = [r for r in rs if r["statut"] == "a_faire"]
            if not a_faire:
                return self._json({"erreur": "Aucun retour à corriger."}, 400)
            for r in a_faire:
                r["statut"] = "envoye"
            m.ecrire(m.chemin(pid, "retours.json"), rs)
            m.ecrire(m.chemin(pid, f"v{v}", "retours-a-corriger.json"),
                     {"version": v, "prochaine": v + 1, "retours": a_faire})
            m.maj_etat(pid, statut="attente_corrections", message="Je corrige tes retours…", depuis=time.time())
            return self._json(vue_projet(pid))
        if action == "valider":
            m.maj_etat(pid, statut="valide", valide_v=v)
            return self._json(vue_projet(pid))
        if action == "rouvrir":
            m.maj_etat(pid, statut="retours")
            return self._json(vue_projet(pid))
        if action == "telecharger":
            return self._json({"chemin": m.livraison(pid)})
        if action == "publier":
            if config()["mode_essai"]:
                return self._json({"essai": True, "message": "Mode essai : rien n'est publié."})
            # 28/10 : vraie publication. Le clic confirmé = le OK de l’utilisateur pour CE carrousel ; Claude envoie (apps/publier.py).
            ok, msg = publier.demander(m.chemin(pid), "carrousel",
                                       [r for r in (d.get("reseaux") or []) if r in ("instagram", "tiktok", "facebook", "linkedin")],
                                       d.get("quand") or "", m.etat(pid).get("titre", pid), cles_registre=(pid,), forcer=bool(d.get("forcer")))
            if msg.startswith("DEJA:"):
                return self._json({"deja": msg[5:]}, 409)
            return self._json({"ok": ok, "message": msg, "projet": vue_projet(pid)}, 200 if ok else 400)
        if action == "da":  # la DA a changé : même texte, nouvelle version rendue avec la nouvelle DA
            src = m.lire(m.chemin(pid, f"v{v}", "description.json"))
            src.pop("corrections", None)
            m.ecrire(m.chemin(pid, f"v{v + 1}", "description.json"), src)
            return self._json(vue_projet(pid))
        return self._json({"erreur": "action inconnue"}, 404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8797
    os.makedirs(m.PROJETS, exist_ok=True)
    threading.Thread(target=boucle, daemon=True).start()
    threading.Thread(target=ouvrier, daemon=True).start()
    threading.Thread(target=publieur, daemon=True).start()
    print(f"SuperCarrousel : http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
