# Tri visuel de B-rolls pour les reels de Cyril (coach business, marque premium)

Tu regardes des planches d'images numérotées (étiquette jaune P### = photo, V### = vidéo courte, image prise au milieu).
Sous chaque vignette : dossier d'origine (Chateau 2 M event = conférence/shooting dans un château, Conf epicu / Conférence Networking / Réseautage = conférences, Dubaï, singapour, Da Nang, Rome, Corse, Turquie = voyages, Photo perso / Studio Photo Da Nang / Dreamax Mobile = shootings) et, pour une photo, combien de photos quasi identiques elle représente.

Référence du visage de Cyril : planches/ref_cyril.jpg (homme, cheveux noirs courts, souvent en noir). LIS-LA EN PREMIER.

## Garder (garder = oui) seulement si TOUT est vrai
- BEAU : net, bien exposé, bien cadré, rendu premium (on doit pouvoir le mettre dans un reel haut de gamme). Pas flou, pas de grimace, pas d'yeux fermés, pas de plan raté/amateur.
- UTILE pour illustrer une idée : Cyril en action (parle sur scène, pose, travaille, voyage, sport, voiture, avec des gens), OU une ambiance forte sans lui (skyline, désert, voiture de luxe, salle de conférence pleine, public qui applaudit, paysage spectaculaire).
- Pas un doublon : dans une série du même plan (même tenue, même fond, même pose), garde AU MAXIMUM les 2 meilleures.
## Rejeter
- Des personnes sans Cyril (amis, clients, modèles) SAUF un public de conférence / foule utile comme ambiance.
- Moments privés (famille, repas en désordre, chambre), images banales (couloir, sol, plafond, ciel vide), textes illisibles, captures.
- Vise environ 25 à 35 % gardés, pas plus. Dans le doute : rejeter.

## Pour chaque élément GARDÉ, remplis
- id : l'étiquette (ex. "P123")
- theme : un seul parmi 01-TRAVAIL, 02-TOURNAGE, 03-TELEPHONE, 04-SPORT, 05-REPAS, 06-LUXE, 07-VILLE-VOYAGE, 08-MAISON, 09-SOCIAL (conférence, réseautage, public, poignée de main), 10-ARGENT, 12-PORTRAIT (pose/portrait), 14-AUTRE
- action : 2 à 5 mots en kebab-case, sans accents, qui décrivent EXACTEMENT ce qu'on voit (ex. "parle-micro-scene-conference", "pose-bras-croises-tesla", "marche-skyline-nuit", "public-applaudit-salle").
- tenue : courte, sans accents (ex. "t-shirt noir", "chemise blanche", "costume bleu"), "" si Cyril absent
- lieu : court, sans accents (ex. "chateau jardin", "salle conference", "desert dubai", "marina bay singapour", "colisee rome")
- qualite : "ok" si vraiment premium, sinon "moyen"
- cyril_visible : true / false

## Sortie
Écris UN fichier JSON (liste) au chemin indiqué, avec seulement les éléments gardés :
[{"id":"P123","theme":"09-SOCIAL","action":"parle-micro-scene-conference","tenue":"chemise blanche","lieu":"salle conference","qualite":"ok","cyril_visible":true}, ...]
Vérifie que le JSON est valide (python3 -c "import json;json.load(open('CHEMIN'))"). Réponds à la fin en 2 lignes : nombre vus, nombre gardés.
