"""Envoi d'un fichier sur l'hébergeur Higgsfield pour les robots de publication (29/10/2026).
  1. après media_upload :  python3 ~/Documents/SuperApps/heberger.py <fichier> '<upload_url>' <content_type>
  2. après media_confirm : python3 ~/Documents/SuperApps/heberger.py --verifier '<url publique>'
Pourquoi : le robot (publier.py) écrivait le curl à sa façon (« curl -s -o /dev/null -X PUT… ») et la permission
« curl -X PUT » le refusait : rien ne partait (CAM20062, 29/10 19:18). Une seule commande fixe = plus de refus.
Sortie : « PUT 200 » ou « URL 200 ». Code 1 si ce n'est pas 200.
"""
import subprocess
import sys
import time


def code(cmd):
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}"] + cmd, capture_output=True, text=True, timeout=900)
    return r.stdout.strip()[-3:] or "000"


def main():
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "--verifier":
        for _ in range(5):   # le lien public peut mettre quelques secondes à répondre
            c = code(["-I", a[1]])
            if c == "200":
                break
            time.sleep(3)
        print("URL", c)
    elif len(a) == 3:
        c = code(["-X", "PUT", "-H", f"Content-Type: {a[2]}", "-H", "If-None-Match: *", "--data-binary", f"@{a[0]}", a[1]])
        print("PUT", c)
    else:
        sys.exit(__doc__)
    sys.exit(0 if c == "200" else 1)


if __name__ == "__main__":
    main()
