# GREEN SCREEN (ex « Toi + une source ») : green screen, réaction (validé par l'utilisateur le 14/10, v8)

Lu après `SKILL.md`. La **démo filmée** (écran du Mac filmé + zooms 4K) a été SUPPRIMÉE par l'utilisateur le 16/10 (« ça sert à rien ») : ne plus jamais la proposer (le code de `source.py` reste, il est partagé).
Réf VALIDÉE : `<dossier>/style-lab/toi-plus-source/greenscreen-metaverified-v8.mp4` (1 visuel par phrase, article Higgsfield au hook, images réalistes en zoom progressif, motion design max 2 d'affilée, zéro visage, musique dynamique).

**Zones mortes (16/10, build.mjs + source.py)** : chaque bloc motion est recalé à 280 px (boîtes mesurées dans `MOBOX`), jamais plus bas qu'avant ni sous 890 px (air au-dessus des sous-titres) ; s'il manque de place il est réduit (dm, chart, profile -16 %, bars -17 %, ring -12 %), sinon il descend simplement (compare, webapp, versus, badge) ; `connect` glisse depuis un cache à 65 px ; react = vidéo en 950 px entre les marges, crédit à 274 px ; bulle à 65 px du bord. **Nouveau type de bloc = mesurer sa boîte et l'ajouter à `MOBOX`**, puis `zones.mjs`.

Il parle face cam pendant toute la vidéo : la source remplit l'écran pendant les phrases qui en parlent, face cam seule le reste. 3 mises en page (`"layout"`) : `greenscreen` (la personne détourée en bas au centre devant la source, ombre douce ; **DÉFAUT**, « le détourage, c'est super »), `split` (source en haut, visage en bas), `bubble` (source plein écran + visage dans une bulle). Sources qui défilent doucement de `y0` à `y1`, ou une vidéo (`"from"`). Sous-titres au-dessus de la tête détourée ; sur fond clair = ombre renforcée automatique (zone `light`), jamais de bande grise (retirée le 14/10).

## Règles de découpe (14/10, après v7 : ce sont elles qui gagnent)
- **UNE phrase** (jusqu'au point / point d'interrogation, pas la virgule) **= UN seul visuel** : image Higgsfield OU motion design OU article.
- Jamais 3 motion design d'affilée (2 max).
- L'**« article » seulement pour le HOOK**, généré sur Higgsfield (titre-question, aucun média réel ni visage, aucune marque de presse). Plus de vraies pages ni d'articles réels au milieu (les « vraies pages qui défilent » des v2-v4 sont remplacées par cette règle).
- **ZÉRO VISAGE** dans toutes les sources : jamais de B-roll de lui ni d'image avec un visage derrière son détourage (v3 rejetée : « deux visages, on ne sait pas où regarder »), jamais de mannequins ni de photos d'auteur.
- Musique Epidemic DYNAMIQUE et émotionnelle (v8 : trap sombre « JUMBOTRON », 120 BPM ; ex. « Bang Bang », « Ultimo »).
- Pas de payant (Artlist) tant que SSD + Higgsfield + Pexels suffisent.

## Images d'idée (Higgsfield)
- Modèle `gpt_image_2_5` (0,25 crédit), photo RÉALISTE et captivante (« candid realistic photo, 35mm, natural light, film grain, not CGI »), pas une nature morte de studio (v4 « encore fades »). Ambiance = celle de la vidéo (matières bois foncé, cuir, laiton, lampe chaude, coche bleue si ça colle). Fond clair de préférence pour que le détourage ressorte.
- Objets dans le TIERS HAUT (sinon cachés derrière lui), AUCUN visage ni main, zéro chrome / néon / texte.
- `"push": 0.10` = zoom PROGRESSIF, `"push": -0.10` = dézoom progressif, `"cy"` = point visé (0 haut, 1 bas) ; JAMAIS de zoom brusque (« punch » ignoré, 14/10).
- Pages et images sont dessinées par HyperFrames (bloc `img` automatique) et non par ffmpeg : ffmpeg bouge au pixel entier = saccades (« pas fluide », mesuré 14/10 : à-coups 1,18 px/image → 0,11 px).

## Motion design HyperFrames (style VALIDÉ 14/10 « nickel », en mettre plus)
`{"src": "@motion", "type": ..., "start", "end"}` ; fond = univers de la vidéo (pièce sombre, LED bleue), lui détouré devant, zéro visage, mouvements expo sans rebond. Types dans `MOTION` (build.mjs) :
- `dm` (boîte de messages, le message avec la coche passe en tête à `highlight`)
- `chart` (courbe « ce que tu espères » qui monte vs « la réalité » plate)
- `badge` (coche qui se dessine + jauge `label` + 5 étoiles)
- `connect` (2 tuiles `left`/`right` qui se relient, données qui circulent, pastille `pill` à `pillAt`)
- `versus` (« Pour qui ? » : la mauvaise raison barrée, la bonne s'allume)
- `profile` (fiche profil sans photo, la coche bleue apparaît à côté du nom)
- `compare` (UNE phrase « pas plus de X, en revanche Y » : barre X à plat, barre Y qui monte à `pivot`)
- `webapp` (astuce prix : appli « + frais des stores » vs PC « prix réduit », `webAt` / `appAt`)
- `ring` (anneau qui se remplit jusqu'à `value` % avec le compteur au centre, `suffix` défaut « % », `label` en serif italique dessous ; pour UN pourcentage dit à voix haute)
- `bars` (`values` = 3-5 barres, `labels` sous chaque barre, `title`, `value` + `prefix`/`suffix` = chiffre qui compte ; les barres grises montent, pause 0,35 s, puis la dernière en accent monte avec son chiffre ; pour une progression « avant → maintenant »)
(`ring` et `bars` ajoutés le 14/10, greffe GitHub, démo `livrables/greffe-motion-github/demo-motion-greffe.mp4`.) Ajouter un type quand une idée revient.

## Options (pas dans la v8 validée, seulement si l'utilisateur le demande)
- **Hook react** (né sur la démo, 14/10) : 3-5 s d'une vidéo du web sur le sujet (`yt-dlp --download-sections "*0:00-0:06"`, accord de l'utilisateur avant tout téléchargement), `"fit": true` (vidéo entière en haut, fond bleu nuit, muette, `"credit"` = source à l'écran, `"pre": "delogo=..."` pour flouter une bulle webcam) ; pas de titre-question en même temps (doublon).
- Capture d'une vraie page : `node $S/shoot.mjs out.png URL [hauteur max]` (largeur mobile x2 = 1080 px, bandeau cookies REFUSÉ, jamais de contrôle anti-robot contourné) ; bas de page impossible à faire défiler jusqu'en haut → recadrer l'extrait dans une image 1080x1920 ; flouter les mini-photos d'auteur.

## Lancer
1. Dérusher la cam (étapes 1-3 de SKILL.md) → `cam.mp4` + `words.json`.
2. Planche 1 i/s de la cam ; pour chaque phrase qui montre quelque chose, UN visuel (image, motion, article au hook).
3. **plan.json** (title / keywords, fixes, cta, music) + `"source": {"cam": "cam.mp4", "layout": "greenscreen", "items": [{"src": "src/page.png", "start", "end", "y0", "y1"}, {"src": "@motion", "type": "versus", "start", "end"}]}`
```bash
python3 $S/source.py compare plan.json A B   # (si la mise en page n'est pas choisie) les 3 côte à côte sur A-B s -> comparatif_mises_en_page.mp4
python3 $S/source.py layout plan.json        # clip.mp4 + cam / subY / subYAt / zoom:false ; green screen = détourage auto de toute la cam (~10 s par s)
node $S/build.mjs --plan plan.json --out index.html && npx --yes hyperframes@0.8.149 render . -q high
python3 $S/mix.py plan.json renders/<x>.mp4 cam.mp4 final.mp4
```
4. Vérifier la 1re image de chaque passage source (planche à 2 i/s) : rien de caché derrière lui, zéro visage.
Test moteur : `<sorties>/montage-greenscreen-metaverified-test/final.mp4` (v4, anciennes versions en `final-v1/v2/v3.mp4`).
Bug corrigé (14/10) : jamais de `-ss` sur la vidéo détourée (webm VP9 + transparence) : la 1re image sortait sans alpha (rectangle noir) → décodage depuis le début + `trim`.
Limites : le visage est filmé large → détouré en 0,66 de la hauteur ; pas encore de vraie « réaction » à une vidéo avec son d'origine (mixage 2 voix) ; captures = pages publiques seulement (rien derrière un login).
