# Choisir les meilleurs moments de vidéos longues (B-rolls des reels de la personne, marque premium)

Chaque LIGNE d'une planche = une vidéo longue (L##, à gauche : dossier, durée, et "GARDER N max").
Chaque vignette = un moment candidat (étiquette L##-k), avec en dessous :
- "SALLE" = pic de réaction du public détecté au son (applaudissements / rires) -> moment fort probable
- "net" = plan net et vivant détecté à l'image
- le minutage.
Le clip extrait fera 7 secondes à partir de ce moment.

Référence du visage de la personne : planches/ref_visage.jpg. LIS-LA EN PREMIER.

## Règles
- Par ligne, garde AU MAXIMUM le nombre indiqué (GARDER N max), et 0 si rien n'est beau.
- Les moments gardés d'une même vidéo doivent être VISUELLEMENT DIFFÉRENTS (cadrage, geste, angle). Jamais deux quasi identiques.
- À qualité égale, préfère : SALLE > geste fort de la personne (main levée, sourire, pointe le public) > plan large avec public visible > le reste.
- Rejette : flou, plan de transition, sol/plafond, plan sans la personne (sauf public de conférence vu de belle façon), image cramée ou noire.
- Plusieurs vidéos peuvent venir du même discours (même salle, même tenue) : sur l'ensemble de ces lignes, ne garde pas plus de 4 moments au total pour un même discours, choisis les plus variés.
- Si l'image est COUCHÉE (filmée de travers, la scène est à 90°), tu peux la garder si elle est belle, mais indique "rotation": 90 si l'image doit tourner dans le sens des aiguilles d'une montre pour être droite, -90 dans l'autre sens. Sinon "rotation": 0.

## Pour chaque moment GARDÉ
{"id":"L00-3","theme":"09-SOCIAL","action":"parle-public-chateau-geste","tenue":"veste bleu canard","lieu":"salle chateau","qualite":"ok","personne_visible":true,"rotation":0}
- theme : un seul parmi 01-TRAVAIL, 02-TOURNAGE, 03-TELEPHONE, 04-SPORT, 05-REPAS, 06-LUXE, 07-VILLE-VOYAGE, 08-MAISON, 09-SOCIAL (conférence, public), 10-ARGENT, 12-PORTRAIT, 14-AUTRE
- action : 2 à 5 mots kebab-case sans accents, ce qu'on voit EXACTEMENT
- tenue / lieu : courts, sans accents ("" si la personne est absente)
- qualite : "ok" si vraiment premium, sinon "moyen"

## Sortie
Un fichier JSON (liste des moments gardés) au chemin indiqué. Valide-le avec python3 -c "import json;json.load(open('CHEMIN'))". Réponds en 2 lignes : lignes vues, moments gardés.
