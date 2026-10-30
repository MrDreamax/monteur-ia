"""Kit SFX du client au 1er lancement (étape 1.4 du process client ; codé le 25/10/2026) : 1 son Epidemic par clé de
config.json "sfx", rangé dans ~/Documents/Montage/SFX/<clé>.wav. Les sons viennent du compte Epidemic DU CLIENT (connecteur
Epidemic de SON Claude, licence à son nom), jamais de celui de l'utilisateur.
  python3 kit_sfx.py liste                 -> pour chaque clé : présent ou pas, terme à chercher, durée max (ms)
  python3 kit_sfx.py pose <clé> <url> [<id> <titre>]  -> télécharge l'URL signée Epidemic, convertit en WAV 48 kHz stéréo,
                                                         range SFX/<clé>.wav, note id + titre dans SFX/_kit.json (preuve de licence)
  python3 kit_sfx.py verifie               -> « KIT SFX OK n/n » ou la liste des clés manquantes (code 1)
  python3 kit_sfx.py libre <clé> [<terme>] -> 5 sons CC0 Openverse (Freesound) pour cette clé : id, durée, titre
  python3 kit_sfx.py libre <clé> --pose [n] -> pose le n-ième (1 par défaut) ; « libre manque --pose » = toutes les clés ⬜
Côté Claude, pour chaque clé manquante : SearchSoundEffects {query: {term}, filter: {duration: {max}}, first: 5}
-> écouter les titres / tags, prendre le 1er qui colle -> DownloadSoundEffect {id, options: {fileType: "WAV"}} -> pose.
Sans compte Epidemic (26/10) : « libre ». Openverse = 5 M de sons, sans clé ; on ne prend QUE du CC0 (aucun crédit, pub Meta OK).
Limite sans clé : 20 recherches/min, 200/jour. Ne pas mettre category=sound_effect (0 résultat).
  python3 kit_sfx.py fabrique <clé> [<id>] -> fabrique le son en code avec earshot (FABRIQUE ci-dessous, ou l'id donné) et le pose
  python3 kit_sfx.py fabrique manque|tout  -> toutes les clés ⬜ (ou toutes) ; le pic du son est noté dans _kit.json (pic_s)
"""
import json, os, subprocess, sys, tempfile, urllib.parse, urllib.request
import reglages  # mêmes sons que mix.py : config.json du kit écrasé par les réglages de CETTE machine (28/10 : lisait le kit seul -> faux 0/12)

CFG = reglages.config()
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
# son earshot par clé (« fabrique », 26/10) : choisis à l'oreille contre le kit de la maison. Liste : earshot sfx list
EARSHOT = os.path.expanduser("~/.local/earshot/.venv/bin/earshot")
FABRIQUE = {
    "number": "whoosh_fast/heavy", "list": "whoosh_fast/tight", "bullet": "click/soft", "broll": "whoosh_fast/sleeve",
    "impact": "impact/punch", "reverse": "reverse_swell/short", "subdrop": "sub_drop/pro", "tick": "fit/tick/domino",
    "sheet": "fit/whoosh.short/bamboo_swish", "type": "fit/key/medium", "publish": "pop/1", "riser": "riser/tension",
}


def dest(k):
    return os.path.expanduser((SFX.get(k) or {}).get("src") or os.path.join(DIR, f"{k}.wav"))


def ok(p):
    if not os.path.exists(p) or os.path.getsize(p) < 1000: return False
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True)
    try: return float(r.stdout.strip()) > 0.05
    except ValueError: return False


def libre(terme, mx):
    """Sons CC0 d'Openverse sous mx ms. Terme Epidemic trop précis = 0 résultat : on retire un mot à la fin jusqu'à trouver."""
    mots = terme.split()
    while mots:
        q = urllib.parse.urlencode({"q": " ".join(mots), "license": "cc0", "page_size": 20})
        req = urllib.request.Request(f"https://api.openverse.org/v1/audio/?{q}", headers={"User-Agent": "supermonteur-kit-sfx"})
        res = json.load(urllib.request.urlopen(req, timeout=30)).get("results", [])
        res = [r for r in res if r.get("license") == "cc0" and r.get("url") and 0 < (r.get("duration") or 0) <= mx]
        if res: return res
        mots.pop()
    return []


def poser(k, url, meta):
    local = os.path.isfile(url)   # son fabriqué par earshot (fichier sur le Mac) ou URL à télécharger
    host = "earshot (fabriqué sur ce Mac)" if local else urllib.parse.urlparse(url).hostname or ""
    if not local and urllib.parse.urlparse(url).scheme != "https": sys.exit("URL refusée : https seulement (URL signée rendue par DownloadSoundEffect)")
    os.makedirs(os.path.dirname(dest(k)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = url if local else os.path.join(tmp, "son")
        codec = ["-c:a", "libmp3lame", "-q:a", "2"] if dest(k).lower().endswith(".mp3") else ["-c:a", "pcm_s16le"]  # config en .mp3 = on garde le .mp3
        if not local: urllib.request.urlretrieve(url, raw)
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-vn", "-ar", "48000", "-ac", "2", *codec, dest(k)],
                           capture_output=True, text=True)
        if r.returncode or not ok(dest(k)): sys.exit(f"pas un son lisible : {r.stderr.strip()[-200:]}")
    os.makedirs(DIR, exist_ok=True)
    kit = json.load(open(KIT)) if os.path.exists(KIT) else {}
    kit[k] = dict(meta, source=host)
    json.dump(kit, open(KIT, "w"), indent=1, ensure_ascii=False)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dest(k)], capture_output=True, text=True).stdout.strip()
    print(f"OK {k} -> {dest(k)} ({float(d):.1f} s)")


cmd = sys.argv[1] if len(sys.argv) > 1 else "liste"
if cmd == "liste":
    for k in SFX:
        t, mx = CHERCHE.get(k, (k.replace("_", " "), 3000))
        print(f"{'✅' if ok(dest(k)) else '⬜'} {k:8} terme « {t} »  max {mx} ms  -> {dest(k)}")
elif cmd == "pose":
    k, url = sys.argv[2], sys.argv[3]
    if k not in SFX: sys.exit(f"clé inconnue : {k} (clés : {', '.join(SFX)})")
    poser(k, url, {"id": sys.argv[4] if len(sys.argv) > 4 else None, "titre": sys.argv[5] if len(sys.argv) > 5 else None,
                   "licence": "Epidemic Sound, compte du client"})
elif cmd == "libre":
    a = sys.argv[2:]
    if not a: sys.exit(__doc__)
    pose = "--pose" in a
    n = int(a[a.index("--pose") + 1]) if pose and a.index("--pose") + 1 < len(a) else 1
    mots = [x for x in a[1:] if x != "--pose" and not x.isdigit()]
    cles = [k for k in SFX if not ok(dest(k))] if a[0] == "manque" else [a[0]]
    for k in cles:
        if k not in SFX: sys.exit(f"clé inconnue : {k} (clés : {', '.join(SFX)})")
        t, mx = CHERCHE.get(k, (k.replace("_", " "), 3000))
        t = " ".join(mots) or t
        res = libre(t, mx)
        if not res: print(f"⬜ {k} : rien en CC0 sous {mx} ms pour « {t} » (essayer un terme plus simple)"); continue
        if not pose:
            for i, r in enumerate(res[:5], 1): print(f"{k} {i}. {r['duration'] / 1000:.1f} s  {r['title'][:60]}  ({r['id']})")
            continue
        r = res[min(n, len(res)) - 1]
        poser(k, r["url"], {"id": r["id"], "titre": r["title"], "licence": "CC0 (Openverse / " + r.get("source", "?") + ")",
                            "page": r.get("foreign_landing_url")})
elif cmd == "fabrique":
    a = sys.argv[2:]
    if not a: sys.exit(__doc__)
    if not os.path.exists(EARSHOT): sys.exit("earshot pas installé (~/.local/earshot) : voir Brain/02-Formations/veille-2026-10-26-sons-claude-et-5-plugins-dev.md")
    cles = [k for k in SFX if not ok(dest(k))] if a[0] in ("manque", "tout") else [a[0]]
    if a[0] == "tout": cles = list(SFX)
    for k in cles:
        if k not in SFX: sys.exit(f"clé inconnue : {k} (clés : {', '.join(SFX)})")
        sid = a[1] if len(a) > 1 and a[0] not in ("manque", "tout") else FABRIQUE.get(k)
        if not sid: print(f"⬜ {k} : pas de son earshot prévu (donner un id : earshot sfx list)"); continue
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "son.wav")
            r = subprocess.run([EARSHOT, "sfx", "render", sid, "-o", wav], capture_output=True, text=True)
            if r.returncode or not ok(wav): sys.exit(f"earshot n'a pas rendu {sid} : {(r.stderr or r.stdout).strip()[-200:]}")
            pic = r.stdout.split("peak at ")[1].split(" s")[0] if "peak at " in r.stdout else None
            poser(k, wav, {"id": sid, "titre": f"earshot {sid}", "licence": "MIT, son fabriqué en code (aucun droit à payer)", "pic_s": pic})
elif cmd == "verifie":
    manque = [k for k in SFX if not ok(dest(k))]
    if manque:
        print(f"KIT SFX INCOMPLET {len(SFX) - len(manque)}/{len(SFX)} : manque {', '.join(manque)}"); sys.exit(1)
    print(f"KIT SFX OK {len(SFX)}/{len(SFX)} ({os.path.dirname(dest(next(iter(SFX))))})")
else:
    sys.exit(__doc__)
