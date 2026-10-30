"""Super (29/10/2026) : les 4 Super dans UNE fenêtre, 4 onglets (maquette super-maquettes/r1/A validée).
Chaque outil garde son serveur et son adresse ; Super les montre dans des cadres qui restent ouverts (rien ne se recharge
quand on change d'onglet). http://localhost:8800 · /api/etat = qui répond · POST /api/rallumer/<outil> = relance son lancer.sh.
"""
import json, os, subprocess, sys, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ICI = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.dirname(ICI)
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8800
OUTILS = {"veille": ("superveille", 8811), "da": ("superda", 8781), "monteur": ("supermonteur", 8801), "carrousel": ("supercarrousel", 8797)}


def repond(port):
    try:
        urllib.request.urlopen(f"http://localhost:{port}/", timeout=1.5)
        return True
    except Exception:
        return False


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def envoyer(self, code, corps, ctype="application/json; charset=utf-8"):
        corps = json.dumps(corps, ensure_ascii=False).encode() if isinstance(corps, (dict, list)) else corps
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"): return self.envoyer(200, open(os.path.join(ICI, "index.html"), "rb").read(), "text/html; charset=utf-8")
        if p == "/favicon.svg": return self.envoyer(200, open(os.path.join(ICI, "favicon.svg"), "rb").read(), "image/svg+xml")
        if p == "/api/etat": return self.envoyer(200, {k: repond(port) for k, (_, port) in OUTILS.items()})
        self.envoyer(404, {"erreur": "introuvable"})

    def do_POST(self):
        o = self.headers.get("Origin")   # seule la page Super peut relancer un outil
        if o and o not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"): return self.envoyer(403, {"erreur": "refusé"})
        k = self.path.rsplit("/", 1)[-1]
        if not self.path.startswith("/api/rallumer/") or k not in OUTILS: return self.envoyer(404, {"erreur": "introuvable"})
        dossier, port = OUTILS[k]
        subprocess.run(["bash", os.path.join(APPS, dossier, "lancer.sh")], cwd=os.path.join(APPS, dossier), capture_output=True, timeout=60)
        self.envoyer(200, {"ok": repond(port)})


if __name__ == "__main__":
    print(f"Super : http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
