# Fiche retours : corriger vite (03/11/2026)

Lue par l'ouvrier de SuperMonteur (Claude Sonnet, sans chat) à chaque « Suivant : corrige mes retours ». But : la version
suivante en moins de 2 min. Tu modifies les fichiers, le serveur remonte la vidéo et répond à l’utilisateur tout seul.

## Ce que tu touches
- `<dossier>/plan.json` : la recette du montage.
- `<dossier>/words.json` : les mots des sous-titres (`{"words": [{"text", "start", "end"}, ...]}`), temps du montage.
- `<dossier>/reponses.json` : ta réponse, 1 ligne par retour, `{"<id>": "..."}`.
- `feedback-retours.md` (ici) : 1 ligne datée par retour (`- 03/11 <reel> : <retour> -> <ce qui a changé>`).
Rien d'autre. Ne lance aucune commande : pas de rendu, pas de dérush.

## Les champs de plan.json
- `title` : `{"l1": "...", "l2": "...", "start": 0, "end": 999, "top": 350}`. 2 lignes de longueur proche, une seule taille,
  la promesse forte du reel (jamais la 1re phrase coupée en 2). Pas de virgule, point ni deux-points. Nombres en chiffres
  (« +35 ans »). `top` = hauteur en px (plus grand = plus bas). Pas de titre = retirer la clé `title`.
- `fixes` : `{"mot faux": "mot juste"}` change CHAQUE occurrence dans les sous-titres. Un mot courant (« dis », « la ») :
  corrige-le dans `words.json` à son indice, pas dans `fixes`.
- `subMax` : nombre de mots max par sous-titre (3 = court).
- `music` : `{"src": "<fichier>", "from": <seconde de départ dans le morceau>, ...}`. Pas de musique = retirer `music`.
- `typo` : style du texte (couleurs, ombre). Ne l'ajoute que si l’utilisateur demande une couleur ou une ombre.
- `subY` : hauteur des sous-titres en px (1100 à 1340). Absent = calculé sur la vidéo.
- `duree_min` : 0 = pas de règle « plus d'1 minute ».
- Le reste (`cam`, `words`, `da`, `cases`, `style_supermonteur`, `_note`) : ne pas toucher.

## Cas courants
- « faute dans le sous-titre » : `fixes` (ou `words.json` pour un mot courant).
- « titre » (texte, taille, place) : `title` (texte) ou `title.top` (place). La taille vient de la DA, ne pas la forcer.
- « sous-titres trop longs » : `subMax` à 3.
- « musique » : autre `from` (temps fort) ; un autre morceau seulement s'il le demande.
- « cut plus serré », « bug ici » sur une coupe, « enlève cette phrase » : c'est le dérush, pas faisable ici.
  Réponds `"pas fait : dérush (coupe à <t> s), à refaire dans le chat"`. Le serveur le laisse à faire, bien visible.

## Temps du retour
`t` = seconde dans la version affichée. Le mot dit à cet instant = celui de `words.json` dont `start <= t < end`.
