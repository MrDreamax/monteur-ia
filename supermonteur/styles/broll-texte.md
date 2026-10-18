# B-ROLL + TEXTE (TOUT VALIDÉ et FIGÉ par Cyril le 16/10, v4 : ne plus y toucher sauf demande)

Lu après `SKILL.md`. 5-7 s, 1 plan (2 max) où la personne est EN ACTION, du texte AU-DESSUS DE LA TÊTE, musique, zéro voix. Le spectateur lit pendant que la vidéo tourne en boucle (Meta compte les relectures dans le temps de visionnage). Format à vues (Ronny Mitchell : vues 10/10, cash 3/10 ; Modern Millie : 4 à 9 abonnés pour 1 000 vues) : pour un client qui veut de la portée. **Pour Cyril lui-même, sa stratégie v2 dit non.** Fiches : Brain `02-Formations/experts-broll-texte.md` (montage) et `02-Formations/experts-copy-broll-texte.md` (copy, avec les décisions de Cyril en tête).
Pas de dérush, de sous-titres, de `build.mjs` ni de `mix.py` ici : tout passe par `brolltexte.py` (texte dessiné avec le Chrome de HyperFrames).

## Règles Cyril 16/10
- **Texte TOUJOURS au-dessus de la tête**, 2 lignes (3 MAX), chacune sur UNE ligne. Police de la DA en majuscules blanches ; le mot fort en serif italique (124 px seul sur sa ligne, 96 px s'il partage la ligne). Une ligne trop longue rétrécit jusqu'à 44 px, au-delà le script refuse (≈ 28 caractères max par ligne) : raccourcir.
- **CTA facultatif** (la 3e ligne n'est pas forcément un CTA) ; s'il y en a un : **EN BAS**, séparé du texte (bas du bloc à 1 420 px).
- **Jamais de ponctuation en fin de texte** (ni point, ni « ? », ni « ! ») : le script la retire de chaque ligne et du CTA, l'emoji final reste.
- **Contraste** : fond clair ou chargé sous le texte (85e centile > 140/255 ou écart > 45) → **voile noir léger en haut** (dégradé 50 % → 0, comme les titres-questions), tout seul. `"veil": true / false` pour forcer.
- **3 intentions qui performent** (ce que Cyril voit sur les B-rolls qui marchent), une par reel :
  - **Émotion = une CITATION** : une vraie phrase de quelqu'un, l'auteur pas forcément nommé à l'écran, SOURCE VÉRIFIÉE (Brain `08-Conseillers`, fiches experts ; jamais une citation de mémoire ni une attribution douteuse) ; pas de CTA ; la légende raconte l'histoire derrière la phrase (et peut nommer l'auteur), termine par « Enregistre-le pour… ».
  - **Aide en commentaire** (remplace le débat) : le texte invite à demander de l'aide en commentaire (« Tu bloques sur ta bio / Colle-la en commentaire ») ; en bas la promesse (« Je réponds à chaque bio ») ; la légende dit quoi poster et ce qu'on y répond. La promesse doit être TENUE : c'est la personne qui répond elle-même (l'humain envoie).
  - **Valeur en légende** (VALIDÉE « nickel ») : le texte promet un contenu concret (« 3 phrases à copier… ») ; en bas « Lis la légende 👇 » (valable ici, même si les experts le classent F seul) ; la légende LIVRE tout (3 points concrets), termine par « Enregistre ce post… ». Pour générer des leads : « Commente MOT » à la place (15 à 25 fois plus de commentaires, mot lié à une ressource qui EXISTE).
- **Style `da` par défaut** (VALIDÉ). Style `natif` (bandeau blanc d'Instagram) seulement si le client le demande.

## Le Copywriter (étape OBLIGATOIRE avant le montage ; copy « Ta première vie, c'est ta preuve » refusé, 4,3/10)
Lire `experts-copy-broll-texte.md` (décisions de Cyril, règles §2 à §5, 18 patrons §6, grille §7) + la voix de la personne (Cyril : Brain `00-Moi/voix-contenu.md` ; client : `legende` dans `da/<client>.json`) + sa cible.
1. Écrire **10 variantes** réparties sur les 3 intentions, chacune sur un patron différent : POUR QUI en 2 s, une émotion ou une question qui reste ouverte, du concret. Faits vrais seulement (Cyril : +120 pros accompagnés, 6 ans de data), jamais de promesse de revenu, pas de « peut-être », rien qui contredit la stratégie de la personne.
2. **Noter** avec la grille (Clarté, Émotion/Curiosité, Concret, Pour moi, Lisibilité, Pont vers la légende, Intention tenue, Voix, 0-10) : garder si moyenne ≥ 7,5 ET Clarté ≥ 5 ET Émotion/Curiosité ≥ 5. Tableau dans `copy.md` du dossier.
3. **Légende** (60-110 mots, `anti-ia` en dernière passe) : 1re ligne = un 2e hook (≤ 125 caractères visibles avant « plus ») qui NE répète PAS l'écran ; paragraphes de 1 à 3 phrases ; preuve vraie ; UN seul geste à la fin.
4. La **meilleure de chaque intention** = 3 reels : Cyril choisit ; chez un client, on livre les 3 (Trial Reels).

## Montage
- Plan = SES vrais B-rolls, la personne EN ACTION (écrit, travaille, téléphone, marche), léger mouvement ; jamais un plan figé ni un plan où elle parle (bouche sans son). Avec de la place au-dessus de la tête de préférence. Stable (`"from": "auto"` = `broll.py steady`), brut, **jamais de filtre** (les experts conseillent un « fade » : Cyril a dit non). Rien qui colle → Pexels. Jamais d'IA avec un visage.
- **Placement automatique** : le script mesure le haut de la tête sur tout le plan (5e centile), pose le texte entre 300 px et la tête - 70 px ; pas assez de place → le plan descend (480 px max) et le haut de l'image est prolongé en fondu (« place rajoutée » validée en montage viral). Pas de visage (de dos, mains, lieu) → texte en haut de la zone sûre. `"y"` force le centre du bloc si besoin.
- Musique Epidemic émotionnelle, `EditRecording` à la durée EXACTE du plan avec `loopable: true`, wav dans `music_epidemic`. Musique seule à -14 LUFS (gain mesuré, limiteur -2 dBTP).
- Republier la même vidéo : changer au moins les 3 premières secondes (plan ou texte), sinon Instagram la marque comme doublon.

## Lancer
1. Copywriter → `copy.md`. Plans : `python3 $S/broll.py search <action>` (écrit, ordinateur, telephone…) + planche d'images.
2. Musique : `SearchRecordings` (émotion, `vocals: false`) → `EditRecording` (`targetDurationMs` = durée du plan, `forceDuration`, `loopable`, `WAV`) → `DownloadRecordingEdit` → `curl` dans `music_epidemic`.
3. **plan.json** (un dossier par variante) :
```json
{"brolls": [{"src": "<chemin absolu>", "from": "auto", "dur": 6}],
 "text": {"lines": ["3 phrases à copier", "dans ta bio de coach"], "strong": "bio de coach", "cta": "Lis la légende 👇"},
 "style": "da", "music": {"src": "<wav Epidemic loopable>"}, "caption": "<légende>"}
```
(`"cta"` facultatif ; `"da": "da/<client>.json"` facultatif : par défaut la DA de `config.json` `client`, sinon Cyril.)
```bash
python3 $S/brolltexte.py plan.json      # place au-dessus de la tête + texte + CTA + musique -> final.mp4 + legende.txt (~30 s)
```
4. Vérifier : planche à 1, 3 et 5 s (texte au-dessus de la tête à chaque instant, CTA hors des mains si possible, rien hors zone), `ebur128` ≈ -14 LUFS, début à 0 s, la fin enchaîne sur le début sans saut.
Tests (16/10) : `~/Documents/Stratosphere/style-lab/broll-texte/v4-E` (citation de Bezos, 8,4), `v4-A` (aide en commentaire, 8,6, voile auto sur le tableau), `v4-V` (valeur, 8,6, VALIDÉE, place rajoutée 140 px + voile) ; copy dans `copy-v4.md`.
