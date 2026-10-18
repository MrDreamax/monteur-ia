# MODE CLIENT (Publieur installé chez un client, décidé avec Cyril le 16/10)

On est chez un client quand `config.json` du skill a un champ `"client"` rempli. Ce fichier passe AVANT `SKILL.md` quand ils se contredisent. Dans `SKILL.md`, « Cyril » = le client pour tout ce qui touche à sa personne (son OK, ses comptes, ses B-rolls, sa DA) ; les règles de qualité restent celles de la maison.

## Ses fichiers à lui (jamais écrasés par une mise à jour)
- `config.json` : sa marque Metricool, son compte Instagram attendu, son disque d'archive, son CTA, sa cible.
- `retours-client.md` : SES retours, lus en premier (le carnet de ce skill chez lui). 1 ligne par retour : `JJ/MM/AAAA · reel · problème → règle`.
- Sa DA : `~/.claude/skills/supermonteur/da/<client>.json` (polices, couleur d'accent, légende tu/vous, emojis, CTA). La cover prend ses polices et ses couleurs toute seule (`config.json` → `"da"`).
- Ses B-rolls : l'index du monteur de sa machine (`~/Documents/Montage/B-ROLLS/_INDEX.csv`).
- Pas de Brain chez lui : les règles de légende sont dans `regles-legendes.md` (à la place du fichier experts du Brain et de `voix-contenu.md`). Sa voix = sa DA (tu/vous, emojis) + ses vraies phrases dans la vidéo.

## 1er lancement (une seule fois, ~15 min, dans cet ordre)
1. `config.exemple-client.json` → copier en `config.json`. Prénom → `"client"` (le même que dans le monteur). `"da"` → son fichier `da/<prenom>.json`. Crée `retours-client.md` s'il n'existe pas.
2. **Metricool gratuit** (1 marque suffit pour lui). Ce qu'il fait lui-même, en 1 ligne : créer son compte sur metricool.com avec SON email, puis dans Connexions brancher son Instagram PRO (via Facebook), sa chaîne YouTube, son TikTok, sa Page Facebook. Puis le connecteur Metricool dans SON Claude (Réglages > Connecteurs). Vérifie avec `session_connectors_status`, jamais de mémoire.
3. `getBrandSettings` dans SON Claude : écris `metricool_brand_id` et `instagram_attendu`. Un seul brand attendu ; si plusieurs, AskUserQuestion pour choisir le sien.
4. **Disque d'archive** (son choix : disque externe) : liste `/Volumes/*` sans le disque du Mac, AskUserQuestion avec les disques trouvés → `archive_dir` = `/Volumes/<disque>/PUBLIÉES`. Test : créer le dossier, y écrire un fichier vide, le supprimer. Aucun disque branché → on note « à faire » et on archive plus tard (le script sort en code 2).
5. CTA et cible : 1 AskUserQuestion, 2 questions. CTA : le mot que son ManyChat (ou son DM) attend vraiment (proposition tirée de `da/<client>.json` → `legende.cta`). Cible : 1 phrase (proposition tirée de `da/<client>.json` → `ambiance`). → `cta_defaut`, `cible`.
6. Higgsfield : sur SON compte (déjà branché pour le monteur). Plafond : `credits_cover_max` (8) par cover, essais compris. Pas de Higgsfield → cover sans retouche (photo B-roll brute étalonnée avec ffmpeg), on le dit.

## Chaque semaine
Même chemin que `SKILL.md` § 1 à 7, avec ses dossiers :
- Reels à publier : les dossiers de `~/Documents/Montage/LIVRES/<date>-<titre>/` (livrés par le monteur : reel + légende), absents de son registre `~/Documents/Montage/PUBLICATION/registre.md`. La légende du monteur sert de base, elle passe quand même les contrôles.
- Fiches et page semaine : `~/Documents/Montage/PUBLICATION/`.
- Cover : SES B-rolls, retouchés sur SON Higgsfield vers SA DA. Le prompt validé de `SKILL.md` § 3 s'adapte : remplace « dark luxury, midnight navy blue, warm golden key light » par l'ambiance et les couleurs de `da/<client>.json` (`ambiance`, `colors.list`, `colors.accent`). Le reste du prompt (garder le visage, la pose, le cadre) ne change pas.
- Heure : ses stats Metricool, sinon 20h provisoire.
- Archive : `archive_ssd.sh` copie chaque vidéo publiée sur SON disque (`archive_dir`).

## Rien ne sort de chez lui
Ses retours, ses fiches et son registre restent sur son Mac. Rien ne part sur le compte Metricool, le Higgsfield ou le SSD de Cyril.

## Pour le ZIP client (à faire dans le chat du kit monteur)
Livrer : `SKILL.md`, `mode-client.md`, `regles-legendes.md`, `config.exemple-client.json`, `scripts/`, `assets/`. Exclure : `config.json` (réglages de Cyril) et `retours-client.md`. Garde-fou : refuser le ZIP si l'id de marque Metricool de Cyril, son pseudo Instagram ou le chemin de son SSD apparaît dans un fichier livré (les valeurs sont dans le `config.json` de Cyril, à comparer).
