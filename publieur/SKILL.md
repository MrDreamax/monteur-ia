---
name: publieur
description: Le Publieur. Programme les reels déjà montés de Cyril ou d'un client sur Instagram, Facebook, YouTube Shorts et TikTok via Metricool - fiche par reel, cover, un seul OK le lundi. Ne publie jamais sans ce OK, jamais sur les comptes perso. Use when "publie", "publication", "programme mes reels", "programme la semaine", "poste mes vidéos", "go semaine", "semaine de publication", "cover de reel", "légende", "Metricool", "publieur", "mets en ligne".
---

# Le Publieur : reels montés → programmés sur 4 réseaux, un seul OK

Chaîne vidéo : veille-reels → scripteur → tournage (Cyril) → supermonteur → **publieur**. Le bouchon de Cyril, c'est publier régulièrement (1 reel publié du 01 au 13/10). Ce skill fait tout, sauf le OK.

**Règle d'or : rien ne part sans le OK explicite de Cyril sur la page de la semaine.** Un OK vaut pour cette semaine-là, pas pour la suivante.

```bash
P=~/.claude/skills/publieur/scripts
```
Durée à annoncer : ~5 min par reel (dont ~1 min Higgsfield), ~30 min pour 7 reels. Coût : ~4 crédits Higgsfield par cover, hébergement 0 crédit.

## 0. Avant tout
1. Lis `config.json` (réglages de cette machine : marque Metricool, comptes, dossiers, disque d'archive, DA). **`"client"` rempli = on est chez un client : lis `mode-client.md` tout de suite**, il passe avant ce fichier. `config.json` absent chez un client = 1er lancement (`mode-client.md`).
2. Lis le carnet (`config.json` → `carnet` : celui de Cyril dans le Brain, `retours-client.md` chez un client). Ses lignes passent AVANT ce fichier. Correction (même en passant) = 1 ligne `JJ/MM/AAAA · correction · problème → règle`, et dis-le en 1 ligne.
3. Metricool : marque `metricool_brand_id`, fuseau `timezone`. Appelle `getBrandSettings` :
   - `instagramData` doit être `instagram_attendu` (le compte pro). Aucun compte de `comptes_interdits` ne doit être branché (chez Cyril : ses comptes perso).
   - Sinon → **on prépare les fiches, on ne programme rien**. Rappelle en 1 ligne l'action Metricool (chez Cyril : `~/Documents/Brain/04-Audits/actions-cyril.md`).
4. Avant d'écrire : les règles de légende (`config.json` → `regles_legendes`) et, chez Cyril, `~/Documents/Brain/00-Moi/voix-contenu.md`.
5. Bilan des passages précédents (à chaque lancement) : voir § 7.

## 1. Quels reels
- Registre : `config.json` → `registre` (chez Cyril `~/Documents/Brain/06-Contenu/publications.md`), 1 ligne par reel. Une vidéo déjà au registre ne repart jamais.
- Candidats : les `final.mp4` des dossiers `montage-*` de `config.json` → `montages` (chez un client : `mode-client.md`) absents du registre, du plus ancien au plus récent. Exclus : `style-lab/`, les dossiers ou fichiers `test`, les comparatifs. Le OK de Cyril sur la semaine vaut validation du montage.
- Nombre : le palier de `hot.md` (7 par semaine au départ, puis 14, 21). Pas assez de reels montés → dis combien manquent en 1 ligne : c'est là que l'argent dort.
- Matière de chaque reel : la transcription du dossier de montage (`words.json` ou `cut.words.json`) et, s'il existe, le script du Scripteur (`~/Documents/Stratosphere/livrables/scripts/`) pour le mot-clé et le CTA. **Rien d'inventé** : la légende ne promet que ce que la vidéo dit.

## 2. La fiche (`fiche.json`)
Dossier : `<config.json → publication>/<AAAA-MM-JJ>-<slug>/` (date de publication prévue).
```json
{"titre": "Tier list des formats Instagram", "video": "/chemin/final.mp4", "duree": 49,
 "date": "2026-10-19T20:00:00", "heure_provisoire": true, "note_heure": "Heure provisoire : ...",
 "plateformes": ["instagram", "facebook", "youtube", "tiktok"],
 "mot_cle": "formats Instagram", "dit_a_voix": true, "sur_cover": false, "cta": "STRAT",
 "cover": {"source": "broll", "photo": "..."},
 "instagram": {"type": "REEL", "legende": "...", "premier_commentaire": "...", "alt": "..."},
 "youtube": {"titre": "...", "description": "..."},
 "tiktok": {"legende": "..."}}
```
Comment l'écrire (modèle validé : `livrables/publication/2026-10-16-echantillon/fiche-publication.png`) :
- **Mot-clé** : 1 principal (ce que la cible tape : « formats Instagram », « trouver des clients coach »). En 1re ligne de légende, dit à voix haute (vérifie dans la transcription). Plus écrit sur la cover (cover sans texte, Cyril 17/10). Règles 6 à 10 de la fiche experts.
- **Légende Instagram + Facebook** : ligne 1 = mot-clé + promesse. 1 à 2 lignes de valeur tirées de la vidéo. Le CTA (une seule fois). 0 à 3 hashtags ciblés (5 max officiel).
- **CTA** : celui du script. Sinon `cta_defaut` de `config.json` ; chez Cyril : 80 % mot-clé freebie, 20 % « Commente STRAT » (`voix-contenu.md`). Un mot-clé freebie seulement si son automatisation ManyChat répond ; dans le doute : STRAT, et alerte dans la fiche.
- **1er commentaire** (Cyril 17/10) : PAS de CTA. Soit un merci à l'audience, soit un conseil de plus tiré du sujet (de la valeur en bonus, rien d'inventé). 1 à 2 phrases, à sa voix.
- **Texte alternatif** : ce qu'on voit vraiment dans la vidéo.
- **YouTube Shorts** : titre de 100 caractères max (mot-clé + bénéfice), description d'1 ou 2 lignes + « Écris STRAT en commentaire ».
- **TikTok** : 1 phrase + 1 question + 3 hashtags.
- **Trial reel** : jamais par défaut. Seulement pour reposter un reel GAGNANT de plus d'1 mois, avec 2 éléments changés, 5 par jour max (`02-Formations/experts-volume-frequence.md`).
- Dernière passe : les règles du skill `anti-ia` (pas de tiret cadratin, pas de « ce n'est pas X, c'est Y », pas de triade forcée), voix posée, tutoiement, zéro argot.

## 3. La cover (Cyril 16/10 : une photo de ses B-rolls, pas une image de la vidéo ; 17/10 : SANS texte)
1. `python3 -E $P/broll.py --mots "4 à 6 mots du sujet" --out <dossier>/broll` puis **regarde** `planche.jpg` (Read). Choisis la photo qui raconte le sujet (ex. formats vidéo → lui en train de se filmer, caméra au premier plan), visage net, visage dans le carré 3:4 du milieu. Tenue et lieu proches de la DA sombre de préférence. SSD absent → dis-le, pas de cover au hasard.
2. Higgsfield (outils chargés en retard : refais un ToolSearch avant de dire que c'est bloqué) : `media_upload` → `curl -X PUT -H "Content-Type: image/png" -H "If-None-Match: *" --data-binary @photo` → `media_confirm` → `generate_image` avec `nano_banana_2`, `aspect_ratio 9:16`, `resolution 2k`, `count 2`, la photo en `image_references`, et CE prompt (Cyril 17/10 : « trop IA » -> retouche NATURELLE, très légère teinte de la DA ; ne pas le réécrire) :
   > Edit this exact photo with a very light touch. Keep everything identical: same man, same face and identity, same expression, same pose and hands, same clothes, same car, same buildings, same sky, same framing, same time of day. Keep natural, realistic colors. Only a subtle grade: slightly deeper navy blue in the shadows and the sky, slightly warmer natural skin tone, a little more contrast and crisp eyes. Do not turn day into night, no heavy cinematic look, no artificial glow, no stylized colors. Natural photograph, true-to-life face, no text.

   Adapte seulement les éléments propres à la photo (« black t-shirt », « camera on its tripod », « window »).
3. `jobs_wait`, télécharge les 2 versions, compare-les à l'original **visage recadré côte à côte** (Read). Visage changé = jeté. Garde la plus fidèle à la DA (bleu nuit, lumière dorée).
4. `python3 -E $P/cover.py --photo retouche.png --out <dossier>` : **aucun texte sur la cover** (Cyril 17/10 : « enlève le texte, sinon c'est bon »). Puis regarde `grille.jpg` : visage entier dans le carré 3:4. Texte seulement si Cyril le redemande (`--titre`, `--sous-titre`).

## 4. L'heure
- 1 reel par jour, du lundi au dimanche. `getBestTimeToPostByNetwork` (instagram, la semaine à venir) en ne gardant que les données d'après le branchement de .business (date dans le carnet) : l'heure la plus forte de chaque jour.
- Pas encore de données business → 20h (plateau 17h-21h) et `heure_provisoire: true`. Tester 2 ou 3 créneaux, pas 10.
- **« Poste maintenant »** (Cyril 17/10) : l'heure de publication = l'heure réelle au moment de `createScheduledPost` + 1 min (minimum Metricool), jamais +5 min. Calcule-la avec `date` juste avant l'appel.

## 5. Validation : la semaine sur une page, un seul OK
1. `python3 -E $P/controle.py <dossier>/fiche.json` pour chaque reel. Un ✗ = tu corriges toi-même avant de montrer.
2. `python3 -E $P/fiche.py fiche <dossier>/fiche.json --out <dossier>/fiche.png` (détail) puis `python3 -E $P/fiche.py semaine <les fiche.json> --out <config.json → publication>/semaine-<AAAA-MM-JJ>.png`.
3. Regarde les images toi-même (Read) avant de les envoyer. Puis `SendUserFile` de la page semaine (render) et AskUserQuestion : « Je programme la semaine ? » → « Go, programme tout (Recommandé) » / « À corriger ». Les fiches détaillées sont dans chaque dossier s'il veut zoomer.
4. Correction → carnet + on refait seulement la fiche concernée, puis on remontre la page semaine.

## 6. Programmer (après le OK, jamais avant)
1. `$P/prep_video.sh final.mp4 <dossier>/reel.mp4` (1080x1920, contrôle 9:16, 3 s à 15 min, 500 Mo max).
2. Hébergement public (testé le 16/10, 0 crédit) : `media_upload` avec `files` = reel.mp4 (video/mp4) + cover.png (image/png) → `curl -X PUT -H "Content-Type: ..." -H "If-None-Match: *" --data-binary @fichier '<upload_url>'` (HTTP 200) → `media_confirm` (type video / image) → les `url` cloudfront. Vérifie `curl -sI <url>` = 200 avant Metricool.
3. `createScheduledPost`, `blogId` = `metricool_brand_id`, `publicationDate {dateTime, timezone}` (fuseau de `config.json`), `autoPublish: true`, `draft: false`. **3 posts par reel** (textes différents) :
   - A. Instagram + Facebook : `text` = légende, `firstCommentText`, `media` [url vidéo], `videoThumbnailUrl` url cover, `mediaAltText` [alt], `instagramData {type: "REEL", showReelOnFeed: true}`, `facebookData {type: "REEL", title: titre}`.
   - B. TikTok : `text` = légende TikTok, `tiktokData {privacyOption: "PUBLIC_TO_EVERYONE", title: titre}` (title obligatoire), `videoThumbnailUrl` (ignoré si compte perso).
   - C. YouTube : `text` = description, `youtubeData {title, type: "short", privacy: "public", madeForKids: false, notifySubscribers: false}` (TOUJOURS false : Cyril 17/10, pas de notification aux abonnés), `videoThumbnailUrl` ; erreur `VIDEO_THUMBNAIL_NOT_APPLICABLE` → refais SANS la cover (chaîne pas vérifiée).
4. **Premier passage (jamais fait au 16/10)** : programme UN seul reel, `getScheduledPosts` pour vérifier réseau, heure, légende, cover, montre le `plannerUrl` à Cyril, note le résultat dans le carnet, puis le reste.
5. Preuve de fin : `getScheduledPosts` sur la semaine → nombre de posts = 3 × reels. Registre mis à jour (statut « programmé », date, plannerUrl) ; chez Cyril, 1 ligne dans `~/Documents/Brain/log.md`.
6. Rappel à Cyril en 1 ligne : répondre lui-même aux commentaires les 7 premiers jours (FAQ Instagram : ça aide la portée) ; les « STRAT » vont au setter.

## 7. Archive des vidéos publiées (demande de Cyril du 16/10)
Historique de toutes les vidéos terminées : `<config.json → archive_dir>/AAAA-MM-JJ - Titre.mp4` (SSD de Cyril : `Montage/PUBLIÉES` ; client : `PUBLIÉES` sur son disque externe).
1. À chaque lancement, prends les lignes « programmé » du registre dont la date est passée. `getScheduledPosts` sur ces dates : le post n'y est plus → il est parti, statut « publié » ; il y est encore → échec, dis-le à Cyril en 1 ligne.
2. Chaque vidéo « publié » : `$P/archive_ssd.sh <final.mp4 d'origine> <AAAA-MM-JJ> "<titre>"` (copie, jamais de déplacement, vérifie la taille, ne copie pas 2 fois). Ajoute « archivée SSD » au statut dans le registre.
3. Disque absent → le script sort en code 2 : on garde la ligne et on archive au prochain passage. Jamais de vidéo archivée avant d'être vraiment publiée.

## Ce que le Publieur ne fait jamais
- Programmer ou publier sans le OK de la semaine. Toucher aux comptes perso (`comptes_interdits`). Chez un client : toucher au Metricool, au Higgsfield ou au disque de Cyril.
- Une promesse, un chiffre ou un résultat client qui n'est pas dans la vidéo.
- Une cover générée de zéro par IA : seulement une vraie photo de Cyril retouchée.
- Répondre aux commentaires ou aux DM (la relation reste humaine).
- Un trial reel par défaut.
