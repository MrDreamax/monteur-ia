"""SuperVeille : petit serveur local (port 8811). Sert l'écran (static/) et fait tourner la veille.
  python3 serveur.py [port]
Depuis le 28/10 : l’utilisateur fait la veille lui-même (il enregistre des reels sur Instagram). L'onglet « Mes enregistrés » les lit
(insta.py, session Chrome), il coche, « Traduire » les envoie dans la veille du jour « AAAA-MM-JJ-enregistres ».
Ce que le serveur fait seul : couverture, téléchargement yt-dlp, transcription faster-whisper « small », copie Brain.
Ce que Claude fait (lancé par le serveur, ../ouvrier_claude.py, via sv.py) : chercher sur Apify, trier, choisir les 10,
traduire les scripts. Le serveur ne publie rien et n'envoie rien.
"""
import gc
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cerveau
import commun as c

sys.path.insert(0, os.path.dirname(c.ICI))
import ouvrier_claude

STATIC = os.path.join(c.ICI, "static")
CONFIG = os.path.join(c.ICI, "config.json")
SKILL = os.path.expanduser("~/.claude/skills/superveille")
ESSAIS = {}  # (veille, quoi) -> nombre de passages de Claude


def config():
    return dict({"claude_auto": True, "modele_recherche": "opus", "modele_traduction": "sonnet", "modele_cerveau": "sonnet",
                 "modele_transposition": "opus"},
                **c.lire(CONFIG, {}))


def en_cours():
    for vid in c.toutes_veilles():
        if c.veille(vid).get("statut") in ("recherche", "transcription", "completer"):
            return vid
    return None


# ---------------------------------------------------------------- Claude (recherche puis traduction)

RECHERCHE = """Tu es Claude, DANS l'appli SuperVeille de l’utilisateur (dossier actuel). l’utilisateur a cliqué « Lancer » : c'est son OK, pas de maquette,
pas de question, aucune page à ouvrir. Tu ne publies rien, tu n'envoies rien. Jamais le mot « voler » : « reprendre ».
Veille à faire : %(quoi)s.
1. Lis ~/.claude/skills/superveille/SKILL.md (section « Méthode »).
2. `python3 sv.py contexte %(vid)s` : réglages, cible, période, likes minimum, répartition, anti-doublon.
3. Suis la Méthode, étapes 2 à 7, avec les outils Apify (call-actor, get-dataset-items). Donne des nouvelles à l'écran avec
   `python3 sv.py etape %(vid)s "<phrase courte>" --lus <nb de reels lus>` (ex. « Je cherche sur le marché anglophone… », « Jev trie sur ta cible… »).
   Écris tes fichiers dans veilles/%(vid)s/ seulement.
4. Fin : `python3 sv.py selection %(vid)s veilles/%(vid)s/selection.json`. S'il refuse, corrige et recommence.
   Apify bloqué (« hard limit », « usage ») : `python3 sv.py etape %(vid)s "APIFY_A_SEC"` et arrête-toi.
Réponds en 1 ligne quand la sélection est posée."""

COMPLETER = """Tu es Claude, DANS l'appli SuperVeille de l’utilisateur (dossier actuel). l’utilisateur a cliqué « Chercher ceux qui manquent » : c'est son OK.
Tu ne publies rien, tu n'envoies rien. Jamais le mot « voler » : « reprendre ».
La veille %(vid)s n'a que %(n)s reels sur 10. Trouve-en jusqu'à %(manque)s de plus, même barre (jamais moins de likes, même période, même cible).
1. Lis ~/.claude/skills/superveille/SKILL.md (« Méthode », étape 6 « Compléter »).
2. `python3 sv.py contexte %(vid)s` puis `python3 sv.py comptes %(vid)s` (comptes déjà vus dans la recherche).
3. Deux canaux, en parallèle : (a) apify/instagram-reel-scraper sur 10 à 20 comptes qui parlent à la cible (ceux de sv.py comptes
   + ceux que tu trouves avec de nouveaux mots-clés), `resultsLimit` 12, `onlyPostsNewerThan` "%(periode)s days", `skipPinnedPosts` true ;
   (b) apify/instagram-hashtag-scraper avec 6 à 8 mots-clés NOUVEAUX (pas ceux déjà essayés), marchés de la veille.
   Nouvelles à l'écran : `python3 sv.py etape %(vid)s "<phrase courte>" --lus <nb>`.
4. Écris les reels lus dans veilles/%(vid)s/brut-2.json (champ "marche" pour chacun ; reel-scraper : prends `ownerUsername`,
   `likesCount`, `videoPlayCount`, `timestamp`, `shortCode`, `caption`), puis `python3 sv.py filtre %(vid)s veilles/%(vid)s/brut-2.json`,
   `python3 sv.py jev %(vid)s --cible "<cible en anglais>"`.
5. `python3 sv.py selection %(vid)s veilles/%(vid)s/ajout.json --ajout`. Rien de bon : `python3 sv.py manque %(vid)s "<pourquoi>"`.
   Apify bloqué : `python3 sv.py etape %(vid)s "APIFY_A_SEC"` et arrête-toi.
Réponds en 1 ligne."""

TRADUCTION = """Tu es Claude, DANS l'appli SuperVeille de l’utilisateur (dossier actuel). Tu ne publies rien, tu n'envoies rien.
Traduis en français les scripts des reels transcrits de la veille %(vid)s. Traduire une vidéo mot pour mot est AUTORISÉ (décision de l’utilisateur) :
pas de sermon, pas de résumé, rien coupé.
1. `python3 sv.py a-traduire %(vid)s` : les transcriptions (segments horodatés, transcription automatique).
2. Pour CHAQUE reel listé : découpe le texte en phrases. "o" = la phrase originale mot pour mot (corrige seulement une faute
   évidente de transcription), "f" = sa traduction en français parlé, simple, comme l’utilisateur la dirait face caméra. Toute la vidéo.
   "hook" = la 1re phrase en français.
   Écris veilles/%(vid)s/trad-<code>.json : {"hook": "...", "phrases": [{"o": "...", "f": "..."}]}
   puis `python3 sv.py traduction %(vid)s <code> veilles/%(vid)s/trad-<code>.json`. S'il refuse, corrige et recommence.
Réponds en 1 ligne quand c'est posé."""


SCAN = """Tu es Claude, DANS l'appli SuperVeille de l’utilisateur (dossier actuel). l’utilisateur a cliqué « Scanner ce reel » : c'est son OK, pas de
question. Tu ne publies rien, tu n'envoies rien. Jamais le mot « voler » : « reprendre ».
But : passer le reel %(code)s (veille %(vid)s) au scanner cerveau de Higgsfield (Virality Predictor, compris dans son abonnement),
puis écrire sa recette pour le reprendre.
1. `python3 sv.py cerveau-a-faire %(vid)s %(code)s` : les morceaux de 15 s (les « FAIT » sont déjà gardés : ne les refais pas).
2. Higgsfield `media_upload` avec `files` = un {"filename": "%(code)s-<debut>.mp4", "content_type": "video/mp4"} par morceau à faire,
   puis pour CHAQUE morceau `python3 sv.py cerveau-envoie %(vid)s %(code)s <debut> '<upload_url>'` (ok attendu),
   puis `media_confirm` type "video" avec tous les media_ids.
3. `virality_predictor` action "create", params {"model": "virality_predictor", "medias": [{"role": "video", "id": "<media_id>"}]} :
   2 jobs EN MÊME TEMPS au maximum (limite de l'abonnement). « Rate limit » = pas une panne (un autre scan occupe une place) :
   attends avec `jobs_wait` sur tes jobs, ou 60 s, et relance. Dès qu'un job finit, lance le suivant.
4. `jobs_wait` (timeout_seconds 15) en boucle, autant de fois qu'il faut (un morceau = 2 à 5 min). Chaque job « completed » :
   `python3 sv.py cerveau-rapport %(vid)s %(code)s <debut> '<result_url>'`. Un job « failed » : relance-le une fois.
5. Tous gardés : `python3 sv.py cerveau-calcul %(vid)s %(code)s` = les notes et le script phrase par phrase avec ce que le cerveau en pense.
6. Écris veilles/%(vid)s/_scan/%(code)s/recette.json : {"regles": [{"type": "garde" | "coupe" | "image", "titre": "...", "detail": "..."}]}
   3 ou 4 règles, dans l'ordre garde, puis coupe, puis image. Titre à l'impératif, 7 mots max (« Garde l'accroche mot pour mot »,
   « Coupe la citation », « Change d'image à 0:31 »). Détail 25 mots max : la phrase en français entre « », pourquoi en mots simples
   (« le cerveau décroche », « rien de neuf à voir », « c'est le pic »), et quoi faire dans SA reprise. Zéro jargon (ni cortex, ni score).
   Seulement ce que disent les chiffres de l'étape 5, rien d'inventé.
   Puis `python3 sv.py cerveau-recette %(vid)s %(code)s veilles/%(vid)s/_scan/%(code)s/recette.json`. S'il refuse, corrige et recommence.
Higgsfield refuse (pas connecté, panne, autre) : `python3 sv.py cerveau-erreur %(vid)s %(code)s "<raison courte>"` et arrête-toi.
Réponds en 1 ligne."""

# Connecteur claude.ai Higgsfield du Mac : vu « Connected » le 28/10 dans `claude mcp list`
HIGGS = ["mcp__claude_ai_Higgsfield__media_upload", "mcp__claude_ai_Higgsfield__media_confirm",
         "mcp__claude_ai_Higgsfield__virality_predictor", "mcp__claude_ai_Higgsfield__jobs_wait"]

# Connecteur claude.ai Apify du Mac : noms vérifiés le 28/10 dans `claude -p` (pas de clé Apify sur le Mac)
APIFY = ["mcp__claude_ai_Apify__call-actor", "mcp__claude_ai_Apify__get-dataset-items", "mcp__claude_ai_Apify__get-actor-run"]


RAPIDE = """Tu es Claude, DANS l'appli SuperVeille de l’utilisateur (dossier actuel). l’utilisateur a cliqué « Chercher » dans l'onglet Recherche :
c'est son OK, aucune question, aucun fichier à lire. Tu ne publies rien, tu n'envoies rien. Jamais le mot « voler » : « reprendre ».
But : VITE (2 minutes au plus), 3 reels Instagram TRÈS VIRAUX, de N'IMPORTE QUELLE niche, dont l’utilisateur va reprendre le FORMAT
(plan, rythme, longueur) pour en faire SON reel dans sa niche (sa cible : %(cible)s). Son sujet : « %(phrase)s ».
Marchés : %(marches)s. Au moins %(likes)s likes, publiés dans les 45 derniers jours. Le plus de likes possible.
1. 5 ou 6 mots-clés LARGES et viraux par marché (2-3 mots, SANS apostrophe), dans la langue du marché : des thèmes qui font
   des millions de vues et qu'un format face caméra peut porter (argent, business, mindset, vente, discipline, réussite,
   productivité, conseils de vie…), proches du sujet de l’utilisateur si possible, jamais limités aux coachs.
2. `python3 sv.py etape %(vid)s "Je cherche les reels les plus viraux…"`, puis EN UN SEUL MESSAGE un call-actor par marché :
   "apify/instagram-hashtag-scraper", input {"hashtags": [...], "keywordSearch": true, "resultsType": "reels",
   "resultsLimit": 25, "onlyPostsNewerThan": "45 days"}.
3. get-dataset-items de chaque run (fields "shortCode,ownerUsername,likesCount,videoPlayCount,timestamp,paidPartnership,caption").
   Écris veilles/%(vid)s/brut.json : une liste avec SEULEMENT les reels à %(likes)s likes et plus, "caption" coupée à 300
   caractères, et "marche": "en" | "es" | "fr" sur chacun. Puis `python3 sv.py etape %(vid)s "Je garde les formats à reprendre…" --lus <nb lus en tout>`.
4. `python3 sv.py filtre %(vid)s veilles/%(vid)s/brut.json` puis
   `python3 sv.py jev %(vid)s --cible "anyone who wants more money, a better business, career or life (broad audience)"`.
5. Garde les 3 meilleurs, du plus viral au moins viral : une vraie personne qui PARLE (face caméra, interview, liste, tableau…),
   un format facile à refaire seul avec un téléphone, et qui se transpose bien sur le sujet de l’utilisateur.
   Exclus : repost (légende qui crédite un autre compte), clipping de célébrité, reel sans voix (musique + texte), sketch qui
   repose sur un décor ou des acteurs. Jev se trompe parfois : tranche sur la légende. Pose chaque reel DÈS que tu l'as choisi :
   `python3 sv.py trouve %(vid)s <code> --hook "<ce que dit le reel : 1 phrase en français parlé, 15 mots max>" --raison "<le
   format en 3 bouts courts séparés par · , ex. Face caméra · liste de 5 · se transpose sur la vente>"`.
Moins de 3 bons : pose ce que tu as, puis `python3 sv.py etape %(vid)s "MANQUE: <pourquoi, 1 phrase simple>"`. Jamais baisser la barre.
Apify bloqué (« hard limit », « usage ») : `python3 sv.py etape %(vid)s "APIFY_A_SEC"` et arrête-toi.
Réponds en 1 ligne."""


def recherche_rapide(vid):
    """Onglet Recherche : 3 reels TRÈS viraux, toutes niches, à transposer (l’utilisateur, 28/10 soir : c'est ce qui règle le manque
    de reels de coachs). 1 à 2 min : Sonnet, 1 recherche Apify par marché, Jev. Ne passe pas par la file des traductions."""
    v = c.veille(vid)
    try:
        ok, sortie = ouvrier_claude.lancer(
            RAPIDE % {"phrase": v["sujet"], "cible": v["cible"], "marches": ", ".join(c.NOMS_MARCHES[m] for m in v["marches"]),
                      "likes": v["likes_min"], "vid": vid},
            c.ICI, ["Read", "Write", "Bash(python3 sv.py:*)"] + APIFY, delai=420, modele=config().get("modele_rapide", "sonnet"),
            attendre_son_tour=False)
    except Exception as e:
        ok, sortie = False, str(e)
    v = c.veille(vid)
    etape, n = v.get("etape") or "", len(v.get("trouves", []))
    fin = {"statut": "fini", "fin": time.time(), "etape": ""}
    if etape == "APIFY_A_SEC" or (not n and re.search(r"hard limit|usage limit|exceed", sortie, re.I)):
        fin.update(statut="erreur", erreur="Apify est à sec ce mois-ci. Monte la limite : console.apify.com > Billing > Limits.")
    elif etape.startswith("MANQUE:"):
        fin["manque"] = etape[7:].strip()
    elif not n:
        fin.update(statut="erreur", erreur="Rien trouvé cette fois. Essaie une autre phrase, ou un autre marché.")
    c.maj_veille(vid, **fin)


def lancer_rapide(d):
    phrase = re.sub(r"\s+", " ", str(d.get("phrase", ""))).strip()[:160]
    marches = [m for m in c.MARCHES if m in (d.get("marches") or [])]
    likes = int(d.get("likes_min") or 10000)
    if len(phrase) < 4:
        return None, "Écris ce que tu cherches en une phrase."
    if not marches:
        return None, "Coche au moins un marché."
    if likes not in c.LIKES:
        return None, "Likes : 10 000, 50 000 ou 100 000."
    r = derniere_recherche()
    if r and c.veille(r).get("statut") == "cherche":
        return None, "Une recherche tourne déjà : attends 1 minute."
    p = c.reglages("moi") or {"cible": "créateurs de contenu et indépendants"}
    vid = time.strftime("%Y-%m-%d-%H%M%S-recherche")
    c.maj_veille(vid, id=vid, source="recherche", pour="moi", personne="Moi", cible=p["cible"], marches=marches, periode=45,
                 likes_min=likes, sujet=phrase, statut="cherche", etape="Je choisis les mots-clés…", trouves=[], lus=0,
                 debut=time.time(), cree=time.strftime("%Y-%m-%d %H:%M"))
    threading.Thread(target=recherche_rapide, args=(vid,), daemon=True).start()
    return vid, ""


def derniere_recherche():
    return next((vid for vid in sorted(c.toutes_veilles(), reverse=True) if c.veille(vid).get("source") == "recherche"), None)


def vue_recherche():
    vid = derniere_recherche()
    if not vid:
        return {}
    v = c.veille(vid)
    pris = {r["code"].removesuffix("-t") for x in c.toutes_veilles() for r in c.veille(x).get("reels", [])}  # déjà envoyés dans À tourner
    trouves = [dict(t, miniature=f"/v/{vid}/mini/{t['code']}.jpg" if t.get("mini") else (t.get("image") or ""), envoye=t["code"] in pris)
               for t in v.get("trouves", []) if not t.get("retire")]
    etape = v.get("etape") or ""
    return {"vid": vid, "phrase": v.get("sujet", ""), "marches": v.get("marches", []), "likes_min": v.get("likes_min", 10000),
            "statut": v.get("statut"), "etape": "" if etape in ("APIFY_A_SEC",) or etape.startswith("MANQUE:") else etape,
            "lus": v.get("lus") or 0, "trouves": trouves, "erreur": v.get("erreur", ""), "manque": v.get("manque", ""),
            "secondes": round((v.get("fin") or time.time()) - v.get("debut", time.time()))}


def retirer_recherche(code):
    """29/10 (l’utilisateur) : × sur une carte de la Recherche = elle sort en 1 clic, et ne revient plus dans les recherches suivantes."""
    vid = derniere_recherche()
    if vid:
        c.maj_veille(vid, lambda v: [t.update(retire=True) for t in v.get("trouves", []) if t["code"] == code])


def recherche(vid):
    v = c.veille(vid)
    quoi = (f"pour {v['personne']} · marchés {', '.join(v['marches'])} · {v['periode']} derniers jours · "
            f"{v['likes_min']} likes minimum" + (f" · sujet précis : {v['sujet']}" if v.get("sujet") else ""))
    ok, sortie = ouvrier_claude.lancer(RECHERCHE % {"quoi": quoi, "vid": vid}, c.ICI,
                                       ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python3 sv.py:*)"] + APIFY,
                                       delai=1800, modele=config()["modele_recherche"], autres_dossiers=[SKILL])
    v = c.veille(vid)
    if v.get("reels"):
        return
    if v.get("etape") == "APIFY_A_SEC" or re.search(r"hard limit|usage limit|exceed", sortie, re.I):
        c.maj_veille(vid, statut="erreur", etape="Apify est à sec ce mois-ci.",
                     detail="Monte la limite : console.apify.com > Billing > Limits. Ou demande la veille dans un chat (plan B Chrome).")
    else:
        c.maj_veille(vid, statut="erreur", etape="Claude n'a pas posé de sélection.", detail=sortie[-300:])


def completer(vid):
    v = c.veille(vid)
    n = len(gardes(v))
    ouvrier_claude.lancer(COMPLETER % {"vid": vid, "n": n, "manque": 10 - n, "periode": v["periode"]}, c.ICI,
                          ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python3 sv.py:*)"] + APIFY,
                          delai=1800, modele=config()["modele_recherche"], autres_dossiers=[SKILL])
    v = c.veille(vid)
    if v.get("statut") == "completer":  # rien ajouté
        apify = v.get("etape") == "APIFY_A_SEC"
        c.maj_veille(vid, statut="fini", etape="", manque=("Apify est à sec ce mois-ci." if apify else v.get("manque") or
                     "Rien de plus à la même barre sur ta cible dans cette période."))


def traduire(vid):
    ok, sortie = ouvrier_claude.lancer(TRADUCTION % {"vid": vid}, c.ICI, ["Read", "Write", "Edit", "Bash(python3 sv.py:*)"],
                                       delai=1200, modele=config()["modele_traduction"])
    return ok


TRANSPOSITION = """Tu es Claude, DANS l'appli SuperVeille de l’utilisateur (dossier actuel). l’utilisateur a collé le lien d'un reel et cliqué « Transposer » :
c'est son OK, pas de question. Tu ne publies rien, tu n'envoies rien. Jamais le mot « voler » : « reprendre ».
But : reprendre le FORMAT de la vidéo de référence (sa structure, son rythme, sa longueur), pas son sujet, et écrire le script de l’utilisateur
dans SA niche.
1. `python3 sv.py a-transposer %(vid)s` : la transcription de chaque référence + le sujet demandé par l’utilisateur (vide = tu choisis).
2. Lis ~/Documents/SuperApps/superveille/ma-marque.md : sa cible, ses sujets, sa voix, son appel à l'action.
   Fichier vide : prends une cible large, un ton simple, et commence ta réponse par « Remplis ma-marque.md ».
3. Pour CHAQUE référence :
   - "format" : le nom du format en une ligne (Podcast, Selfie, Green screen, Liste…), + face caméra / voix off.
   - "plan" : la structure de la référence en 3 à 7 étapes courtes, génériques (« Hook choc », « Erreur n°1 + exemple », « CTA »).
   - Le sujet : celui de l’utilisateur s'il en a donné un, sinon le problème n°1 de sa cible.
   - "hook" + "script" : le script de l’utilisateur, MÊME plan étape par étape, même rythme, longueur à ±30 %% de la référence. "hook" = la
     1re phrase, mot à mot. "script" = la suite, d'un seul bloc prêt à dire (sans le hook). Tutoiement, sa voix, phrases courtes,
     zéro ton IA, aucun tiret cadratin. Rien d'inventé : un chiffre ou un résultat client qu'on n'a pas = [à remplir].
     La référence finit par un appel à l'action : celui de l'utilisateur, lié au sujet.
   - Référence marquée « AUCUNE VOIX » (bureau + texte) : ouvre l'image indiquée avec Read et ajoute "ecran" = le texte à l'écran de
     la référence, mot pour mot, une ligne par texte, dans l'ordre. Alors "format" dit « bureau + texte, sans voix », "hook" = le 1er
     texte à l'écran de l’utilisateur, "script" = ses textes suivants, une ligne par écran (retours à la ligne), à peu près autant que la
     référence. Pas d'appel à l'action si la référence n'en a pas.
   Écris veilles/%(vid)s/transpo-<code>.json : {"format": "...", "plan": ["..."], "hook": "...", "script": "..."}
   (+ "ecran": ["..."] pour une référence sans voix)
   puis `python3 sv.py transposition %(vid)s <code> veilles/%(vid)s/transpo-<code>.json`. S'il refuse, corrige et recommence.
Réponds en 1 ligne quand c'est posé."""


def transposer(vid):
    ok, sortie = ouvrier_claude.lancer(TRANSPOSITION % {"vid": vid}, c.ICI, ["Read", "Write", "Edit", "Bash(python3 sv.py:*)"],
                                       delai=1500, modele=config()["modele_transposition"])
    return ok


def ouvrier():
    """Fait travailler Claude dès que l'écran attend quelque chose : plus besoin d'un chat ouvert."""
    while True:
        try:
            if config()["claude_auto"]:
                for vid in c.toutes_veilles():
                    v = c.veille(vid)
                    if v.get("statut") == "recherche" and not v.get("reels"):
                        ESSAIS[(vid, "recherche")] = ESSAIS.get((vid, "recherche"), 0) + 1
                        if ESSAIS[(vid, "recherche")] > 1:
                            continue
                        c.maj_veille(vid, etape="Claude lit ta cible et choisit les mots-clés…")
                        recherche(vid)
                        break
                    if v.get("statut") == "completer":
                        cle = (vid, "completer", v.get("tour"))  # 1 passage de Claude par clic
                        ESSAIS[cle] = ESSAIS.get(cle, 0) + 1
                        if ESSAIS[cle] == 1:
                            completer(vid)
                            break
                    attente = [r for r in v.get("reels", []) if r["statut"] == "transcrit"]
                    for r in attente:  # 3 passages de Claude par reel au plus, sinon la carte le dit
                        ESSAIS[(vid, r["code"])] = ESSAIS.get((vid, r["code"]), 0) + 1
                        if ESSAIS[(vid, r["code"])] > 3:
                            c.maj_reel(vid, r["code"], statut="erreur", erreur="La traduction n'est pas passée.")
                    if any(ESSAIS[(vid, r["code"])] <= 3 for r in attente):
                        (transposer if v.get("source") == "transposes" else traduire)(vid)
                        break
        except Exception:
            traceback.print_exc()
        time.sleep(3)


def a_scanner():
    """Le plus ancien reel où l’utilisateur a cliqué « Scanner ce reel »."""
    attente = [(r["cerveau"].get("demande", 0), vid, r) for vid in c.toutes_veilles() for r in c.veille(vid).get("reels", [])
               if (r.get("cerveau") or {}).get("statut") == "attente"]
    return min(attente, key=lambda x: x[0])[1:] if attente else (None, None)


def scanner():
    """Un reel à la fois : vidéo, morceaux de 15 s, puis Claude fait Higgsfield et la recette (~10 min pour 1 min de vidéo)."""
    while True:
        vid, r = a_scanner()
        if not vid:
            time.sleep(3)
            continue
        code = r["code"]
        try:
            cerveau.maj(vid, code, statut="prepare", erreur="")
            d = cerveau.dossier(vid, code)
            if not c.lire(os.path.join(d, "parts.json"), {}).get("parts"):
                video = telecharger(vid, code)
                cerveau.sp.decoupe(video, d)
                os.remove(video)  # on ne garde que les morceaux, jetés à la fin du scan
            parts = c.lire(os.path.join(d, "parts.json"), {})["parts"]
            faits = len([f for f in os.listdir(d) if f.startswith("rapport-")])
            cerveau.maj(vid, code, statut="scan", total=len(parts), faits=faits)
            ok, sortie = ouvrier_claude.lancer(SCAN % {"vid": vid, "code": code}, c.ICI, ["Read", "Write", "Bash(python3 sv.py:*)"] + HIGGS,
                                               delai=2700, modele=config()["modele_cerveau"])
            fin = (cerveau.reel(vid, code).get("cerveau") or {})
            if fin.get("statut") not in ("fini", "erreur"):
                cerveau.maj(vid, code, statut="erreur", erreur="Le scan ne s'est pas fini. Réessaie." if ok else sortie[-160:])
        except Exception as e:
            traceback.print_exc()
            cerveau.maj(vid, code, statut="erreur", erreur=f"Vidéo illisible : {str(e)[:150]}")


# ---------------------------------------------------------------- atelier : couverture, vidéo, transcription

MODELE = {}


def whisper():
    if "m" not in MODELE:
        from faster_whisper import WhisperModel
        MODELE["m"] = WhisperModel("small", compute_type="int8")
    return MODELE["m"]


def liberer_whisper():
    if MODELE.pop("m", None) is not None:
        gc.collect()  # Mac 8 Go : on rend la mémoire entre deux veilles


def couverture(vid, r):
    dest = c.chemin(vid, "mini", r["code"] + ".jpg")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        return True
    ref = r.get("ref", r["code"])  # transposé : « code » porte -t, la vidéo Instagram est « ref »
    deja = os.path.join(c.ENREG_MINI, ref + ".jpg")  # reel enregistré : miniature déjà là
    if os.path.exists(deja):
        shutil.copy(deja, dest)
        return True
    for url in (r.get("image"), c.url_couverture(ref)):
        if url and c.telecharger_couverture(url, dest):
            return True
    return False


def telecharger(vid, code, ref=None, infos=None):
    """La vidéo du reel. infos (dict) : rempli avec créateur, likes, date lus par yt-dlp (reel transposé, collé à la main)."""
    d = c.chemin(vid, "_video")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, code + ".%(ext)s")
    cmd = [c.YTDLP, "-q", "--no-playlist", "-f", "mp4/best", "-o", out, f"https://www.instagram.com/reel/{ref or code}/"]
    if infos is not None:
        cmd[1:1] = ["--print-json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode:  # Instagram refuse sans connexion : on réessaie avec la session de Chrome (lecture seule)
        r = subprocess.run(cmd[:1] + ["--cookies-from-browser", "chrome"] + cmd[1:], capture_output=True, text=True, timeout=300)
    vids = [f for f in os.listdir(d) if f.startswith(code + ".")]
    if r.returncode or not vids:
        raise RuntimeError((r.stderr or r.stdout or "vidéo illisible").strip().splitlines()[-1][:200])
    if infos is not None:
        try:
            j = json.loads(r.stdout.strip().splitlines()[-1])
            infos.update(createur=j.get("channel") or j.get("uploader_id") or "", likes=j.get("like_count") or 0,
                         vues=j.get("view_count") or 0, date="-".join((j.get("upload_date") or "")[i:i + n] for i, n in ((0, 4), (4, 2), (6, 2))).strip("-"))
        except (ValueError, IndexError):
            pass
        if not infos.get("vues"):  # yt-dlp ne donne jamais les vues d'un reel Insta : on les lit sur Instagram (session Chrome)
            try:
                import insta
                m = insta.reel(ref or code)
                if m:
                    infos.update({k: m[k] for k in ("createur", "likes", "vues", "date") if m.get(k) and not infos.get(k)}, vues=m["vues"])
            except Exception:
                pass
    return os.path.join(d, vids[0])


def phrases_fr(segments):
    """Reel déjà en français : l'original EST le script. Découpe en phrases, sans Claude."""
    texte = " ".join(s["texte"] for s in segments)
    morceaux = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", texte) if p.strip()]
    return [{"o": p, "f": p} for p in morceaux]


ENV_FF = dict(os.environ, PATH=os.environ.get("PATH", "") + ":" + os.path.expanduser("~/.local/bin"))
LANGUES = {"en": "anglais", "es": "espagnol", "fr": "français", "hi": "hindi", "pt": "portugais", "it": "italien", "de": "allemand"}


def a_ecarter(v, r):
    """Raison d'écarter un reel une fois transcrit (None = il reste). Une légende anglaise ne dit pas la langue parlée :
    vu le 28/10, @spotlitesensei écrit en anglais et parle hindi ; @brunogeracosta n'a que du texte à l'écran."""
    t = r.get("transcription") or {}
    mots = sum(len(s["texte"].split()) for s in t.get("segments", []))
    if mots < 15 and v.get("source") != "transposes":  # transposé sans voix : Claude lit le texte à l'écran (28/10 nuit)
        return "Pas de voix (texte à l'écran ou musique) : rien à reprendre mot pour mot."
    if v.get("source") not in ("enregistres", "transposes") and t.get("langue") not in v["marches"]:  # choisi par l’utilisateur : toute langue
        return f"Parle {LANGUES.get(t.get('langue'), t.get('langue'))}, pas la langue d'un marché coché."
    return None


def preparer_reel(vid, r, i, n):
    c.maj_veille(vid, etape=f"Je transcris le reel {i} sur {n}…")
    infos = {} if not r.get("createur") or not r.get("vues") else None  # lien collé (transposé OU traduit) : créateur, likes, vues lus en même temps
    video = telecharger(vid, r["code"], r.get("ref"), infos)
    if infos:
        c.maj_reel(vid, r["code"], **{k: x for k, x in infos.items() if x})
    mini = c.chemin(vid, "mini", r["code"] + ".jpg")
    if not os.path.exists(mini):  # pas de couverture Instagram : une image de la vidéo
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", video, "-frames:v", "1", "-vf", "scale=540:-2", mini],
                       timeout=60, env=ENV_FF)
        c.maj_reel(vid, r["code"], miniature=os.path.exists(mini))
    segs, info = whisper().transcribe(video, beam_size=5, vad_filter=True)
    segments = [{"debut": round(s.start, 1), "fin": round(s.end, 1), "texte": s.text.strip()} for s in segs if s.text.strip()]
    sans_voix = r.get("transpose") and sum(len(s["texte"].split()) for s in segments) < 15
    if sans_voix:  # 28/10 nuit (l’utilisateur) : bureau + texte, sans voix → 12 images de la vidéo, Claude y lit le texte à l'écran
        planche = c.chemin(vid, "_ecran", r["code"] + ".jpg")
        os.makedirs(os.path.dirname(planche), exist_ok=True)
        duree = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                     capture_output=True, text=True, env=ENV_FF).stdout.strip() or 12)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vf", f"fps={12 / max(duree, 1):.4f},scale=360:-2,tile=4x3",
                        "-frames:v", "1", planche], timeout=120, env=ENV_FF)
        segments = []
    os.remove(video)  # disque du Mac : on ne garde que le texte et la miniature
    trans = {"langue": "texte à l'écran" if sans_voix else info.language, "segments": segments}
    raison = a_ecarter(c.veille(vid), dict(r, transcription=trans))
    if sans_voix:
        c.maj_reel(vid, r["code"], transcription=trans, statut="transcrit", sans_voix=True, marche="")
    elif raison:
        c.maj_reel(vid, r["code"], transcription=trans, statut="ecarte", raison=raison)
    elif info.language == "fr" and not r.get("transpose"):  # transposé : même en français, Claude réécrit dans sa niche
        ph = phrases_fr(segments)
        c.maj_reel(vid, r["code"], transcription=trans, statut="pret", phrases=ph, hook=ph[0]["f"], marche="fr")
    else:
        c.maj_reel(vid, r["code"], transcription=trans, statut="transcrit", marche=info.language)


def atelier():
    while True:
        try:
            vid = en_cours()
            v = c.veille(vid) if vid else {}
            reels = v.get("reels", [])
            if v.get("statut") == "transcription":
                # 1. toutes les couvertures d'abord : les cartes arrivent une par une en quelques secondes
                for r in reels:
                    if r["statut"] == "attente":
                        c.maj_reel(vid, r["code"], statut="miniature", miniature=couverture(vid, r))
                # 2. puis chaque vidéo, une à la fois (Mac 8 Go)
                comptent = [r for r in c.veille(vid)["reels"] if r["statut"] != "ecarte"]
                for i, r in enumerate(comptent, 1):  # « reel 6 sur 6 » : les écartés ne comptent pas
                    if r["statut"] == "miniature":
                        try:
                            preparer_reel(vid, r, i, len(comptent))
                        except Exception as e:
                            traceback.print_exc()
                            c.maj_reel(vid, r["code"], statut="erreur", erreur=f"Vidéo illisible : {str(e)[:150]}")
                liberer_whisper()
                v = c.veille(vid)
                for r in v["reels"]:  # veilles d'avant la règle : on écarte aussi
                    raison = r["statut"] in ("pret", "transcrit") and r.get("transcription") and a_ecarter(v, r)
                    if raison:
                        c.maj_reel(vid, r["code"], statut="ecarte", raison=raison)
                v = c.veille(vid)
                if all(r["statut"] in ("pret", "erreur", "ecarte") for r in v["reels"]):
                    p = c.ecrire_brain(vid)
                    c.maj_veille(vid, statut="fini", fin=time.time(), etape="", brain=p)
                elif not any(r["statut"] in ("attente", "miniature") for r in v["reels"]):
                    c.maj_veille(vid, etape="J'écris ton script dans ta niche…" if v.get("source") == "transposes"
                                 else "Je traduis les scripts en français…")
        except Exception:
            traceback.print_exc()
        time.sleep(2)


def reprise():
    """Serveur relancé en pleine veille : on reprend où on en était (rien ne se perd)."""
    for vid in c.toutes_veilles():
        v = c.veille(vid)
        if v.get("statut") == "recherche" and not v.get("reels"):
            c.maj_veille(vid, statut="erreur", etape="Recherche coupée (appli relancée).", detail="Relance la veille.")
        if v.get("statut") == "completer":
            c.maj_veille(vid, statut="fini", etape="")
        if v.get("statut") == "cherche":  # Recherche rapide coupée : on garde les cartes déjà posées
            c.maj_veille(vid, statut="fini" if v.get("trouves") else "erreur", etape="",
                         erreur="" if v.get("trouves") else "Recherche coupée (appli relancée). Relance-la.")
        ecartes = [r for r in v.get("reels", []) if r["statut"] in ("pret", "transcrit") and r.get("transcription") and a_ecarter(v, r)]
        for r in ecartes:  # règle du 28/10 (pas de voix, mauvaise langue) appliquée aux veilles d'avant
            c.maj_reel(vid, r["code"], statut="ecarte", raison=a_ecarter(v, r))
        if ecartes and c.veille(vid).get("statut") == "fini":
            c.ecrire_brain(vid)
        for r in v.get("reels", []):
            if r["statut"] == "miniature" and not r.get("transcription"):
                pass  # l'atelier la reprend tout seul
            if (r.get("cerveau") or {}).get("statut") in ("prepare", "scan", "calcul"):
                cerveau.maj(vid, r["code"], statut="erreur", erreur="Scan coupé (appli relancée). Réessaie : il reprend où il en était.")


# ---------------------------------------------------------------- vues

def gardes(v):
    """Les reels qui comptent (sans les écartés), numérotés dans l'ordre d'affichage."""
    return [dict(r, n=i) for i, r in enumerate((r for r in v.get("reels", []) if r["statut"] != "ecarte"), 1)]


def vue_reel(vid, r):
    t = c.lire(c.TOURNAGE, {}).get(r["code"], {})
    out = {k: r.get(k) for k in ("n", "code", "lien", "marche", "createur", "likes", "vues", "date", "format", "hook", "phrases",
                                  "statut", "erreur", "muet")}
    out["veille"] = vid
    out["langue"] = (r.get("transcription") or {}).get("langue")
    out["miniature"] = f"/v/{vid}/mini/{r['code']}.jpg" if r.get("miniature") else None
    out["tournage"] = t.get("statut")
    out["tourne_le"] = t.get("tourne_le")
    out["cerveau"] = r.get("cerveau")
    for k in ("transpose", "plan", "script", "format_repris", "sujet", "texte"):  # reel transposé (lien collé) ; texte = son script retouché
        out[k] = r.get(k)
    return out


def vue_veille(vid):
    v = c.veille(vid)
    out = {k: v.get(k) for k in ("id", "pour", "personne", "marches", "periode", "likes_min", "sujet", "statut", "etape", "detail",
                                  "lus", "passent_likes", "gardes", "manque", "debut", "fin", "cree")}
    out["reels"] = [vue_reel(vid, r) for r in gardes(v)]
    out["ecartes"] = [{"createur": r["createur"], "raison": r.get("raison", "")} for r in v.get("reels", []) if r["statut"] == "ecarte"]
    out["prets"] = sum(1 for r in v.get("reels", []) if r["statut"] == "pret")
    return out


def vue_tournage():
    """Tourné (28/10 : « À tourner » = tous les traduits, voir vue_traduits ; supprimé = caché partout)."""
    t = c.lire(c.TOURNAGE, {})
    out = {"tourne": []}
    for code, x in sorted(t.items(), key=lambda kv: kv[1].get("tourne_le") or kv[1].get("quand", ""), reverse=True):
        v = c.veille(x["veille"])
        r = next((r for r in v.get("reels", []) if r["code"] == code), None)
        if r and r["statut"] != "ecarte" and x["statut"] == "tourne":
            out["tourne"].append(vue_reel(x["veille"], r))
    return out


def accueil():
    vids = c.toutes_veilles()
    gens = c.personnes()
    return {"personnes": [c.reglages(p["fichier"]) for p in gens], "marches": c.MARCHES, "noms_marches": c.NOMS_MARCHES,
            "periodes": c.PERIODES, "likes": c.LIKES, "veilles": [{"id": x, "personne": c.veille(x).get("personne"),
            "statut": c.veille(x).get("statut"), "cree": c.veille(x).get("cree"), "n": len(gardes(c.veille(x)))} for x in vids[:12]],
            "derniere": vids[0] if vids else None, "en_cours": en_cours()}


def lancer(d):
    p = c.reglages(d.get("pour", ""))
    if not p:
        return None, "Personne inconnue : ajoute sa ligne dans Brain/07-Clients/veille-reglages.md."
    marches = [m for m in c.MARCHES if m in (d.get("marches") or p["marches"])]
    periode = int(d.get("periode") or p["periode"])
    likes = int(d.get("likes_min") or p["likes_min"])
    if not marches:
        return None, "Coche au moins un marché."
    if periode not in c.PERIODES:
        return None, "Période : 15, 45 ou 90 jours."
    if likes < 10000:
        return None, "Jamais moins de 10 000 likes."
    if en_cours():
        return None, "Une veille tourne déjà : attends qu'elle finisse."
    c.garder_reglages(p["fichier"], marches, periode, likes)
    vid = time.strftime("%Y-%m-%d-%H%M%S-") + p["fichier"]
    c.maj_veille(vid, id=vid, pour=p["fichier"], personne=p["court"], cible=p["cible"], marches=marches, periode=periode,
                 likes_min=likes, sujet=(d.get("sujet") or "").strip()[:120], statut="recherche", etape="Je prépare la recherche…",
                 reels=[], debut=time.time(), cree=time.strftime("%Y-%m-%d %H:%M"))
    return vid, ""


def tournage(code, vid, statut):
    with c.verrou(c.TOURNAGE):
        t = c.lire(c.TOURNAGE, {})
        if statut is None:
            t.pop(code, None)
        else:
            x = t.get(code, {"veille": vid, "quand": time.strftime("%Y-%m-%d %H:%M")})
            x["statut"] = statut
            if statut == "tourne":
                x["tourne_le"] = time.strftime("%Y-%m-%d %H:%M")
            t[code] = x
        c.ecrire(c.TOURNAGE, t)


# ---------------------------------------------------------------- Tournage du jour (29/10, l’utilisateur) : les 25 formats, des idées sous chacun

FORMATS = ["Podcast", "Selfie", "Green screen", "Split screen", "Démonstration", "Conférence", "Questions-réponses", "Fiction",
           "Face caméra", "Débat", "Tier list", "Mauvais, bien, excellent", "Clone", "Liste", "Comparaison en T", "Motion design",
           "Vlog", "Objets", "Tableau blanc", "B-roll + texte", "Voix off", "Mèmes", "Carrousels", "Visio (Zoom)", "Réaction"]


def vue_jour():
    """Les 25 formats dans l'ordre, chacun avec ses idées : un script de « À tourner » (fiche complète) ou une phrase."""
    j = c.lire(c.JOUR, {})
    out = []
    for n, nom in enumerate(FORMATS, 1):
        idees = []
        for x in j.get(str(n), []):
            if x.get("code"):
                r = next((r for r in c.veille(x["veille"]).get("reels", []) if r["code"] == x["code"]), None)
                if r:
                    idees.append(dict(vue_reel(x["veille"], r), id=x["id"]))
            else:
                idees.append({"id": x["id"], "texte": x.get("texte", "")})
        out.append({"n": n, "nom": nom, "idees": idees})
    return {"formats": out}


def jour(d):
    """Ajouter une idée (code + veille d'un script, ou texte) sous un format, ou la retirer. Renvoie un message d'erreur ou ""."""
    n = str(d.get("format", ""))
    if not n.isdigit() or not 1 <= int(n) <= len(FORMATS):
        return "Format inconnu."
    with c.verrou(c.JOUR):
        j = c.lire(c.JOUR, {})
        L = j.setdefault(n, [])
        if d.get("action") == "retirer":
            j[n] = [x for x in L if x["id"] != d.get("id")]
        else:
            code, vid, texte = str(d.get("code", "")), str(d.get("veille", "")), str(d.get("texte", "")).strip()[:300]
            if code:
                if not any(r["code"] == code for r in c.veille(vid).get("reels", [])):
                    return "Script introuvable."
                if any(x.get("code") == code for x in L):
                    return "Déjà dans ce format."
                L.append({"id": uuid.uuid4().hex[:8], "code": code, "veille": vid, "quand": time.strftime("%Y-%m-%d %H:%M")})
            elif texte:
                L.append({"id": uuid.uuid4().hex[:8], "texte": texte, "quand": time.strftime("%Y-%m-%d %H:%M")})
            else:
                return "Écris une idée ou choisis un script."
        c.ecrire(c.JOUR, j)
    return ""


# ---------------------------------------------------------------- enregistrés Instagram (28/10 : l’utilisateur fait la veille lui-même)

LECTURE = {"en_cours": False, "erreur": "", "debut": 0}


MAX_ENREG = 100  # 28/10 (l’utilisateur) : ses 2 comptes mélangés, les 100 derniers enregistrés


def enregistres():
    """Les reels enregistrés de ses comptes MÉLANGÉS (1er de chaque compte, puis 2e de chaque…, chaque liste va du dernier
    enregistré au plus ancien), sans doublons ni retirés, 100 au plus. Renvoie (reels, nb retirés)."""
    e = c.lire(c.ENREG, {})
    retires, vus, out = set(e.get("retires", [])), set(), []
    listes = [x.get("items", []) for x in sorted(e.get("comptes", {}).values(), key=lambda x: -x.get("lu", 0))]
    for rang in range(max(map(len, listes), default=0)):
        for items in listes:
            x = items[rang] if rang < len(items) else None
            if x and x["code"] not in vus and x["code"] not in retires:
                vus.add(x["code"])
                out.append(x)
    return out[:MAX_ENREG], len(retires)


def lire_enregistres():
    try:
        import insta
        avant = c.lire(c.ENREG, {}).get("comptes", {})
        deja = {k: {x["code"] for x in v["items"]} for k, v in avant.items() if v.get("complet")}  # lus en entier : les nouveaux seulement
        lus = insta.lire(deja)
        with c.verrou(c.ENREG):
            e = c.lire(c.ENREG, {})
            for compte, (items, complet) in lus.items():  # un compte pas lu cette fois (autre profil fermé) garde sa liste
                vieux = e.setdefault("comptes", {}).get(compte, {})
                codes = {x["code"] for x in items}
                e["comptes"][compte] = {"lu": time.time(), "complet": complet or vieux.get("complet", False),
                                        "items": items + [x for x in vieux.get("items", []) if x["code"] not in codes]}
            c.ecrire(c.ENREG, e)
        LECTURE["en_cours"] = False  # la grille s'affiche, les miniatures arrivent derrière
        os.makedirs(c.ENREG_MINI, exist_ok=True)
        for x in enregistres()[0]:
            dest = os.path.join(c.ENREG_MINI, x["code"] + ".jpg")
            if not os.path.exists(dest) and x.get("image"):
                c.telecharger_couverture(x["image"], dest)
    except Exception as ex:
        traceback.print_exc()
        LECTURE["erreur"] = str(ex) if type(ex).__name__ == "Erreur" else f"Lecture impossible ({str(ex)[:120]})."
    finally:
        LECTURE["en_cours"] = False


def actualiser(force):
    """À l'ouverture : une lecture toutes les 5 min au plus. Bouton Actualiser : tout de suite (30 s entre deux clics)."""
    lu = max([x.get("lu", 0) for x in c.lire(c.ENREG, {}).get("comptes", {}).values()] or [0])
    if LECTURE["en_cours"] or time.time() - LECTURE["debut"] < 30 or (not force and time.time() - lu < 300):
        return
    LECTURE.update(en_cours=True, erreur="", debut=time.time())
    threading.Thread(target=lire_enregistres, daemon=True).start()


def retirer(code, statut):
    """Retirer = la vidéo sort de la grille (elle reste enregistrée sur Instagram). statut None = tout remettre."""
    with c.verrou(c.ENREG):
        e = c.lire(c.ENREG, {})
        r = set(e.get("retires", []))
        if statut is None:
            r = set()
        elif statut:
            r.add(code)
        else:
            r.discard(code)
        e["retires"] = sorted(r)
        c.ecrire(c.ENREG, e)


def etats():
    """code -> (veille, reel) pour chaque reel déjà pris (la veille la plus récente gagne)."""
    out = {}
    for vid in c.toutes_veilles():
        for r in c.veille(vid).get("reels", []):
            if not r.get("transpose"):  # un transposé n'est pas sa traduction
                out.setdefault(r["code"], (vid, r))
    return out


ETAT = {"pret": "traduit", "ecarte": "ecarte", "erreur": "erreur"}  # sinon : en_cours


def transposes():
    """Codes Instagram déjà transposés (prêts ou en cours) : badge « Transposé » sur la carte, pour ne pas le refaire."""
    return {r.get("ref") or r["code"][:-2] for vid in c.toutes_veilles() for r in c.veille(vid).get("reels", [])
            if r.get("transpose") and r.get("statut") not in ("erreur", "ecarte")}


def vue_enregistres():
    items, retires = enregistres()
    et = etats()
    tp = transposes()
    out = []
    for x in items:
        vid, r = et.get(x["code"], (None, None))
        mini = os.path.exists(os.path.join(c.ENREG_MINI, x["code"] + ".jpg"))
        out.append(dict({k: x.get(k) for k in ("code", "lien", "createur", "likes", "vues", "date", "duree", "legende")},
                        miniature=f"/e/{x['code']}.jpg" if mini else x.get("image"), veille=vid, transpose=x["code"] in tp,
                        etat=ETAT.get(r["statut"], "en_cours") if r else None, raison=(r or {}).get("raison") or (r or {}).get("erreur")))
    lu = max([x.get("lu", 0) for x in c.lire(c.ENREG, {}).get("comptes", {}).values()] or [0])
    return {"items": out, "retires": retires, "lu": lu, "lecture": LECTURE["en_cours"], "erreur": LECTURE["erreur"]}


def traduire_selection(codes, hors_enregistres=None):
    """Les reels cochés partent dans la veille du jour « enregistres » : miniature, transcription, traduction (comme avant)."""
    items = {x["code"]: x for x in enregistres()[0]}
    items.update(hors_enregistres or {})
    et = etats()
    pris = ("pret", "attente", "miniature", "transcrit")
    codes = [k for k in dict.fromkeys(codes or []) if k in items and (et[k][1]["statut"] not in pris if k in et else True)]
    if not codes:
        return None, "Rien de nouveau à traduire."
    if len(codes) > 30:
        return None, "30 vidéos maximum à la fois."
    vid = time.strftime("%Y-%m-%d-enregistres")
    if en_cours() not in (None, vid):
        return None, "Une veille tourne déjà : attends qu'elle finisse."

    def ajouter(v):
        v["reels"] = [r for r in v.get("reels", []) if r["code"] not in codes]  # une erreur d'avant : on reprend
        for k in codes:
            x = items[k]
            ESSAIS.pop((vid, k), None)
            v["reels"].append({"code": k, "lien": x["lien"], "marche": "", "createur": x["createur"], "likes": x["likes"],
                               "vues": x["vues"], "date": x["date"], "format": "", "legende": x["legende"],
                               "image": x.get("image"), "statut": "attente"})
    neuve = {} if c.veille(vid) else {"debut": time.time(), "cree": time.strftime("%Y-%m-%d %H:%M")}
    c.maj_veille(vid, ajouter, id=vid, source="enregistres", pour="moi", personne="Moi", marches=[],
                 statut="transcription", etape="Je prépare les miniatures…", **neuve)
    return vid, ""


def deja_vu(ref):
    """Ce qu'on sait déjà d'un reel (créateur, likes, vues, date, image) : ses enregistrés, sinon une carte de la Recherche.
    28/10 soir : envoyé depuis la Recherche, il arrivait dans À tourner en « @ » et « ♥ 0 »."""
    x = next((i for i in enregistres()[0] if i["code"] == ref), None)
    if x:
        return x
    for vid in c.toutes_veilles():
        if vid.endswith("-recherche"):
            t = next((t for t in c.veille(vid).get("trouves", []) if t["code"] == ref), None)
            if t:
                return t
    return {}


def traduire_lien(lien):
    """Lien collé en haut, bouton « Traduire » : traduit mot pour mot comme un enregistré, même s'il n'est pas enregistré
    (créateur et likes lus ensuite sur la vidéo par yt-dlp)."""
    mo = re.search(r"instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/([\w-]+)", lien or "")
    if not mo:
        return None, "Colle le lien d'un reel Instagram (instagram.com/reel/…)."
    ref = mo.group(1)
    vu = deja_vu(ref)
    x = {"code": ref, "lien": f"https://www.instagram.com/reel/{ref}/", "createur": vu.get("createur", ""), "likes": vu.get("likes", 0),
         "vues": vu.get("vues", 0), "date": vu.get("date", ""), "legende": vu.get("legende", ""), "image": vu.get("image")}
    vid, err = traduire_selection([ref], {ref: x} if ref not in {i["code"] for i in enregistres()[0]} else None)
    if vid:
        tournage(ref, vid, None)  # recollé après « Supprimer » : il revient
    return vid, err


def transposer_lien(lien, sujet):
    """Lien collé en haut : le reel part dans la veille du jour « transposes » (miniature, transcription, puis Claude écrit
    le script de l’utilisateur au même format). Son code porte -t : il peut aussi être traduit mot pour mot à côté."""
    mo = re.search(r"instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/([\w-]+)", lien or "")
    if not mo:
        return None, "Colle le lien d'un reel Instagram (instagram.com/reel/…)."
    ref = mo.group(1)
    vid = time.strftime("%Y-%m-%d-transposes")
    code = ref + "-t"
    x = deja_vu(ref)  # déjà dans ses enregistrés ou la Recherche : créateur et likes connus
    sujet = (sujet or "").strip()[:160]

    def ajouter(v):
        v["reels"] = [r for r in v.get("reels", []) if r["code"] != code]  # recollé : on refait (nouveau sujet possible)
        ESSAIS.pop((vid, code), None)
        v["reels"].append({"code": code, "ref": ref, "transpose": True, "sujet": sujet, "lien": f"https://www.instagram.com/reel/{ref}/",
                           "marche": "", "createur": x.get("createur", ""), "likes": x.get("likes", 0), "vues": x.get("vues", 0),
                           "date": x.get("date", ""), "format": "", "legende": x.get("legende", ""), "image": x.get("image"),
                           "statut": "attente"})
    neuve = {} if c.veille(vid) else {"debut": time.time(), "cree": time.strftime("%Y-%m-%d %H:%M")}
    c.maj_veille(vid, ajouter, id=vid, source="transposes", pour="moi", personne="Moi", marches=[],
                 statut="transcription", etape="Je regarde la vidéo de référence…", **neuve)
    tournage(code, vid, None)  # recollé après « Supprimer » : il revient
    return vid, ""


def vue_traduits():
    """L'onglet « À tourner » (28/10 : remplace « Traduits ») : tous les scripts, les plus récents d'abord, sauf tournés et supprimés."""
    reels = []
    t = c.lire(c.TOURNAGE, {})
    for vid in c.toutes_veilles():
        reels += [vue_reel(vid, r) for r in reversed(gardes(c.veille(vid)))
                  if t.get(r["code"], {}).get("statut") not in ("tourne", "supprime")]
    vid = en_cours()
    scan = any((r.get("cerveau") or {}).get("statut") in ("attente", "prepare", "scan", "calcul") for r in reels)
    return {"reels": reels, "en_cours": vid, "etape": c.veille(vid).get("etape", "") if vid else "", "scan": scan}


def demander_scan(vid, code):
    r = cerveau.reel(vid, code) if c.veille(vid) else None
    if not r or r["statut"] != "pret" or not r.get("phrases"):
        return "Ce reel n'a pas encore son script."
    if (r.get("cerveau") or {}).get("statut") in ("attente", "prepare", "scan", "calcul"):
        return "Le scan tourne déjà."
    cerveau.maj(vid, code, statut="attente", demande=time.time(), erreur="")
    return ""


# ---------------------------------------------------------------- HTTP

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        b = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _fichier(self, p):
        if not os.path.isfile(p):
            return self._json({"erreur": "introuvable"}, 404)
        ct = mimetypes.guess_type(p)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ct + ("; charset=utf-8" if ct.startswith("text/") else ""))
        self.send_header("Content-Length", str(os.path.getsize(p)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(p, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def _corps(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path
        if p == "/":
            return self._fichier(os.path.join(STATIC, "index.html"))
        if p.startswith("/static/"):
            f = os.path.normpath(os.path.join(STATIC, p[8:]))
            return self._fichier(f) if f.startswith(STATIC) else self._json({}, 403)
        if p.startswith("/v/"):
            f = os.path.normpath(os.path.join(c.VEILLES, urllib.parse.unquote(p[3:])))
            return self._fichier(f) if f.startswith(c.VEILLES) and "/mini/" in f else self._json({}, 403)
        mo = re.fullmatch(r"/e/([\w-]+)\.jpg", p)
        if mo:
            return self._fichier(os.path.join(c.ENREG_MINI, mo.group(1) + ".jpg"))
        if p == "/api/enregistres":
            return self._json(vue_enregistres())
        if p == "/api/recherche":
            return self._json(vue_recherche())
        if p == "/api/traduits":
            return self._json(vue_traduits())
        if p == "/api/accueil":
            return self._json(accueil())
        if p == "/api/tournage":
            return self._json(vue_tournage())
        if p == "/api/jour":
            return self._json(vue_jour())
        mo = re.fullmatch(r"/api/veille/([\w-]+)", p)
        if mo and c.veille(mo.group(1)):
            return self._json(vue_veille(mo.group(1)))
        return self._json({"erreur": "introuvable"}, 404)

    def _autre_site(self):
        """Serrure : seule la page SuperVeille elle-même peut envoyer des ordres (pas un autre site ouvert dans le navigateur)."""
        o = self.headers.get("Origin")
        port = self.server.server_address[1]
        if o and o not in ("http://localhost:%d" % port, "http://127.0.0.1:%d" % port):
            self._json({"erreur": "refusé"}, 403)
            return True
        return False

    def do_POST(self):
        if self._autre_site():
            return
        p = urllib.parse.urlparse(self.path).path
        d = self._corps()
        if p == "/api/enregistres/actualiser":
            actualiser(bool(d.get("force")))
            return self._json(vue_enregistres())
        if p == "/api/enregistres/retirer":
            retirer(str(d.get("code", "")), d.get("retire"))
            return self._json(vue_enregistres())
        if p == "/api/traduire":
            vid, err = traduire_selection(d.get("codes"))
            return self._json(vue_traduits() if vid else {"erreur": err}, 200 if vid else 400)
        if p == "/api/recherche/retirer":
            retirer_recherche(str(d.get("code", "")))
            return self._json(vue_recherche())
        if p == "/api/recherche":
            vid, err = lancer_rapide(d)
            return self._json(vue_recherche() if vid else {"erreur": err}, 200 if vid else 400)
        if p == "/api/traduire-lien":
            vid, err = traduire_lien(str(d.get("lien", "")))
            return self._json(vue_traduits() if vid else {"erreur": err}, 200 if vid else 400)
        if p == "/api/transposer":
            vid, err = transposer_lien(str(d.get("lien", "")), str(d.get("sujet", "")))
            return self._json(vue_traduits() if vid else {"erreur": err}, 200 if vid else 400)
        if p == "/api/cerveau":
            err = demander_scan(str(d.get("veille", "")), str(d.get("code", "")))
            return self._json(vue_traduits() if not err else {"erreur": err}, 400 if err else 200)
        if p == "/api/lancer":
            vid, err = lancer(d)
            return self._json({"id": vid} if vid else {"erreur": err}, 200 if vid else 400)
        mo = re.fullmatch(r"/api/veille/([\w-]+)/completer", p)
        if mo:
            vid = mo.group(1)
            v = c.veille(vid)
            if not v or v.get("statut") != "fini" or len(gardes(v)) >= 10:
                return self._json({"erreur": "Rien à compléter."}, 400)
            if en_cours():
                return self._json({"erreur": "Une veille tourne déjà : attends qu'elle finisse."}, 400)
            c.maj_veille(vid, statut="completer", manque="", tour=(v.get("tour") or 0) + 1,
                         etape=f"Je cherche les {10 - len(gardes(v))} qui manquent…")
            return self._json(vue_veille(vid))
        if p == "/api/ouvrir":
            lien = str(d.get("lien", ""))
            if not re.fullmatch(r"https://(www\.)?instagram\.com/[\w./-]+/?", lien):
                return self._json({"erreur": "lien refusé"}, 400)
            subprocess.Popen(["open", "-a", "Google Chrome", lien])  # 29/10 (l’utilisateur) : nouvel onglet, pas nouvelle fenêtre
            return self._json({"ok": True})
        if p == "/api/script":  # 28/10 (l’utilisateur) : le script transposé se retouche dans l'appli, hook compris, d'une traite
            code, vid, texte = str(d.get("code", "")), str(d.get("veille", "")), str(d.get("texte", ""))[:20000]
            if not any(r["code"] == code for r in c.veille(vid).get("reels", [])):
                return self._json({"erreur": "introuvable"}, 404)
            c.maj_veille(vid, lambda v: [r.update(texte=texte) for r in v["reels"] if r["code"] == code])
            return self._json({"ok": True})
        if p == "/api/jour":
            err = jour(d)
            return self._json({"erreur": err} if err else vue_jour(), 400 if err else 200)
        if p == "/api/tournage":
            code, vid, statut = d.get("code", ""), d.get("veille", ""), d.get("statut")
            v = c.veille(vid)
            if not any(r["code"] == code for r in v.get("reels", [])) or statut not in ("a_tourner", "tourne", "supprime", None):
                return self._json({"erreur": "introuvable"}, 404)
            tournage(code, vid, None if statut == "a_tourner" else statut)  # remettre à tourner = sortir de tournage.json
            return self._json(vue_tournage())
        return self._json({"erreur": "introuvable"}, 404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8811
    os.makedirs(c.VEILLES, exist_ok=True)
    reprise()
    threading.Thread(target=ouvrier, daemon=True).start()
    threading.Thread(target=atelier, daemon=True).start()
    threading.Thread(target=scanner, daemon=True).start()
    print(f"SuperVeille : http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
