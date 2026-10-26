# Règles des experts (12 domaines) : lire avant chaque montage

Créé le 13/10/2026. 3 agents, 71 vidéos lues + guides officiels (Netflix, BBC, W3C, EBU, Meta, TikTok, GSAP).
**Priorité : `feedback.md` (notes de Cyril) > Style Lab `~/Documents/Stratosphere/style-lab/STYLE.md` (Locked) > ce fichier.** Si un expert contredit Cyril, Cyril gagne.
Détail, sources et minutages : Brain `02-Formations/experts-<domaine>.md` (montage-video, montage-court-reseaux, sous-titrage, colorimetrie, direction-artistique-video, cadrage-9-16, motion-design, sound-design, sfx, musique-cinematique, montage-musique, mixage-audio).
[P] = l'expert le dit lui-même. [M] = mesuré sur la réf monteur ou les reels de Victor Heras. [H] = hypothèse, à tester.

## A. Règles de plan (à appliquer en écrivant `plan.json`, elles passent dans le plan montré à Cyril)

### Montage et rythme
1. À chaque coupe, décider dans cet ordre : émotion > histoire > rythme > regard. Un blanc de 0,6-0,9 s avant la phrase clé n'est jamais resserré (c'est LE silence). Murch [P]
2. Structure en 4 temps : hook 0-7 s, contexte jusqu'à ~60 %, réponse ~15 %, CTA ≤ 10 s. Musique, zooms et preuves suivent ces phases. Heras [P]
3. Dans les 2,4 premières secondes : la promesse dite + 1 événement (mot géant, impact, zoom lent). Si la promesse arrive plus tard dans le rush : le dire à Cyril (c'est le script). Heras [P], Meta [P]
4. Face cam posée : 1 changement (zoom lent, b-roll, carton) toutes les 8 à 15 s après le hook. Rafale de b-rolls (4 max, ~1 s) seulement sur une énumération. Victor 9,6-14,5 s [M]
5. Débit cible 165-195 mots/min, alerte au-dessus de 240. Le monteur humain est à 276 : trop rapide pour 35-50 ans. Victor 158-192 en studio [M]
6. Chaque élément du plan (b-roll, insert, carton, mot géant, chiffre, preuve) a un champ `why` : le mot déclencheur + ce qu'il montre. Pas de `why` = pas d'élément. Heras, Block [P]
7. Un plein écran ou un b-roll démarre 0 à 0,15 s APRÈS le début du mot ou du geste, jamais avant. Il finit sur le dernier mot de l'idée. Tim Smith [P]
8. Incrustations à moins d'une largeur de tête du visage (≤ 300 px), du côté où il regarde ou pointe. Tim Smith [P]
9. Chaque chiffre ou affirmation a sa vraie preuve à l'écran dans les 5 s. Heras [P]
10. Une seule montée par reel : la punchline (riser + silence + impact au même endroit) (→ Cyril 17/10 : la musique ne se coupe jamais, « on dirait un bug » ; la montée finit sur une frappe de la musique). Événements visuels par tranche de 10 s : ≤ 2, ≤ 3, ≤ 4 au pic, ≤ 2 à la fin. Block [P], plafonds [H]

### Direction artistique, couleur, cadrage
11. **Fiche univers AVANT tout visuel**, tirée du RUSH : les 7 composantes de Bruce Block (espace, ligne, forme, couleur, ton, mouvement, rythme) + la source de lumière (côté, couleur, dureté). Elle remplit `plan.colors` et la lumière des prompts Higgsfield. Block, Deakins [P]
12. Test "5 sur 7" sur chaque ajout : il partage au moins 5 composantes avec le rush. Il peut contraster sur UNE seule, exprès (l'accent). Sinon on jette. Block [P], seuil [H]
13. Test "sortir de la vidéo" sur chaque ajout : d'où vient sa lumière ? Est-il dans CETTE pièce ? Sert-il la phrase ? Un seul non = retiré. Deakins [P]
14. Palette : 3 teintes dominantes max (prises sur le rush) + 1 accent. Ombre portée d'un insert du côté opposé à la source de lumière. Deakins [P]
15. Caler les inserts SUR le rush (luminosité, couleur, netteté, grain), jamais le rush sur les inserts. Jamais de LUT sur la cam. Waqas Qazi [P], tolérances [H]
16. Pas d'étalonnage créatif : noirs tenus (jamais relevés : ça fait un voile gris, testé [M]), garder le bleu des LED, zéro néon. Darren Mostyn, Cullen Kelly [P]
17. Cadre : yeux entre 33 et 36 % de la hauteur, visage centré (47-53 % de la largeur). Réf monteur : 35,1 % et 49,7 % [M]

### Motion design
18. Deux familles d'easing seulement. Forte : `power3.out` 0,45 s (entrées), `expo.out` (mots géants, preuves). Douce : `sine.inOut` (zoom 1,4 s). Sortie : `power2.in`. Jamais `back` ni `elastic` (rebond). GSAP, NN/g, Ben Marriott [P]
19. Un seul mouvement héros à la fois : jamais 2 entrées à moins de 0,25 s (sauf éléments d'une même liste). Ben Marriott [P]
20. La durée suit la taille : petit objet 0,25-0,35 s, moyen 0,35-0,5 s, plein écran 0,45-0,6 s, moment rare (hook, punchline) jusqu'à 0,8 s. NN/g [P], seuils [H]
20b. (greffe GitHub 14/10, détail Brain `02-Formations/experts-motion-hyperframes-github.md`) Pause de 0,3-0,75 s entre l'action et son résultat (« virgule dramatique »), ex. barres grises puis barre accent. HeyGen `motion-doctrine` [P]
20c. Deux blocs qui s'enchaînent bougent sur le même axe et dans le même sens ; jamais d'aller-retour gauche / droite d'un bloc à l'autre ; 2-3 types de transitions par vidéo, pas plus. HeyGen `motion-doctrine` [P]
20d. Un chiffre qui compte : 1,2-2 s si la place le permet (moins de 0,8 s = flash illisible), il grossit pendant qu'il compte, le suffixe arrive après. Jamais de rebond sur un chiffre (c'est une donnée). HeyGen `counting-dynamic-scale` [P]
20e. Graphiques : 1 seule donnée en accent (la dernière barre, la ligne « réalité »), pas de camembert, le moins de grille et de légende possible. HeyGen `stat-bars-and-fills`, `data-in-motion` [P]

### Sous-titres
Le style est VERROUILLÉ par Cyril au Style Lab (13/10) : Montserrat 700 majuscules blanc 52 px, 1-3 mots, mot fort SEUL à l'écran en serif blanc 132 px, fondu 0,1 s, haut du bloc ~95 px sous le col (1 310 px sur Meta Verified). Les experts ne changent rien à ça. Ils ajoutent seulement :
21. Durée minimale d'un bloc = max(0,5 s ; 0,3 s par mot), sinon fusionner avec le bloc suivant. ≤ 20 caractères/s : au-delà, c'est le dérush qui est trop rapide. BBC, Netflix [P]
22. Jamais 2 mots forts de suite, 6 à 10 par 40 s. Wampus, Isaac [P]
23. Jamais finir un bloc sur un petit mot (et, mais, que, de, en...). Jamais séparer un nombre de son unité ni un prénom de son nom. Netflix, BBC [P]
24. Ne jamais descendre sous 46 px (lecteurs de 35-50 ans). BBC, Legge [P]
25. Si un reel part en PUB : Meta cache le bas sous y = 1 248. Les sous-titres à 1 310 seraient alors en partie sous l'interface : le dire à Cyril avant. En organique : OK. Meta [P pubs]

### Son
26. Musique : écrire l'émotion en 1 mot (`music[].emotion`) AVANT de chercher. Piano seul fragile ou drone sombre, sans voix, BPM ≤ 75 (→ Cyril 16/10 : jamais de drone ni de nappe sans mélodie ; une émotion qu'on sent, dark cinématique avec cordes, voir SKILL.md). Juger avec la voix posée dessus, garder 3 finalistes. Reznor/Ross, Michelmore [P]
27. Le sommet naturel du morceau (`from`, `preferenceRegions`) tombe sur le silence ou la punchline. Après le pic, le dernier segment 2 dB plus bas pour le CTA. Michelmore [P]
28. 2 morceaux max sur 40 s, changement seulement quand le sujet change, recalé sur une fin de phrase (pause ≥ 0,15 s), jamais au milieu d'un mot. Michelmore, Standard Story [P]
29. 3 couches max en même temps : voix + musique + 1 SFX. ≤ 1 SFX toutes les 4 s en moyenne, plafond = durée / 4. Quand ça déborde, on enlève dans l'ordre : whoosh b-roll, chiffre, plein écran. On garde : hook, silence, CTA. Murch, Burtt, Thom [P]
30. Riser : son pic tombe pile sur l'événement, pic 2 à 4 s après le début du riser. S'il jure avec la musique : riser "souffle" (non tonal). Epidemic, Spitfire [P]
31. Silence (→ abandonné le 17/10 par Cyril : musique jamais coupée) : 0,6 à 2,5 s (→ moteur : 0,6-0,9 s, la vraie pause gardée au dérush). Un seul kit SFX Epidemic sombre par reel, jamais mélangé aux vieux sons SSD. Murch, Herman Huang [P]
32. Musique à -31 LUFS ±1,5 (→ -29 depuis le 16/10, Cyril : à -31 elle « n'existait pas ») sous la voix, mesurée PAR segment (pas seulement en global). Cyril 13/10

## B. À tester en A/B (proposer à Cyril, ne jamais imposer)
- Musique qui entre à la fin de la 1re phrase (fondu 1,5 s) contre dès 0 s. Reznor/Ross [P]
- Voix à -16 LUFS (Curtis Judd, Boykin, EBU) contre -14 (actuel).
- Visage plus clair au hook (35 % de luma, MrBeast) contre la réf monteur sombre (27 %).
- Coupe sèche de musique avec une petite queue de 0,3-0,6 s contre coupe nette.
- 3 variantes de hook par vidéo pour les Trial Reels (pratique de Victor Heras [S]).
- (greffe GitHub 14/10, NON appliqué car ça contredit un choix validé de Cyril) Sous-titres sur 3 tailles (support 52-80 px, ancre 76-112 px, mot héros 150-240 px) contre 52 px partout (Style Lab). audrey-560 `hyperframes-cinematic-caption` [P]
- (idem) Zéro mouvement « d'attente » (dérive lente des blocs motion, flottement des inserts) contre la règle Cyril « jamais figé ». HeyGen `motion-doctrine` [P]
- (idem) Sortie = 75 % de l'entrée (inserts 0,34 s au lieu de 0,25 s, listes 0,14 s au lieu de 0,3 s) contre les sorties validées le 13/10. HeyGen `motion-doctrine` [P]
- Passer HyperFrames de 0.6.81 à 0.8.x (sous-titres embarqués, blocs du registre, `hyperframes check`) : risque de casser le moteur, à tester sur une copie.

## C. Changements du moteur
### Appliqués le 13/10 (OK de Cyril, testés)
- `derush.py` : micro-fondu 0,03 s à chaque coupe (test son continu : saut 3 630 -> 145, normal 119) + plages calées sur la grille des images (image 49,833 s = son 49,835 s sur 60 s de rush).
- `mix.py` : plafond -2 dBTP suréchantillonné (Meta Verified : -1,0 -> -2,4 dBTP, -14,0 LUFS) ; chaque morceau mesuré et recalé sur -31 LUFS sous la voix (→ -29 depuis le 16/10) (test : -31,1 / -31,0) ; creux -4 dB à 1,2 kHz ; musique -5 dB pendant ~1 s sous impact / sub drop / plein écran / CTA (mesuré : -5,0 dB) ; fondus qsin.
- `build.mjs` : `contrast(1.05)` retiré de la cam et des b-rolls ; pastilles en `power3.out` (plus de rebond).
- `config.json` : whoosh de b-roll et d'insert coupés (`broll` retiré de `sfx_auto`) ; `music_target_lufs` = -31 (→ -29 depuis le 16/10).

### Appliqués le 13/10 au soir (2e lot, OK de Cyril, testés)
- Sorties douces `power2.in` (inserts et chiffres 0,25 s ; listes, preuves, CTA 0,3 s) seulement si ≥ 1,5 s de face cam derrière. Vérifié image par image sur Meta Verified : le badge s'efface entre 2,65 et 2,90 s au lieu de disparaître d'un coup.
- Sidechain 30 / 450 ms (la musique remonte en douceur entre les phrases).
- Zoom : 5 s mini entre deux zooms dans le hook (0-7 s), 8 s ensuite.
- Outils : `lookstats.py` (mesure du look + cadre), `match_look.py` (cale chaque ajout sur le rush, couleur réelle jamais touchée), `univers_check.py` (fiche univers + test 5 sur 7 + planche), `score.py` (débit, car/s, image cam, yeux).
- Voix : paramètre `voice_lufs` (config, défaut -14 ; musique et SFX suivent). Test A/B -14 / -16 rendu : `livrables/test-voix-AB/`, en attente du choix de Cyril.

### Appliqués le 14/10 (greffe GitHub, « tout greffer » de Cyril, testés sur copies OPUS + green screen, sauvegarde `_backup/2026-10-14-avant-greffe-github/`)
- Bug corrigé : GSAP arrondissait `strokeDashoffset` au px entier, donc tout tracé `pathLength=1` sautait de vide à plein à mi-course (courbe `chart`, coche `badge`, lien `connect`, courbe et axes des preuves). `F()` ajoute `autoRound:false`. Mesuré : anneau 0,81 -> 0,52 -> 0,26 -> 0,08 au lieu de 1 -> 1 -> 0 -> 0.
- Chiffres géants qui comptent : 0,55 s -> 1,2-2 s (selon la place), le chiffre grossit de 55 % à 100 % en comptant, chasse fixe (plus de tremblement), suffixe après le compte. Vu : 39 -> 89 -> 99 puis « % ».
- Cartons liste : cascade `power4.out` 0,2 s, montée 40 px (avant 14 px, `power2.out` 0,22 s), flou -> net gardé.
- 2 blocs motion ajoutés : `ring` (anneau + compteur) et `bars` (barres, pause, barre accent + compteur). Démo : `~/Documents/Stratosphere/livrables/greffe-motion-github/demo-motion-greffe.mp4`.
- Écartés : cotes du viseur REC de heditor (elles visent un écran de surveillance, le nôtre respecte les zones sûres Instagram) ; tout rebond, glitch, flash, néon, sous-titres multicolores.

### Trouvé en testant (à proposer)
- Cadrage : le rush Meta Verified est filmée large (yeux 47,6 %, visage 24,5 %) ; le rush « vidéos virales » (réf FINAL.mp4) est filmée serré (34,5 %, 33 %). Le monteur humain ne recadre PAS (mesuré). `cadre.py` recadre depuis la 4K (x 1,34 sur Meta Verified : yeux 47 % -> 36 %, visage 25 % -> 33 %, mesuré sur le fichier produit). VALIDÉ par Cyril le 13/10 : automatique à l'étape 1 (rush déjà serré = pas touchée, testé sur « vidéos virales »). Attention : `score.py` compare à FINAL.mp4, un autre rush.
- Débit Meta Verified 268 mots/min et 26,5 car/s au pire moment : au-dessus des repères (240 et 20).
