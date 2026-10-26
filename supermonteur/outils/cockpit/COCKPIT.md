# Le Cockpit v3 « Claude te guide » (23/10/2026) : la page où la personne retouche le reel que Claude a monté

Remplace **Style Lab ET Cut Notes** (décision de l'utilisateur, 23/10). Maquette validée en 2 rounds (Brain `01-Projets/cockpit-montage.md`,
images `Stratosphere/livrables/cockpit-montage/complet-r1/C.png`, `complet-r2/1c.png` et `2b.png`). Ancienne page v2 (panneau de cartes)
et ancien serveur : `supermonteur/_backup/2026-10-23-cockpit-v2/`. Look Apple clair. Utilisable par un client SANS bibliothèque de B-rolls
ni de photos, ni de musique.

**Règle 23/10 : jamais d'étalonnage ni de traitement du son du rush.** Un look = polices + couleur du texte + rythme. Rien d'autre.

## v5 (23/10 soir) : ÉTAPE 1 = TIMELINE façon Premiere Pro = « DERUSH LAB »
**Décision 23/10 ~20h15 (Cyril) : cette timeline s'appelle Derush Lab, outil INTERNE (jamais pour les clients ni le kit), qui sert
EXCLUSIVEMENT à dérusher une vidéo.** Séparation « dérush seul » à faire (Brain 01-Projets/cockpit-montage.md, Reprise 23/10 ~20h15).
 (prime sur la v4 ci-dessous pour l'étape 1)
- **DERUSH LAB = `cockpit.py <dossier> --port <p> --lab` (codé le 23/10 ~23h31, maquette `livrables/cockpit-montage/derushlab-r1/A.png`
  choisie par Cyril)** : la timeline SEULE. En haut « Derush Lab · titre · 1:00 → 0:34 », plus d'étapes, ni Tout auto, ni Exporter
  (`body.lab`). Pas besoin de `plan.json` (dossier = words_rush.json + 1er dérush derush.py + cut.words.json → words.json + cockpit.json
  + cadre.json). Bouton « ✓ Valider le dérush » → `/api/valider` : derush.py `--plages` si la timeline a changé (clip.mp4), puis
  **`gardien.py <dossier> --derush`** (~5 s : mot coupé, respiration, plans ≥ 2 s, micro-coupure, silence, flash ; rapport
  `gardien-derush.json`, log `_cockpit/gardien-derush.log`) ; `cockpit-etat.json` `lab` = {plages, ok, quand}. Tout vert = message
  « ✅ Dérush validé » + bouton vert « ▶ Revoir le dérush » ; un rouge = « ❌ 1 point à régler : … » ; une retouche après = à revalider.
  Testé sur une copie d'IMG_6850 : 20 s, 6/6 vert, clip.mp4 h264 1080x1920 33,8 s, 0 erreur dans la page. Sauvegarde avant :
  `supermonteur/_backup/2026-10-23-derushlab-avant/`.
Demande de Cyril : « une timeline pour contrôler précisément ce qu'on coupe / garde, 1er dérush déjà fait par l'IA, plus de texte ».
Maquettes : `livrables/cockpit-montage/timeline-r1/` (A, B, C) puis `timeline-r2/1.png` VALIDÉE + son `timeline-r2/courbe-1-bourse.png`
(« courbe depuis le bas » finition Bourse, MAIS « exacte, très précise »). Sauvegarde avant v5 : `supermonteur/_backup/2026-10-23-cockpit-v4/`.
- **Écran** : la conversation se range (classe `.main.e1`) ; en haut à gauche le téléphone joue le RUSH en sautant les coupes ;
  à droite la **LOUPE** = le bloc ouvert en grand (images du rush + son) avec 1,6 s autour, règle en secondes, ‹ Précédent / Suivant ›
  (de coupe en coupe), − / + (zoom ; pincer ou ctrl + molette aussi, glisser = avancer), « Tout remettre » (coupe ouverte) ou
  « Retirer ce bloc » (bloc gardé) ; en bas **le reel bout à bout** : blocs gardés à la vraie échelle, coupes en PETIT (18 / 40 / 58 px,
  image grise + son gris, « ✂ 12,2 s » rouge si des mots dedans = reprise, gris = blanc), clic sur un bloc = il s'ouvre dans la loupe ;
  tout en bas le message de Claude + « Suivant : étape 2 Style ».
- **Gestes** (loupe) : tirer dans le son = choisir un bout → barre noire « ↺ Remettre ce bout » (s'il touche du gris) / « ✂ Retirer »
  (s'il touche du bleu) / « ▶ Écouter » (le rush tel quel) ; ↵ = remettre, ⌫ = retirer, Échap = annuler ; les bords des blocs (traits
  noirs, poignée au milieu) se tirent librement jusqu'au bloc voisin (min 0,15 s) ; ← → = 10 ms (⇧ = 100 ms) sur le dernier bord ou la
  dernière poignée touchée ; clic simple = la vidéo va là ; C = « Couper ici » (1er appui début, 2e appui fin, à la barre rouge) ;
  « ↺ Remettre comme Claude » = son 1er dérush. Après chaque geste la vidéo rejoue 1 s avant / 1 s après.
- **Son** : courbe « Bourse » (trait bleu + fondu), EXACTE : 1 valeur par pixel = le PIC des tranches de 10 ms (`/api/onde`), interpolée
  seulement quand on zoome sous 10 ms/pixel ; aucun lissage. Gris = coupé. Images : `/api/planche` (`_cockpit/planche.jpg`, 2 images/s,
  54 x 96, 20 par ligne, faite au lancement après `rush.mp4`).
- **Données** : `cockpit-etat.json` `derush` = {"plages": [[a, b], ...] gardées en secondes du rush, "applique"}. 1er dérush de Claude
  gardé dans `_cockpit/segments.claude.json` (copie de `cut.segments.json` au 1er lancement v5). Un état v4 (« coupes / bords ») est
  repris tel quel depuis `cut.segments.json`. « Suivant » écrit `plages.json`, remet `drop.json` = `drop.claude.json`, efface `bords.json`
  et relance **`derush.py --plages plages.json`** seulement si ça a changé. Les reels d'essai courts suivent les mêmes plages.
- **derush.py `--plages`** : les plages remplacent tout le calcul auto (qui sert de référence) ; ce qui est remis en plus = gardé exprès
  (jamais baissé, `souffle_garde`) ; un bord posé à la main (à plus de 50 ms d'un bord auto) = coupe « serrée » : le Gardien la signale
  « à écouter » sans bloquer (fins ET débuts) ; mots hors des plages = retirés des sous-titres. Le Gardien bloque toujours un plan < 2 s :
  la timeline montre en orange un bloc gardé < 2 s.

- **Barre de lecture (23/10, maquette `livrables/cockpit-montage/barre-r1/C`, son choix « barre en rouge sur la timeline et sur la
  coupe en grand »)** : la barre rouge s'attrape et se tire dans le reel bout à bout ET dans la loupe (étiquette = l'instant du reel,
  ou « coupé ») ; la vidéo suit en pause, l'image du rush s'affiche au-dessus du doigt (reel bout à bout), la loupe suit si on sort de sa
  fenêtre. Fonctions `brancherTete`, `ovVersRush`.
- **1er dérush (23/10)** : derush.py ne coupe JAMAIS en milieu de phrase (seulement après . , ! ? … ; :) ; voir SKILL.md.
- **Gardien (23/10, IMG_6850)** : fin de mot = voix douce 6 dB au-dessus du bruit de la pièce (`queue_mot.py`) ; une coupe dans un plan qui
  bouge n'est pas un « flash » (`mouvement()` dans gardien.py) ; build.mjs : mot fort calé sur toute la ligne + marge de 12 % avec un style perso.

## v4 (23/10 soir, retours de Cyril après test) : CE QUI A CHANGÉ (prime sur le reste de cette notice)
- **Plus de Chrome** : la page s'ouvre dans la fenêtre navigateur intégrée à l'appli Claude. Serveur lancé en Bash `run_in_background`
  (macOS refuse ~/Documents aux serveurs de preview), puis `preview_start {url: "http://127.0.0.1:<port>"}` (pas de `name`).
- **2 étapes seulement : 1 Dérushage › 2 Style**, puis Exporter. L'étape 3 (moments forts : zoom, carton, mot géant, motion, B-roll)
  est SUPPRIMÉE : `plan_final` n'appelle plus `ajouter_moments` (code laissé dormant, ne plus le proposer).
- **Étape 1 = dérushage « phrase en grand »** (maquette `livrables/cockpit-montage/derush-r2/B.png`) : à gauche le téléphone joue le
  RUSH en sautant ce qui est coupé (montage virtuel, instantané) ; à droite le texte en phrases (`cockpit.json` `"phrases"` [[i, j]]
  si Claude les écrit, sinon découpage auto : reprises de `_cockpit/drop.claude.json`, mots de liaison, vrais blancs) ; dessous le son
  de la phrase choisie en grand (`/api/onde`, 10 ms, en dB) avec 2 poignées Début / Fin (←/→ = 10 ms, rejoue 1 s autour de la coupe
  au lâcher), clic sur un mot = le retirer, ⌫ = retirer la phrase, « Garder / Couper le souffle ». Choix dans `cockpit-etat.json`
  `derush` {coupes: [mots], bords: {debut: {i: t}, fin: {j: t}}} ; « Suivant » (ou Tout auto) écrit `drop.json` + `bords.json` et
  relance `derush.py --bords` seulement si ça a changé. **v4.1 (23/10, « les barres se bloquent ») : poignées LIBRES dans toute la
  fenêtre** (seule limite : 0,15 s entre Début et Fin) ; les mots de la phrase laissés dehors sont barrés tout seuls et remis quand la
  poignée revient (un mot barré à la main reste barré). Clic dans le son = la vidéo va à cet instant.
- **derush.py `--bords`** : bords posés à la main, après tout le calcul auto ; un bord au milieu d'une plage la coupe en deux ; le souffle
  gardé exprès n'est jamais baissé et le Gardien ne le bloque pas (`cut.voice.json` `souffle_garde`). Phrase retirée collée au mot
  d'avant (aucun blanc) : coupe au creux du son, notée `serrees` (Gardien : signalée « à écouter », pas bloquante).
- **Étape 2** = la vidéo habillée : style (galerie des 6 polices à la 1re vidéo seulement, sinon « Changer de style »), ouverture,
  sous-titres, musique, puis « Terminer → Exporter ». La bande ne montre plus les coupes (elles se règlent à l'étape 1).
- **Export** : seul le reel est coché par défaut. Carrousel, story et reels d'essai = proposés à la fin (« Oui, fais-les » /
  « Non merci », `cockpit-etat.json` `extras`).
- À venir : avant le rendu, choix entre 3 styles de montage (Cyril envoie 3 reels exemples).
- Sauvegarde avant v4 : `supermonteur/_backup/2026-10-23-cockpit-v3/`.

## L'écran
- **À droite, la conversation** (420 px ; à droite depuis le 23/10 : « mieux pour le contrôle » ; logo Stratosphère en haut, `logo-stratosphere.png`). Chaque bulle de Claude vient de l'état du montage, rien n'est écrit à la main :
  « J'ai monté ta vidéo : 0:42 → 0:37 » ; 1 bulle par coupe (Écouter / Remettre / C'est bon, ou Couper à nouveau si remise) ;
  l'ouverture en 3 vignettes (les `hooks`) ; les sous-titres (plus petit / plus grand, haut / menton / bas, mots forts) ; la musique
  (les émotions de `cockpit.json`, + Ajoute ta musique, Sans musique) ; puis les phrases de la personne et les réponses de Claude.
- **En bas, « Dis-moi ce que tu veux changer… »** (+ dictée) : si la vidéo est en pause, la phrase prend le timecode (pastille bleue).
  Elle part dans `cockpit-notes.json`. **Claude ne répond PAS en direct dans la page** : il lit les notes quand la personne revient dans
  son chat, corrige, puis écrit dans la note `"statut": "corrigé"` + `"reponse": "J'ai retiré le « euh » de 0:12."` : la page affiche
  « Fait ✓ … ▶ Revoir » toute seule (elle relit l'état toutes les 5 s).
- **Au centre, la vidéo** (téléphone + calques HTML) et la bande : coupes en rouge numérotées en haut, notes en bleu en bas. Barre espace =
  lecture. En pause, la **zone interdite d'Insta** (règle 16/10 : haut 270 px, bas 1480 px, côtés 65 px, 120 px à droite sous 1100 px) est en rouge sur la vidéo ; le Gardien (`zones.mjs`) bloque tout rendu avec du texte dedans. « Écouter » une coupe = le téléphone passe sur le rush (`/video/rush`) le temps du passage. Voile « Je remets le passage… »
  pendant le dérush. Pas de zone qui défile dans la page : si la conversation est longue, c'est la page qui défile, la vidéo reste en place.
- **1er lancement (ni style ni ancien look)** : « Bienvenue » + **5 lignes qui se déplient** (23/10, maquettes `livrables/cockpit-montage/perso-r1/`) :
  1 Police (ouvre la **galerie des 6 polices au centre**, en blanc), 2 Taille (titre S / M / L / XL, sous-titres 44-58 px), 3 Couleurs
  (titre ligne 1, ligne 2, sous-titres : 6 pastilles + une couleur libre), 4 Position (titre en haut / plus bas, centré / à gauche ;
  sous-titres haut / menton / bas), 5 Plus (majuscules ou minuscules, 1 à 4 mots, ombre douce / forte). La vidéo se pose pendant le titre
  et suit en direct. « Enregistrer mon style » ; ensuite « Changer de style » dans la 1re bulle.
- **Exporter = la planche des 6 contenus au centre** : reel, carrousel, story, 3 reels d'essai, un interrupteur sur chacun (sauf le reel),
  la date dessous (touche la date du reel ou d'un essai pour la changer), les réseaux du reel, « Fabriquer le reel » (puis Télécharger)
  et « Programmer N contenus ». Pendant la fabrication : une roue sur chaque carte, ✓ ou ✗ à la fin. « Revenir au montage » en haut.

## Les 3 étapes (23/10, maquettes validées : `livrables/cockpit-montage/passes-r1/A.png` + `r2-3b.png`)
- **Barre du haut : 1 Dérushage › 2 Style › 3 Motion / B-roll** (`cockpit-etat.json` `passe`). On touche une étape pour y aller.
  **⚡ Tout auto** (en haut à droite) : garde tous les conseils de Claude (coupes, ouverture, style « Ton combo » si aucun, moments
  forts, musique) et lance « Fabriquer le reel » (pas de programmation).
- **Étape 1** : la bulle du dérush (0:42 → 0:37), une bulle par coupe, l'ouverture, les notes, puis « Suivant ». Dès qu'un style
  existe (2e vidéo), l'étape 2 est verte (« Style · Condensé géant · Changer ») et « Suivant » va droit à l'étape 3.
- **Étape 2** : les 5 lignes du style (plus bas). 1re vidéo = la galerie des 6 polices s'ouvre. « Enregistrer » → étape 3.
- **Étape 3 (facultative)** (maquettes `etape3-r1/r1-a.png` liste + `r2-a.png` 3 idées de B-roll, validées 23/10) : les moments forts
  en LISTE, celui qu'on touche s'ouvre. Assez pour toute la vidéo (un toutes les 3-4 s). Claude les écrit dans `cockpit.json`
  `"moments": [{id, t0, t1, texte, mot, reco, reglage?, carton?, brolls?}]` (temps du REEL = `words.json`) ; sans eux `moments_auto`
  (mots forts puis mots longs, 3,5 s d'écart). Effets → `moments_choix`, réglages → `moments_reglages` {id: {...}}.
  **23/10 (Cyril, après test dans Chrome) : POUR TOUT LE MONDE, l'étape 3 ne propose plus que Zoom, Carton plein et Rien.**
  Mot géant, Motion design et Ton B-roll sont CACHÉS, pas supprimés (`build.mjs`, `matte.py`, `headtop.py`, `/api/biblio`, `/illus/`
  intacts). La liste vient de `cockpit.py` `CHOIX_MOMENT` (la page la lit dans `/api/etat` `effets`) ; pour les remettre : `CHOIX_MOMENT =
  TOUS_EFFETS`. Un choix ou une reco cachée devient le plus proche (`effet_permis`) : mot → carton si les 2 lignes tiennent (22 signes),
  sinon zoom ; motion et broll → zoom. `moments_auto` ne recommande que zoom / carton / rien. Le mot géant de l'OUVERTURE (hook) reste.
  Les 6 effets (3 cachés depuis le 23/10) :
  - Zoom `zoom: avant | arriere` → `plan.zooms` [{start, end, dir?}] (arrière : s'avance 1 s avant, recule sur le moment).
  - Mot géant `mot: tete | sous` → `plan.bigwords` (matte.py, derrière la tête) ou `plan.subwords` (en géant dans le sous-titre, même avec un titre).
  - Carton plein `carton: {l1, l2, fond: nuit | noir | bleu | flou}` → `plan.mini` card. Fond TOUJOURS en dégradé (jamais uni, Cyril 23/10).
  - Motion design `motion: chiffres | trait` (+ `illus` pour trait) → `plan.motions` (build.mjs). Validé le 23/10 après 5 rounds
    (`livrables/cockpit-montage/motion-r2/` motion3-F + motion5-L ; étude Jun Yuh : Brain 02-Formations/jun-yuh-motion-design.md) :
    `chiffres` = 1-2-3 géants derrière la tête (matte.py `fgm_k`), numérotés dans l'ordre de la vidéo, 4 max, mot au-dessus ;
    `trait` = illustration du Carrousel (`art.py`, 8 : camera, script_long, chat, checklist, stairs, chart_up, copies, apples_grid) au
    trait blanc, côté opposé au visage, mot dessous ; servie par `GET /illus/<nom>.svg` (`-trait` = version au trait). Le moment peut
    imposer `"illustration"` dans cockpit.json, sinon choix par mots-clés. Coupe franche, aucun rebond ; un motion s'arrête quand le
    suivant arrive. Anciens coeur / entoure / souligne (« dégueulasses ») = plus proposés.
  - Ton B-roll `broll: <chemin dans la bibliothèque> | perso` → `plan.brolls` (`from: auto`). « Proposé par Claude » = `brolls` du moment
    (3 chemins relatifs à `brolls_root`) ou recherche sur ses mots ; « Ma bibliothèque » = `GET /api/biblio?q=` (index SSD + tri, sans
    plans écartés ni téléphone), vignettes `/biblio/vignette?f=`, aperçu 3 s `/biblio/apercu?f=` (seulement les fichiers de l'index).
    « Envoyer une vidéo » = `POST /api/broll` (`perso`). Jamais d'image ni de vidéo générée par IA.
  « Sauter l'étape » = `passe3: "sautee"`. Musique en bas de l'étape 3. L'aperçu suit tout (zoom, mot derrière la tête masqué par
  une ellipse posée sur la tête mesurée `tetes`, mot dans le sous-titre, carton, motion, B-roll).
- **Mot géant derrière la tête** : `headtop.py` mesure la silhouette détourée (RVM) ; sans tête à l'image, le mot passe devant, au
  milieu, ombre forte. Le moteur retire un son à moins de 1,5 s du précédent (règle Gardien).

## Ce qui est branché sur le vrai moteur
1. **Coupes** : « Remettre » une reprise = sa plage sort de `drop.json` ; un blanc = une plage dans `garde.json` ; puis `derush.py` (~20 s).
   « Couper à nouveau » fait l'inverse. Les corrections de texte de Claude sont reportées (`_cockpit/corrections.json`).
2. **Style (23/10, remplace les looks à l'écran)** : `POLICES` dans `cockpit.py` = 6 polices validées par l'utilisateur : Ton combo
   (Montserrat + Instrument Serif), Condensé géant (Bebas Neue), Fin + gras (Outfit), Large (Archivo étiré), Manuscrit (Figtree + Caveat),
   Tech (Space Grotesk + Space Mono). Chacune = `t1` (titre ligne 1), `t2` (ligne 2), `sub` (sous-titres) : police, graisse, taille,
   majuscules, espacement, largeur, italique, `scale` (équivalence avec Montserrat). Règles : police principale (ligne 1 + sous-titres)
   TOUJOURS sans serif ; jamais de bande, d'étiquette ni de trait derrière le titre ; couleurs réglées à part. Choisi → `cockpit-etat.json`
   `style` ; au rendu `plan_final` met `plan.typo` (lu par `build.mjs`), `title.top`, `subMax`, `plan.da` (`_cockpit/da-look.json`) et
   `plan.style`. **Sans style : plan inchangé** (vérifié 23/10 : même page du moteur, mêmes tailles 42 / 104 px). Le style passe avant un
   ancien look. Essais et story prennent le même style.
   **Titre 2 lignes max (toutes les vidéos, avec ou sans style)** : `build.mjs` mesure chaque ligne (Pillow, axes graisse / largeur des
   polices variables) et baisse sa taille jusqu'à tenir dans 940 px (`titre rétréci…` dans `build.log`) ; l'aperçu fait pareil
   (`fitJS`, mesure refaite quand une police arrive). Tests 23/10 sur la copie IMG_6799 : Condensé or taille L (129 → 124 / 119 px) et
   Large à gauche en minuscules ombre forte : Gardien ✅, `zones.mjs` 0 texte en zone interdite.
   **Anciens looks** : 3 par défaut dans `cockpit.py` (`LOOKS`) : Premium sombre (Montserrat + Instrument Serif, blanc = le style actuel de
   l'utilisateur), Clair épuré (Inter + DM Serif, mots en serif bleu clair), Cinéma chaud (Poppins + Playfair, texte ivoire, serif or doux).
   Un client peut avoir les siens : `cockpit.json` → `"looks": [{id, nom, sans, serif, texte, serif_couleur, accent, rythme}]`
   (polices dans `supermonteur/fonts`). Choisi → `cockpit-etat.json` `look` + `affine` ; au rendu, `plan_final` écrit
   `_cockpit/da-look.json` (la DA de base choisie comme `build.mjs` + polices, `colors.text`, `colors.serif`, `colors.accent`, `zoomGap`)
   et met `plan.da` + `plan.look`. **Sans look : plan inchangé, rendu identique au reel validé.** `build.mjs` lit `colors.serif`
   (titre ligne 2, mots forts, mot géant ; absent = comme avant). La story et les 3 reels d'essai prennent le même look que le reel (décision 23/10).
3. **Musique** : « Ajoute ta musique » envoie le fichier brut (`POST /api/musique`, en-tête `X-Nom`, MP3 / M4A / WAV / AAC, 60 Mo max) →
   `_cockpit/musique-perso.<ext>`, id `perso`, servi par `/musique/perso`. « Sans musique » = `musique: "sans"` → le plan n'a pas de
   `music` (mix.py : voix seule). `cockpit.json` `musiques` peut être vide pour un client (Suno abandonné pour les clients le 23/10 :
   ses conditions interdisent la revente). L'utilisateur garde sa bibliothèque.
4. **Fabriquer / Programmer** : `plan.json` réécrit depuis `_cockpit/plan.base.json` + les choix, `matte.py` si mot géant, `monte.sh`
   (Gardien avant ET après). « Fabriquer le reel » = `POST /api/tout {ids: ["reel"], programmer: false}` (ne touche pas aux interrupteurs).
   « Programmer » fabrique les contenus cochés un par un (Mac 8 Go) puis écrit `publication.json` : une DEMANDE, rien n'est publié.
   Claude la fait passer par le Publieur seulement après un OK dans le chat (reel d'essai = Metricool `instagramData.type` `TRIAL_REEL`).

## Comment Claude s'en sert
1. Étapes 1-4 du SKILL (cadre, transcription du rush, `drop.json` + dérush, `words.json` corrigé, `plan.json`).
2. Écrire `cockpit.json` dans le dossier du reel (exemple : `montages/2026-10-22-img6799-cockpit/cockpit.json`) : `titre`, `rush`
   (chemin du rush ORIGINAL), `hooks` (3 : `id`, `nom`, `detail`, + `title` ou `bigwords`), `reco_hook`, `keywords` (6-10 mots forts),
   `musiques` (0 à 3 : `id`, `nom`, `titre`, `artiste`, `src`, `from`, `pourquoi`), `reco_musique`, `legende`, `raisons`, `essais`,
   `story`, `carrousel`, et `looks` seulement pour un client qui a les siens.
3. Lancer le serveur en tâche de fond (Bash `run_in_background`, PAS preview_start : macOS refuse ~/Documents aux serveurs de preview) :
   `python3 -u ~/.claude/skills/supermonteur/outils/cockpit/cockpit.py <dossier> --port 8790`, puis `preview_start {url: "http://127.0.0.1:8790"}` (fenêtre dans Claude, plus Chrome depuis le 23/10).
   Un seul serveur par dossier : deux serveurs sur la même copie gardent chacun un état en mémoire, le plus ancien devient faux.
4. Quand la personne revient : lire `cockpit-notes.json`, corriger chaque note « à faire », puis écrire `statut` + `reponse`.
5. À la fin : vérifier `final.mp4` + `gardien.log` (✅), lire `publication.json`, montrer la demande, programmer via le Publieur APRÈS son OK.

Pour Claude : `GET /api/plan` = le plan que « Fabriquer » enverrait au moteur. `?t=2.6` fige la vidéo (captures de contrôle).
Le panneau navigateur caché gèle les calques (requestAnimationFrame) : normal, pas un bug.

## Testé le 23/10 sur la COPIE d'IMG_6799 (port 8793 ; le reel validé n'a pas été touché)
Voir la section « v3 codé » du Brain `01-Projets/cockpit-montage.md`.
