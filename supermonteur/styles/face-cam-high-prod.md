# FACE CAM · degré 3 : HIGH PROD (reel phare)

Lu après `SKILL.md`. Tout l'arsenal : chiffres géants, mots géants, listes, preuves, B-rolls, images, CTA. On peut couvrir la tête : B-rolls et/ou motion design plein écran pendant qu'il parle. La tête n'a pas besoin d'être à l'écran tout le temps.
Brief en plus : **Style** Sobre / Dynamique (plans plus courts, plus de B-rolls et zooms).
Étalon : la version de son monteur humain quand elle existe (`/Volumes/SSD Dreamax/Montage/INSTA/FINAL BUSINESS/<titre>.mp4`), sinon `ref/FINAL.mp4`. Le but : faire mieux que lui.

## 1 bis. Fiche univers (après l'étape 1 de SKILL.md ; Bruce Block, Deakins : l'univers du reel = celui de la rush)
```bash
python3 $S/univers_check.py fiche clip.mp4      # univers.json + univers.jpg : palette, couleur de la lumière, noirs / hautes lumières, cadre
```
Compléter `univers.json` à l'œil (source de lumière, espace, ligne, forme), remplir `plan.colors` depuis la palette, mettre la lumière dans chaque prompt Higgsfield. `python3 $S/lookstats.py clip.mp4 --face` = mesure seule (bornes : noirs P1 1-8, P99 ≤ 235, néon < 0,5 %).

## 4. Champs plan.json du high prod (en plus des champs communs de SKILL.md)
```json
{
  "numbers": [{"text": "30", "start": 0.4, "end": 1.95},
              {"text": "99", "suffix": "%", "count": 99, "start": 16.6, "end": 18.35}],
  "lists": [{"start": 10.72, "end": 13.42, "title": ["50 façons de parler", "d'une seule idée"],
             "pages": [["1-Les problèmes autour du sujet", "..."], ["19-...", "..."]]}],
  "bullets": {"at": [30.1, 30.32, 30.54], "end": 32.2},
  "brolls": []
}
```
- **numbers** : chaque chiffre fort prononcé (30 secondes, 99 %, 800 vidéos) → chiffre géant derrière la tête, du début du mot à ~1.5 s. `count` = compteur qui défile. Aussi gros que la réf, jamais coupé en haut ; le chiffre sort du sous-titre.
- **lists** : quand la personne cite une liste (« 50 sujets », « 16 principes ») → carton plein écran, du mot qui l'annonce jusqu'à la phrase suivante. Pages de 14-18 éléments max. Contenu : celui de la personne (doc, script, Brain) ; ne jamais inventer une liste de son savoir-faire sans le dire.
- **bullets** : « 3 points / 3 étapes » → pastilles, une par élément.
- **inserts suivis (tracking)** : `python3 $S/track.py clip.mp4 0.3 3.0 --point index_tip --out track_badge.json` (points : index_tip, thumb_tip, palm, head_top, head_left, head_right, chin) puis `{"src": "hf/badge.png", "start", "end", "track": "track_badge.json", "offset": [0, -150], "w": 260}` : l'objet suit le geste (testé 13/10 : 41/41 images détectées). Après recadrage (`cadre.py`), vérifier que l'objet suivi reste dans le cadre.
- **hook** (guide OPUS, 13/10) : `{}` = ouverture : impact grave seulement. Viseur REC = `"rec": true`, seulement si la vidéo parle de tournage (Cyril : « REC, ça n'a rien à voir »). **Jamais de bandes noires** (rejetées le 13/10 ; `bars: true` les remet, ne pas l'utiliser). Options : `rec`, `impact` (false pour couper), `recEnd`. Hook complet en 7 s : REC (0 s) → mot géant derrière la tête (~0,9 s) → plein écran éclair < 1 s (B-roll ou preuve) avant 3,5 s.
- **bigwords** : `[{"text": "dangereux", "start": 3.6, "end": 4.95}]` = LE mot-clé en serif géant derrière la tête, lettre par lettre depuis le centre, 2 échos en contour qui dérivent, zoom d'impact + aspiration inversée. 1 à 2 par vidéo, surtout dans le hook. Passe par `matte.py` comme les chiffres. Le mot sort du sous-titre tout seul. Ignoré si la vidéo a un `title`.
- **proofs** = « montrer au lieu de dire » : quand la phrase porte une preuve, un chiffre ou une durée, plein écran pendant que la voix continue. **3 à 5 pleins écrans max en tout (listes + preuves + B-rolls plein écran), 1 à 5 s chacun, jamais deux types identiques à la suite.** Sous-titres masqués dessous.
  - `{"type": "curve", "start", "end", "title": ["Copier un hook", "ou le construire"], "from": "Hook copié", "to": "16 principes", "levels": ["Débutant", "Expert"], "steps": [...], "climax": 20.9}` → papier ivoire : la ligne grise plafonne en bas, la ligne accent monte d'un coup (`climax` = l'instant où elle part, calé sur le mot fort). Pour : « même avec 6 mois », « ce que tout le monde fait vs ». **Seul type de preuve autorisé.**
  - ÉCARTÉS par Cyril le 13/10 (ne pas utiliser ni proposer) : `clock` (horloge qui s'emballe) et `dashboard` (verre sombre 3D). Chiffres de preuve = ceux de la personne (vrais résultats), jamais inventés.

## 5. B-rolls (si utiles : par défaut AUCUN, voir le cahier des charges)
Décider la densité pour TOUTE la vidéo : `none` / `low` / `high`.
```bash
python3 $S/broll.py slots plan.json words.json --density low     # créneaux réguliers + ce qui est dit à ce moment
python3 $S/broll.py search tournage camera                       # chercher dans la bibliothèque, verticaux d'abord
```
Pour chaque créneau, choisir le fichier qui illustre EXACTEMENT ce qui est dit et qui est beau (net, vertical bien cadré, lumière propre), l'ajouter dans `plan.brolls` (`{"src": "<chemin absolu>", "from": 2.0, "start": .., "end": ..}` ; `"from": "auto"` = passage le plus stable). Une personne visible dans le B-roll = la même que la face cam (vérifier, l'index dit seulement « personne visible » ; plans bannis : `broll_exclus.txt`). Jamais tourné avant 2024 (`brolls_min_date`), sauf photos `usage=souvenir` pour illustrer son passé. Pas de bon fichier → on garde la face cam, mais la répartition doit rester régulière (sinon passer à `none`). Mieux vaut 2 B-rolls parfaits que 4 moyens.
```bash
python3 $S/broll.py prep plan.json                               # coupe + recadre les B-rolls dans broll/
```

## 5 bis. Images sur-mesure (incrustations)
**Qui paie ?** Cyril → Higgsfield (MCP, ses crédits). Client → Higgsfield sur SON compte ; sans compte Higgsfield → Gemini sur SA clé (voir `mode-client.md`).
Quand une idée se montre mieux en image (logo, objet, chiffre en 3D, schéma, produit) et que rien dans la bibliothèque ne colle : la générer sur Higgsfield (si `"higgsfield": true`). Outils Higgsfield = outils différés : les charger via ToolSearch.
- **Charte AVANT tout visuel** (Cyril 13/10 : chrome 3D / néon = « très cheap ») : zéro chrome, zéro néon, zéro glow ; 1 visuel test validé avant le reste. Objet réel (badge Meta, logo, interface) = vraie forme et vraie couleur (réf Google Images / version du monteur), détouré, éclairé comme la scène.
- Prompt = l'idée exacte dite à cet instant + la lumière de la fiche univers + `broll.prompt_higgsfield` de la DA. Format 1:1 ou 4:5. Modèle par défaut : `nano_banana_2` (rapide). Texte lisible dans l'image → `gpt_image_2`. Rendu ciné → `soul_cinematic`. VIDÉO générée seulement pour un gros moment sans visage (voir cahier des charges).
- Détourer avec `remove_background` → PNG transparent, télécharger dans le dossier du reel (`ins/`).
- Ajouter dans `plan.inserts` : `{"src": "ins/x.png", "start": .., "end": .., "pos": "top"}` ; `top` = au-dessus de la tête, jamais sur le visage (défaut) ; `center` = grande carte qui cache le visage, ≤ 2 s.
- Même règle que les B-rolls : régulier, exact, beau. Pas de plafond d'images (Cyril, 12/10) : autant que nécessaire, mais régulier et utile. Annoncer les crédits dépensés.
- Image plein écran (pas détourée) → la mettre dans `plan.brolls` (le moteur accepte .png/.jpg).
- Client sans Higgsfield (Gemini, images fixes seulement, animées par HyperFrames) :
```bash
python3 $S/gemini_image.py "<prompt + broll.prompt_higgsfield de la DA>" ins/x.png --client <prenom> --ratio 1:1   # 9:16 pour un B-roll plein écran
```
Pas de clé → le script affiche le lien + la commande trousseau à donner au client. Détourage d'un PNG Gemini : `remove_background` Higgsfield ou rembg local.

## 5 ter. Caler les ajouts sur la rush, puis test « 5 sur 7 » (avant tout rendu)
```bash
python3 $S/match_look.py clip.mp4 ins/*.png broll/*.mp4 --w 400 --fix   # objet : exposition baissée s'il brille plus que la pièce, couleur JAMAIS touchée ; b-roll : brut, seulement blancs brûlés / voile gris
python3 $S/univers_check.py check plan.json                             # couleur, ton, mouvement, rythme mesurés + univers-check.jpg
```
Remplacer dans `plan.json` chaque fichier calé par son `.cale`. Regarder `univers-check.jpg` (rush à gauche, ajout à droite) et juger espace, ligne, forme : il faut 5 composantes sur 7 en commun, sinon on retire ou on refait. Puis le test Deakins : d'où vient sa lumière ? est-il dans CETTE pièce ? sert-il la phrase ? `--color` seulement pour un visuel GÉNÉRÉ (jamais un vrai logo ni ses vrais plans).

## 6. Détourage avant le rendu
```bash
python3 $S/matte.py plan.json                                    # tête devant les chiffres et mots géants (~20 s par chiffre)
```
Puis l'étape 6 de `SKILL.md` (build, lint, zones, rendu, mix).

## Comparer à l'étalon avant d'envoyer
Planches 1 i/s côte à côte + `analyse_ref.py` sur les deux (coupes, débit, SFX sur les coupes ~60 %). Puis la note /10 (`note-10.md`).

## Formats validés par Cyril sur le reel Tesla/SpaceX (17/10, 4 rounds de Cut Notes)
- **Hook sur une actu** : SPLIT SCREEN dès l'image 0 (vidéo officielle en haut 1080x960, lui en bas, même temps que la cam = bouche synchro), pendant toute la 1re phrase. Même split quand il pointe « regarde juste ici ».
- **Images d'actu** : vidéos / photos des comptes officiels (Apify instagram-scraper), vidéos 4:5 posées en 1080x1350 sur fond noir avec fondu haut / bas ; crédit dans la légende.
- **B-rolls enchaînés** : fondu 0,3 s entre eux (pas 3 coupes sèches). Début / fin de B-roll calés sur les coupes du dérush : automatique (build.mjs lit cut.segments.json).
- **« Mes comptes sont passés de ça à ça »** : captures du VRAI profil au-dessus de la tête (Apify instagram-profile-scraper : photo, abonnés, publications), avant puis après, chacune ≥ 1,2 s.
- **Concept nommé (effet Médicis…)** : motion design plein écran qui l'explique (ex. 2 cercles qui se croisent), choc calé sur le mot et la frappe de la musique, titre lisible ~2 s.
- **Images générées** (Higgsfield) : dans l'univers de la vidéo (nuit, bleu nuit, rouge de l'événement), jamais un plein jour gris ; voile sombre en haut si les sous-titres tombent sur un ciel clair.
- **Visage très proche** (selfie voiture) : `subY` ~380 (au-dessus de la tête) ; les sous-titres s'effacent seuls sous chiffres, mots géants et captures.
- **Durée demandée > 1 min** : garder la signature (« Mr Dreamax »), `fin_musique: false`, fin de musique recalée à la main.
