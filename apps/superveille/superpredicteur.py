#!/usr/bin/env python3
"""SuperPredicteur : passe un reel au « scanner cerveau » de Higgsfield (Virality Predictor).

Higgsfield refuse plus de 16 s : on coupe le reel en morceaux de 15 s,
Claude envoie chaque morceau (MCP Higgsfield), puis on recolle les rapports.
Moteur commun : le skill superpredicteur ET l'appli SuperVeille (import de decoupe / analyse).

  python3 superpredicteur.py decoupe <reel.mp4> <dossier>
      -> <dossier>/part-000.mp4, part-015.mp4 ... + parts.json
  python3 superpredicteur.py lis <dossier> [--mots mots.json]
      -> lit <dossier>/rapport-000.html, rapport-015.html ... (téléchargés par Claude)
      -> écrit <dossier>/verdict.json + verdict.md et affiche le verdict en français
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

MORCEAU = 15  # Higgsfield : 16 s max
QUEUE_MIN = 3  # dernier bout plus court (souvent la signature) : pas envoyé


def duree(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def decoupe(video, dossier):
    """Coupe en morceaux de 15 s. Renvoie [{"fichier", "debut", "duree"}]."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    total = duree(video)
    parts = []
    debut = 0
    while debut == 0 or debut < total - QUEUE_MIN:
        sortie = dossier / f"part-{debut:03d}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(debut), "-i", str(video),
                        "-t", str(MORCEAU), "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(sortie)], check=True)
        parts.append({"fichier": str(sortie), "debut": debut, "duree": round(duree(sortie), 2)})
        debut += MORCEAU
    (dossier / "parts.json").write_text(json.dumps({"video": str(video), "duree": total, "parts": parts},
                                                   ensure_ascii=False, indent=1))
    return parts


def lire_rapport(chemin):
    s = Path(chemin).read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'<script type="application/json" id="analysisJson">([\s\S]*?)</script>', s)
    if not m:
        raise ValueError(f"Pas de données dans {chemin} (le rapport Higgsfield a changé de format ?)")
    return json.loads(html.unescape(m.group(1)) if m.group(1).lstrip().startswith("&") else m.group(1))


def charger_mots(chemin):
    d = json.loads(Path(chemin).read_text())
    mots = d if isinstance(d, list) else d.get("words", [])
    return [(float(w.get("start", 0)), float(w.get("end", 0)), (w.get("word") or w.get("text") or "").strip())
            for w in mots]


def phrase(mots, de, a):
    return " ".join(t for s, e, t in mots if e > de and s < a + 1).strip()


def fenetres(secondes):
    """[3,4,5,9] -> [(3,5),(9,9)]"""
    out = []
    for t in sorted(secondes):
        if out and t - out[-1][1] <= 1:
            out[-1][1] = t
        else:
            out.append([t, t])
    return [tuple(f) for f in out]


def mmss(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def plage(a, b):
    return mmss(a) if a == b else f"{mmss(a)}-{mmss(b)}"


def analyse(dossier):
    """Recolle les rapport-XXX.html d'un dossier. Renvoie le verdict (dict) et l'écrit dans verdict.json."""
    dossier = Path(dossier)
    rapports = sorted(dossier.glob("rapport-*.html"))
    if not rapports:
        raise ValueError(f"Aucun rapport-XXX.html dans {dossier}")

    courbe, mental, visuel, notes, bords = {}, {}, {}, [], []
    for r in rapports:
        debut = int(re.search(r"rapport-(\d+)", r.name).group(1))
        d = lire_rapport(r)
        sc = d["scores"]
        notes.append({"debut": debut, "duree": d["duration_seconds"] + 1, **{k: sc[k] for k in (
            "overall_score", "brain_engagement", "hook_score", "viral_potential", "sustain")}})
        if debut:
            bords.append(debut)
        regions = {x["id"]: x for x in d["regions"]}
        for i, t in enumerate(d["time_seconds"]):
            courbe[debut + t] = d["global_scores_by_frame"][i]
            if "default_mode" in regions:
                mental[debut + t] = regions["default_mode"]["values_by_frame"][i]
            if "visual_occipital" in regions:
                visuel[debut + t] = regions["visual_occipital"]["values_by_frame"][i]

    poids = sum(n["duree"] for n in notes)
    note = round(sum(n["overall_score"] * n["duree"] for n in notes) / poids)
    engagement = round(sum(n["brain_engagement"] * n["duree"] for n in notes) / poids)
    accroche = notes[0]["hook_score"]

    # Le cerveau décroche = attention dans le 25 % bas ET « pilote automatique » (default mode) dans le 25 % haut.
    # La 1re seconde de chaque morceau (hors début du reel) est ignorée : c'est un raccord, pas le reel.
    sec = [t for t in sorted(courbe) if t not in bords]
    bas = sorted(courbe[t] for t in sec)[max(0, len(sec) // 4 - 1)]
    haut = sorted((mental[t] for t in sec if t in mental), reverse=True)
    haut = haut[max(0, len(haut) // 4 - 1)] if haut else 9
    decroche = fenetres([t for t in sec if courbe[t] <= bas and mental.get(t, 0) >= haut])
    if not decroche:  # pas de chevauchement : on garde les 3 secondes les plus basses
        decroche = fenetres(sorted(sec, key=lambda t: courbe[t])[:3])
    fin = max(sec)
    pic = max((t for t in sec if t < fin) or sec, key=lambda t: courbe[t])  # la dernière seconde (signature, CTA) ne compte pas

    # Rien de neuf à voir = l'œil s'éteint au moins 5 s d'affilée (zone visuelle qui baisse à chaque seconde)
    plat, run = [], []
    for t in sorted(visuel):
        if run and t - run[-1] == 1 and visuel[t] < visuel[run[-1]] and t not in bords:
            run.append(t)
        else:
            if len(run) >= 5:
                plat.append((run[0], run[-1]))
            run = [t]
    if len(run) >= 5:
        plat.append((run[0], run[-1]))

    verdict = {
        "note": note, "accroche": accroche, "engagement": engagement,
        "pic": pic, "decroche": decroche, "rien_a_voir": plat, "morceaux": notes, "bords": bords,
        "courbe": {str(t): round(courbe[t], 4) for t in sorted(courbe)},
        "mental": {str(t): round(mental[t], 4) for t in sorted(mental)},
    }
    (dossier / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1))
    return verdict


def lis(dossier, chemin_mots=None):
    v = analyse(dossier)
    mots = charger_mots(chemin_mots) if chemin_mots else []

    def cite(a, b):
        p = phrase(mots, a, b)
        return f" (« {p[:90]} »)" if p else ""

    lignes = [f"Note : {v['note']}/100 · Accroche (0-3 s) : {v['accroche']}/100 · Cerveau accroché : {v['engagement']}/100",
              f"Pic d'attention : {mmss(v['pic'])}{cite(v['pic'], v['pic'])}"]
    for a, b in v["decroche"][:3]:
        lignes.append(f"Le cerveau décroche : {plage(a, b)}{cite(a, b)}")
    for a, b in v["rien_a_voir"][:2]:
        lignes.append(f"Rien de neuf à voir : {plage(a, b)} -> mettre un B-roll, un zoom ou un texte")
    texte = "\n".join(lignes)
    (Path(dossier) / "verdict.md").write_text(texte + "\n")
    print(texte)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "decoupe":
        print(json.dumps(decoupe(sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=1))
    elif len(sys.argv) >= 3 and sys.argv[1] == "lis":
        try:
            lis(sys.argv[2], sys.argv[sys.argv.index("--mots") + 1] if "--mots" in sys.argv else None)
        except ValueError as e:
            sys.exit(str(e))
    else:
        sys.exit(__doc__)
