"""Dérush : coupe les silences, les respirations et les répétitions, sans jamais couper un mot ni une phrase en deux.
  python3 derush.py clip.mp4 words.json cut.mp4 [--drop drop.json] [--pause 57]
--pause i = indice (dans words.json source) du mot PUNCHLINE qui aura LE silence du reel : on GARDE la vraie pause avant lui
(jusqu'à 0,9 s) au lieu de la resserrer. Sans pause dans le rush, pas de silence possible (le dire à Cyril : marquer un temps au tournage).
drop.json = [[i, j], ...] plages d'indices de mots à supprimer (répétitions, phrases ratées : on garde la DERNIÈRE prise).
On ne coupe que dans les blancs entre deux mots :
  - fin de phrase (ponctuation) : blanc + respiration supprimés, on garde 0.06 s avant le mot suivant
  - milieu de phrase : le blanc est seulement resserré à 0.15 s (la phrase reste d'un seul tenant)
Écrit aussi cut.segments.json (plages gardées dans la source, dans l'ordre).
"""
import json, math, subprocess, sys

src, words_p, out = sys.argv[1:4]
drop = json.load(open(sys.argv[sys.argv.index("--drop") + 1])) if "--drop" in sys.argv else []
W = json.load(open(words_p))["words"]
dead = {k for a, b in drop for k in range(a, b + 1)}
PAUSE = int(sys.argv[sys.argv.index("--pause") + 1]) if "--pause" in sys.argv else None
keep = [w for i, w in enumerate(W) if i not in dead]
PRE, POST, MID, MAXGAP = 0.06, 0.12, 0.15, 0.25
# 17/10 (Cyril, Tesla v3 : « on n'entend pas le mot data en entier ») : les temps de Whisper sont faux de 0,1-0,3 s aux bords
# des mots. Aux coupes qui retirent un blanc entier (fin de phrase, prise sautée), on coupe sur le VRAI son : fin = 1er blanc
# de 120 ms après le mot, début = vraie attaque de la voix. Seuil = niveau de parole (95e centile) - 21 dB (énergie lissée 30 ms).
_ENV = []
def _env():
    if not _ENV:
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, dtype=np.float32); n = len(x) // 160 * 160
        db = 20 * np.log10(np.sqrt((x[:n].reshape(-1, 160) ** 2).mean(1)) + 1e-9)
        db = np.convolve(db, np.ones(3) / 3, "same")     # lissé sur 30 ms : le bruit de la pièce frôle le seuil
        _ENV.extend([db, float(np.percentile(db, 95)) - 21])
    return _ENV
def speech_end(t, lim):    # vraie fin du mot qui finit vers t : 1er blanc >= 120 ms qui COMMENCE entre t - 0,05 et lim
    db, q = _env(); run = 0  # (120 ms : le « t » de « data » fait un trou de 60-90 ms DANS le mot)
    for i in range(max(0, int(t * 100) - 5), min(len(db), int(lim * 100) + 12)):
        run = run + 1 if db[i] < q else 0
        if run >= 12: return (i - 11) / 100 + 0.03 if (i - 11) / 100 <= lim else None
    return None
def speech_start(t, lo):   # vraie attaque du mot annoncé à t : DERNIER passage blanc -> voix (3 x 10 ms) entre lo et t + 0,15
    db, q = _env(); best = None   # (le dernier, pour ne jamais reprendre la queue du mot d'avant, supprimé)
    for k in range(max(0, int(lo * 100)), min(len(db) - 4, int((t + 0.15) * 100))):
        if db[k] < q and (db[k + 1:k + 4] >= q).all(): best = (k + 1) / 100 - 0.04
    return best
MINCUT, MINSEG = 0.45, 0.6   # 17/10 : pas de coupe pour un blanc < 0,45 s ; pas de bout de face cam < 0,6 s entre deux coupes

segs = []
for i, w in enumerate(keep):
    s, e = w["start"] - PRE, w["end"] + POST
    if segs:
        prev = keep[i - 1]
        gap = w["start"] - prev["end"]
        end_of_sentence = prev["text"].rstrip()[-1:] in ".!?,"
        jumped = W.index(w) != W.index(prev) + 1          # une répétition a sauté entre les deux
        if W.index(w) == PAUSE and not jumped:            # LE silence du reel : vraie pause gardée (max 0,9 s)
            if gap <= 0.9: segs[-1][1] = e; continue
            segs[-1][1] = prev["end"] + 0.45; s = w["start"] - 0.45
            segs.append([s, e]); continue
        if W.index(w) == PAUSE and jumped:                # 17/10 : punchline juste après une prise ratée coupée -> on recolle
            j, pj = W.index(w), W.index(prev)             # le vrai blanc après le mot d'avant + le vrai blanc avant la punchline
            after = (W[pj + 1]["start"] if pj + 1 < len(W) else prev["end"]) - prev["end"]
            before = w["start"] - W[j - 1]["end"]
            if after >= 0.3 and before >= 0.3:
                segs[-1][1] = prev["end"] + min(0.45, after); s = w["start"] - min(0.45, before)
                segs.append([s, e]); continue
        if not jumped and gap <= MAXGAP:
            segs[-1][1] = e; continue                    # parole continue
        if not jumped and gap < MINCUT:                  # 17/10 (Cyril, Tesla : « micro cuts qui buggent ») : une coupe qui ne
            segs[-1][1] = e; continue                    # gagne que 0,1-0,3 s = un saut de tête visible pour rien -> on garde
        if not jumped and not end_of_sentence:
            segs[-1][1] = prev["end"] + MID / 2          # milieu de phrase : on resserre seulement
            s = w["start"] - MID / 2
        else:
            segs[-1][1] = min(segs[-1][1], w["start"] - 0.01)
            j, pj = W.index(w), W.index(prev)
            if jumped:   # 17/10 (Cyril, Tesla 49,3 s « petit silence mal cut ») : la marge POST gardait 0,1 s du mot SUPPRIMÉ
                         # qui suit (« data e- »). Les marges s'arrêtent au mot voisin dans le RUSH.
                segs[-1][1] = min(segs[-1][1], max(prev["end"], W[pj + 1]["start"] - 0.01))
                s = max(s, min(w["start"], W[j - 1]["end"] + 0.01))
            # prise sautée : le blanc doit commencer avant le mot supprimé suivant + 0,15 s (sinon on garderait ce mot)
            se = speech_end(prev["end"], W[pj + 1]["start"] + 0.15 if jumped else min(prev["end"] + 0.35, w["start"] - 0.05))
            if se: segs[-1][1] = se                      # fin réelle du mot (pas celle de Whisper)
            ss = speech_start(w["start"], max(w["start"] - 0.3, W[j - 1]["end"] if jumped else prev["end"]))
            if ss: s = max(ss, segs[-1][1] if not jumped else ss)   # attaque réelle : pas de blanc gardé avant le mot
    segs.append([max(0.0, s), e])
segs = [[a, b] for a, b in segs if b - a > 0.05]
# 17/10 (Cyril, Tesla 14,8 s : « enlève le micro rush inutile qui saccade ») : un bout gardé < MINSEG entre deux coupes
# (« par » seul, 0,17 s, puis saut) = la tête saute deux fois. On le recolle au bout voisin de la même prise (blanc gardé).
k = 0
while k < len(segs):
    a, b = segs[k]
    if b - a < MINSEG and len(segs) > 1:
        # recollé seulement si le blanc gardé reste court (< 0,5 s) : sinon on entend un silence (Cyril 17/10 v2, 15 s : « par … exemple »)
        if k + 1 < len(segs) and segs[k + 1][0] - b < 0.5:  segs[k + 1][0] = a; segs.pop(k); continue
        if k > 0 and a - segs[k - 1][1] < 0.5:            segs[k - 1][1] = b; segs.pop(k); continue
        print(f"!! bout de {b - a:.2f} s à {a:.2f} s dans le rush, entre deux prises : le couvrir d'un B-roll ou prendre une autre prise (drop.json)")
    k += 1
# Entrée et sortie (Cyril 16/10 : « ça coupe un peu sec au niveau du hook et à la fin ») : avant, la vidéo démarrait 0,06 s
# avant le 1er mot et s'arrêtait 0,12 s après le dernier. On garde LEAD avant le 1er mot (assez court pour ne pas garder
# la respiration) et TAIL après le dernier (la phrase retombe, la musique peut finir). --lead / --tail pour régler.
LEAD = float(sys.argv[sys.argv.index("--lead") + 1]) if "--lead" in sys.argv else 0.15
TAIL = float(sys.argv[sys.argv.index("--tail") + 1]) if "--tail" in sys.argv else 0.6
if segs:
    segs[0][0] = max(0.0, min(segs[0][0], keep[0]["start"] - LEAD))
    segs[-1][1] = max(segs[-1][1], keep[-1]["end"] + TAIL)
# Synchro image/son (13/10) : chaque plage est calée sur la grille des images (début arrondi en dessous, fin au-dessus).
# Avant, l'image se coupait à l'image près et le son ailleurs : sur 40 coupes, la bouche pouvait se décaler.
# Plages qui se touchent ou se chevauchent = fusionnées (sinon le fondu anti-clic doublerait le volume au raccord).
FPS = eval(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                                    "-of", "csv=p=0", src]).decode().strip())
snapped = []
for a, b in segs:
    a, b = math.floor(a * FPS + 1e-6) / FPS, math.ceil(b * FPS - 1e-6) / FPS
    if snapped and a <= snapped[-1][1] + 1e-6: snapped[-1][1] = max(snapped[-1][1], b)
    else: snapped.append([a, b])
segs = [[round(a, 4), round(b, 4)] for a, b in snapped]
HALF = 0.5 / FPS   # image : on prend les images de a à b exclu -> exactement (b - a) s, comme le son

vexpr = "+".join(f"between(t,{a - HALF:.4f},{b - HALF:.4f})" for a, b in segs)   # demi-image de marge : insensible aux arrondis
expr = "+".join(f"between(t,{a},{b})" for a, b in segs)
# Anti-clic (experts 13/10, Vashi Nedomansky) : micro-fondu au début et à la fin de chaque plage gardée, sinon chaque coupe
# peut claquer. 0,03 s : tient dans la marge avant le mot (PRE 0,06 s), ne mange jamais une syllabe.
# asetnsamples=64 : trames audio de 1,3 ms, sinon le fondu (et la coupe) se calent sur des trames de 21 ms.
AFADE = 0.03
fade = "+".join(f"clip(min((t-{a})/{AFADE},({b}-t)/{AFADE}),0,1)" for a, b in segs)
subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", src,
    "-vf", f"select='{vexpr}',setpts=N/FRAME_RATE/TB",
    "-af", f"asetnsamples=n=64,volume='{fade}':eval=frame,aselect='{expr}',asetpts=N/SR/TB",
    "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", out])
json.dump(segs, open(out.rsplit(".", 1)[0] + ".segments.json", "w"))
# Mots recalés sur la version coupée (16/10) : <out>.words.json = la transcription du rush (souvent meilleure que celle
# refaite sur le montage coupé, qui a perdu son contexte) avec les temps de la version coupée.
off, moved = 0.0, []
for a, b in segs:
    for i, w in enumerate(W):
        if i not in dead and a <= w["start"] < b:
            moved.append({**w, "start": round(off + w["start"] - a, 3), "end": round(off + min(w["end"], b) - a, 3)})
    off += b - a
json.dump({"words": moved}, open(out.rsplit(".", 1)[0] + ".words.json", "w"), ensure_ascii=False)
before = W[-1]["end"]; after = sum(b - a for a, b in segs)
print(f"{len(segs)} plages · {before:.1f}s -> {after:.1f}s · {len(dead)} mots retirés -> {out}")
