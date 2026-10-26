#!/bin/bash
# Archive une vidéo PUBLIÉE sur le disque d'archive (16/10 : historique de toutes les vidéos terminées).
# Dossier = "archive_dir" des réglages (config.json + Brain/00-Moi/reglages/publieur.json) : ton disque d'archive, ou celui du client.
# Copie (jamais de déplacement) sous le nom « AAAA-MM-JJ - Titre.mp4 ». Code 2 = disque absent, on réessaie au prochain passage.
# Usage : archive_ssd.sh final.mp4 2026-10-19 "Tier list des formats Instagram"
set -e
SRC="$1"; DATE="$2"; TITRE="$3"
ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="$(python3 -E -c "import sys; sys.path.insert(0, '$ICI'); from _config import config; print(config().get('archive_dir', ''))")"
[ -n "$DEST_DIR" ] || { echo "archive_dir vide dans config.json (chez un client : choisir son disque au 1er lancement)"; exit 1; }
case "$DEST_DIR" in /Volumes/*) VOL="/Volumes/$(echo "${DEST_DIR#/Volumes/}" | cut -d/ -f1)"; [ -d "$VOL" ] || { echo "Disque absent ($VOL) : archive à refaire au prochain passage"; exit 2; };; esac
[ -f "$SRC" ] || { echo "Vidéo introuvable : $SRC"; exit 1; }
mkdir -p "$DEST_DIR"
NOM=$(printf '%s' "$TITRE" | tr '/:' '--')
DEST="$DEST_DIR/$DATE - $NOM.${SRC##*.}"
if [ -f "$DEST" ] && [ "$(stat -f%z "$DEST")" = "$(stat -f%z "$SRC")" ]; then echo "DÉJÀ ARCHIVÉE $DEST"; exit 0; fi
cp -p "$SRC" "$DEST"
[ "$(stat -f%z "$DEST")" = "$(stat -f%z "$SRC")" ] || { echo "ERREUR : copie incomplète $DEST"; exit 1; }
echo "OK $DEST"
