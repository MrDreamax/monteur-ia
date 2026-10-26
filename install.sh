#!/usr/bin/env bash
# Monteur IA Stratosphère : installe (ou met à jour) les skills supermonteur et publieur chez le client.
# Usage : bash install.sh      (depuis le dossier dézippé). Relançable sans risque : c'est aussi la mise à jour.
#
# Ce que le script ne touche JAMAIS une fois installé (le dossier du client) :
#   supermonteur : config.json, da/<client>.json, retours-client.md, broll_exclus.txt, ref/
#   publieur     : config.json, retours-client.md
#   et tout ~/Documents/Montage
# Avant une mise à jour, l'ancien moteur est sauvegardé dans ~/.claude/backups/<skill>-<date>/.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/supermonteur"
PSRC="$(dirname "$SRC")/publieur"
DEST="$HOME/.claude/skills/supermonteur"
PDEST="$HOME/.claude/skills/publieur"
MONT="$HOME/Documents/Montage"
TS="$(date +%Y%m%d-%H%M%S)"

[[ -d "$SRC" ]] || { echo "Dossier supermonteur introuvable à côté de install.sh"; exit 1; }
[[ "$(uname)" == "Darwin" ]] || echo "Attention : testé sur Mac seulement."

if [[ -d "$DEST" ]]; then
  mkdir -p "$HOME/.claude/backups"
  cp -R "$DEST" "$HOME/.claude/backups/supermonteur-$TS"
  echo "Ancienne version sauvegardée : ~/.claude/backups/supermonteur-$TS"
fi
mkdir -p "$DEST"
# moteur remplacé ; fichiers du client protégés (exclus = ni copiés ni supprimés)
rsync -a --delete \
  --exclude config.json --exclude retours-client.md --exclude broll_exclus.txt \
  --exclude 'da/*.json' --exclude ref/ \
  "$SRC/" "$DEST/"
cp "$SRC/da/exemple.json" "$DEST/da/exemple.json"

if [[ ! -f "$DEST/config.json" ]]; then
  sed "s#~/#$HOME/#g" "$SRC/config.exemple.json" > "$DEST/config.json"
  echo "Réglages créés : $DEST/config.json"
fi
[[ -f "$DEST/retours-client.md" ]] || printf '# Mes retours (lus AVANT chaque montage, passent avant tout le reste)\nFormat : JJ/MM/AAAA · reel · ce qui n%sallait pas → règle\n\n' "'" > "$DEST/retours-client.md"
[[ -f "$DEST/broll_exclus.txt" ]] || echo "# B-rolls à ne jamais utiliser (une action de _INDEX.csv par ligne)" > "$DEST/broll_exclus.txt"
mkdir -p "$MONT/B-ROLLS" "$MONT/MUSIQUE" "$MONT/SFX" "$MONT/LIVRES" "$MONT/RUSHS"

# Publieur : config.json absent = 1er lancement (Claude le crée avec lui, mode-client.md), jamais écrasé ensuite
if [[ -d "$PSRC" ]]; then
  if [[ -d "$PDEST" ]]; then
    mkdir -p "$HOME/.claude/backups"
    cp -R "$PDEST" "$HOME/.claude/backups/publieur-$TS"
    echo "Ancien publieur sauvegardé : ~/.claude/backups/publieur-$TS"
  fi
  mkdir -p "$PDEST"
  rsync -a --delete --exclude config.json --exclude retours-client.md "$PSRC/" "$PDEST/"
  [[ -f "$PDEST/retours-client.md" ]] || printf '# Mes retours sur la publication (lus AVANT chaque semaine, passent avant tout le reste)\nFormat : JJ/MM/AAAA · reel · problème → règle\n\n' > "$PDEST/retours-client.md"
  mkdir -p "$MONT/PUBLICATION"
fi

bash "$DEST/scripts/setup.sh"
echo "Monteur IA installé (version $(cat "$DEST/VERSION")). Dans Claude, onglet Code : « Monte-moi ce rush » + glisse ta vidéo."
if [[ -d "$PDEST" ]]; then echo "Publieur installé. Dans Claude : « Programme ma semaine »."; fi
