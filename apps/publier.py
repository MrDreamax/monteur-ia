"""Vraie publication depuis SuperMonteur et SuperCarrousel (28/10/2026, l'utilisateur : « Oui, active »).

Le clic sur « Publier maintenant » / « Programmer » (confirmé une 2e fois à l'écran) = le OK de l'utilisateur pour CE contenu.
Le serveur prépare les fichiers (vidéo au format Metricool, planche des images candidates pour la cover, slides en JPG)
puis lance Claude (ouvrier_claude, connecteurs Metricool + Higgsfield, rien d'autre) qui suit le skill publieur :
contrôle du compte .business, cover = meilleure image du reel, hébergement Higgsfield, createScheduledPost, vérification.
Aucune clé dans le code : Metricool et Higgsfield passent par les connecteurs claude.ai déjà branchés.

Garde-fous : un contenu à la fois sur le Mac ; jamais deux envois du même contenu en même temps ; un contenu déjà au
registre de publication (reglages_apps) demande « Republier quand même » ; aucun nouvel essai automatique (un échec
partiel ne doit jamais publier deux fois le même réseau) ; tout est écrit dans <dossier>/publication.json.
"""
import datetime
import json
import os
import re
import subprocess
import threading
import time

import ouvrier_claude
import reglages_apps

ICI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.expanduser("~/.claude/skills/publieur")
MC = "mcp__claude_ai_Metricool_Social_Media_Management__"
HF = "mcp__claude_ai_Higgsfield__"
OUTILS = ["Read", "Write", "Edit", "Glob", "Grep", "ToolSearch",
          "Bash(date:*)", "Bash(curl -X PUT:*)", "Bash(curl -sI:*)",
          MC + "getBrandSettings", MC + "createScheduledPost", MC + "getScheduledPosts",
          HF + "media_upload", HF + "media_confirm"]
VERROU = threading.Lock()


def lire(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def ecrire(p, o):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def etat(dossier):
    return lire(os.path.join(dossier, "publication.json"), {}) or {}


def deja_publie(*cles):
    """La ligne du registre qui cite ce contenu (dossier du montage, du reel ou du carrousel), sinon None."""
    try:
        txt = open(reglages_apps.publieur()["registre"], encoding="utf-8").read()
    except OSError:
        return None
    for ligne in txt.splitlines():
        if ligne.startswith("|") and any(c and c in ligne for c in cles):
            col = [x.strip() for x in ligne.strip("|").split("|")]
            return f"{col[0]} · {col[1]}" if len(col) > 1 else ligne[:120]
    return None


def demander(dossier, quoi, reseaux, quand, titre, cles_registre=(), forcer=False):
    """Le clic de l'utilisateur. Renvoie (ok, message). quoi = "reel" ou "carrousel" ; quand = "maintenant" ou "AAAA-MM-JJTHH:MM"."""
    e = etat(dossier)
    if e.get("statut") in ("a_faire", "en_cours"):
        return False, "Déjà en cours d'envoi : attends la fin."
    if not reseaux:
        return False, "Choisis au moins un réseau."
    if quand != "maintenant":
        try:
            if datetime.datetime.fromisoformat(quand) < datetime.datetime.now() + datetime.timedelta(minutes=2):
                return False, "Cette heure est déjà passée : choisis plus tard, ou « Publier maintenant »."
        except ValueError:
            return False, "Date illisible."
    deja = deja_publie(*cles_registre)
    if deja and not forcer:
        return False, f"DEJA:{deja}"
    ecrire(os.path.join(dossier, "publication.json"), {
        "statut": "a_faire", "quoi": quoi, "titre": titre, "reseaux": reseaux, "quand": quand, "deja": deja,
        "demande_le": datetime.datetime.now().isoformat(timespec="seconds"), "etape": "Je prépare l'envoi…"})
    return True, "C'est parti : Claude envoie à Metricool (2 à 5 min)."


def _maj(dossier, **k):
    e = etat(dossier)
    e.update(k)
    ecrire(os.path.join(dossier, "publication.json"), e)


def preparer_reel(dossier, video):
    """Vidéo au format Metricool + planche d'images (2 par seconde) pour choisir la cover."""
    pub = os.path.join(dossier, "_publication")
    os.makedirs(pub, exist_ok=True)
    r = subprocess.run(["bash", os.path.join(SKILL, "scripts", "prep_video.sh"), video, os.path.join(pub, "reel.mp4")],
                       capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise RuntimeError((r.stdout + r.stderr).strip()[-300:] or "vidéo refusée")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", "fps=2,scale=270:-1,tile=8x8",
                    "-frames:v", "1", os.path.join(pub, "candidats.jpg")], timeout=300)
    return pub


def preparer_carrousel(dossier, slides):
    """Slides PNG -> JPG (Metricool et Instagram), dans l'ordre."""
    pub = os.path.join(dossier, "_publication")
    os.makedirs(pub, exist_ok=True)
    sortie = []
    for i, s in enumerate(slides, 1):
        j = os.path.join(pub, f"slide-{i}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", s, "-q:v", "2", j], check=True, timeout=120)
        sortie.append(j)
    return pub, sortie


CONSIGNE = """Tu es Claude, DANS l'appli {appli} de l'utilisateur. Il vient de cliquer « {bouton} » puis de confirmer à l'écran :
c'est SON OK pour publier CE {quoi}, sur CES réseaux seulement : {reseaux}. Ne publie rien d'autre, ne touche à aucun autre post.

À lire d'abord : ~/.claude/skills/publieur/SKILL.md (§ 2 légendes, § 3 cover, § 6 programmer), son mode-client.md, et le carnet
{carnet} (ses lignes passent AVANT le skill). Les outils Metricool et Higgsfield se chargent avec ToolSearch.

Le {quoi} : « {titre} ». Dossier : {dossier}
{fichiers}
Légendes déjà écrites (à garder si elles respectent le carnet, sinon corrige-les) : {legendes}
Heure : {heure}

Étapes :
1. getBrandSettings (blogId {brand}) : Instagram doit être « {instagram} ». Sinon : n'envoie RIEN, va à l'étape 6 avec l'erreur.
2. {etape_cover}
3. Héberge les fichiers avec Higgsfield : media_upload, puis pour chaque fichier EXACTEMENT
   `curl -X PUT -H "Content-Type: <type>" -H "If-None-Match: *" --data-binary @<fichier> '<upload_url>'`, puis media_confirm,
   puis `curl -sI <url>` doit répondre 200.
4. createScheduledPost (blogId {brand}, fuseau Europe/Paris, autoPublish true, draft false) : un post par groupe de réseaux
   comme dans le skill et le carnet ({groupes}). « maintenant » = lance `date` JUSTE avant chaque appel et mets l'heure + 1 min.
   Un appel qui échoue : relance-le UNE fois. Ne recrée JAMAIS un réseau déjà parti (vérifie avec getScheduledPosts).
5. getScheduledPosts sur la journée : vérifie qu'il y a bien un post par réseau demandé.
6. Écris {dossier}/publication.json en gardant ses champs et en changeant : "statut" ("programme" si tout est parti,
   "partiel" si un réseau manque, "erreur" si rien n'est parti), "fini_le", "heure" (l'heure de publication),
   "posts" [{{"reseaux": [...], "planner": "<plannerUrl>"}}], "manque" [réseaux pas partis], "message" (1 phrase pour l'utilisateur),
   "legendes" (celles envoyées){cover_champ}.
7. Ajoute 1 ligne au tableau de {registre} (crée-le s'il manque : | date | titre | fichier | statut | réseaux | liens |), au format des lignes existantes
   (date et heure, titre, chemin du fichier, statut, réseaux, liens planner).
Réponds en 1 ligne."""


def lancer(dossier, appli, contexte):
    """Fait le travail pour un dossier dont publication.json est « a_faire ». contexte = ce que l'appli sait du contenu :
    quoi, video ou slides, legendes (dict réseau -> texte)."""
    e = etat(dossier)
    pub = reglages_apps.publieur()
    if not pub["brand"]:
        _maj(dossier, statut="erreur", etape="", message="Metricool n'est pas branché : dans Claude, écris « Programme ma semaine » "
                                                          "pour le 1er lancement du Publieur. Rien n'est parti.")
        return
    with VERROU:
        _maj(dossier, statut="en_cours", etape="Je prépare les fichiers…", debut=time.time())
        try:
            reseaux = ", ".join(e["reseaux"])
            if e["quoi"] == "reel":
                pub = preparer_reel(dossier, contexte["video"])
                fichiers = f"Vidéo prête pour Metricool : {pub}/reel.mp4 (type video/mp4).\nPlanche des images (2 par seconde, de gauche à droite puis ligne par ligne) : {pub}/candidats.jpg"
                # la transcription du montage : le CTA DIT dans la vidéo (« deux barres, ça m'intéresse ») va en ligne 2 de la légende
                mots = next((os.path.join(dossier, f) for f in ("words.json", "cut.words.json") if os.path.isfile(os.path.join(dossier, f))), None)
                if mots:
                    fichiers += f"\nTranscription du reel (mots dits, lis-la pour le sujet et le CTA dit à voix haute) : {mots}"
                cover = ("Cover = la meilleure image DU reel (skill § 3) : regarde candidats.jpg (Read), choisis l'image (visage net, "
                         "yeux ouverts, pas de sous-titre sur le visage), envoie-la comme moment de la vidéo (videoCoverMilliseconds = "
                         "rang de l'image × 500 ms, et l'équivalent TikTok / YouTube). Jamais une image générée.")
                groupes = "Instagram + Facebook ensemble, TikTok, YouTube Shorts, LinkedIn : seulement ceux demandés"
                cover_champ = ', "cover_ms" (le moment choisi)'
            else:
                pub, jpgs = preparer_carrousel(dossier, contexte["slides"])
                fichiers = "Slides prêtes, dans l'ordre (type image/jpeg) :\n" + "\n".join(jpgs)
                cover = "Pas de cover à choisir : la 1re slide est la couverture. Regarde quand même la 1re et la dernière slide (Read)."
                groupes = ("Instagram (type POST, alt text), Facebook à part, TikTok mode photo (title obligatoire, autoAddMusic true), "
                           "LinkedIn (publishImagesAsPDF + documentTitle) : seulement ceux demandés ; hors Instagram, pas de « Commente MOT »")
                cover_champ = ""
            heure = "maintenant" if e["quand"] == "maintenant" else e["quand"].replace("T", " ") + " (heure de Paris)"
            prompt = CONSIGNE.format(appli=appli, bouton="Publier maintenant" if e["quand"] == "maintenant" else "Programmer",
                                     quoi=e["quoi"], reseaux=reseaux, titre=e.get("titre", ""), dossier=dossier, fichiers=fichiers,
                                     legendes=json.dumps(contexte.get("legendes") or {}, ensure_ascii=False), heure=heure,
                                     brand=pub["brand"], instagram=pub["instagram"] or "le compte de la marque (getBrandSettings)",
                                     carnet=pub["carnet"], registre=pub["registre"], etape_cover=cover, groupes=groupes, cover_champ=cover_champ)
            _maj(dossier, etape="Claude envoie à Metricool (2 à 5 min)…")
            ok, sortie = ouvrier_claude.lancer(prompt, dossier, OUTILS, delai=1500, modele="opus",
                                               autres_dossiers=(os.path.dirname(pub["registre"]), SKILL))
            if etat(dossier).get("statut") == "en_cours":   # Claude n'a pas écrit le résultat : on ne sait pas ce qui est parti
                _maj(dossier, statut="erreur", message="Je ne sais pas si c'est parti : vérifie le planner Metricool avant de relancer. "
                                                       + (sortie or "")[-200:])
        except Exception as x:
            _maj(dossier, statut="erreur", message=f"Rien n'est parti : {str(x)[:250]}")
        finally:
            _maj(dossier, etape="")
