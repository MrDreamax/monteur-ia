"""SuperMonteur : le petit serveur local (28/10/2026).  python3 serveur.py [port]  ->  http://localhost:8801

Écrans : 0 style · 1 retours · 2 Ma DA (tiroir SuperDA) · 3 publier. Les reels vivent dans reels/<id>/ (etat.json,
retours.json, versions/). « Suivant : corrige mes retours » écrit reels/<id>/demande.json + a-corriger.json (la boîte
que Claude lit, mode d'emploi : CLAUDE.md). Rien ne part sur Internet : publication en mode essai, Metricool en lecture.
"""
import datetime, io, json, mimetypes, os, re, shutil, subprocess, sys, threading, time, urllib.parse, urllib.request, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP = os.path.dirname(os.path.abspath(__file__))
REELS = os.path.join(APP, "reels")
WEB = os.path.join(APP, "web")
sys.path.insert(0, APP)
import da as DA
from monter import lire, ecrire, etat
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
    "Autre": [],
}
RESEAUX = ["Instagram", "TikTok", "YouTube Shorts", "Facebook", "LinkedIn"]


def D(rid):
    if not re.fullmatch(r"[\w-]+", rid or ""): raise KeyError(rid)
    d = os.path.join(REELS, rid)
    if not os.path.isdir(d): raise KeyError(rid)
    return d


def lancer(action, rid):
    log = open(os.path.join(D(rid), f"_{action}.log"), "a")
    subprocess.Popen([sys.executable, os.path.join(APP, "monter.py"), action, D(rid)], stdout=log, stderr=log, cwd=APP,
                     start_new_session=True)


CONSIGNE = """Tu es Claude, DANS l'appli SuperMonteur de l'utilisateur (dossier actuel). Ne publie rien.
l'utilisateur a cliqué « Suivant : corrige mes retours » pour le reel %s (dossier %s, version %s). Ses retours :
%s
Suis la section « Quand l'utilisateur dit corrige mes retours » de CLAUDE.md (lis-le d'abord) et les règles du skill
~/.claude/skills/supermonteur/ (SKILL.md, feedback.md, fichier du style). Regarde l'image au temps de chaque retour
(`ffmpeg -ss <t> -i <dossier>/final.mp4 -frames:v 1 <dossier>/_retour-<n>.jpg` puis Read), corrige plan.json,
lance `python3 monter.py remonter <dossier>`, passe chaque retour traité en "statut": "corrige" + "reponse" (1 ligne) dans retours.json,
retire ce reel de a-corriger.json, et note 1 ligne datée par retour dans feedback-retours.md (ici).
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
    if not e:
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
    """Dès qu'un reel a un publication.json « a_faire » (clic confirmé de l'utilisateur), Claude l'envoie à Metricool."""
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
                etat(d, statut="montage", style=style, cases=b.get("cases", {}), etape="Je prépare le montage…", erreur=None)
                lancer("monter", rid)
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
            if act == "publier":
                if reglages_apps.mode_essai(APP):
                    return self.envoyer(400, {"ok": False, "message": "Mode essai : rien n'est publié. Pour publier pour de vrai : "
                                                                      "supermonteur/config.json, \"mode_essai\": false."})
                # 28/10 : vraie publication. Le clic confirmé = le OK de l'utilisateur pour CE reel ; Claude envoie (apps/publier.py).
                ok, msg = publier.demander(d, "reel", [r for r in (b.get("reseaux") or []) if r in RESEAUX], b.get("quand") or "",
                                           titre_reel(d) or e.get("nom", rid), cles_registre=(rid,), forcer=bool(b.get("forcer")))
                if msg.startswith("DEJA:"): return self.envoyer(409, {"deja": msg[5:]})
                return self.envoyer(200 if ok else 400, {"ok": ok, "message": msg, "publication": publier.etat(d)})
            return self.envoyer(404, {"erreur": "action inconnue"})
        except KeyError:
            return self.envoyer(404, {"erreur": "reel introuvable"})

    def nouveau(self, rush):
        rush = os.path.expanduser(rush.strip().strip("'\""))
        if not os.path.isfile(rush): return self.envoyer(400, {"erreur": f"vidéo introuvable : {rush}"})
        base = re.sub(r"[^\w-]", "", os.path.splitext(os.path.basename(rush))[0]).lower() or "reel"
        rid = f"{datetime.date.today():%Y-%m-%d}-{base}"
        k = 2
        while os.path.exists(os.path.join(REELS, rid)):
            rid = f"{datetime.date.today():%Y-%m-%d}-{base}-{k}"
            k += 1
        d = os.path.join(REELS, rid)
        os.makedirs(d)
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
        with open(p, "wb") as f:
            while n > 0:
                bloc = self.rfile.read(min(1 << 20, n))
                if not bloc: break
                f.write(bloc)
                n -= len(bloc)
        return self.nouveau(p)


if __name__ == "__main__":
    print(f"SuperMonteur : http://localhost:{PORT}")
    threading.Thread(target=ouvrier, daemon=True).start()
    threading.Thread(target=publieur, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
