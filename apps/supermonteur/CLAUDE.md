# SuperMonteur : mode d'emploi pour Claude (28/10/2026)

L'écran de montage de l'utilisateur. Lancer : `bash ~/Documents/SuperApps/supermonteur/lancer.sh` puis `preview_start {name: "supermonteur"}` (le navigateur intégré ne peut pas lancer lui-même un serveur qui lit ~/Documents : macOS bloque). Lien : http://localhost:8801

Ne réécrit pas le moteur : tout passe par le skill `~/.claude/skills/supermonteur/` (transcribe, derush, build.mjs, monte.sh, Gardien).

## Le parcours
1. **Écran 0 « Quel style pour ce reel ? »** : l'utilisateur glisse sa vidéo (ou Claude ouvre `POST /api/nouveau {"rush": "<chemin>"}`). `monter.py regarder` transcrit, lance `devine_format.py` et entoure le style conseillé. Il coche ses cases, « Monter le reel ».
2. **Montage v1 automatique** (`monter.py monter`) : dernière prise gardée (phrase reprise = l'ancienne saute), dérush, titre = 1re phrase, musique de REELS INSTA (jamais utilisée d'abord, temps fort par `attaque.py`), DA de SuperDA (`apps/superda/da.json` traduite par `da.py`), puis `monte.sh` (Gardien avant + après rendu). Un seul rendu à la fois sur le Mac.
   La v1 auto est une base : mots forts, cartons, animations, fixes de transcription = Claude, au 1er tour de retours.
3. **Écran 1 « Tes retours »** : chaque retour s'accroche à l'image (`reels/<id>/retours.json`). « Suivant : corrige mes retours » écrit `reels/<id>/demande.json` et la boîte `a-corriger.json`.
4. **Écran 3 « Publier »** : Metricool lu dans `metricool.json`. Pas branché = un seul bouton Télécharger (zip : vidéo + `legendes.txt`, 5 réseaux). Branché + `config.json` `"mode_essai": false` = **vraie publication** (par défaut `true` : rien ne part) : 1er clic arme le bouton, 2e clic dans les 6 s = son OK pour CE reel ; `../publier.py` prépare la vidéo + la planche de cover, puis Claude (connecteurs Metricool + Higgsfield seulement) suit le skill publieur et écrit `reels/<id>/publication.json` (statut programme / partiel / erreur, liens planner) + 1 ligne au registre de publication (`registre` des réglages du Publieur). Reel déjà au registre = « Republier quand même ». Aucun nouvel essai automatique.

## Claude tout seul (28/10/2026)
Le serveur lance lui-même Claude Code (`../ouvrier_claude.py`, Opus) dès qu'un reel arrive dans `a-corriger.json` : il suit la section ci-dessous, sans chat ouvert. Outils limités : lire / écrire, `python3 monter.py remonter`, `ffmpeg -ss` (pas le dérush du skill ni son feedback.md : ses lignes vont dans `feedback-retours.md`, à recopier dans le skill). 2 essais max par version, sinon le reel passe en « bloqué ». Journal : `_claude.log`.

## Quand l'utilisateur dit « corrige mes retours » (ou qu'`a-corriger.json` n'est pas vide)
1. Lire `a-corriger.json` -> pour chaque reel : `dossier`, `version`, `retours` (`t` = seconde dans la version affichée, `texte`).
2. Regarder l'image au temps du retour (`ffmpeg -ss <t> -i <dossier>/final.mp4 -frames:v 1`) et corriger **plan.json** du dossier (règles du skill : `SKILL.md`, `feedback.md`, fichier du style). Retour sur le dérush = `drop.json` puis `derush.py` comme dans le skill.
3. `python3 ~/Documents/SuperApps/supermonteur/monter.py remonter <dossier>` -> version N+1 (`versions/vN.mp4`), l'écran se met à jour seul.
4. Dans `retours.json`, pour chaque retour traité : `"statut": "corrige"` + `"reponse"` (1 ligne : ce qui a changé, ex. « raccourci à 1,8 s »). L'écran passe la pastille au vert avec « ▶ Revoir ».
5. Retirer le reel de `a-corriger.json`. Chaque retour = 1 ligne datée dans `feedback.md` du skill (boucle feedback, étape 9).

## Reels montés dans un chat (28/10/2026)
À chaque ouverture de l'accueil, `importer_montages()` (serveur.py) range les dossiers `montages/<date>-<nom>/` qui ont un `final.mp4` dans « Tes reels » : `reels/<id>` = raccourci vers le dossier, `_v1…_vN` puis `final.mp4` = versions 1…N (`versions/vN.mp4`, lien dur), `etat.json` + `retours.json` ajoutés. Les dossiers test / cockpit / essai sont ignorés.

## Légendes
`reels/<id>/legendes.json` = `{"Instagram": "...", "TikTok": "...", "YouTube Shorts": "...", "Facebook": "...", "LinkedIn": "..."}` écrites par Claude (mémoire legende-courte : 1-2 phrases, 0 hashtag). Absent = brouillon tiré du titre, signalé dans le zip.

## Fichiers
`serveur.py` (port 8801) · `monter.py` (regarder / monter / remonter) · `da.py` (SuperDA -> moteur) · `web/` (page) · `reels/<id>/` (etat.json, retours.json, versions/, plan.json, final.mp4) · `preuves/` (captures comparées aux maquettes `livrables/supermonteur-maquettes/final/`) · `capture.sh` (capture 1440 x 900).
