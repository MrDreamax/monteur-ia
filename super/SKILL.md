---
name: super
description: Ouvre Super, l'appli unique qui regroupe les 4 outils en onglets (Veille, DA, Monteur, Carrousel), dans Chrome. Use when "/super", "ouvre super", "ouvre tout", "ouvre mes applis", "ouvre SuperMonteur", "ouvre SuperCarrousel", "ouvre SuperVeille", "ouvre SuperDA".
---

# Super : les 4 outils dans une seule fenêtre

1. Lance : `bash ~/Documents/SuperApps/ouvrir-super.sh [veille|da|monteur|carrousel]`
2. Vérifie : `curl -s localhost:8800/api/etat` doit répondre les 4 à `true`.
3. Réponds en 1 ligne : « Super est ouvert dans Chrome. » Si un outil est à `false` : dis lequel + la dernière ligne de son `serveur.log`.

Les 4 outils gardent leur serveur : SuperVeille 8811, SuperDA 8781, SuperMonteur 8801, SuperCarrousel 8797.
