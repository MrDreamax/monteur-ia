# Fin réelle d'un mot (22/10/2026, IMG_6799 v1 : « à un moment le mot est coupé, et à la fin aussi le mot est coupé »).
# Partagé par derush.py (où couper / baisser la voix) et gardien.py (contrôle « Pas de mot coupé ») : une seule définition.
#
# Un mot ne s'arrête pas quand la voix forte s'arrête. Après la dernière note de voix il peut rester :
#  - une voix douce qui traîne (« e » muet : « scrip-te », fin de voyelle) : suivie tant qu'elle reprend en moins de 0,30 s ;
#  - une queue SOURDE collée (« x » de « Dreamax » (la signature) 0,20 s, « s », « tre ») : gardée si elle dure 0,25 s au plus, sinon c'est
#    un souffle collé au mot (on garde alors 0,12 s de queue, le reste peut être baissé) ;
#  - l'explosion d'un « t », « p », « k » après 30-90 ms de fermeture (silence) : sourde et brutale (+10 dB en 30 ms),
#    gardée 0,25 s au plus. Une reprise douce (inspiration) ou voisée (le mot suivant) n'en est pas une.
# Seuils : q = seuil de parole (95e centile - 21 dB), floor = bruit de la pièce (3e centile). Trames de 10 ms, énergie lissée 30 ms.

def fin_du_mot(db, voisee, q, floor, e, cap):
    """db : énergie par trame de 10 ms ; voisee(k) -> bool ; e : où la voix forte s'arrête (s) ; cap : limite dure (s)."""
    thr = floor + 15
    # 23/10 (IMG_6850, Gardien « mot coupé » à 59,2 s sur la fin de « ça. ») : sur un rush calme, le seuil de voix douce (q - 4)
    # tombe AU NIVEAU du bruit de la pièce (ici q = -44 dB, bruit = -47 dB), et ce bruit bourdonne (« voisé ») : la voix douce était
    # suivie dans le bourdonnement jusqu'à 0,6 s après le mot. Une voix douce doit rester 6 dB au-dessus du bruit de la pièce.
    doux = max(q - 4, floor + 6)
    k0, n = int(e * 100), min(len(db), int((cap - 0.02) * 100))
    lv = k0
    for k in range(k0, min(n, k0 + 60)):                      # 1) voix douce qui traîne
        if db[k] >= doux and voisee(k):
            if k - lv > 30 or (db[k] >= q + 8 and k - lv > 3): break   # trop loin, ou voix forte = le mot suivant
            lv = k
    last, gap, burst = lv, 0, None
    for k in range(lv + 1, min(n, lv + 60)):                  # 2) queue sourde, puis explosion éventuelle
        if db[k] >= thr:
            if burst is None and gap >= 3:
                if gap > 9 or voisee(k) or db[min(len(db) - 1, k + 2)] - db[k - 1] < 10: break
                burst = k
            elif burst is not None and gap >= 2: break
            if burst is None and k - lv > 25: return max(e, (lv + 13) / 100)          # souffle collé
            if burst is not None and (k - burst >= 25 or (db[k] >= q + 8 and voisee(k))): break
            last, gap = k, 0
        else:
            gap += 1
            if gap > 9 or (burst is not None and gap >= 2): break
    return max(e, (last + 1) / 100 + 0.04)
