# Style Lab client : la DA de montage choisie sur SA 1re rush (Cyril 16/10 : 1 seul tour)

Quand : 1er lancement chez un client (`mode-client.md`), après les connecteurs et `setup.sh`. Le client vote sur de vrais rendus de lui, ça écrit `da/<prenom>.json` tout seul.
Durée : ~25 min dont ~10 min de rendu (8 variantes). Coût : ~1 crédit Higgsfield (4 images), 4 musiques Epidemic sur SON compte.
5 sections, 1 seule variable par carte : **Ton ambiance** (4 images de lui), **Tes polices** (4 couples), **Ta couleur** (2 de son rush + sa marque + bleu maison), **Ta musique** (4 émotions), **Ton rythme** (posé / nerveux).
Le reste est réglé par la maison et ne se vote pas : sous-titres au col, mot fort seul à l'écran, zones mortes Insta, musique émotionnelle Epidemic, zéro néon / chrome.

## 1. Matière (dossier `~/Documents/Montage/STYLE-LAB/`)
1. Il glisse sa 1re rush. Étapes 1-3 de `SKILL.md` (cadrage, transcription, dérush) → `clip.mp4` + `words.json`.
2. Lire `words.json` : choisir un passage de **8-12 s** qui finit sur une phrase entière, avec **1 mot fort** et **1 punchline** de 2-3 lignes (SES mots, dits dans le passage). Noter les corrections Whisper (`fixes`).
3. **Ambiance** (méthode `da/DA-VISUELLE.md`) : 3 images nettes de son visage tirées du rush → `media_upload` + `curl PUT` + `media_confirm` → `generate_image_batch`, `gpt_image_2_5`, 9:16, les 3 réfs en `medias`, 4 prompts (Premium sombre, Cinéma chaud, Clair épuré, Énergique coloré). Chaque prompt finit par « Photorealistic, natural skin texture, keep identity exactly. No text, no logos, no floating objects, no neon, no glow. » **Vérifier que c'est son visage sur les 4** (planche), sinon refaire avec d'autres réfs AVANT de lui montrer. Télécharger, réduire en JPG 720 px.
4. **Musique** : sur SON compte Epidemic, 1 morceau par émotion (motivation qui monte, dark cinématique, cordes cinéma, émotion piano), `vocals: false` → `EditRecording` à la durée du passage (`forceDuration`, WAV) → `DownloadRecordingEdit` → `~/Documents/Montage/MUSIQUE/` + 1 ligne dans `_LICENCE.txt`.
5. **Sa marque** : demander sa couleur en 1 ligne (code couleur, ou la tirer de son logo / profil). Aucune → la carte devient « Noir et blanc ».

## 2. Fabriquer le round (~10 min)
```bash
python3 ~/.claude/skills/supermonteur/outils/style-lab/round.py build --client <prenom> --clip clip.mp4 --words words.json \
  --start <s> --end <s> --keyword <mot fort> --card "*ligne serif|ligne|*ligne serif" --card-at <s> --card-end <s> \
  --fixes '{"faute": "correction"}' --brand "#RRGGBB" \
  --music m1.wav m2.wav m3.wav m4.wav --music-labels "Motivation|Dark cinématique|Cordes cinéma|Émotion piano" \
  --da-images da1.jpg da2.jpg da3.jpg da4.jpg --out round
```
Sortie : `round/round.json` (sections + cartes + ce que chaque carte règle) et, par carte, `full.mp4` (avec le son) + `preview.mp4` (muet, léger), plus `round/planche-<section>.jpg`. Regarder les planches avant de publier : sous-titres lisibles, carton qui tient, rien hors zone.

## 3. La page de vote
1. Copier `outils/style-lab/style-lab.html` dans le dossier de travail, la publier en artifact : `capabilities: {"db": {}, "user": {}, "assets": {}}`, icône `palette`. URL dans `STYLE-LAB/style-lab.url`.
2. Uploader dans les assets de l'artifact (`asset: true`, `file_paths` par lots de 25) : `preview.mp4` + `full.mp4` de chaque carte vidéo, l'image de chaque carte ambiance. Garder l'id de chaque fichier.
3. Écrire la base en un `ArtifactData` `batch` : `round/current` = `round.json` → `round` ; `sections/<id>` = chaque section sans son id ; `cards/<id>` = `{section, label, desc, kind, preview: <id asset>, full: <id asset>, sound, order}` (sans `meta` ni `file_*`) ; `profile/current` = `{handle: <son pseudo Insta>}`.
4. Vérifier : `ArtifactData list` de `cards` = le nombre de cartes de `round.json`. Puis lui envoyer le lien en 1 ligne : « Une carte "Garder" par section, puis "Envoyer mon avis", puis écris done ici. »

## 4. Verrouiller (quand il écrit « done »)
1. `ArtifactData list` de `submissions` → la plus récente dans `STYLE-LAB/vote.json` (0 soumission : lire la collection `notes`, et lui demander en 1 ligne s'il a fini).
2. `python3 .../round.py lock --round round/round.json --vote vote.json --client <prenom>` → `da/<prenom>.json`.
   Code 3 = une section a 0 ou plusieurs « Garder » : la trancher en QCM dans le chat (option recommandée = sa carte « Peut-être », sinon la 1re = la maison), puis relancer avec `--pick section=carte`.
3. Lire ses notes (le script les affiche) : un réglage demandé (« plus gros », « plus foncé ») → l'appliquer dans la fiche (`subSize`, `colors`…) et le dire en 1 ligne.
4. Ce qui ne se voit pas (légende : tu / vous, emojis, CTA) : `da/QUESTIONNAIRE.md` en 3 clics.
5. Copier la fiche dans `retours-client.md` (1 ligne : « Style Lab du JJ/MM : … »).

## Plan B (la page ne garde rien chez lui : elle affiche « Cette page ne joint pas Claude »)
Montrer `round/planche-<section>.jpg` une par une et poser 1 QCM par section dans le chat (les vidéos avec son : lui donner le chemin de `full.mp4`), puis `lock` avec un `--pick` par section (sans `--vote`).
