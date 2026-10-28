---
name: carrousel
description: Le Carrousel. Carrousel Instagram (1080x1440) style Apple - fond blanc, vraies photos de l'utilisateur (ou images de son reel) + illustrations 2D SVG, jamais d'image IA. Passe par l'appli SuperCarrousel. Livre PNG + légendes, ne publie jamais sans son OK. Use when "carrousel", "carousel", "fais-moi un carrousel", "carrousel de la semaine", "transforme ce reel en carrousel", "carrousel sur X", "carousel maker".
---

# Le Carrousel : une grande idée, des slides, la DA de SuperDA

**Premier geste de toute demande de carrousel : ouvrir SuperCarrousel** (`bash ~/Documents/SuperApps/supercarrousel/lancer.sh` puis http://localhost:8797 dans le navigateur intégré), avant toute question.
Mode d'emploi côté Claude : `~/Documents/SuperApps/supercarrousel/README.md` et `python3 sc.py a-faire` (dans ce dossier).

## Carnet d'apprentissage
- Avant de commencer : lis `retours-client.md` (dans ce dossier, absent = rien à lire). Ses règles passent AVANT ce fichier.
- Si l'utilisateur corrige, note ou refuse ton travail : ajoute UNE ligne dans ce carnet, `JJ/MM/AAAA · correction · ce qui n'allait pas → règle`. Dis-le en une ligne : « Noté dans mon carnet : ... ».

## Ce que fait SuperCarrousel
- 3 départs : **Un reel** (fichier ou lien Instagram / TikTok / YouTube : images + texte du reel) · **Un carrousel à reprendre** (garder son idée et son ordre, refaire DA, mots, photos) · **Une idée** (écrite ou dictée).
- Le serveur lit le reel, Claude écrit la description (texte des slides + 4 légendes), le serveur rend chaque slide avec ce moteur.
- Écran de retours : un retour accroché à une slide, « Suivant : corrige mes retours » → Claude écrit la version suivante.
- La DA vient de SuperDA (`~/Documents/SuperApps/superda/da.json`, onglet Carrousels).
- Publier : Instagram, TikTok (photos), Facebook, LinkedIn (document), jamais YouTube. Sans Metricool : Télécharger seul. `config.json` `"mode_essai": true` (défaut) = rien ne part.

## Le modèle style Apple
- Description avec `"style": "apple"` → `scripts/carrousel.py` appelle `scripts/apple.py` (rendu local par Google Chrome, ~20 s pour 8 slides).
- Exemple : `exemples/exemple-apple.json` (FICTIF : remplace les photos par les siennes). Types : `cover` (kicker, title, photo, note), `photo` (title, body ou steps ; `"pop": false` si la personne est petite dans l'image), `art` (title, body, steps, ou `cta` + `cta_q` + `cta_line` pour la fin en 3 bulles). Note manuscrite : `note` + `note_pos`.
- Le détourage ne garde que la tête au-dessus de la photo. Vérifie le haut de chaque slide photo en grand.

| Élément | Règle |
|---|---|
| Format | 3:4, 1080x1440, 6 à 10 slides |
| Visuel | photo ou dessin selon l'idée de la slide (couverture = photo) |
| Photos | VRAIES photos de l'utilisateur ou images de son reel. Jamais d'image générée par IA |
| Illustrations | 2D motion design en SVG (`scripts/art.py`) : fond blanc, grand cercle clair, aplats, 2 à 4 petits éléments déco |
| Slides | 1 idée par slide : titre + 1 phrase courte (ou liste de 3 lignes). Jamais de pavé, jamais de ponctuation seule en fin de ligne |
| Fin | « Commente MOT » + la ressource promise (qui EXISTE). Flèche de swipe partout sauf sur la dernière |

## Le texte
- Une seule grande idée, qui touche un problème de sa cible.
- Couverture : écris 10 titres (résultat, objection ou temps, chiffre si possible), garde le meilleur. Elle et la slide 2 doivent accrocher seules.
- Chaque slide ouvre la suivante (« … », question, « mais »). Une slide de preuve vers la fin, seulement avec une preuve VRAIE qu'il t'a donnée. Rien d'inventé.
- Légende : une par réseau, courte, finit par le CTA.

## Pas de photos ? Les images viennent d'un reel
- Vidéo : le RUSH d'abord (zéro texte sur l'image). Le reel fini seulement s'il n'y a rien d'autre.
- `python3 scripts/reel2frames.py <video> <out>/_reel --words <words.json>` : 16 images nettes + `00-candidates.jpg` (planche) + `texte.txt`.
- Garde 4 images variées (gestes différents, pas les yeux fermés, pas la main devant le visage).

## Les illustrations
- `scripts/art.py` : `apples_grid`, `copies`, `stairs`, `chart_up`, `chat`, `checklist`, `camera`, `script_long`.
- Sujet nouveau : une nouvelle fonction dans `art.py` (mêmes couleurs, `frame()`, dessin entre y 80 et 820) ajoutée à `ARTS`, ou un `.svg` à côté de la description (`"svg": "mon-dessin.svg"`).

## Vérifier (jamais livrer sans)
Texte lisible, pas de mot seul sur une ligne, illustration qui ne touche pas le texte, photo qui colle à la slide, bon mot-clé à la fin, PNG en 1080x1440.

## Ne jamais
- Publier ou programmer sans son OK (2e clic à l'écran, ou OK dans le chat).
- Une image générée par IA, une preuve inventée, une ressource qui n'existe pas.

## Technique
- Il faut Google Chrome et Python 3 avec `pillow numpy onnxruntime scipy opencv-python` (installés par `install.sh`).
- Détourage : modèle du skill supermonteur (`~/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx`, téléchargé par son setup).
- Couleurs par défaut : `scripts/marque.py` (bleu et blanc) ; la DA de SuperDA passe par-dessus.
