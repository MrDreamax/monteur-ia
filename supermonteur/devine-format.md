# DEVINER LE FORMAT : « monte cette vidéo » = je devine, il confirme (26/10)

Règle maison (26/10) : « Je dis toujours "monte cette vidéo" et c'est à toi d'en déduire le type de montage : "tu veux un montage tier list ?" ou "tu veux juste titre + sous-titre ?" ou "tu veux un split screen ?" ou "tu veux un montage animé ?" ou "c'est un montage FAQ simple ?" ».
Il ne nomme jamais le format. Ne jamais lui demander « quel style ? » à froid : je regarde, je devine, je propose.

## 1. Regarder (1 commande, ~1 min)
```bash
python3 $S/devine_format.py rush.MOV --out <dossier>
```
-> `devine.json` (signaux + 4 formats classés + pourquoi) et `devine.jpg` (planche de 8 images). Whisper du Mac, gratuit, 150 premières secondes.
Si la transcription est déjà faite : `--words words.json`. Fichier audio seul (mémo vocal) = voix off directement.

## 2. Juger (moi, pas le script)
Toujours OUVRIR `devine.jpg` (Read) : le script rate ce qui se voit et ne s'entend pas.
- Scène, micro à la main, public, écran géant derrière = **Conférence** (le script ne le voit pas).
- Fond vert brut = **Green screen**. Il pointe derrière lui / parle d'un post, d'un article = Green screen aussi (le fond est posé au montage).
- 2 personnes = Podcast / Débat / Visio. 2 fois lui au même endroit = **Clone**.
- Plans sans visage + voix = **Voix off**. Plans sans voix = **B-roll + texte**. Caméra qui marche = **Vlog**.
- Il dit « tier », « je classe » = Tier list ; « à ne pas faire / à faire » = Comparaison en T ; « mauvais… bien… excellent » = Mauvais, bien, excellent ; il compte (« 10 raisons », « numéro 1 ») = Liste ; il répond à une question = FAQ / Questions-réponses ; il montre une capture / un écran = Split screen.
- Rien de tout ça = face caméra simple.

## 3. Demander : UNE question, en boutons (AskUserQuestion)
**26/10 : quand SuperMonteur sera codé, ces 2 questions (style + cases) passent sur son 1er écran « Quel style pour ce reel ? » (5 cartes, mon conseil entouré « Conseillé », cases dessous, « Monter le reel »). Maquette : `livrables/supermonteur-maquettes/final/0-style.png`. D'ici là, on garde les boutons du chat ci-dessous.**
Question = ma devinette, dans ses mots : « Tu veux un montage tier list ? », « Style minimaliste (titre + sous-titres) ? », « Style dynamique ? ». Options = seulement les 5 styles, sous leur nom.
Options (4 max, la devinette en 1er avec « (Recommandé) ») : la devinette + les 2-3 autres plausibles pour CE rush. Chaque option dit en clair ce qu'il verra (« le tableau S/A/B/C se remplit au-dessus de ta tête »). Le reste passe par « Autre ».
Une question pour le style, puis la question des cases (3 bis). L'ambiance et la musique se règlent ensuite comme d'habitude (cockpit).

## 3 bis. Les cases à cocher du style (26/10, dans le chat, juste après le style)
AskUserQuestion `multiSelect: true`, 1er bouton = « La totale (Recommandé) » (= tout coché). Il coche ce qu'il veut garder. **La musique n'est pas une case : toujours là.** Le style Autre n'a pas de cases.
| Style | Cases |
|---|---|
| Dynamique | titre, sous-titres, écran coupé en deux (toi + animation), cartons en dégradé, animations plein écran, mots géants, B-rolls, bruitages |
| Minimaliste | titre, sous-titres |
| Comparatif | titre, tableau, sous-titres, bruitages |
| Interview | titre, sous-titres, écran coupé en deux, plein écran sur celui qui parle |
4 options max par question : au-delà (Dynamique), 2 questions dans le même appel (« Texte » : titre, sous-titres, mots géants, cartons ; « Images et son » : écran coupé, animations, B-rolls, bruitages), chacune avec « La totale » en 1er.
Ses cases vont dans `plan.json` → `"cases": {...}` ; case décochée = le champ correspondant n'est pas écrit (pas de `title`, pas de `keywords`, `brolls: []`, `sfx: []`…). (Contrôle par le Gardien : pas encore codé.)

## 4. Ce que chaque réponse lance : les 5 styles SEULS (26/10), tous avec musique
| Ce qu'il choisit | Style | Recette |
|---|---|---|
| Face caméra (il parle seul, sujet à illustrer) | 1. Dynamique | `styles/face-cam.md` : mix split screen (cam + animation) / cam seule / carton dégradé / animation plein écran |
| Juste titre + sous-titres, FAQ, clip, selfie | 2. Minimaliste | `styles/raw.md` : titre ou question jusqu'à la fin + sous-titres + musique |
| Tier list, Comparaison en T, Mauvais / bien / excellent | 3. Comparatif | `styles/montage-viral.md` : sous-titres + fondu sombre au-dessus de la tête avec titre + tableau |
| Interview, Podcast, Débat, Visio (2 personnes) | 4. Interview | `styles/a-plusieurs.md` |
| Autre chose (voix off, green screen, B-roll + texte, tableau blanc, style d'un créateur) | 5. Autre | voir la ligne « Autre » du tableau des styles dans SKILL.md |
| Carrousel | pas un montage | skill `carrousel` |

Selfie, clip, FAQ = Minimaliste ; démonstration = Dynamique ; fiction à 2 = Interview (26/10).
