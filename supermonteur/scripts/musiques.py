"""Musiques du dossier music_reels (réglages), avec leur dernière utilisation (28/10, l’utilisateur : « varier les musiques en
fonction de l'ambiance, pas toujours réutiliser les mêmes »).

    python3 musiques.py        -> jamais utilisées d'abord, puis la plus ancienne ; « INTERDITE » = 3 derniers reels ou 7 derniers jours ; [ambiance] = fiche d'écoute

Choisir ensuite d'après l'AMBIANCE du sujet (pas la 1re de la liste), puis attaque.py pour le temps fort de départ.
"""
import csv, datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reglages

CFG = reglages.config()
dossier = CFG.get("music_reels")
J = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "musiques_utilisees.csv")
rows = list(csv.DictReader(open(J))) if os.path.exists(J) else []
reels = []
for r in rows:   # ordre du carnet = ordre des montages
    if r["reel"] not in reels: reels.append(r["reel"])
limite = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()   # 29/10 : « arrête d'utiliser tout le temps Survivor » : aussi 7 jours
recents = {os.path.basename(r["musique"]) for r in rows if r["reel"] in reels[-3:] or r["date"] >= limite}   # même morceau rangé dans 2 dossiers = même musique
A = os.path.expanduser("~/Documents/Brain/00-Moi/reglages/musiques-ambiance.json")   # 02/11 : fiche de chaque morceau, écouté par Gemini
AMB = json.load(open(A)) if os.path.exists(A) else {}
der = {}
for r in rows: der[os.path.basename(r["musique"])] = (r["date"], os.path.basename(r["reel"]))
if not dossier or not os.path.isdir(dossier): sys.exit("pas de dossier music_reels dans les réglages (ou SSD absent)")
L = sorted((f for f in os.listdir(dossier) if not f.startswith(".") and f.lower().endswith((".mp3", ".wav", ".m4a"))),
           key=lambda f: (f in der, der.get(f, ("",))[0]))
for f in L:
    p = os.path.join(dossier, f)
    etat = "INTERDITE (3 derniers reels ou 7 jours)" if f in recents else (f"utilisée le {der[f][0]} ({der[f][1]})" if f in der else "jamais utilisée")
    a = AMB.get(f, {})
    print(f"{etat:38s} " + (f"[{a.get('ambiance')} · énergie {a.get('energie')}/5{' · chant' if a.get('chant') else ''}] " if a else "") + f)
