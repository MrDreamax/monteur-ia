# FACE CAM · degré 1 : SOUS-TITRES (validé par Cyril le 16/10, « nickel »)

Lu après `SKILL.md`. Le plus rapide : conseil court, volume (7 → 14 reels/sem).
Réf : `~/Documents/Stratosphere/style-lab/face-cam-minimaliste/soustitres-metaverified-v1.mp4`.

- Socle de `SKILL.md` : étapes 1-3 (cadrage, transcription, dérush), SES sous-titres verrouillés (Montserrat + mot fort serif, jamais changés), musique Epidemic accordée à la vidéo, étape 7 (vérifier).
- **plan.json** = `cam`, `words`, `fixes`, `keywords` (mots forts), `music`, **`"zoom": false`**. Rien d'autre : pas de hook, pas d'image, pas de B-roll, pas de SFX, pas d'image générée. Seule option : un `title` si la vidéo le demande (conf du 16/10, redemandé ; avec titre = pas de mots forts), à proposer dans le plan.
- 0 SFX tout seul : sans `hook`, chiffres ni cartons, `build.mjs` n'écrit aucun son dans `cues.json` (vérifier la liste affichée par `mix.py`).
- Les règles experts d'événements (règles 3-4 de `regles-experts.md` : 1 événement au hook, 1 changement toutes les 8-15 s) ne s'appliquent PAS à ce degré : choix de Cyril.
- Sauter la fiche univers, les B-rolls, les images, le calage (`match_look`, `univers_check`) et `matte.py`.
- Note /10 (`note-10.md`) : critères 4, 5, 7 = sans objet.
