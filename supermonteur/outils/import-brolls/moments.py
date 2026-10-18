"""Vidéos longues (> 60 s) : trouve les moments candidats (réaction de la salle + plan net et vivant).
Sortie : moments.json  {path: [{"t": s, "why": "...", "score": x}, ...]} + une image par candidat dans cand/.
"""
import json, os, subprocess, sys, unicodedata
import numpy as np, librosa
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SEL = json.load(open(os.path.join(HERE, "selection.json")))
OUT = os.path.join(HERE, "moments.json"); CAND = os.path.join(HERE, "cand"); os.makedirs(CAND, exist_ok=True)
CONF = {"Chateau 2 M event", "Conf epicu", "Conférence Networking", "Réseautage"}
done = json.load(open(OUT)) if os.path.exists(OUT) else {}

def audio_reaction(path, dur):
    """Applaudissements / rires = son fort ET bruité (spectral flatness haute), par pas de 0,5 s."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    y = np.frombuffer(raw, np.float32)
    if y.size < 16000: return np.zeros(int(dur * 2) + 1)
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=8000))
    rms = np.sqrt((S ** 2).mean(0)); flat = librosa.feature.spectral_flatness(S=S)[0]
    z = lambda a: (a - np.median(a)) / (a.std() + 1e-9)
    r = np.clip(z(np.log(rms + 1e-9)), 0, None) * np.clip(z(flat), 0, None)
    return np.convolve(r, np.ones(4) / 4, "same")          # lissé sur 2 s

def keyframes(path):
    pk = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,flags",
                         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split()      # sans décodage
    ts = sorted(float(l.split(",")[0]) for l in pk if "," in l and "K" in l.split(",")[1] and l.split(",")[0] not in ("", "N/A"))
    W, H = 160, 90
    raw = subprocess.run(["ffmpeg", "-v", "error", "-discard", "nokey", "-skip_frame", "nokey", "-i", path, "-an", "-vf",
                          f"scale={W}:{H},format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-"], capture_output=True).stdout
    F = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    n = min(len(ts), len(F)); ts, F = np.array(ts[:n]), F[:n]
    lap = np.abs(F[:, 1:-1, 1:-1] * 4 - F[:, :-2, 1:-1] - F[:, 2:, 1:-1] - F[:, 1:-1, :-2] - F[:, 1:-1, 2:]).mean((1, 2))
    mot = np.r_[0, np.abs(np.diff(F, axis=0)).mean((1, 2))]
    bri = F.mean((1, 2))
    return ts, lap, mot, bri

def pick(path, dur, conf):
    ts, lap, mot, bri = keyframes(path)
    if len(ts) < 3: return []
    rank = lambda a: a.argsort().argsort() / max(1, len(a) - 1)
    vis = rank(lap) * 0.7 + rank(np.minimum(mot, np.percentile(mot, 90))) * 0.3   # net + un peu de mouvement
    vis[(bri < 35) | (bri > 225)] = 0                                                 # noir / cramé
    vis[(ts < 1.5) | (ts > dur - 6)] = 0                                              # début/fin de prise
    cands = []
    if conf:
        reac = audio_reaction(path, dur)
        for i in np.argsort(-reac):
            t = i / 2
            if reac[i] < max(np.percentile(reac, 97), 1e-6) or len(cands) >= 5: break   # pics relatifs (top 3 %)
            if any(abs(t - c["t"]) < 25 for c in cands) or t < 4 or t > dur - 6: continue
            j = np.argmin(np.abs(ts - (t - 2)))
            cands.append({"t": round(max(0, t - 3), 1), "why": "réaction salle", "score": round(float(reac[i]), 2), "vis": round(float(vis[j]), 2)})
    gap = max(8, dur / 12)
    for i in np.argsort(-vis):
        if len(cands) >= 9 or vis[i] <= 0: break
        t = float(ts[i])
        if any(abs(t - c["t"]) < gap for c in cands): continue
        cands.append({"t": round(max(0, t - 1), 1), "why": "plan net", "score": 0, "vis": round(float(vis[i]), 2)})
    return cands

todo = [r for r in SEL if r["type"] == "video" and r["duree_s"] > 60 and r["path"] not in done]
todo.sort(key=lambda r: r["duree_s"])
for k, r in enumerate(todo, 1):
    try:
        c = pick(r["path"], r["duree_s"], unicodedata.normalize("NFC", r["dossier"]) in CONF)
    except Exception as e:
        print("ERREUR", r["path"], e, flush=True); c = []
    for n, x in enumerate(c):
        x["img"] = os.path.join(CAND, f"{abs(hash(r['path']))}_{n}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(x["t"] + 2), "-i", r["path"], "-frames:v", "1",
                        "-vf", "scale=320:320:force_original_aspect_ratio=decrease", x["img"]])
    done[r["path"]] = c
    json.dump(done, open(OUT, "w"), ensure_ascii=False)
    print(f"{k}/{len(todo)} {r['duree_s']:6.0f}s {len(c)} candidats  {r['dossier']}/{os.path.basename(r['path'])}", flush=True)
print("FINI")
