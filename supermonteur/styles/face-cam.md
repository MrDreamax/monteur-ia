# FACE CAMÉRA (le SEUL style face cam, 19/10/2026)

**26/10 (remplace le 19/10) : le style DYNAMIQUE (la face caméra) = un MIX À ÉQUILIBRER de 4 plans : (1) split screen = face cam + animation, (2) face cam seule, (3) carton plein écran avec un DÉGRADÉ PROPRE (jamais de couleur unie, 23/10), (4) animation plein écran (motion design HyperFrames niveau Jun Yuh, jamais d'image IA). Toujours ses sous-titres + une musique.** Équilibre = aucun des 4 ne domine, jamais 2 pleins écrans du même type à la suite, la face cam revient entre deux. Les mots géants, chiffres, listes ci-dessous restent des outils pour les plans 1, 3 et 4. B-rolls seulement s'il les demande (23/10). Les anciens degrés « sous-titres », « high prod » restent supprimés (« minimaliste » = autre style depuis le 26/10, `styles/raw.md`). Anciens fichiers : `styles/_archive/`.

**29/10/2026 22h35 : MOTION DESIGN PAR DÉFAUT = « Écrans iPhone » façon Apple** (l’utilisateur, reel complet CAM20065 : « garde en mémoire ce type de motion design, j'adore, c'est vraiment ce qu'il faut »). Pour le split screen (animation en haut 1080x960, lui en bas) et les animations : vrais écrans iOS refaits en HTML (profil Instagram, notif, appel avec chrono, Messages, cartes Santé, listes, paiement reçu, reel), UN SEUL iPhone qui se transforme d'un écran à l'autre (pas de coupure), caméra qui zoome pour lire, dérive douce + inclinaison 3D, typo SF géante (une idée par écran), mots barrés en rouge, entrées en flou + échelle sans rebond, sons d'iPhone calés sur l'image (notif, pop, raccroché, bulle, caisse). Fond gris clair Apple, sous-titres #1D1D1F à 885 px sans ombre, fondu clair 800-960 px. Modèle : `styles/split-apple/modele-ecrans-iphone.html` (helper K des états), sons : `styles/split-apple/ajoute_sons.py` + `sons.json`. Échantillon de 20 s d'abord.

Lu après `SKILL.md`. Tout l'arsenal : chiffres géants, mots géants, listes, preuves, B-rolls, images, CTA. On peut couvrir la tête : B-rolls et/ou motion design plein écran pendant qu'il parle. La tête n'a pas besoin d'être à l'écran tout le temps.
Pas de question de degré ni de « Sobre / Dynamique » : le dosage se décide à l'œil selon la vidéo, puis se valide en maquettes (2 rounds).
Étalon : la version de son monteur humain quand elle existe (`/Volumes/son disque externe/1 - Contenu/2 - Vidéos finies/Reels business/<titre>.mp4`), sinon `ref/FINAL.mp4`. Le but : faire mieux que lui.

## 1 bis. Fiche univers (après l'étape 1 de SKILL.md ; Bruce Block, Deakins : l'univers du reel = celui du rush)
```bash
python3 $S/univers_check.py fiche clip.mp4      # univers.json + univers.jpg : palette, couleur de la lumière, noirs / hautes lumières, cadre
```
Compléter `univers.json` à l'œil (source de lumière, espace, ligne, forme), remplir `plan.colors` depuis la palette, mettre la lumière dans chaque prompt Higgsfield. `python3 $S/lookstats.py clip.mp4 --face` = mesure seule (bornes : noirs P1 1-8, P99 ≤ 235, néon < 0,5 %).

## 4. Champs plan.json (en plus des champs communs de SKILL.md)
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
- **hook** (guide OPUS, 13/10) : `{}` = ouverture : impact grave seulement. Viseur REC = `"rec": true`, seulement si la vidéo parle de tournage (retour : « REC, ça n'a rien à voir »). **Jamais de bandes noires** (rejetées le 13/10 ; `bars: true` les remet, ne pas l'utiliser). Options : `rec`, `impact` (false pour couper), `recEnd`. Hook complet en 7 s : REC (0 s) → mot géant derrière la tête (~0,9 s) → plein écran éclair < 1 s (B-roll ou preuve) avant 3,5 s.
- **bigwords** : `[{"text": "dangereux", "start": 3.6, "end": 4.95}]` = LE mot-clé en serif géant derrière la tête, lettre par lettre depuis le centre, 2 échos en contour qui dérivent, zoom d'impact + aspiration inversée. 1 à 2 par vidéo, surtout dans le hook. Passe par `matte.py` comme les chiffres. Le mot sort du sous-titre tout seul. Permis aussi avec un `title` depuis le 21/10 (L'utilisateur).
- **proofs** = « montrer au lieu de dire » : quand la phrase porte une preuve, un chiffre ou une durée, plein écran pendant que la voix continue. **3 à 5 pleins écrans max en tout (listes + preuves + B-rolls plein écran), 1 à 5 s chacun, jamais deux types identiques à la suite.** Sous-titres masqués dessous.
  - `{"type": "curve", "start", "end", "title": ["Copier un hook", "ou le construire"], "from": "Hook copié", "to": "16 principes", "levels": ["Débutant", "Expert"], "steps": [...], "climax": 20.9}` → papier ivoire : la ligne grise plafonne en bas, la ligne accent monte d'un coup (`climax` = l'instant où elle part, calé sur le mot fort). Pour : « même avec 6 mois », « ce que tout le monde fait vs ». (19/10 : courbe papier REFUSÉE, ne plus l'utiliser. 26/10 : l'animation plein écran redevient un des 4 plans du format, en motion design propre niveau Jun Yuh, pas cette courbe.)
  - ÉCARTÉS par l'utilisateur le 13/10 (ne pas utiliser ni proposer) : `clock` (horloge qui s'emballe) et `dashboard` (verre sombre 3D). Chiffres de preuve = ceux de la personne (vrais résultats), jamais inventés.

## 5. B-rolls (23/10 : plus obligatoires. Par défaut AUCUN, montage dans le cockpit. Seulement s'il les demande : cinématiques, choisis par moi sans round (26/10), corrigés dans le Cockpit, voir SKILL.md 4 bis)
Densité quand il en demande = `high` : environ 1 par phrase quand un vrai plan colle. Préférer `VIDEOS/` (caméra) à `B-ROLL-TELEPHONE/`. Choisir seul le meilleur plan par phrase (règles de variété de SKILL.md 4 bis), il corrige dans le Cockpit.
Décider la densité pour TOUTE la vidéo : `none` / `low` / `high`.
```bash
python3 $S/broll.py slots plan.json words.json --density low     # créneaux réguliers + ce qui est dit à ce moment
python3 $S/broll.py search tournage camera                       # chercher dans la bibliothèque, verticaux d'abord
```
Pour chaque créneau, choisir le fichier qui illustre EXACTEMENT ce qui est dit et qui est beau (net, vertical bien cadré, lumière propre), l'ajouter dans `plan.brolls` (`{"src": "<chemin absolu>", "from": 2.0, "start": .., "end": ..}` ; `"from": "auto"` = passage le plus stable). Une personne visible dans le B-roll = la même que la face cam (vérifier, l'index dit seulement « personne visible » ; plans bannis : `broll_exclus.txt`). Jamais tourné avant 2024 (`brolls_min_date`), sauf photos `usage=souvenir` pour illustrer son passé. Pas de bon fichier → on garde la face cam, mais la répartition doit rester régulière (sinon passer à `none`). Mieux vaut 2 B-rolls parfaits que 4 moyens.
```bash
python3 $S/broll.py prep plan.json                               # coupe + recadre les B-rolls dans broll/
```

## 5 bis. Images générées : INTERDITES (19/10)
Jamais d'image ni de vidéo générée par IA (Higgsfield, Kling, Gemini...). Une idée à montrer = son vrai plan, une vraie capture, un vrai logo détouré, ou un carton plein écran. Rien qui colle → face cam.

## 4 bis. Cartons plein écran (repris de l'ex-minimaliste, 19/10)
Sur les punchlines (1 toutes les 10-20 s, 1 à 3 lignes de 1-3 mots, SES mots, condensés). Couleurs = celles de SON rush (`plan.colors.grad`). 1 whoosh à l'entrée (auto, `list`). Jamais 2 pleins écrans du même type à la suite ; anti-flash géré par le moteur.
Syntaxe `plan.mini` (build.mjs) :
- `{"type": "card", "start", "end", "bg": "grad" | "flat" | "#hex", "lines": [{"text": "en revanche", "font": "serif"}, {"text": "gagner en"}, {"text": "crédibilité", "font": "serif", "size": 190}]}` → carton plein écran, chaque mot apparaît QUAND il est dit (cherché dans la transcription) ; `"at"` + `"whole": true` = toute la ligne d'un coup ; `"swap": true` = la ligne remplace celle d'avant au même endroit (« IMPORTANT » → « ASSET ») ; `font` sans = MAJUSCULES grasses (défaut), serif = italique ; taille auto (tient dans 900 px). Compte comme plein écran : anti-flash, pas de sous-titres dessous.
- `{"type": "icon", "icon": "eye" | ["calendar", "calendar"], "start", "end", "cross": t, "y": 360, "size": 210}` → icône(s) au trait fin blanc au-dessus de la tête (y sous le haut de la tête : `headtop.py`) ; `cross` = croix rouge tracée à cet instant (« non », « pas »). Icônes : eye, calendar, user, users, chart, phone, message, clock, money, badge, shield, heart, star, idea, handshake (en ajouter dans `MINI_ICONS`).
- `{"type": "shot", "src": "ins/x.png", "start", "end", "y": 210, "w": 900, "circle": {"at", "cx", "cy", "rx", "ry"}}` → capture recadrée sur l'utile, carte arrondie au-dessus de la tête, légère dérive ; cercle blanc tracé à la main à `at` (coordonnées en px de l'image ; `color` possible).

## 5 ter. Caler les ajouts sur le rush, puis test « 5 sur 7 » (avant tout rendu)
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

## Formats validés par l'utilisateur sur le reel Tesla/SpaceX (17/10, 4 rounds de Cut Notes)
- **Hook sur une actu** : SPLIT SCREEN dès l'image 0 (vidéo officielle en haut 1080x960, lui en bas, même temps que la cam = bouche synchro), pendant toute la 1re phrase. Même split quand il pointe « regarde juste ici ».
- **Images d'actu** : vidéos / photos des comptes officiels (Apify instagram-scraper), vidéos 4:5 posées en 1080x1350 sur fond noir avec fondu haut / bas ; crédit dans la légende.
- **B-rolls enchaînés** : fondu 0,3 s entre eux (pas 3 coupes sèches). Début / fin de B-roll calés sur les coupes du dérush : automatique (build.mjs lit cut.segments.json).
- **« Mes comptes sont passés de ça à ça »** : captures du VRAI profil au-dessus de la tête (Apify instagram-profile-scraper : photo, abonnés, publications), avant puis après, chacune ≥ 1,2 s.
- **Concept nommé (effet Médicis…)** : motion design plein écran qui l'explique (ex. 2 cercles qui se croisent), choc calé sur le mot et la frappe de la musique, titre lisible ~2 s.
- (OBSOLÈTE 19/10, IA interdite) **Images générées** (Higgsfield) : dans l'univers de la vidéo (nuit, bleu nuit, rouge de l'événement), jamais un plein jour gris ; voile sombre en haut si les sous-titres tombent sur un ciel clair.
- **Visage très proche** (selfie voiture) : `subY` ~380 (au-dessus de la tête) ; les sous-titres s'effacent seuls sous chiffres, mots géants et captures.
- **Durée demandée > 1 min** : garder la signature (« Mr Dreamax »), `fin_musique: false`, fin de musique recalée à la main.
