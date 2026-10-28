# SuperCarrousel

L'écran des carrousels (maquettes validées le 26/10/2026, codé la nuit du 28/10/2026).
Lien : http://localhost:8797 · lancer : `bash ~/Documents/SuperApps/supercarrousel/lancer.sh`
puis `preview_start` « supercarrousel » (le navigateur intégré ne peut pas lancer un serveur qui lit ~/Documents).

## Le flux
0. **Départ** : Un reel (vidéo déposée, choisie dans tes montages, ou lien Instagram / TikTok / YouTube) · Un carrousel à reprendre (lien ou captures) · Une idée (écrite ou dictée).
1. **Je fabrique** : le serveur lit le reel tout seul (`reel2frames.py` du skill + transcription), Claude écrit le texte, le serveur rend chaque slide avec le vrai moteur (elles apparaissent une par une).
2. **Tes retours** : une slide en grand, un retour accroché à la slide. « Suivant : corrige mes retours » écrit `projets/<id>/vN/retours-a-corriger.json` ; Claude écrit la version N+1.
3. **Ma DA** : tiroir qui ouvre SuperDA (`?tiroir=carrousels`) ; si SuperDA ne tourne pas, les 7 lignes en lecture + « Demande à Claude ». Une DA changée = carrousel refait avec la nouvelle DA (même texte).
4. **Publier** : 4 réseaux (Instagram, TikTok photos, Facebook, LinkedIn document), jamais YouTube. Metricool pas vérifié = un seul bouton Télécharger (images + 4 légendes, rangé dans Téléchargements). `config.json` `mode_essai: false` : vraie publication, 2 clics (le 2e = OK de l'utilisateur), `../publier.py` + Claude (connecteurs Metricool + Higgsfield), résultat dans `projets/<id>/publication.json`. `mode_essai: true` = Publier ne publie rien.

## Claude tout seul (28/10/2026)
Le serveur lance lui-même Claude Code (`../ouvrier_claude.py`, Opus, outils limités : lire/écrire + `python3 sc.py`) dès que l'écran attend un texte ou des corrections : plus besoin d'un chat ouvert. 2 essais max par version, sinon l'écran passe en « erreur ». Journal : `_claude.log`. `config.json` `"claude_auto": false` = revenir au chat (sc.py attendre).

## Côté Claude (sc.py)
- `python3 sc.py a-faire` : ce que l'écran attend (texte à écrire, retours à corriger, demandes de DA).
- `python3 sc.py attendre` : bloque jusqu'à la prochaine demande (à lancer en arrière-plan).
- `python3 sc.py ecrire <id> <description.json>` : pose la version suivante, le serveur la rend.
- `python3 sc.py metricool oui "<compte>"` : après une vérification en lecture seule (getBrandSettings).
Description = celle du skill carrousel (style Apple) + `name`, `legendes` {instagram, tiktok, facebook, linkedin}, `corrections` [{retour, ligne, slide}].

## La DA
Lue dans `apps/superda/da.json` (contrat `da-schema.json`, clés `commun` + `carrousels`). Sans ce fichier : la DA actuelle du skill (style Apple). Modèles rendus : **Épuré** (moteur Apple du skill) et **Cinéma** (`modeles.py`). Collage, Carnet, Impact, Post texte : rendus en Épuré tant qu'ils ne sont pas codés.

## Fichiers
`serveur.py` (HTTP + boucle de rendu, un rendu à la fois) · `moteur.py` (DA, typo, rendu slide par slide, Télécharger) · `modeles.py` (Cinéma) · `sc.py` (Claude) · `static/` (l'écran) · `projets/<id>/` (demande, versions, retours) · `preuves/` (captures du 28/10).
