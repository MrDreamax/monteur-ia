"""Kit SFX du client au 1er lancement (étape 1.4 du process client ; codé le 25/10/2026) : 1 son Epidemic par clé de
config.json "sfx", rangé dans ~/Documents/Montage/SFX/<clé>.wav. Les sons viennent du compte Epidemic DU CLIENT (connecteur
Epidemic de SON Claude, licence à son nom), jamais de celui de l'utilisateur.
  python3 kit_sfx.py liste                 -> pour chaque clé : présent ou pas, terme à chercher, durée max (ms)
  python3 kit_sfx.py pose <clé> <url> [<id> <titre>]  -> télécharge l'URL signée Epidemic, convertit en WAV 48 kHz stéréo,
                                                         range SFX/<clé>.wav, note id + titre dans SFX/_kit.json (preuve de licence)
  python3 kit_sfx.py verifie               -> « KIT SFX OK n/n » ou la liste des clés manquantes (code 1)
Côté Claude, pour chaque clé manquante : SearchSoundEffects {query: {term}, filter: {duration: {max}}, first: 5}
-> écouter les titres / tags, prendre le 1er qui colle -> DownloadSoundEffect {id, options: {fileType: "WAV"}} -> pose.
"""
import json, os, subprocess, sys, tempfile, urllib.parse, urllib.request

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(SK, "config.json")))
SFX = CFG.get("sfx") or {}
DIR = os.path.expanduser("~/Documents/Montage/SFX")
KIT = os.path.join(DIR, "_kit.json")
# terme Epidemic et durée max (ms) par clé : calés sur le kit de la maison (whoosh courts, impact cinéma, riser sombre…)
CHERCHE = {
    "number": ("whoosh low short", 1500), "list": ("whoosh simple", 1500), "bullet": ("mouse click", 600),
    "broll": ("whoosh air subtle", 1500), "impact": ("cinematic impact boom dark", 4000), "reverse": ("reverse riser short", 2500),
    "subdrop": ("sub drop boom", 3000), "tick": ("clock tick", 1000), "sheet": ("paper swoosh", 1500),
    "type": ("keyboard typing", 4000), "publish": ("pop", 800), "riser": ("riser dark low", 6000),
}


def dest(k):
    return os.path.expanduser((SFX.get(k) or {}).get("src") or os.path.join(DIR, f"{k}.wav"))


def ok(p):
    if not os.path.exists(p) or os.path.getsize(p) < 1000: return False
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True)
    try: return float(r.stdout.strip()) > 0.05
    except ValueError: return False


cmd = sys.argv[1] if len(sys.argv) > 1 else "liste"
if cmd == "liste":
    for k in SFX:
        t, mx = CHERCHE.get(k, (k.replace("_", " "), 3000))
        print(f"{'✅' if ok(dest(k)) else '⬜'} {k:8} terme « {t} »  max {mx} ms  -> {dest(k)}")
elif cmd == "pose":
    k, url = sys.argv[2], sys.argv[3]
    if k not in SFX: sys.exit(f"clé inconnue : {k} (clés : {', '.join(SFX)})")
    host = urllib.parse.urlparse(url).hostname or ""
    if urllib.parse.urlparse(url).scheme != "https": sys.exit("URL refusée : https seulement (URL signée rendue par DownloadSoundEffect)")
    os.makedirs(os.path.dirname(dest(k)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "son")
        urllib.request.urlretrieve(url, raw)
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", dest(k)],
                           capture_output=True, text=True)
        if r.returncode or not ok(dest(k)): sys.exit(f"pas un son lisible : {r.stderr.strip()[-200:]}")
    kit = json.load(open(KIT)) if os.path.exists(KIT) else {}
    kit[k] = {"id": sys.argv[4] if len(sys.argv) > 4 else None, "titre": sys.argv[5] if len(sys.argv) > 5 else None,
              "source": host, "licence": "Epidemic Sound, compte du client"}
    json.dump(kit, open(KIT, "w"), indent=1, ensure_ascii=False)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dest(k)], capture_output=True, text=True).stdout.strip()
    print(f"OK {k} -> {dest(k)} ({float(d):.1f} s)")
elif cmd == "verifie":
    manque = [k for k in SFX if not ok(dest(k))]
    if manque:
        print(f"KIT SFX INCOMPLET {len(SFX) - len(manque)}/{len(SFX)} : manque {', '.join(manque)}"); sys.exit(1)
    print(f"KIT SFX OK {len(SFX)}/{len(SFX)} ({DIR})")
else:
    sys.exit(__doc__)
