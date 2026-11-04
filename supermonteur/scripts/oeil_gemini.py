"""L'Œil (31/10/2026, méthode theyo) : Gemini regarde la vidéo EN ENTIER et la note. Claude ne voit que des images isolées, Gemini voit
le rythme, les coupes, le son. Le juge n'est jamais celui qui a monté.
  python3 oeil_gemini.py <video.mp4 | lien YouTube> [--grille grille.md] [--prompt "texte libre"] [--sortie oeil-gemini.json] [--modele gemini-3.1-pro-preview] [--regles regles-oeil.md | --regles non]
Sans --prompt : rend le JSON {note, criteres, a_corriger, verdict} sur la grille (défaut : note-10-youtube.md en 16:9, note-10.md en vertical). Avec --prompt : réponse libre.
Vidéo locale : copie légère 480p envoyée à Google, effacée de chez eux après la réponse. Code de sortie : 0 = note >= 9, 1 = à refaire.
Clé : GEMINI_API_KEY, sinon trousseau (service supermonteur-gemini, compte = prénom de marque.json), jamais dans un fichier.
Chez un client : seulement avec SA clé (son rush ne part pas sur le compte de l'utilisateur).
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import reglages

a = sys.argv[1:]
if not a: sys.exit(__doc__)
def opt(name, default=None):
    return a[a.index(name) + 1] if name in a else default
src = a[0]
modele = opt("--modele", "gemini-3.1-pro-preview")
grille = opt("--grille")
if not grille:   # 16:9 = grille YouTube, vertical = grille reel
    larg = bool(re.match(r"https://", src))
    if not larg:
        w, h = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src]).decode().strip().split(",")[:2]
        larg = int(w) > int(h)
    grille = os.path.join(S, "..", "note-10-youtube.md" if larg else "note-10.md")
prompt_libre, sortie = opt("--prompt"), opt("--sortie")
regles = opt("--regles", "non" if "youtube" in grille else os.path.join(S, "..", "regles-oeil.md"))   # goûts de l’utilisateur sur les reels, tirés de ses retours (calibrage 31/10)

try: client = reglages.config().get("client")
except Exception: client = None
try: moi = (json.load(open(os.path.join(os.path.dirname(reglages.REG), "marque.json"))).get("prenom") or "").lower()
except Exception: moi = ""
compte = client or moi or "moi"
key = os.environ.get("GEMINI_API_KEY") or subprocess.run(
    ["security", "find-generic-password", "-s", "supermonteur-gemini", "-a", compte, "-w"], capture_output=True, text=True).stdout.strip()
if not key:
    sys.exit(f"Pas de clé Gemini pour '{compte}' : https://aistudio.google.com/apikey , puis rangée au trousseau (service supermonteur-gemini).")
BASE = "https://generativelanguage.googleapis.com"
H = {"x-goog-api-key": key}


def req(url, body=None, headers=None, method=None, timeout=600):
    r = urllib.request.Request(url, body, {**H, **(headers or {})}, method=method)
    return urllib.request.urlopen(r, timeout=timeout)


def envoie(path):
    """Copie 480p (une vidéo longue passe en quelques Mo), envoi résumable, attente ACTIVE. Rend (uri, nom)."""
    tmp = tempfile.mkdtemp()
    proxy = os.path.join(tmp, "proxy.mp4")
    w, h = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", path]).decode().strip().split(",")[:2]
    taille = "scale=-2:480" if int(w) > int(h) else "scale=540:-2"   # vertical : sous-titres lisibles
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf", taille, "-c:v", "h264_videotoolbox", "-b:v", "900k",
                    "-c:a", "aac", "-b:a", "96k", proxy], check=True)
    data = open(proxy, "rb").read()
    r = req(f"{BASE}/upload/v1beta/files", json.dumps({"file": {"display_name": "montage"}}).encode(),
            {"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start", "X-Goog-Upload-Header-Content-Length": str(len(data)),
             "X-Goog-Upload-Header-Content-Type": "video/mp4", "Content-Type": "application/json"})
    url = r.headers["X-Goog-Upload-URL"]
    f = json.load(req(url, data, {"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"}, timeout=900))["file"]
    while f.get("state") == "PROCESSING":
        time.sleep(5)
        f = json.load(req(f"{BASE}/v1beta/{f['name']}"))
    if f.get("state") != "ACTIVE": sys.exit(f"Google n'a pas accepté la vidéo : {f.get('state')}")
    return f["uri"], f["name"]


CONSIGNE = """Tu es le chef monteur le plus dur d'une chaîne YouTube à 1 million d'abonnés. Tu juges ce montage, tu ne l'as pas fait.
Regarde la vidéo entière et écoute-la. Note chaque critère de la grille, sans gonfler : dans le doute, la note du bas.
Chaque défaut a un timecode précis et une correction faisable. Réponds en français simple.
Un 10 veut dire rien à corriger : si tu listes un défaut, le critère concerné ne peut pas valoir 1, et la note suit.

GRILLE :
"""
SCHEMA = {"type": "object", "required": ["note", "criteres", "a_corriger", "verdict"], "properties": {
    "note": {"type": "number"}, "verdict": {"type": "string"},
    "criteres": {"type": "array", "items": {"type": "object", "required": ["nom", "note", "preuve"], "properties": {
        "nom": {"type": "string"}, "note": {"type": "number"}, "preuve": {"type": "string"}}}},
    "a_corriger": {"type": "array", "items": {"type": "object", "required": ["timecode", "probleme", "correction"], "properties": {
        "timecode": {"type": "string"}, "probleme": {"type": "string"}, "correction": {"type": "string"}}}}}}

nom = None
youtube = re.match(r"https://(www\.|m\.)?(youtube\.com|youtu\.be)/", src)
if youtube: uri = src
else: uri, nom = envoie(src)
parts = [{"file_data": {"file_uri": uri, **({} if youtube else {"mime_type": "video/mp4"})}}]
texte_regles = open(regles, encoding="utf8").read() if regles != "non" and os.path.exists(regles) else ""
parts.append({"text": prompt_libre or CONSIGNE + open(grille, encoding="utf8").read() + ("\n\nRÈGLES DE CYRIL (elles passent avant la grille) :\n" + texte_regles if texte_regles else "")})
body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": 0.2}}
if not prompt_libre:
    body["generationConfig"].update({"responseMimeType": "application/json", "responseSchema": SCHEMA})
try:
    rep = json.load(req(f"{BASE}/v1beta/models/{modele}:generateContent", json.dumps(body).encode(), {"Content-Type": "application/json"}, timeout=900))
except urllib.error.HTTPError as e:
    sys.exit(f"Gemini a refusé : {e.code} {e.read().decode()[:400]}")
finally:
    if nom:
        try: req(f"{BASE}/v1beta/{nom}", method="DELETE")
        except Exception: pass

texte = "".join(p.get("text", "") for p in rep["candidates"][0]["content"]["parts"])
u = rep.get("usageMetadata", {})
print(f"[Œil] {modele} · {u.get('totalTokenCount', '?')} jetons", file=sys.stderr)
if sortie: open(sortie, "w", encoding="utf8").write(texte)
print(texte)
if not prompt_libre:
    sys.exit(0 if json.loads(texte)["note"] >= 9 else 1)
