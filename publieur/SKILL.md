---
name: publieur
description: Le Publieur. Programme les reels déjà montés de l'utilisateur ou d'un client sur Instagram, Facebook, YouTube Shorts et TikTok via Metricool - fiche par reel, cover = meilleure image du reel (28/10), 3 reels par jour maximum, un seul OK par lot, à la demande (aucune routine). Ne publie jamais sans ce OK, jamais sur les comptes perso. Use when "publie", "publication", "programme mes reels", "programme la semaine", "poste mes vidéos", "go semaine", "semaine de publication", "cover de reel", "légende", "Metricool", "publieur", "mets en ligne".
---

## Règle n°1 : maquette d'abord (19/10/2026)
Avant de coder, monter, générer en volume ou exécuter quoi que ce soit : montre d'abord une MAQUETTE (une image, un écran, 1 slide, 10 s, 3 lignes) et attends que l'utilisateur la valide. Toujours PLUSIEURS versions (3 en général, ma recommandée en premier, chacune nommée en 3 mots) qui CHALLENGENT la direction artistique : 3 directions vraiment différentes (couleurs, typo, mise en page, ambiance), jamais 3 variantes du même style. Vote : un seul bouton « Garder celle-ci » (il en garde une, les autres sont jetées) + une note facultative, rien d'autre (pas de Peut-être ni de Jeter). DEUX rounds avant validation : round 1 = aspect global, styles vraiment différents ; round 2 = plein de détails de la maquette gardée (plusieurs parties dans le même round, une option gardée par partie). Vaut aussi pour le montage vidéo. Pour passer au round suivant, l'utilisateur dit « suivant » (plus « done ») : le bouton s'appelle « Suivant ». Pas de validation = pas d'exécution. Vaut pour tout : site, tunnel de vente, montage, PDF, scripts, pubs.

# Le Publieur : reels montés → programmés sur 4 réseaux, un seul OK

Chaîne vidéo : superveille → scripteur → tournage (l'utilisateur) → supermonteur → **publieur**. Le bouchon, c'est publier régulièrement. Ce skill fait tout, sauf le OK.

**Règle d'or : rien ne part sans le OK explicite de l'utilisateur sur la page du lot.** Un OK vaut pour ce lot-là, pas pour le suivant.

**Rythme (21/10/2026, pour tout le monde)** : 3 reels par jour maximum. **Aucune routine** : tu programmes seulement quand l'utilisateur te le demande.

```bash
P=~/.claude/skills/publieur/scripts
```
Durée à annoncer : ~3 min par reel, ~20 min pour 7 reels. Coût : 0 crédit (pas de cover depuis le 22/10, hébergement gratuit).

## Photos et vidéos de l'utilisateur
Seulement des images qu'il accepte : ses interdits (shooting, look, période) sont dans son carnet et passent avant tout. Vaut pour tout : site, carrousel, slides, montage, B-roll, cover, pub, référence Higgsfield.

## 0. Avant tout
1. Lis les réglages de cette machine : `python3 -E $P/_config.py` (le `config.json` du skill = défauts du kit, écrasé clé par clé par `~/Documents/Brain/00-Moi/reglages/publieur.json` s'il existe). Plus bas, « `config.json` → X » = la valeur X de ces réglages (marque Metricool, comptes, dossiers, disque d'archive, DA). **`"client"` rempli = on est chez un client : lis `mode-client.md` tout de suite**, il passe avant ce fichier. `config.json` absent chez un client = 1er lancement (`mode-client.md`).
2. Lis le carnet (`config.json` → `carnet` : celui de l'utilisateur dans le Brain, `retours-client.md` chez un client). Ses lignes passent AVANT ce fichier. Correction (même en passant) = 1 ligne `JJ/MM/AAAA · correction · problème → règle`, et dis-le en 1 ligne.
3. Metricool : marque `metricool_brand_id`, fuseau `timezone`. Appelle `getBrandSettings` :
   - `instagramData` doit être `instagram_attendu` (le compte pro). Aucun compte de `comptes_interdits` ne doit être branché (ses comptes perso).
   - Sinon → **on prépare les fiches, on ne programme rien**. Rappelle en 1 ligne l'action Metricool (et note-la dans son fichier `actions` (00-Moi/marque.json ; vide : dis-le dans le chat)).
4. Avant d'écrire : les règles de légende (`config.json` → `regles_legendes`) et, s'il existe, `~/Documents/Brain/00-Moi/voix-contenu.md`.
5. Bilan des passages précédents (à chaque lancement) : voir § 7.

## 1. Quels reels
- Registre : `config.json` → `registre`, 1 ligne par reel. Une vidéo déjà au registre ne repart jamais.
- Candidats : les `final.mp4` des dossiers `montage-*` de `config.json` → `montages` (chez un client : `mode-client.md`) absents du registre, du plus ancien au plus récent. Exclus : `style-lab/`, les dossiers ou fichiers `test`, les comparatifs. Le OK de l'utilisateur sur le lot vaut validation du montage.
- Nombre : tous les reels montés pas encore programmés, rangés à 3 par jour maximum. Moins de 3 par jour → dis combien manquent en 1 ligne : c'est là que l'argent dort.
- Quota Metricool (carnet 21/10) : le plan Free = 5 reels par mois sur 4 réseaux, au-delà rien ne sort. Choix par défaut (21/10) : rester en Free jusqu'à la limite, toujours sur les 4 réseaux. Compte les publications déjà programmées ce mois-ci (`getScheduledPosts`), programme jusqu'à 20, puis dis en 1 ligne « Limite atteinte : passe en Starter (metricool.com/pricing) » et arrête-toi. Les reels en trop attendent le mois suivant ou le Starter.
- Matière de chaque reel : la transcription du dossier de montage (`words.json` ou `cut.words.json`) et, s'il existe, le script du Scripteur (`<sorties>/scripts/`, <sorties> = `sorties` de 00-Moi/marque.json, sinon ~/Documents/Contenu) pour le mot-clé et le CTA. **Rien d'inventé** : la légende ne promet que ce que la vidéo dit.

## 2. La fiche (`fiche.json`)
Dossier : `<config.json → publication>/<AAAA-MM-JJ>-<slug>/` (date de publication prévue).
```json
{"titre": "Tier list des formats Instagram", "video": "/chemin/final.mp4", "duree": 49,
 "date": "2026-10-19T20:00:00", "heure_provisoire": true, "note_heure": "Heure provisoire : ...",
 "plateformes": ["instagram", "facebook", "youtube", "tiktok"],
 "mot_cle": "formats Instagram", "dit_a_voix": true, "sur_cover": false, "cta": "GUIDE", "cta_dans_video": false,
 "cover": {"source": "video", "note": "aucune cover envoyée (22/10)"},
 "instagram": {"type": "REEL", "legende": "...", "premier_commentaire": "...", "alt": "..."},
 "youtube": {"titre": "...", "description": "..."},
 "tiktok": {"legende": "..."}}
```
Comment l'écrire (modèle validé : `livrables/publication/2026-10-16-echantillon/fiche-publication.png`) :
- **Mot-clé** : 1 principal (ce que la cible tape : « formats Instagram », « trouver des clients coach »). En 1re ligne de légende, dit à voix haute (vérifie dans la transcription). Plus écrit sur la cover (cover sans texte, 17/10). Règles 6 à 10 de la fiche experts.
- **Légende Instagram + Facebook (20/10)** : COURTE, 1 ou 2 phrases, c'est tout. Phrase 1 = mot-clé + promesse. S'il y a un CTA DANS la vidéo, il devient la phrase 2 ; sinon, pas de CTA. **Aucun hashtag.** (Remplace l'ancienne légende en 4 blocs + hashtags.)
- **CTA** : seulement s'il est dit dans la vidéo (champ `cta_dans_video`), repris tel quel en phrase 2. Sinon aucun. Celui du script si la vidéo le dit. Sinon `cta_defaut` de `config.json` (vide = `mot_cle` de 00-Moi/marque.json), dans le dosage que donne son carnet. Un mot-clé freebie seulement si son automatisation (ManyChat ou GoHighLevel) répond ; dans le doute : `cta_defaut`, et alerte dans la fiche.
- **1er commentaire : AUCUN** (20/10 : « pas de commentaire »). Ne pas envoyer `firstCommentText`.
- **Texte alternatif** : ce qu'on voit vraiment dans la vidéo.
- **YouTube Shorts** : titre de 100 caractères max (mot-clé + bénéfice), description = la même règle que la légende (1 ou 2 phrases, CTA en phrase 2 seulement s'il est dans la vidéo, aucun hashtag).
- **TikTok** : même règle : 1 ou 2 phrases, CTA en phrase 2 seulement s'il est dans la vidéo, aucun hashtag.
- **Trial reel : SUPPRIMÉ le 29/10** (l’utilisateur : « tout ce qui est en lien avec les reels d'essai, tu peux tout supprimer »). Jamais de `TRIAL_REEL`, jamais de reel d'essai.
- Dernière passe : les règles du skill `anti-ia` (pas de tiret cadratin, pas de « ce n'est pas X, c'est Y », pas de triade forcée), voix posée, tutoiement, zéro argot.

## 3. La cover : LA MEILLEURE IMAGE DU REEL (28/10/2026, remplace « aucune cover » du 22/10)
**28/10 (« à chaque fois que tu publies, choisis la meilleure image dans le reel à mettre en couverture ») : à CHAQUE publication, je choisis seul une image DU reel (pas de planche, pas de vote).** Méthode : `ffmpeg -v error -i final.mp4 -vf fps=2,scale=270:-1,tile=8x8 <dossier>/candidats.jpg`, je regarde (Read) ; je garde visage net, yeux ouverts, expression forte, visage dans le carré 3:4 du milieu, pas de menu CTA ni de sous-titre coupé en plein visage ; un plan avec un mot géant derrière la tête est un bon candidat. Envoyée comme MOMENT de la vidéo (`videoCoverMilliseconds` et l'équivalent TikTok / YouTube dans Metricool), jamais une image générée ou retouchée. Je montre l'image choisie dans la fiche. Le texte ci-dessous (22/10) ne vaut plus.
Ancienne règle du 22/10 :
**22/10 (« ne mets plus de couverture ») : on n'envoie plus de cover.** Pas de planche de 3 covers, pas de `videoThumbnailUrl`, pas de `videoCoverMilliseconds` : chaque réseau prend lui-même une image de la vidéo. Pour l'aperçu de la fiche seulement (jamais envoyé) : `ffmpeg -v error -y -ss 0.5 -i final.mp4 -frames:v 1 <dossier>/image1.png` puis `python3 -E $P/cover.py --photo <dossier>/image1.png --out <dossier>` (sort cover_480.jpg et grille.jpg pour fiche.py).

Ancien process, **seulement si l'utilisateur redemande une cover** :
20/10 : proposer TROIS covers à choisir (3 photos de ses B-rolls vraiment différentes, ma recommandée en 1er, sur une planche + boutons). Il garde une. S'il dit « choisis » ou « libre arbitre », je choisis seul. Jamais de retouche IA lourde (19/10 : plus d'images générées) : la vraie photo, au plus un étalonnage naturel.
1. `python3 -E $P/broll.py --mots "4 à 6 mots du sujet" --out <dossier>/broll` puis **regarde** `planche.jpg` (Read). Choisis la photo qui raconte le sujet (ex. formats vidéo → lui en train de se filmer, caméra au premier plan), visage net, visage dans le carré 3:4 du milieu. Tenue et lieu proches de la DA sombre de préférence. SSD absent → dis-le, pas de cover au hasard.
2. Higgsfield (outils chargés en retard : refais un ToolSearch avant de dire que c'est bloqué) : `media_upload` → `curl -X PUT -H "Content-Type: image/png" -H "If-None-Match: *" --data-binary @photo` → `media_confirm` → `generate_image` avec `nano_banana_2`, `aspect_ratio 9:16`, `resolution 2k`, `count 2`, la photo en `image_references`, et CE prompt (17/10 : « trop IA » -> retouche NATURELLE, très légère teinte de la DA ; ne pas le réécrire) :
   > Edit this exact photo with a very light touch. Keep everything identical: same man, same face and identity, same expression, same pose and hands, same clothes, same car, same buildings, same sky, same framing, same time of day. Keep natural, realistic colors. Only a subtle grade: slightly deeper navy blue in the shadows and the sky, slightly warmer natural skin tone, a little more contrast and crisp eyes. Do not turn day into night, no heavy cinematic look, no artificial glow, no stylized colors. Natural photograph, true-to-life face, no text.

   Adapte seulement les éléments propres à la photo (« black t-shirt », « camera on its tripod », « window »).
3. `jobs_wait`, télécharge les 2 versions, compare-les à l'original **visage recadré côte à côte** (Read). Visage changé = jeté. Garde la plus fidèle à la DA (bleu nuit, lumière dorée).
4. `python3 -E $P/cover.py --photo retouche.png --out <dossier>` : **aucun texte sur la cover** (17/10 : « enlève le texte, sinon c'est bon »). Puis regarde `grille.jpg` : visage entier dans le carré 3:4. Texte seulement si l'utilisateur le redemande (`--titre`, `--sous-titre`).

## 4. L'heure
- 3 reels par jour maximum, à partir du lendemain (jamais le jour même). Au moins 2 h entre deux reels du même jour (02-Formations/experts-volume-frequence.md l.87 : espacer de 90 à 120 min pour lire chaque post). `getBestTimeToPostByNetwork` (instagram, les jours du lot) en ne gardant que les données d'après le branchement de .business (date dans le carnet) : les 3 heures les plus fortes de chaque jour (moins si le lot en a moins).
- Pas encore de données business → 20h (plateau 17h-21h) et `heure_provisoire: true`. Tester 2 ou 3 créneaux, pas 10.
- **« Poste maintenant »** (17/10) : l'heure de publication = l'heure réelle au moment de `createScheduledPost` + 1 min (minimum Metricool), jamais +5 min. Calcule-la avec `date` juste avant l'appel.

## 5. Validation : le lot sur une page, un seul OK
1. `python3 -E $P/controle.py <dossier>/fiche.json` pour chaque reel. Un ✗ = tu corriges toi-même avant de montrer.
2. `python3 -E $P/fiche.py fiche <dossier>/fiche.json --out <dossier>/fiche.png` (détail) puis `python3 -E $P/fiche.py semaine <les fiche.json> --out <config.json → publication>/semaine-<AAAA-MM-JJ>.png`.
3. Regarde les images toi-même (Read) avant de les envoyer. Puis `SendUserFile` de la page du lot (render) et AskUserQuestion : « Je programme ce lot ? » → « Go, programme tout (Recommandé) » / « À corriger ». Les fiches détaillées sont dans chaque dossier s'il veut zoomer.
4. Correction → carnet + on refait seulement la fiche concernée, puis on remontre la page du lot.

## 6. Programmer (après le OK, jamais avant)
1. `$P/prep_video.sh final.mp4 <dossier>/reel.mp4` (1080x1920, contrôle 9:16, 3 s à 15 min, 500 Mo max).
2. Hébergement public (testé le 16/10, 0 crédit) : `media_upload` avec `files` = reel.mp4 (video/mp4) seul (plus de cover depuis le 22/10) → `curl -X PUT -H "Content-Type: ..." -H "If-None-Match: *" --data-binary @fichier '<upload_url>'` (HTTP 200) → `media_confirm` (type video / image) → les `url` cloudfront. Vérifie `curl -sI <url>` = 200 avant Metricool.
3. `createScheduledPost`, `blogId` = `metricool_brand_id`, `publicationDate {dateTime, timezone}` (fuseau de `config.json`), `autoPublish: true`, `draft: false`. **3 posts par reel** (textes différents) :
   - A. Instagram + Facebook : `text` = légende (pas de `firstCommentText`), `media` [url vidéo], `mediaAltText` [alt] (pas de `videoThumbnailUrl` : 22/10), `instagramData {type: "REEL", showReelOnFeed: true}`, `facebookData {type: "REEL", title: titre}`.
   - B. TikTok : `text` = légende TikTok, `tiktokData {privacyOption: "PUBLIC_TO_EVERYONE", title: titre}` (title obligatoire), pas de cover.
   - C. YouTube : `text` = description, `youtubeData {title, type: "short", privacy: "public", madeForKids: false, notifySubscribers: false}` (TOUJOURS false : 17/10, pas de notification aux abonnés), pas de cover.
4. **Premier passage (jamais fait au 16/10)** : programme UN seul reel, `getScheduledPosts` pour vérifier réseau, heure, légende, cover, montre le `plannerUrl` à l'utilisateur, note le résultat dans le carnet, puis le reste.
5. Preuve de fin : `getScheduledPosts` sur les jours du lot → nombre de posts = 3 × reels. Registre mis à jour (statut « programmé », date, plannerUrl) ; 1 ligne dans `~/Documents/Brain/log.md` s'il existe.
6. Rappel à l'utilisateur en 1 ligne : répondre lui-même aux commentaires les 7 premiers jours (FAQ Instagram : ça aide la portée) ; les commentaires avec son mot-clé (`mot_cle` de marque.json) partent en DM.

## 7. Archive des vidéos publiées (16/10)
Historique de toutes les vidéos terminées : `<config.json → archive_dir>/AAAA-MM-JJ - Titre.mp4` (son disque d'archive ; client : `PUBLIÉES` sur son disque externe ; vide = pas d'archive).
1. À chaque lancement, prends les lignes « programmé » du registre dont la date est passée. `getScheduledPosts` sur ces dates : le post n'y est plus → il est parti, statut « publié » ; il y est encore → échec, dis-le à l'utilisateur en 1 ligne.
2. Chaque vidéo « publié » : `$P/archive_ssd.sh <final.mp4 d'origine> <AAAA-MM-JJ> "<titre>"` (copie, jamais de déplacement, vérifie la taille, ne copie pas 2 fois). Ajoute « archivée SSD » au statut dans le registre.
3. Disque absent → le script sort en code 2 : on garde la ligne et on archive au prochain passage. Jamais de vidéo archivée avant d'être vraiment publiée.

## Ce que le Publieur ne fait jamais
- Programmer ou publier sans le OK du lot. Toucher aux comptes perso (`comptes_interdits`). Chez un client : toucher au Metricool, au Higgsfield ou au disque du coach qui l'a installé.
- Une promesse, un chiffre ou un résultat client qui n'est pas dans la vidéo.
- Une cover qui n'est pas une image du reel (28/10 : toujours la meilleure image du reel). Et jamais une cover générée de zéro par IA.
- Répondre aux commentaires ou aux DM (la relation reste humaine).
- Un trial reel (`TRIAL_REEL`) : supprimé le 29/10.
- Inventer une info absente du Brain ou de la vidéo : dis « je ne l'ai pas ».

En cas d'échec (Metricool muet, vidéo introuvable, programmation refusée) : une ligne dans ~/Documents/Brain/04-Audits/erreurs-taches.md (date, tâche, erreur) et dis-le en une ligne.
