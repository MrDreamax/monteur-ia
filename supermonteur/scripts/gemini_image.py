"""Génère une image avec Gemini (Nano Banana) sur la clé API du CLIENT : il paie à l'image, pas d'abonnement.
  python3 gemini_image.py "<prompt>" out.png [--client <prenom>] [--ratio 9:16] [--size 1K] [--model gemini-nano-banana-2.1] [--ref photo.jpg]

Clé : variable GEMINI_API_KEY, sinon trousseau macOS (jamais en clair dans un fichier) :
  security add-generic-password -s supermonteur-gemini -a <prenom> -w '<clé>'
Prix indicatif (ai.google.dev/gemini-api/docs/pricing, 10/2026) : Nano Banana 2.1 ≈ 0,034 $ en 1K, 0,05 $ en 2K.
"""
import base64, json, os, subprocess, sys, urllib.error, urllib.request

a = sys.argv[1:]
def opt(name, default):
    return a[a.index(name) + 1] if name in a else default
prompt, out = a[0], a[1]
try:
    _cfg_client = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"))).get("client")
except Exception:
    _cfg_client = None
client = opt("--client", _cfg_client or "cyril")
ratio, size, model, ref = opt("--ratio", "9:16"), opt("--size", "1K").upper(), opt("--model", "gemini-nano-banana-2.1"), opt("--ref", None)
# Le prompt de la DA dit souvent "vertical 9:16" : en 1:1 Gemini compose alors en vertical avec des bandes floues. On retire tout format écrit et on impose le bon.
import re
prompt = re.sub(r",?\s*(vertical|horizontal|square)?\s*\d{1,2}:\d{1,2}", "", prompt, flags=re.I).strip(" ,") + f", full-bleed {ratio} composition filling the whole frame, no borders"

key = os.environ.get("GEMINI_API_KEY")
if not key:
    r = subprocess.run(["security", "find-generic-password", "-s", "supermonteur-gemini", "-a", client, "-w"], capture_output=True, text=True)
    key = r.stdout.strip()
if not key:
    sys.exit(f"Pas de clé Gemini pour '{client}'. Le client la crée sur https://aistudio.google.com/apikey puis :\n"
             f"  security add-generic-password -s supermonteur-gemini -a {client} -w '<clé>'")

BASE = "https://generativelanguage.googleapis.com/v1beta"
def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)

def find_image(o):
    """Cherche récursivement le premier bloc base64 d'image dans la réponse (format Interactions ou generateContent)."""
    if isinstance(o, dict):
        mime = o.get("mime_type") or o.get("mimeType") or ""
        if isinstance(o.get("data"), str) and (mime.startswith("image") or len(o["data"]) > 1000):
            return o["data"]
        for v in o.values():
            if (d := find_image(v)):
                return d
    elif isinstance(o, list):
        for v in o:
            if (d := find_image(v)):
                return d

ref_b64 = base64.b64encode(open(ref, "rb").read()).decode() if ref else None
ref_mime = "image/png" if ref and ref.lower().endswith(".png") else "image/jpeg"

# 1) API Interactions (format actuel de la doc) ; 2) repli sur generateContent (format historique)
try:
    inp = [{"type": "text", "text": prompt}, {"type": "image", "mime_type": ref_mime, "data": ref_b64}] if ref_b64 else prompt
    res = post(f"{BASE}/interactions", {"model": model, "input": inp,
               "response_format": {"type": "image", "mime_type": "image/png", "aspect_ratio": ratio, "image_size": size}})
except urllib.error.HTTPError as e:
    first_err = e.read().decode()[:400]
    parts = [{"text": prompt}] + ([{"inlineData": {"mimeType": ref_mime, "data": ref_b64}}] if ref_b64 else [])
    try:
        res = post(f"{BASE}/models/{model}:generateContent", {"contents": [{"parts": parts}],
                   "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": ratio, "imageSize": size}}})
    except urllib.error.HTTPError as e2:
        sys.exit(f"Gemini a refusé.\nInteractions : {first_err}\ngenerateContent : {e2.read().decode()[:400]}")

img = find_image(res)
if not img:
    sys.exit("Pas d'image dans la réponse : " + json.dumps(res)[:600])
open(out, "wb").write(base64.b64decode(img))
print(f"OK {out} ({model}, {ratio}, {size}, client={client})")
