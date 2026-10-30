"""Mots + temps de chaque mot, pour tous les outils du Monteur (26/10) : ElevenLabs Scribe d'abord, Whisper small du Mac en secours.
  from mots import transcrire
  words, moteur = transcrire("rush.mp4", debut=12.0, fin=18.5, langue="fr")   # temps relatifs au début de l'extrait
langue=None = détection automatique. mac=True = Whisper forcé.
ElevenLabs (23/10, rush IMG_6799) : 16/16 vraies pauses contre 8/16 pour Whisper, bords à 0,03 s, 2 s au lieu de 39 s.
Envoi en Opus 32 kb/s mono (26/10) : 45 min de podcast = ~11 Mo au lieu de 88 Mo en WAV (l'envoi WAV expirait).
Clé lue dans le trousseau (service elevenlabs-api-key), jamais dans un fichier. Pas de clé, quota vide, pas d'internet
ou toute autre erreur -> 29/10 : le montage S'ARRÊTE (SansElevenLabs) ; Whisper seulement si secours=True ou mac=True.
"""
import os, subprocess, sys, tempfile, time
import numpy as np


def _extrait(src, debut, fin):
    cut = []
    if debut is not None: cut += ["-ss", str(debut)]
    if fin is not None: cut += ["-t", str(fin - (debut or 0))]
    return cut + ["-i", src, "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000"]


def elevenlabs(src, debut=None, fin=None, langue="fr"):
    key = subprocess.run(["security", "find-generic-password", "-s", "elevenlabs-api-key", "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        raise RuntimeError("pas de clé dans le trousseau")
    import requests
    with tempfile.TemporaryDirectory() as tmp:
        ogg = os.path.join(tmp, "a.ogg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *_extrait(src, debut, fin), "-c:a", "libopus", "-b:a", "32k", ogg],
                       check=True)
        data = {"model_id": "scribe_v1", "timestamps_granularity": "word", "tag_audio_events": "false"}
        if langue: data["language_code"] = langue
        for attente in (3, 8, None):                              # 26/10 : 429 « system_busy » passager -> 2 nouveaux essais
            with open(ogg, "rb") as f:
                r = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": key},
                                  files={"file": ("a.ogg", f, "audio/ogg")}, data=data, timeout=900)
            if r.status_code not in (429, 500, 502, 503, 504) or attente is None: break
            print(f"ElevenLabs occupé ({r.status_code}), nouvel essai dans {attente} s", file=sys.stderr)
            time.sleep(attente)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code} : {r.text[:200]}")
    words = []
    for w in r.json()["words"]:
        t = w["text"].strip()
        if w.get("type") != "word" or not t: continue
        if not any(c.isalnum() for c in t):                          # 26/10 : « ? » renvoyé seul = sous-titre « ? » à l'écran
            if words: words[-1]["text"] += t                          # -> collé au mot d'avant
            continue
        words.append({"text": t, "start": round(w["start"], 3), "end": round(w["end"], 3)})
    return words


def whisper(src, debut=None, fin=None, langue="fr", modele="small", **opts):
    from faster_whisper import WhisperModel
    raw = subprocess.check_output(["ffmpeg", "-v", "error", *_extrait(src, debut, fin), "-f", "f32le", "-"])
    segs, _ = WhisperModel(modele, compute_type="int8").transcribe(np.frombuffer(raw, np.float32), language=langue,
                                                                   word_timestamps=True, **opts)
    return [{"text": w.word.strip(), "start": round(float(w.start), 3), "end": round(float(w.end), 3)} for s in segs for w in s.words]


# 29/10 (crédits vides de 13h26 à 20h28 sans que l’utilisateur le sache, 3 reels publiés sur Whisper) : un refus d'ElevenLabs
# (quota, clé) écrit ALERTE (bandeau rouge de SuperMonteur) et sonne sur son iPhone (ntfy, 1 fois par 3 h max).
# Une transcription ElevenLabs réussie efface l'alerte. Une panne de ffmpeg (vidéo sans son) n'est pas un refus.
ALERTE = os.path.expanduser("~/.claude/skills/supermonteur/.alerte-elevenlabs.json")


def _alerter(e):
    import json
    texte = str(e)
    if "quota" in texte: raison = "plus de crédit"
    elif "clé" in texte or " 401" in texte: raison = "clé refusée"
    else: return
    vieux = {}
    try: vieux = json.load(open(ALERTE))
    except Exception: pass
    a = {"raison": raison, "depuis": vieux.get("depuis") or time.strftime("%d/%m à %Hh%M"), "detail": texte[:200],
         "sonne": vieux.get("sonne", 0)}
    if time.time() - a["sonne"] > 3 * 3600:
        topic = subprocess.run(["security", "find-generic-password", "-s", "ntfy-topic-ventes", "-w"],
                               capture_output=True, text=True).stdout.strip()
        if topic:
            r = subprocess.run(["curl", "-s", "-m", "10", "-o", "/dev/null", "-w", "%{http_code}",
                                "-H", "Title: ElevenLabs : " + raison, "-H", "Tags: warning", "-H", "Priority: high",
                                "-d", "Tes montages passent sur le Mac (plus lent, plus de fautes). Recharge : elevenlabs.io/app/subscription",
                                "https://ntfy.sh/" + topic], capture_output=True, text=True)
            if r.stdout.strip() == "200": a["sonne"] = time.time()
    json.dump(a, open(ALERTE, "w"), ensure_ascii=False)


class SansElevenLabs(RuntimeError):
    pass


# 29/10 (l’utilisateur : « Bloquer le montage ») : Whisper du Mac = 20 fois plus lent et dérush moins juste (CAM20065 : une phrase
# entière sautée). ElevenLabs refuse = le MONTAGE s'arrête (SansElevenLabs) au lieu de passer sur Whisper.
# secours=True = Whisper permis (SuperCarrousel, qui n'est pas un montage). mac=True = Whisper forcé, à la main seulement.
def transcrire(src, debut=None, fin=None, langue="fr", modele="small", mac=False, secours=False, **opts):
    """-> (mots, moteur). opts = options Whisper (ex. condition_on_previous_text=False), secours seulement."""
    if not mac:
        try:
            mots = elevenlabs(src, debut, fin, langue)
            if os.path.exists(ALERTE): os.remove(ALERTE)
            return mots, "ElevenLabs"
        except Exception as e:
            try: _alerter(e)
            except Exception: pass
            if not secours:
                raison = "plus de crédit" if "quota" in str(e) else str(e)[:160]
                raise SansElevenLabs(f"ElevenLabs : {raison}. Recharge sur elevenlabs.io/app/subscription puis clique « Monter le reel »")
            print(f"ElevenLabs indisponible ({e}) -> secours Whisper du Mac", file=sys.stderr)
    return whisper(src, debut, fin, langue, modele, **opts), "Mac (Whisper)"
