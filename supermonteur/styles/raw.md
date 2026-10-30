# STYLE MINIMALISTE : clip, FAQ, selfie (style 2 des 5 styles seuls, 26/10 ; ex-« raw »)

Lu après `SKILL.md`. Le montage le plus simple : **titre ou question qui RESTE à l'écran jusqu'à la fin + sous-titres + musique.** Rien d'autre : pas de mots géants, pas de cartons, pas de B-roll, pas d'animation.
Réfs validées (22/10, avant le nom « minimaliste ») : IMG_6798 « Comment mieux parler en face caméra ? » v2 et IMG_6799 v2 (voir `feedback.md`).

1. Étapes communes de SKILL.md (transcription, dérush serré), MAIS cadre d'origine : `--vf "scale=1080:1920:flags=lanczos,fps=30"` au dérush, PAS le `vf` de `cadre.py` (27/10 CAM20062 puis 28/10 CAM20058 : le cadre serré met les cheveux dans le titre qui reste toute la vidéo). Avant le rendu : 1 image avec une ligne à 280 et 470 px, le haut de la tête doit être sous 470.
2. **plan.json** : champs communs + `title` qui couvre toute la vidéo :
   `"title": {"l1": "Comment mieux parler", "l2": "en face caméra ?", "start": 0, "end": 999}` (le moteur coupe à la durée du clip). FAQ = la question posée, mot pour mot. Clip = le sujet en 2 lignes. Jamais de virgule, point ni deux-points.
   Pas de `keywords`, `bigwords`, `numbers`, `lists`, `brolls`.
3. **Musique obligatoire** (tous les styles en ont une, 26/10) : règles de SKILL.md (28/10 : dossier `music_reels` des réglages seulement, sinon bibliothèque SUNO de son disque externe, continue d'un seul passage, montée calée sur la phrase forte).
4. Taille et police du titre et des sous-titres = la DA du setup (`titleSize`, `subSize`, `fonts`), jamais réglées au montage.
5. **Par défaut (29/10) : `python3 $S/express.py .`** (~1 min : titre + sous-titres dessinés puis posés par ffmpeg, même mix, même Gardien). Seulement s'il sort en code 2 (mot fort, B-roll…), le moteur normal :
```bash
node $S/build.mjs --plan plan.json --out index.html && node $S/zones.mjs .
npx --yes hyperframes@0.8.149 render . -q high
python3 $S/mix.py plan.json renders/<x>.mp4 clip.mp4 final.mp4
```
6. Vérifier : le titre est là de la 1re à la dernière image, ne touche ni la tête ni les sous-titres, hors zones mortes.
