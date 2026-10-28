# Monteur IA + les Super applis

Monte tes reels, fais tes carrousels et règle ta DA, directement dans Claude.

| Appli | Ce qu'elle fait | Lien (une fois lancée) |
|---|---|---|
| **SuperDA** | Ta direction artistique : polices, couleurs, tailles, style des carrousels. Réglée une fois, les 2 autres la suivent. | http://localhost:8781 |
| **SuperMonteur** | Tu glisses ta vidéo, il monte le reel 9:16 (titre, sous-titres, musique). Tu cliques sur l'image pour tes retours, Claude corrige. | http://localhost:8801 |
| **SuperCarrousel** | Un carrousel Instagram depuis un reel, un lien ou une idée. Retours slide par slide, puis téléchargement. | http://localhost:8797 |

## Installer (une seule fois)
1. Ouvre l'app Claude sur ton Mac, onglet **Code**.
2. Colle cette phrase :

   > Installe les applis qui sont ici : https://github.com/MrDreamax/monteur-ia

3. Clique « Autoriser » quand Claude le demande.

À avoir avant : un Mac et l'abonnement Claude Pro. Pour la musique : un compte Epidemic Sound (ou tes propres musiques).

## Ensuite
- Double-clic sur `Documents/SuperApps/ouvrir.command`, ou écris dans Claude : « Ouvre SuperMonteur ».
- Tes reels arrivent dans `Documents/Montage`.
- **Publication en mode essai** : le bouton Publier ne publie rien tant que tu ne l'actives pas toi-même (`"mode_essai": false` dans `supermonteur/config.json` et `supercarrousel/config.json`, après avoir branché Metricool avec « Programme ma semaine »).

## Pour Claude (installation)
1. `git clone https://github.com/MrDreamax/monteur-ia ~/Documents/monteur-ia` (ou `git pull` s'il existe déjà).
2. `bash ~/Documents/monteur-ia/install.sh` (relançable : c'est aussi la mise à jour ; les réglages, la DA, les reels et les carrousels de la personne ne sont jamais écrasés, l'ancien moteur est sauvegardé dans `~/.claude/backups/`).
3. Demande son prénom (bouton) et écris-le dans `~/Documents/SuperApps/config.json` → `"nom"`.
4. Lance les 3 applis : `bash ~/Documents/SuperApps/superda/lancer.sh`, puis `supermonteur/lancer.sh` et `supercarrousel/lancer.sh` (même dossier). Ouvre http://localhost:8801 dans le navigateur intégré et montre-lui.
5. Les applis appellent Claude toutes seules (corrections, textes des carrousels) : vérifie `claude auth status`. Pas connecté = double-clic sur `~/Documents/SuperApps/superda/connecter-claude.command`.
6. Monter dans le chat (sans l'appli) : lis `~/.claude/skills/supermonteur/mode-client.md` et fais le 1er lancement avec la personne.
7. Ne mets jamais `"mode_essai": false` toi-même : c'est à la personne de le faire.

Ce qui est installé : les skills `supermonteur`, `publieur` et `carrousel` dans `~/.claude/skills/`, les applis dans `~/Documents/SuperApps/`.

Crédit : Cyril MrDreamax · byStratosphere
