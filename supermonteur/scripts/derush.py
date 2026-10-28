"""Dérush : coupe les silences, les respirations et les répétitions, sans jamais couper un mot ni une phrase en deux.
  python3 derush.py clip.mp4 words.json cut.mp4 [--drop drop.json] [--pause 57] [--vf "<vf de cadre.json>"] [--plages plages.json]
  (--vf : on part du RUSH originale et le recadrage se fait sur les seules secondes gardées, voir SKILL étape 1)
--pause i = indice (dans words.json source) du mot PUNCHLINE qui aura LE silence du reel : on GARDE la vraie pause avant lui
(jusqu'à 0,9 s) au lieu de la resserrer. Sans pause dans le rush, pas de silence possible (le dire à l'utilisateur : marquer un temps au tournage).
drop.json = [[i, j], ...] plages d'indices de mots à supprimer (répétitions, phrases ratées : on garde la DERNIÈRE prise).
On ne coupe que dans les blancs entre deux mots :
  - fin de phrase (ponctuation) : blanc + respiration supprimés, on garde 0.06 s avant le mot suivant
  - milieu de phrase : le blanc est seulement resserré à 0.15 s (la phrase reste d'un seul tenant)
Écrit aussi cut.segments.json (plages gardées dans la source, dans l'ordre).
"""
import os, json, math, subprocess, sys

src, words_p, out = sys.argv[1:4]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdr import sdr, BT709
src = sdr(src)   # 25/10 : rush iPhone HDR -> SDR (même fichier que cadre.py, réutilisé)
drop = json.load(open(sys.argv[sys.argv.index("--drop") + 1])) if "--drop" in sys.argv else []
W = json.load(open(words_p))["words"]
dead = {k for a, b in drop for k in range(a, b + 1)}
PAUSE = int(sys.argv[sys.argv.index("--pause") + 1]) if "--pause" in sys.argv else None
keep = [w for i, w in enumerate(W) if i not in dead]
PRE, POST, MID, MAXGAP = 0.06, 0.12, 0.15, 0.25
# 17/10 (Tesla v3 : « on n'entend pas le mot data en entier ») : les temps de Whisper sont faux de 0,1-0,3 s aux bords
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
# 19/10 soir (CAM20031, 3 respirations restées après le dérush) : une inspiration fait -27 à -34 dB quand la voix fait -10 à -16 :
# au seuil « 95e centile - 21 dB » elle passait pour de la voix et la fin du mot s'allongeait jusqu'à +0,35 s. Pour trouver la FIN
# d'un mot, le blanc est compté 6 dB plus haut (respiration = blanc) ; l'attaque d'un mot garde le seuil normal.
BREATH_DB = 6
PAUSE_DB = 10   # pause / inspiration DANS une plage : >= 0,3 s sous « 95e centile - 11 dB » (CAM20031 : souffle à -22/-26, voix à -10/-16)
# 22/10 (IMG_6799 v1 : « à un moment le mot est coupé, et à la fin aussi le mot est coupé ») : la queue SOURDE d'un mot
# (« t » de « script » : 70 ms de silence puis l'explosion à -28/-35 dB ; « x » de « Dreamax » (la signature) à -36/-41 dB) est sous le seuil
# de parole, donc speech_end / tail_end la prenaient pour un blanc et la coupaient. Elle est pourtant 20 dB au-dessus du bruit
# de la pièce (FLOOR = 3e centile, -59 dB sur ce rush). word_tail() prolonge la fin tant que le son reste > FLOOR + 15 dB,
# en tolérant UN trou de 30-90 ms (la fermeture d'un « t », « p », « k ») ; la queue doit finir dans le calme avant 0,45 s,
# sinon (souffle qui dure, mot suivant collé) on ne prolonge pas.
_FL = []
def _floor():
    if not _FL:
        import numpy as np
        _FL.append(float(np.percentile(_env()[0], 3)))
    return _FL[0]
_SA = []
def _voiced(k):
    import numpy as np
    if not _SA:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
        _SA.append(np.frombuffer(raw, dtype=np.float32))
    f = _SA[0][k * 160: k * 160 + 480].astype(np.float64); f = f - f.mean()
    if len(f) < 480 or (f * f).sum() <= 0: return False
    return max((f[:-l] * f[l:]).sum() / np.sqrt((f[:-l] ** 2).sum() * (f[l:] ** 2).sum() + 1e-12) for l in range(40, 200, 2)) > 0.55
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from queue_mot import fin_du_mot       # même définition que le Gardien
def word_tail(e, cap):                  # fin réelle du mot dont la voix forte s'arrête juste avant e (queue comprise)
    db, q = _env(); j = int(e * 100)
    while j > max(0, int(e * 100) - 60) and db[j] < q + 6: j -= 1
    return fin_du_mot(db, _voiced, q, _floor(), j / 100 if db[j] >= q + 6 else e, cap)
def speech_end(t, lim, cap=None):    # vraie fin du mot qui finit vers t : 1er blanc >= 120 ms qui COMMENCE entre t - 0,05 et lim
    db, q = _env(); run = 0  # (120 ms : le « t » de « data » fait un trou de 60-90 ms DANS le mot)
    for i in range(max(0, int(t * 100) - 5), min(len(db), int(lim * 100) + 12)):
        run = run + 1 if db[i] < q + BREATH_DB else 0
        if run >= 12:
            t0 = (i - 11) / 100
            return word_tail(t0, cap if cap is not None else lim) if t0 <= lim else None
    return None
def speech_start(t, lo):   # vraie attaque du mot annoncé à t : DERNIER passage blanc -> voix (3 x 10 ms) entre lo et t + 0,15
    db, q = _env(); best = None   # (le dernier, pour ne jamais reprendre la queue du mot d'avant, supprimé)
    for k in range(max(0, int(lo * 100)), min(len(db) - 4, int((t + 0.15) * 100))):
        if db[k] < q and (db[k + 1:k + 4] >= q).all(): best = (k + 1) / 100 - 0.04
    return best
SERRE = []   # coupes sans blanc (phrase retirée collée au mot d'avant), voir plus bas
MINCUT, MINSEG, BREATH = 0.45, 0.6, 0.3   # 17/10 : pas de coupe pour un blanc < 0,45 s ; pas de bout de face cam < 0,6 s entre deux coupes
# 23/10 (l'utilisateur, règle pour TOUT 1er dérush : « ne coupe jamais en plein milieu d'une phrase, toujours sur un point ou une virgule »,
# déjà dit le 21/10 sur CAM20033). L'IMAGE n'est coupée qu'après un mot qui finit par . , ! ? … ; : (ou à une reprise sautée).
# Un blanc ou une respiration en milieu de phrase reste à l'image ; seul son SON est baissé au bruit de la pièce (MUTE plus bas).
# Les bords posés à la main (--bords, --plages : timeline du cockpit) ne sont pas concernés : c'est la personne qui décide.
PONCT = ".,!?…;:"
fin_phrase = lambda w: w["text"].rstrip()[-1:] in PONCT

segs = []
for i, w in enumerate(keep):
    s, e = w["start"] - PRE, w["end"] + POST
    if segs:
        prev = keep[i - 1]
        gap = w["start"] - prev["end"]
        end_of_sentence = fin_phrase(prev)
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
        if not jumped and not end_of_sentence:            # 23/10 : milieu de phrase = JAMAIS de coupe (le souffle est baissé, pas coupé)
            segs[-1][1] = e; continue
        if jumped and not end_of_sentence:
            print(f"!! reprise : coupe après « {prev['text'].strip()} » ({prev['end']:.2f} s), sans point ni virgule : vérifier que la phrase gardée est entière")
        # 19/10 (lot de 6 : « respiration cut sur tous les rushs ») : un blanc >= BREATH entre deux mots = une respiration
        # (souvent sans ponctuation dans la transcription) -> coupée en entier comme une fin de phrase, même si < MINCUT.
        breath = end_of_sentence or gap >= BREATH
        if not jumped and gap < MINCUT and not breath:   # 17/10 (Tesla : « micro cuts qui buggent ») : une coupe qui ne
            segs[-1][1] = e; continue                    # gagne que 0,1-0,3 s = un saut de tête visible pour rien -> on garde
        if not jumped and not breath:
            segs[-1][1] = prev["end"] + MID / 2          # milieu de phrase : on resserre seulement
            s = w["start"] - MID / 2
        else:
            segs[-1][1] = min(segs[-1][1], w["start"] - 0.01)
            j, pj = W.index(w), W.index(prev)
            if jumped:   # 17/10 (Tesla 49,3 s « petit silence mal cut ») : la marge POST gardait 0,1 s du mot SUPPRIMÉ
                         # qui suit (« data e- »). Les marges s'arrêtent au mot voisin dans le RUSH.
                segs[-1][1] = min(segs[-1][1], max(prev["end"], W[pj + 1]["start"] - 0.01))
                s = max(s, min(w["start"], W[j - 1]["end"] + 0.01))
            # prise sautée : le blanc doit commencer avant le mot supprimé suivant + 0,15 s (sinon on garderait ce mot)
            se = speech_end(prev["end"], W[pj + 1]["start"] + 0.15 if jumped else min(prev["end"] + 0.35, w["start"] - 0.05),
                            cap=W[pj + 1]["start"] if jumped else w["start"] - 0.05)   # 22/10 : la queue du mot s'arrête avant le mot suivant
            if se: segs[-1][1] = se                      # fin réelle du mot (pas celle de Whisper)
            elif jumped and W[pj + 1]["start"] - prev["end"] < 0.1:
                # 23/10 (cockpit v4 : phrase barrée collée au mot d'avant, « sujet | et le message ») : aucun blanc entre les deux.
                # On coupe au creux du son entre les deux mots ; la coupe est notée « serrée » (le Gardien la signale sans bloquer :
                # c'est la personne qui a choisi de retirer la suite).
                db, _ = _env(); lo, hi = int((prev["end"] - 0.1) * 100), int((W[pj + 1]["start"] + 0.1) * 100)
                if hi > lo: segs[-1][1] = (lo + int(min(range(hi - lo), key=lambda n: db[lo + n]))) / 100 + 0.01
                SERRE.append(segs[-1][1])
            ss = speech_start(w["start"], max(w["start"] - 0.3, W[j - 1]["end"] if jumped else prev["end"]))
            if ss: s = max(ss, segs[-1][1] if not jumped else ss)   # attaque réelle : pas de blanc gardé avant le mot
            s = max(s, w["start"] - 0.15)               # 19/10 : l'inspiration juste avant le mot passe le seuil -> jamais > 0,15 s avant
    segs.append([max(0.0, s), e])
segs = [[a, b] for a, b in segs if b - a > 0.05]
# 19/10 soir (CAM20031) : Whisper colle souvent une pause DANS un mot (« c » de 106,9 à 107,4 s, « intelligence » sur 9 s) et
# le dérush ne la voyait pas : respirations et pauses restaient. Toute pause RÉELLE >= BREATH (énergie sous le seuil
# « respiration », mesurée sur le son, pas sur Whisper) à l'intérieur ou au bord d'une plage gardée est coupée.
def inner_pauses(a, b):
    db, q = _env(); thr = q + PAUSE_DB; out = []; run0 = None
    for i in range(int(a * 100), min(len(db), int(b * 100) + 1)):
        if db[i] < thr:
            if run0 is None: run0 = i
        else:
            if run0 is not None and (i - run0) >= 8: out.append((run0 / 100, i / 100))
            run0 = None
    if run0 is not None and int(b * 100) - run0 >= 8: out.append((run0 / 100, b))
    return out
# 20/10 (retour : « enlève les respirations en début et en fin de phrase, sans couper le mot, il faut que ce soit bien audible ») :
# marges autour de la voix forte = EDGE_IN avant l'attaque (consonne douce gardée), EDGE_OUT après la fin (« s », « x » finals gardés).
EDGE_IN, EDGE_OUT = 0.12, 0.10
# 20/10 (retour : « "longueur d'avance" : on n'entend pas la dernière syllabe ») : la fin douce d'un mot (« -vance », « s », « x »)
# est sous le seuil « voix forte » : couper à p0 + 0,10 la mangeait. La fin du mot = 1er VRAI silence (sous le seuil de parole q,
# 60 ms d'affilée) après la voix forte ; le souffle éventuel qui suit part avec le reste.
def tail_end(p0, lim):
    db, q = _env(); run = 0
    for k in range(int(p0 * 100), min(len(db), int(lim * 100))):
        run = run + 1 if db[k] < q else 0
        if run >= 6: return word_tail((k - 5) / 100, lim)   # 22/10 : fin réelle du mot (queue sourde gardée, souffle collé retiré)
    return None
# 22/10 (IMG_6799 : le « M » de « la signature » mangé) : la voix qui reprend après une pause commence souvent par une consonne
# douce VOISÉE (m, n, l, j, v : -26/-36 dB) sous le seuil « voix forte » de inner_pauses ; p1 - EDGE_IN la coupait (ou la
# baissait). soft_attack remonte depuis p1 tant que le son est au-dessus du bruit de la pièce (FLOOR + 12) et redevient voisé
# (trous sourds de 80 ms max : le « st » de « Mister ») ; une inspiration (sourde) l'arrête : elle reste retirée.
def soft_attack(p0, p1):
    db, q = _env(); fl = _floor() + 12; j, first, miss = int(p1 * 100) - 1, None, 0
    while j > int(p0 * 100) and miss < 9:
        if db[j] >= fl and _voiced(j): first, miss = j, 0
        else: miss += 1
        j -= 1
    return first / 100 if first is not None else p1
_new = []
for a, b in segs:
    cur, end = a, b
    for p0, p1 in inner_pauses(a, b):
        if p0 - cur < 0.05: cur = max(cur, soft_attack(p0, p1) - EDGE_IN); continue   # début de plage : inspiration / blanc retiré (pas de coupe en plus)
        if p1 >= b - 0.01:                                             # fin de plage : souffle / blanc retiré, mot entier
            te = tail_end(p0, b); end = min(end, te if te else end); break
        # 20/10 (retour : « micro-coupures, on dirait que la vidéo bugue ») : une pause AU MILIEU n'est coupée que si on gagne
        # >= MINCUT (marges 0,04 + 0,06 s comprises). Avant : des coupes de 0,16-0,34 s = sauts de tête pour rien.
        _pw = max((w for w in keep if w["end"] <= p0 + 0.1), key=lambda w: w["end"], default=None)
        if _pw is not None and not fin_phrase(_pw): continue   # 23/10 : pause en milieu de phrase = jamais coupée (son baissé)
        te = tail_end(p0, p1) or p0 + EDGE_OUT
        pa = soft_attack(p0, p1) - EDGE_IN
        if pa - te >= MINCUT: _new.append([cur, te]); cur = pa
    if end - cur > 0.05: _new.append([cur, end])
segs = _new
# 17/10 (Tesla 14,8 s : « enlève le micro rush inutile qui saccade ») : un bout gardé < MINSEG entre deux coupes
# (« par » seul, 0,17 s, puis saut) = la tête saute deux fois. On le recolle au bout voisin de la même prise (blanc gardé).
k = 0
while k < len(segs):
    a, b = segs[k]
    if b - a < MINSEG and len(segs) > 1:
        # recollé seulement si le blanc gardé reste court (< 0,5 s) : sinon on entend un silence (17/10 v2, 15 s : « par … exemple »)
        if k + 1 < len(segs) and segs[k + 1][0] - b < 0.5:  segs[k + 1][0] = a; segs.pop(k); continue
        if k > 0 and a - segs[k - 1][1] < 0.5:            segs[k - 1][1] = b; segs.pop(k); continue
        print(f"!! bout de {b - a:.2f} s à {a:.2f} s dans le rush, entre deux prises : le couvrir d'un B-roll ou prendre une autre prise (drop.json)")
    k += 1
# 20/10 (retour : « chaque plan dure minimum 2 secondes », « plus de micro-coupures ») : tout bout de face cam < MINSHOT est recollé
# à son voisin quand la pause entre les deux est courte (< SHOTGAP : elle reste, c'est un temps naturel). Entre deux prises
# (pause longue), impossible : le script le signale, le bout doit être caché sous un B-roll ou un carton.
MINSHOT, SHOTGAP = 2.0, 0.6   # 20/10 : 3 s demandé puis « passe à minimum 2 secondes »
changed = True
while changed and len(segs) > 1:
    changed = False
    for k in range(len(segs)):
        a, b = segs[k]
        if b - a >= MINSHOT: continue
        gn = segs[k + 1][0] - b if k + 1 < len(segs) else 9
        gp = a - segs[k - 1][1] if k > 0 else 9
        if min(gn, gp) >= SHOTGAP: continue
        if gn <= gp: segs[k + 1][0] = a
        else:        segs[k - 1][1] = b
        segs.pop(k); changed = True; break
# 21/10 (CAM20033 v1 à 42 s : « ne fais jamais de cut en plein milieu d'une phrase, j'étais en train de faire des sons
# avec ma bouche ») : --garde garde.json = [[a, b], ...] plages du RUSH où l'on ne coupe jamais (bruitage fait avec la bouche,
# geste, temps voulu) : deux plages gardées dont le blanc tombe dans une zone --garde sont recollées.
GARDE = json.load(open(sys.argv[sys.argv.index("--garde") + 1])) if "--garde" in sys.argv else []
k = 0
while k + 1 < len(segs):
    b0, a1 = segs[k][1], segs[k + 1][0]
    if any(ga < a1 and b0 < gb for ga, gb in GARDE): segs[k][1] = segs[k + 1][1]; segs.pop(k + 1); continue
    k += 1
# 21/10 (CAM20033, Gardien avant rendu : coupes visibles de 0,13 et 0,17 s à 61,2 et 51,7 s) : une virgule comptait comme fin
# de phrase et faisait couper un blanc de 0,26 s pour gagner 0,13 s = saut de tête pour rien. « Zéro micro-coupure » (20/10)
# passe avant « couper toutes les respirations » : deux plages de la MÊME prise (aucun mot supprimé entre elles) séparées de
# moins de MINCUT sont recollées, le petit blanc reste (temps naturel).
k = 0
while k + 1 < len(segs):
    b0, a1 = segs[k][1], segs[k + 1][0]
    if a1 - b0 < MINCUT and not any(b0 - 0.05 <= W[i]["start"] < a1 for i in dead):
        segs[k][1] = segs[k + 1][1]; segs.pop(k + 1); continue
    k += 1
for a, b in segs:
    if b - a < MINSHOT: print(f"!! plan de {b - a:.2f} s ({a:.2f}-{b:.2f} s dans le rush) entre deux prises : à cacher sous un B-roll ou un carton (règle 3 s)")
# Entrée et sortie (16/10 : « ça coupe un peu sec au niveau du hook et à la fin ») : avant, la vidéo démarrait 0,06 s
# avant le 1er mot et s'arrêtait 0,12 s après le dernier. On garde LEAD avant le 1er mot (assez court pour ne pas garder
# la respiration) et TAIL après le dernier (la phrase retombe, la musique peut finir). --lead / --tail pour régler.
LEAD = float(sys.argv[sys.argv.index("--lead") + 1]) if "--lead" in sys.argv else 0.15
TAIL = float(sys.argv[sys.argv.index("--tail") + 1]) if "--tail" in sys.argv else 0.6
if segs:
    segs[0][0] = max(0.0, min(segs[0][0], keep[0]["start"] - LEAD))
    segs[-1][1] = max(segs[-1][1], keep[-1]["end"] + TAIL)
# 28/10 (CAM20062 v1 : « à la toute fin, le rush est mal coupé, il y a une microseconde de trop ») : après le dernier mot il
# s'immobilise (28,33 s), puis rebouge à 28,73 s (il sort du rôle) et TAIL gardait ce geste. La fin s'arrête maintenant sur la
# dernière image immobile : mouvement mesuré image par image dans la traîne, coupe juste avant qu'il ne reparte.
def _fin_immobile(t0, t1):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{t1 - t0:.3f}",
                          "-vf", "fps=30,scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8)
    if len(f) < 108 * 192 * 4: return None
    f = f[: len(f) // (108 * 192) * 108 * 192].reshape(-1, 192, 108).astype(float)
    d = [np.abs(f[i] - f[i - 1]).mean() for i in range(1, len(f))]
    still = next((i for i, x in enumerate(d) if x < 0.8), None)
    if still is None: return None
    go = next((i for i in range(still, len(d)) if d[i] > 0.8 and (i + 1 >= len(d) or d[i + 1] > 0.8)), None)
    return None if go is None else t0 + go / 30   # d[i] = image i+1 contre image i : on garde jusqu'à l'image i comprise
if segs and "--fin-libre" not in sys.argv:
    fe = _fin_immobile(keep[-1]["end"], segs[-1][1])
    if fe and fe >= keep[-1]["end"] + 0.15 and fe < segs[-1][1] - 0.02:
        print(f"fin : il rebouge après le dernier mot -> coupe sur la dernière image immobile ({segs[-1][1] - fe:.2f} s retirées)")
        segs[-1][1] = fe
# 21/10 (CAM20033 v2, Cut Notes : « enlève la respiration dès le départ », « respiration à cut » à 18,6 s, « bug ici » à 11 s) :
# au début d'une plage (1er mot de la vidéo, reprise après une coupe), deux restes passaient :
#  1) une inspiration FORTE (-16/-25 dB, presque la voix) que le seuil d'énergie prenait pour de la parole ;
#  2) la queue d'un mot supprimé (« …tion » de « information ») : Whisper étalait le mot gardé (« mais ») sur 0,8 s, pause comprise.
# Correctifs, sur les seuls débuts de plage (aucune coupe en plus) :
#  - une pause >= 0,12 s À L'INTÉRIEUR du 1er mot selon Whisper = ce qui la précède n'est pas ce mot -> la plage démarre après ;
#  - une inspiration n'a pas de note (pas de voix « voisée ») : la plage démarre EDGE_V avant la 1re trame voisée (la consonne
#    sourde du début, « p », « s », « ch », reste entière).
_RAW = []
def _raw():
    if not _RAW:
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
        _RAW.append(np.frombuffer(raw, dtype=np.float32))
    return _RAW[0]
def first_voiced(t0, t1):   # 1re trame de 10 ms VOISÉE (note de voix : autocorrélation > 0,55 entre 80 et 400 Hz) et assez forte
    import numpy as np
    x, (db, q) = _raw(), _env()
    for k in range(int(t0 * 100), min(len(db), int(t1 * 100))):
        if db[k] < q: continue   # 22/10 (IMG_6799, « Mr » coupé) : un « m », « n », « l » voisé et doux (-26/-36 dB) est une vraie attaque
        f = x[k * 160: k * 160 + 480].astype(np.float64); f = f - f.mean()
        if len(f) < 480: break
        if (f * f).sum() <= 0: continue
        r = max((f[:-l] * f[l:]).sum() / np.sqrt((f[:-l] ** 2).sum() * (f[l:] ** 2).sum() + 1e-12) for l in range(40, 200, 2))
        if r > 0.55: return k / 100
    return None
EDGE_V = 0.10   # mesuré sur CAM20033 : à 0,14 s il restait 0,1 s de souffle (aigus > 30 %, pas de note) ; une consonne sourde fait 0,06-0,12 s
for sg in segs:
    a = sg[0]; w = next((x for x in keep if x["end"] > a + 0.02), None)
    if not w or w["start"] > a + 1.0: continue
    db, q = _env(); run = 0; cut_at = None
    for k in range(int(max(a, w["start"]) * 100), int((w["end"] - 0.05) * 100)):
        run = run + 1 if db[k] < q + PAUSE_DB else 0
        if run >= 12: cut_at, run0 = (k + 1) / 100, k - run + 1   # pause de 120 ms DANS le mot selon Whisper : on démarre après
    if cut_at:
        k = int(cut_at * 100)
        while k < len(db) and db[k] < q + PAUSE_DB: k += 1
        # 22/10 (IMG_6799 : « Mr » de « la signature » perdait son « M ») : la consonne douce du début (-26/-36 dB) est sous le seuil
        # « voix forte » et passait pour la pause. L'attaque = juste après le DERNIER vrai calme (bruit de la pièce + 12 dB)
        # de la pause ; s'il n'y en a pas (souffle d'un bout à l'autre), on garde l'ancien point.
        j = k - 1
        while j > run0 and db[j] >= _floor() + 12: j -= 1
        if j > run0: k = j + 1
        a = max(a, k / 100 - EDGE_IN)
    v = first_voiced(a, min(sg[1], a + 1.2))
    if v is not None and v - EDGE_V > a + 0.03: a = v - EDGE_V
    if a > sg[0] + 0.01 and sg[1] - a > 0.3:
        print(f"début de plage {sg[0]:.2f} -> {a:.2f} s (respiration / reste du mot supprimé retiré)"); sg[0] = round(a, 3)
# 23/10 (cockpit v4, dérushage « phrase en grand ») : --bords bords.json = {"debut": {"i": t}, "fin": {"j": t}}, les bords posés
# À LA MAIN par la personne (poignées Début / Fin, bouton « Garder le souffle ») : i = 1er mot gardé d'une phrase, j = dernier,
# t = seconde du RUSH. Ils passent après tout le calcul automatique. Un bord au milieu d'une plage (pas de coupe là) la coupe en
# deux. Ce qu'elle garde exprès avant / après la voix (souffle) n'est jamais baissé, et le Gardien ne le bloque pas.
BORDS = json.load(open(sys.argv[sys.argv.index("--bords") + 1])) if "--bords" in sys.argv else {}
LIBRE = []
def _plage(t):
    return next((k for k, (a, b) in enumerate(segs) if a - 0.3 <= t <= b + 0.3), None)
def _voisin(i, pas):   # mot gardé juste avant (pas -1) ou juste après (pas +1)
    i += pas
    while 0 <= i < len(W) and i in dead: i += pas
    return i if 0 <= i < len(W) else None
for i, t in sorted((int(k), float(v)) for k, v in BORDS.get("debut", {}).items()):
    if i in dead or i >= len(W) or (k := _plage(W[i]["start"])) is None: continue
    a, b = segs[k]; pk = _voisin(i, -1)
    if pk is None or W[pk]["end"] <= a + 0.02: segs[k][0] = round(t, 3)
    elif t > W[pk]["end"] + 0.05:
        fp = BORDS.get("fin", {}).get(str(pk))
        fp = float(fp) if fp is not None else (speech_end(W[pk]["end"], min(W[pk]["end"] + 0.35, t - 0.02), cap=t - 0.02) or W[pk]["end"] + 0.1)
        segs[k:k + 1] = [[a, round(min(fp, t - 0.01), 3)], [round(t, 3), b]]
    if t < W[i]["start"] - 0.02: LIBRE.append((t, W[i]["start"]))
    print(f"bord posé à la main : début de « {W[i]['text']} » à {t:.2f} s")
for j, t in sorted((int(k), float(v)) for k, v in BORDS.get("fin", {}).items()):
    if j in dead or j >= len(W) or (k := _plage(W[j]["end"])) is None: continue
    a, b = segs[k]; nk = _voisin(j, 1)
    if nk is None or W[nk]["start"] >= b - 0.02: segs[k][1] = round(t, 3)
    elif t < W[nk]["start"] - 0.05:
        dn = BORDS.get("debut", {}).get(str(nk))
        dn = float(dn) if dn is not None else (speech_start(W[nk]["start"], max(t, W[nk]["start"] - 0.3)) or W[nk]["start"] - 0.06)
        segs[k:k + 1] = [[a, round(t, 3)], [round(max(dn, t + 0.01), 3), b]]
    if t > W[j]["end"] + 0.02: LIBRE.append((W[j]["end"], t))
    print(f"bord posé à la main : fin de « {W[j]['text']} » à {t:.2f} s")
segs = sorted([[a, b] for a, b in segs if b - a > 0.05])
# 23/10 (cockpit v5, dérushage en TIMELINE, maquette livrables/cockpit-montage/timeline-r2/1.png) : --plages plages.json =
# [[a, b], ...] les plages GARDÉES posées à la main sur la timeline (secondes du RUSH). Elles remplacent tout le calcul
# automatique (qui ne sert plus qu'à savoir ce que la personne a changé) :
#  - ce qu'elle a remis en plus du calcul auto = gardé exprès (jamais baissé, souffle_garde pour le Gardien) ;
#  - un bord qu'elle a posé elle-même (absent du calcul auto) = coupe « serrée » : le Gardien la signale (à écouter), sans bloquer ;
#  - les mots dont le milieu tombe hors des plages = retirés (sous-titres).
VFS = sys.argv[sys.argv.index("--vf") + 1].split(",") if "--vf" in sys.argv else []
VPRE = "".join(p + "," for p in VFS if p.startswith("fps="))
VPOST = "".join("," + p for p in VFS if not p.startswith("fps="))
FPS = eval(VPRE[4:-1]) if VPRE else eval(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                    "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", src]).decode().strip())
SERRE_D = []
if "--plages" in sys.argv:
    _auto = segs
    segs = sorted([[round(float(a), 3), round(float(b), 3)] for a, b in json.load(open(sys.argv[sys.argv.index("--plages") + 1])) if float(b) - float(a) > 0.05])
    for a, b in segs:   # les morceaux gardés en plus du calcul auto
        cur = a
        for x, y in _auto:
            if y <= cur or x >= b: continue
            if x > cur + 0.05: LIBRE.append((cur, x))
            cur = max(cur, y)
        if b > cur + 0.05: LIBRE.append((cur, b))
    # bord « à la main » = pas sur la même IMAGE qu'un bord auto (le calcul auto calé sur la grille des images, comme cut.segments.json
    # d'où viennent les plages) ; 23/10 IMG_6850 : un bord v4 à 37,20 s, à 1 image du bord auto 37,23 s, passait pour auto.
    _g = lambda t, haut: (math.ceil(t * FPS - 1e-6) if haut else math.floor(t * FPS + 1e-6)) / FPS
    SERRE += [b for a, b in segs if not any(abs(b - _g(y, True)) < 0.005 for x, y in _auto)]
    SERRE_D += [a for a, b in segs if not any(abs(a - _g(x, False)) < 0.005 for x, y in _auto)]
    dead = {i for i, w in enumerate(W) if not any(a - 0.02 <= (w["start"] + w["end"]) / 2 <= b + 0.02 for a, b in segs)}
    keep = [w for i, w in enumerate(W) if i not in dead] or keep
    print(f"plages posées à la main : {len(segs)} ({len(LIBRE)} bout(s) remis, {len(SERRE) + len(SERRE_D)} bord(s) à la main)")
# Synchro image/son (13/10) : chaque plage est calée sur la grille des images (début arrondi en dessous, fin au-dessus).
# Avant, l'image se coupait à l'image près et le son ailleurs : sur 40 coupes, la bouche pouvait se décaler.
# Plages qui se touchent ou se chevauchent = fusionnées (sinon le fondu anti-clic doublerait le volume au raccord).
# 19/10 : avec --vf (rush originale, souvent 29,97 i/s), le passage à 30 i/s (fps=30 du cadre) se fait AVANT la coupe, comme
# quand cadre.py encodait tout le rush : sinon 1 coupe sur 11 tombait 1 image avant le son (mesuré sur c31). Recadrage APRÈS.
snapped = []
for a, b in segs:
    a, b = math.floor(a * FPS + 1e-6) / FPS, math.ceil(b * FPS - 1e-6) / FPS
    if snapped and a <= snapped[-1][1] + 1e-6: snapped[-1][1] = max(snapped[-1][1], b)
    else: snapped.append([a, b])
segs = [[round(a, 4), round(b, 4)] for a, b in snapped]
HALF = 0.5 / FPS   # image : on prend les images de a à b exclu -> exactement (b - a) s, comme le son
# 21/10 (CAM20033 v1, note à 0 s : « au début de chaque phrase, enlève la respiration ») : les petits blancs gardés pour ne
# pas faire de micro-coupure (< MINCUT, recollés plus haut) et la marge LEAD du tout début gardaient l'inspiration. On ne coupe
# plus l'IMAGE pour ça : on coupe seulement le SON de la voix dans ces blancs (la musique continue dessous), avec les mêmes bords
# que les coupes validées le 20/10 (EDGE_IN avant l'attaque : consonne douce gardée ; tail_end : dernière syllabe gardée).
# Jamais dans une zone --garde (bruitage de bouche).
# 19/10 soir (CAM20031 v1 : « à la toute fin, tu pourrais cut mon souffle ») : TAIL garde 0,6 s d'IMAGE après le dernier
# mot (la phrase retombe, la musique finit), mais le son de la voix s'éteint juste après le dernier mot : plus de souffle final.
_lw = keep[-1]["end"] if keep else 0
_se = speech_end(_lw, _lw + 0.35) if keep else None
VOICE_END = (_se + 0.06 if _se else _lw + 0.1)   # +0,06 s : le « x » / « s » final reste entier
if keep and str(W.index(keep[-1])) in BORDS.get("fin", {}):   # fin posée à la main sur le dernier mot : sa voix va jusque-là
    VOICE_END = max(VOICE_END, float(BORDS["fin"][str(W.index(keep[-1]))]))
# 21/10 (CAM20033 v2 à 11 s, « bug ici ») puis 22/10 (IMG_6799 v1 : « dès que j'arrête de parler, il y a un gros silence, ce
# n'est pas naturel ») : la voix ne descend JAMAIS sous le niveau des blancs naturels du rush. Avant : -22 dB fixes dans chaque
# blanc (sur l'iPhone, les blancs vivent à -42/-45 dB : ils tombaient à -65 = trou à chaque fois qu'il se tait) et silence
# numérique (-180 dB) après le dernier mot. Maintenant chaque blanc est baissé juste assez pour que son 90e centile retombe au
# niveau CALME du rush (10e centile de toute la voix, -45 dB ici) : une inspiration forte disparaît, un blanc normal ne bouge pas.
def room_gain(m0, m1):
    import numpy as np
    db = _env()[0]; seg = db[int(m0 * 100):max(int(m0 * 100) + 1, int(m1 * 100))]
    return min(1.0, 10 ** ((float(np.percentile(db, 10)) - float(np.percentile(seg, 90))) / 20))
# 22/10 (IMG_6799, contrôle « mot coupé » du Gardien) : une « pause » de inner_pauses (sous la voix FORTE) peut être de la
# voix douce (« concentre sur » à -27/-33 dB) : elle était baissée de 22 dB sur 60 ms = trou dans la phrase. Et quand la queue
# du mot ne retombe pas dans le calme (souffle juste derrière), tail_end coupait l'explosion du « t » (word_tail la garde).
# Désormais une zone de moins de 0,10 s ou voisée à plus de 20 % n'est jamais baissée.
def voiced_share(m0, m1):
    db = _env()[0]; ks = range(int(m0 * 100), int(m1 * 100))
    return sum(1 for k in ks if db[k] >= _floor() + 12 and _voiced(k)) / max(1, len(ks))
MUTE = []
for a, b in segs:
    for p0, p1 in inner_pauses(a, b):
        m0 = a if p0 - a < 0.05 else (tail_end(p0, p1) or p0 + EDGE_OUT)
        m1 = b if p1 >= b - 0.01 else soft_attack(p0, p1) - EDGE_IN
        if m0 >= VOICE_END - 0.05: continue   # après le dernier mot : géré par la fin de voix (sinon baissé 2 fois)
        if os.environ.get("DERUSH_DEBUG"): print(f"  blanc {p0:.2f}-{p1:.2f} -> baisse {m0:.2f}-{m1:.2f} voisé {voiced_share(m0, m1) if m1 > m0 else 0:.2f}")
        if m1 - m0 < 0.10 or voiced_share(m0, m1) > 0.2: continue
        if any(la < m1 and m0 < lb for la, lb in LIBRE): continue   # souffle gardé exprès (--bords)
        if not any(ga < m1 and m0 < gb for ga, gb in GARDE):
            MUTE.append((round(m0, 3), round(m1, 3), round(room_gain(m0, m1), 3)))
RAMP = 0.015
mute = "+".join(f"{1 - g:.3f}*clip(min((t-{m0})/{RAMP},({m1}-t)/{RAMP}),0,1)" for m0, m1, g in MUTE) or "0"
print(f"{len(MUTE)} respiration(s) / blanc(s) baissés au niveau du bruit de la pièce (image intacte)")

vexpr = "+".join(f"between(t,{a - HALF:.4f},{b - HALF:.4f})" for a, b in segs)   # demi-image de marge : insensible aux arrondis
expr = "+".join(f"between(t,{a},{b})" for a, b in segs)
# Anti-clic (experts 13/10, Vashi Nedomansky) : micro-fondu au début et à la fin de chaque plage gardée, sinon chaque coupe
# peut claquer. 0,03 s : tient dans la marge avant le mot (PRE 0,06 s), ne mange jamais une syllabe.
# asetnsamples=64 : trames audio de 1,3 ms, sinon le fondu (et la coupe) se calent sur des trames de 21 ms.
AFADE = 0.03
GEND = room_gain(VOICE_END, segs[-1][1]) if segs and segs[-1][1] - VOICE_END > 0.05 else 1.0   # souffle final -> bruit de la pièce
fade = "+".join((f"clip(min(min((t-{a})/{AFADE},({b}-t)/{AFADE}),max({GEND:.3f},({VOICE_END:.3f}-t)/0.06)),0,1)" if k == len(segs) - 1 else
                 f"clip(min((t-{a})/{AFADE},({b}-t)/{AFADE}),0,1)") for k, (a, b) in enumerate(segs))   # min() d'ffmpeg = 2 arguments
# 19/10 (retour : « le montage prend du temps ») : --vf "<cadre.json vf>" = le recadrage se fait ICI, sur les seules secondes
# gardées, au lieu d'encoder tout le rush avant (cadre.py --apply). Puce vidéo du Mac (VideoToolbox) au lieu de libx264.
# Plage de couleurs de la source gardée telle quelle (caméra = pc, iPhone = tv) : convertir pc -> tv assombrissait l'image (~5 %).
# JAMAIS -hwaccel videotoolbox au décodage : avec la conversion de plage, l'image sort toute VERTE (testé 19/10). Décodage processeur.
RNG = "pc" if subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_range",
                              "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip() == "pc" else "tv"
subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", src,
    "-vf", f"{VPRE}select='{vexpr}',setpts=N/FRAME_RATE/TB{VPOST},scale=out_range={RNG},format=nv12",
    "-af", f"asetnsamples=n=64,volume='({fade})*(1-({mute}))':eval=frame,aselect='{expr}',asetpts=N/SR/TB",
    "-c:v", "h264_videotoolbox", "-q:v", "75", "-g", "60", "-color_range", RNG, *BT709, "-c:a", "aac", "-b:a", "192k", out])
json.dump(segs, open(out.rsplit(".", 1)[0] + ".segments.json", "w"))
# 22/10 : pour le Gardien (« Pas de mot coupé ») : chaque endroit du RUSH où la voix s'arrête ou est baissée.
PAUSES_PHRASE, _off = [], 0.0   # 23/10 : blancs de milieu de phrase gardés à l'image (temps du montage), le Gardien les signale sans bloquer
for a, b in segs:
    _ks = [w for w in keep if a - 0.1 <= w["start"] < b]
    for w0, w1 in zip(_ks, _ks[1:]):
        if w1["start"] - w0["end"] >= 0.3 and not fin_phrase(w0):
            PAUSES_PHRASE.append([round(_off + w0["end"] - a, 3), round(_off + w1["start"] - a, 3)])
    _off += b - a
json.dump({"src": src, "floor": round(_floor(), 2), "pauses_phrase": PAUSES_PHRASE, "q": round(_env()[1], 2), "voice_end": round(VOICE_END - 0.06, 3),
           "souffle_garde": [k for k, (a, b) in enumerate(segs) if any(la - 0.05 <= a < lb for la, lb in LIBRE) or any(abs(a - x) < 0.06 for x in SERRE_D)],
           "serrees": [round(b - AFADE, 3) for a, b in segs[:-1] if any(abs(b - x) < 0.06 for x in SERRE)]
                      + [round(a + AFADE, 3) for a, b in segs[1:] if any(abs(a - x) < 0.06 for x in SERRE_D)],
           "starts": [round(a + AFADE, 3) for a, b in segs[1:]] + [m1 for m0, m1, g in MUTE if g < 0.5 and not any(abs(m1 - b) < 0.05 for a, b in segs)],
           "ends": [round(b - AFADE, 3) for a, b in segs[:-1]] + [m0 for m0, m1, g in MUTE
                                                                   if g < 0.5 and not any(abs(m0 - a) < 0.05 for a, b in segs)]},
          open(out.rsplit(".", 1)[0] + ".voice.json", "w"))
# Mots recalés sur la version coupée (16/10) : <out>.words.json = la transcription du rush (souvent meilleure que celle
# refaite sur le montage coupé, qui a perdu son contexte) avec les temps de la version coupée.
# 22/10 (IMG_6799 : « je » de « je prépare » absent des sous-titres) : Whisper le faisait démarrer 0,02 s avant la plage
# (9,45 s pour une plage à 9,47 s) : il était oublié. Un mot gardé qui démarre jusqu'à 0,1 s avant la plage en fait partie.
off, moved, seen = 0.0, [], set()
for a, b in segs:
    for i, w in enumerate(W):
        if i not in dead and i not in seen and a - 0.1 <= w["start"] < b and w["end"] > a + 0.03:
            seen.add(i)
            moved.append({**w, "start": round(off + max(w["start"], a) - a, 3), "end": round(off + min(w["end"], b) - a, 3)})
    off += b - a
json.dump({"words": moved}, open(out.rsplit(".", 1)[0] + ".words.json", "w"), ensure_ascii=False)
before = W[-1]["end"]; after = sum(b - a for a, b in segs)
print(f"{len(segs)} plages · {before:.1f}s -> {after:.1f}s · {len(dead)} mots retirés -> {out}")
