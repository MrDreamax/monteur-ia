# Super : ta veille, ta DA, tes reels et tes carrousels, dans une seule appli

Une fenêtre, 4 onglets. Tout tourne sur ton Mac, avec ton abonnement Claude.

| Onglet | Ce qu'il fait |
|---|---|
| **Veille** | Lit les reels que tu enregistres sur Instagram. Tu coches, il traduit le script mot pour mot, ou reprend le format dans ta niche. |
| **DA** | Ta direction artistique : polices, couleurs, tailles. Réglée une fois, les autres onglets la suivent. |
| **Monteur** | Tu glisses ta vidéo, il monte le reel 9:16 (titre, sous-titres, musique). Tu cliques sur l'image pour tes retours, Claude corrige. |
| **Carrousel** | Un carrousel Instagram depuis un reel, un lien ou une idée. Retours slide par slide, puis téléchargement. |

## Installer (ou mettre à jour)
1. Ouvre l'app Claude sur ton Mac, onglet **Code**.
2. Colle cette phrase :

   > Installe les applis qui sont ici : https://github.com/MrDreamax/monteur-ia

3. Clique « Autoriser » quand Claude le demande.

À avoir avant : un Mac, Google Chrome et l'abonnement Claude Pro. Pour la musique : un compte Epidemic Sound (ou tes propres musiques).

## Ensuite
- Double-clic sur `Documents/SuperApps/ouvrir.command`, ou écris dans Claude : « Ouvre Super ».
- Super s'ouvre dans Chrome : http://localhost:8800
- **Veille** : connecte-toi à Instagram dans Chrome. Au 1er lancement, ton Mac demande l'accès au trousseau pour Chrome : clique « Autoriser ». L'appli lit, elle n'écrit rien sur Instagram.
- **Tes scripts à ta voix** : remplis `Documents/SuperApps/superveille/ma-marque.md`, ou demande à Claude de le faire avec toi.
- **Publication en mode essai** : le bouton Publier ne publie rien tant que tu ne l'actives pas toi-même (`"mode_essai": false` dans `supermonteur/config.json` et `supercarrousel/config.json`, après avoir branché Metricool avec « Programme ma semaine »).

## En option
- **Recherche de reels viraux** (onglet Veille) : demande le connecteur Apify dans Claude.
- **Scanner cerveau** (onglet Veille) : demande le connecteur Higgsfield dans Claude.
- Sans eux, tout le reste marche.

## Pour Claude (installation)
1. `git clone https://github.com/MrDreamax/monteur-ia ~/Documents/monteur-ia` (ou `git pull` s'il existe déjà).
2. `bash ~/Documents/monteur-ia/install.sh` (relançable : c'est aussi la mise à jour ; les réglages, la DA, les reels, les carrousels et les veilles de la personne ne sont jamais écrasés, l'ancien moteur est sauvegardé dans `~/.claude/backups/`).
3. Demande son prénom (bouton) et écris-le dans `~/Documents/SuperApps/config.json` → `"nom"`.
4. Lance Super : `bash ~/Documents/SuperApps/ouvrir-super.sh`, puis vérifie `curl -s localhost:8800/api/etat` (les 4 à `true`).
5. Les applis appellent Claude toutes seules : vérifie `claude auth status`. Pas connecté = double-clic sur `~/Documents/SuperApps/superda/connecter-claude.command`.
6. Remplis avec la personne `~/Documents/SuperApps/superveille/ma-marque.md`. Monter dans le chat, sans l'appli : lis `~/.claude/skills/supermonteur/mode-client.md`.
7. Ne mets jamais `"mode_essai": false` toi-même : c'est à la personne de le faire.

Ce qui est installé : les skills `super`, `superveille`, `supermonteur`, `publieur` et `carrousel` dans `~/.claude/skills/`, l'appli dans `~/Documents/SuperApps/`.

Crédit : Cyril MrDreamax · byStratosphere
