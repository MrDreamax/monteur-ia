# DA visuelle par refsheet (méthode principale, validée en test le 12/10/2026 ; branchée dans le Style Lab client le 16/10 : `outils/style-lab/STYLE-LAB.md`)

Le client ne remplit rien : on lui MONTRE 4 DA avec son propre visage, il clique sur celle qu'il préfère.

1. **Refsheet** depuis sa rush face cam (déjà envoyée) : 3 images nettes, expressions différentes.
   `ffmpeg -ss <t> -i <rush> -frames:v 1 -vf "crop=...,scale=1024:-1" ref/refN.jpg` (le visage bien centré, pas flou).
   Une face cam ne donne que la face : ça suffit, le visage a bien tenu au test (3 réfs de face).
2. **Upload** Higgsfield : `media_upload` (3 fichiers) → `curl PUT` → `media_confirm`.
3. **4 DA** en 1 lot : `generate_image_batch`, modèle `gpt_image_2_5`, 9:16, les 3 réfs en `image_references`.
   Prompt : « Exact same man/woman from the reference photos (same face, glasses, hair), talking to camera, chest-up, vertical framing, head in the upper middle with space above the head » + ambiance + « Photorealistic, natural skin texture, keep identity exactly. No text, no logos, no floating objects, no neon, no glow. »
   Les 4 par défaut : Premium sombre · Cinéma chaud · Clair épuré · Énergique coloré (aplats de couleur au mur, lumière du jour : JAMAIS de néon ni d'objets qui volent, refusés le 13/10). Adapter à sa niche. Prompts testés le 16/10 : `livrables/style-lab-client-test/` (planche `da-visuelle/planche.jpg`).
   **Coût mesuré : 0,25 crédit l'image → 1 crédit les 4.**
4. **Planche** : télécharger les 4, `hstack` en une image, vérifier le visage. Le client choisit dans le Style Lab (section « Ton ambiance »).
5. **Vidéo** (optionnel, seulement la DA choisie) : `kling3_0` std 5 s sans son = **6,25 crédits** (25 images). `seedance_2_5` = 15 crédits : non.
6. **Fiche** : écrire `da/<prenom>.json` (modèle `cyril.json`) en tirant les couleurs de l'image choisie (dégradé `list`, `halo`, `glow`) + `broll.prompt_higgsfield` = l'ambiance de la DA choisie.
   Fait tout seul par `round.py lock` ; polices, couleur, musique et rythme se choisissent aussi dans le Style Lab. `QUESTIONNAIRE.md` = seulement la légende.

Vérifier : le visage est-il le sien sur les 4 ? Sinon refaire avec d'autres réfs AVANT de montrer au client. Un client qui ne se reconnaît pas = pire que pas de DA.
