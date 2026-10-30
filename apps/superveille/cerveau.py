"""Le scanner cerveau dans SuperVeille (28/10/2026) : 1 clic « Scanner ce reel » dans la fiche d'un reel traduit.
Le calcul vient du SuperPredicteur (~/.claude/skills/superpredicteur/scripts/superpredicteur.py, moteur commun) :
Higgsfield (Virality Predictor, compris dans l'abonnement) prédit le cerveau seconde par seconde, 16 s max par vidéo,
2 analyses à la fois au plus. Ici : où sont les fichiers, le temps de chaque phrase, l'étiquette de chaque phrase, la recette.
reel["cerveau"] = {statut: attente | prepare | scan | calcul | fini | erreur, faits, total, note, accroche, decroche_a,
                   tags: [{tag, t}] (une par phrase), regles: [{type, titre, detail}], erreur}
"""
import os
import re
import shutil
import sys

import commun as c

import superpredicteur as sp  # noqa: E402

TYPES = ("garde", "coupe", "image")


def dossier(vid, code):
    return c.chemin(vid, "_scan", code)


def reel(vid, code):
    return next((r for r in c.veille(vid).get("reels", []) if r["code"] == code), None)


def maj(vid, code, **champs):
    def f(v):
        for r in v.get("reels", []):
            if r["code"] == code:
                r["cerveau"] = dict(r.get("cerveau") or {}, **champs)
    c.maj_veille(vid, f)


def temps_phrases(r):
    """(début, fin) en secondes de chaque phrase traduite. Les mots de chaque segment Whisper sont étalés sur sa durée,
    puis les phrases prennent leurs mots dans l'ordre (recalé si la traduction a corrigé quelques mots)."""
    mots = []
    for s in (r.get("transcription") or {}).get("segments", []):
        w = s["texte"].split()
        pas = (s["fin"] - s["debut"]) / max(1, len(w))
        mots += [(s["debut"] + i * pas, s["debut"] + (i + 1) * pas) for i in range(len(w))]
    phrases = r.get("phrases") or []
    tailles = [max(1, len(ph["o"].split())) for ph in phrases]
    if not mots:
        return [(0, 0)] * len(phrases)
    ratio, k, out = len(mots) / sum(tailles), 0.0, []
    for n in tailles:
        a, b = int(k), max(int(k), int(k + n * ratio) - 1)
        out.append((round(mots[min(a, len(mots) - 1)][0], 1), round(mots[min(b, len(mots) - 1)][1], 1)))
        k += n * ratio
    return out


def etiquettes(v, temps):
    """Une étiquette par phrase, en COMPARANT les phrases entre elles (28/10 : sur le reel viral de @thechrisdo, « touche une
    seconde basse » mettait 14 phrases sur 25 en rouge) : accroche = la 1re phrase ; decroche = les 3 phrases les plus basses
    au plus (15 %) ; garde = les 3 plus hautes au plus ; image = la phrase la plus prise dans chacune des 2 plus longues
    plages « rien de neuf à voir »."""
    courbe = {int(t): x for t, x in v["courbe"].items()}
    bords = set(v.get("bords", []))

    def moyenne(a, b):
        sec = [t for t in range(int(a), int(b) + 1) if t in courbe and t not in bords]
        return sum(courbe[t] for t in sec) / len(sec) if sec else None

    scores = [moyenne(a, b) for a, b in temps]
    accroche = 0 if temps and temps[0][0] < 3 else None
    idx = sorted((i for i, x in enumerate(scores) if x is not None and i != accroche), key=lambda i: scores[i])
    k = max(1, min(3, round(len(idx) * 0.15))) if idx else 0
    bas, haut = set(idx[:k]), set(idx[-k:]) - set(idx[:k])
    tags = [None] * len(temps)
    if accroche is not None:
        tags[0] = "accroche"
    for i in bas:
        tags[i] = "decroche"
    for i in haut:
        tags[i] = "garde"
    for x, y in sorted(v["rien_a_voir"], key=lambda w: w[0] - w[1])[:2]:  # les 2 plus longues
        prise = {i: min(int(b), y) - max(int(a), x) + 1 for i, (a, b) in enumerate(temps) if tags[i] is None}
        prise = {i: n for i, n in prise.items() if n > 0}
        if prise:
            tags[max(prise, key=prise.get)] = "image"
    return [{"tag": tg, "t": sp.mmss(a)} for tg, (a, b) in zip(tags, temps)]


def calcul(vid, code):
    """Recolle les rapports, pose les notes et les étiquettes sur le reel. Renvoie le texte que Claude lit pour la recette."""
    r = reel(vid, code)
    v = sp.analyse(dossier(vid, code))
    temps = temps_phrases(r)
    tags = etiquettes(v, temps)
    dec = next((x["t"] for x in tags if x["tag"] == "decroche"), "")
    maj(vid, code, statut="calcul", note=v["note"], accroche=v["accroche"], decroche_a=dec, tags=tags)
    mots = {"accroche": "ACCROCHE", "decroche": "LE CERVEAU DÉCROCHE", "image": "RIEN DE NEUF À VOIR", "garde": "PIC D'ATTENTION"}
    lignes = [f"Note cerveau {v['note']}/100 · accroche (0-3 s) {v['accroche']}/100 (sous 50 = faible)",
              "Les phrases sont comparées entre elles : PIC = les plus hautes, DÉCROCHE = les plus basses du reel.", ""]
    for ph, (a, b), tg in zip(r.get("phrases") or [], temps, tags):
        lignes.append(f"[{sp.mmss(a)}] {mots.get(tg['tag'], '-')} · {ph['f']}")
    return "\n".join(lignes)


def valider_recette(d):
    """Refus (texte) ou None. 3 ou 4 règles, garde puis coupe puis image, courtes."""
    regles = d.get("regles") if isinstance(d, dict) else None
    if not isinstance(regles, list) or not 3 <= len(regles) <= 4:
        return "il faut 3 ou 4 règles dans \"regles\"."
    ordre = [TYPES.index(x.get("type")) if x.get("type") in TYPES else -1 for x in regles]
    if -1 in ordre:
        return "type = garde, coupe ou image."
    if ordre != sorted(ordre):
        return "ordre : garde d'abord, puis coupe, puis image."
    for x in regles:
        if not x.get("titre") or len(re.findall(r"\w+", x["titre"])) > 7:  # les mots, pas « ? »
            return f"titre vide ou de plus de 7 mots : {x.get('titre')!r}."
        if not x.get("detail") or len(re.findall(r"\w+", x["detail"])) > 30:
            return f"détail vide ou trop long (30 mots max) : {x.get('titre')!r}."
        if any(m in (x["titre"] + x["detail"]).lower() for m in ("cortex", "default mode", "score", "voler")):
            return "zéro jargon (cortex, default mode, score) et jamais « voler »."
    return None


def ranger(vid, code):
    """Fin du scan : on garde verdict.json, on jette les morceaux vidéo et les rapports (6 Mo chacun)."""
    d = dossier(vid, code)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith((".mp4", ".html")):
                os.remove(os.path.join(d, f))


def oublier(vid, code):
    shutil.rmtree(dossier(vid, code), ignore_errors=True)
