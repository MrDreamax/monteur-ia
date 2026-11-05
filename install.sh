#!/usr/bin/env bash
# Super : installe (ou met à jour) les skills supermonteur, publieur, carrousel, super et superveille + l'appli Super
# et ses 4 outils : Veille, DA, Monteur, Carrousel (dans ~/Documents/SuperApps).
# Usage : bash install.sh      (depuis le dossier dézippé). Relançable sans risque : c'est aussi la mise à jour.
#
# Ce que le script ne touche JAMAIS une fois installé (le dossier du client) :
#   supermonteur : config.json, da/<client>.json, retours-client.md, broll_exclus.txt, ref/
#   publieur     : config.json, retours-client.md
#   carrousel    : retours-client.md
#   applis       : config.json, superda/da.json + img/ + historique/, reels/, projets/, metricool.json, journaux,
#                  superveille : ma-marque.md, enregistres/, enregistres.json, veilles/, mes-notes/, tournage*.json, reglages.json
#   et tout ~/Documents/Montage
# Avant une mise à jour, l'ancien moteur est sauvegardé dans ~/.claude/backups/<skill>-<date>/.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/supermonteur"
PSRC="$(dirname "$SRC")/publieur"
DEST="$HOME/.claude/skills/supermonteur"
PDEST="$HOME/.claude/skills/publieur"
CSRC="$(dirname "$SRC")/carrousel"
CDEST="$HOME/.claude/skills/carrousel"
ASRC="$(dirname "$SRC")/apps"
ADEST="$HOME/Documents/SuperApps"
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

# Carrousel : le moteur des carrousels (style Apple), utilisé par SuperCarrousel
if [[ -d "$CSRC" ]]; then
  if [[ -d "$CDEST" ]]; then
    mkdir -p "$HOME/.claude/backups"
    cp -R "$CDEST" "$HOME/.claude/backups/carrousel-$TS"
    echo "Ancien skill carrousel sauvegardé : ~/.claude/backups/carrousel-$TS"
  fi
  mkdir -p "$CDEST"
  rsync -a --delete --exclude retours-client.md --exclude __pycache__ "$CSRC/" "$CDEST/"
  [[ -f "$CDEST/retours-client.md" ]] || printf '# Mes retours sur les carrousels (lus AVANT chaque carrousel)\nFormat : JJ/MM/AAAA · carrousel · ce qui n%sallait pas → règle\n\n' "'" > "$CDEST/retours-client.md"
fi

# Super et ses 4 outils : le code est remplacé, les données de la personne jamais touchées
if [[ -d "$ASRC" ]]; then
  mkdir -p "$ADEST"
  rsync -a --delete \
    --exclude config.json --exclude /superda/da.json --exclude /superda/img/ --exclude /superda/historique/ --exclude /superda/inspiration/ \
    --exclude demandes.jsonl --exclude /supermonteur/reels/ --exclude /supercarrousel/projets/ --exclude metricool.json \
    --exclude '*.log' --exclude a-corriger.json --exclude feedback-retours.md --exclude .rendu.lock --exclude _outils/ \
    --exclude preuves/ --exclude __pycache__ \
    --exclude ma-marque.md --exclude /superveille/enregistres/ --exclude /superveille/enregistres.json --exclude '/superveille/*.lock' \
    --exclude /superveille/veilles/ --exclude /superveille/mes-notes/ --exclude '/superveille/tournage*.json' --exclude /superveille/reglages.json \
    "$ASRC/" "$ADEST/"
  for a in "" supermonteur/ supercarrousel/ superveille/; do
    [[ -f "$ADEST/${a}config.json" ]] || cp "$ADEST/${a}config.exemple.json" "$ADEST/${a}config.json"
  done
  [[ -f "$ADEST/superda/da.json" ]] || cp "$ADEST/superda/da.defaut.json" "$ADEST/superda/da.json"
  # 1.7 : tailles par défaut revues (titre 62 px en une seule taille, sous-titres 54 px). Seulement si la personne
  # n'a jamais touché aux tailles (encore 104 · 52 de la 1.6) : sinon ses réglages restent.
  python3 - "$ADEST/superda/da.json" <<'PYDA' || true
import json, sys
p = sys.argv[1]
d = json.load(open(p))
m, duo = d.get("montage", {}), d.get("commun", {}).get("duo", {})
if m.get("titre", {}).get("taille") == 104 and m.get("sous_titres", {}).get("taille") == 52:
    m["titre"].update(taille=62, decalage=60, _y=350)
    m["sous_titres"].update(taille=54, majuscules=False)
    if duo.get("id") == "moderne" and "ratio_ligne1" not in duo.get("principale", {}):
        duo["principale"].update(graisse_ligne1=700, ratio_ligne1=1)
        duo.get("secondaire", {})["graisse"] = 700
    for r in d.get("_resume", {}).get("montage", []):
        if r.get("cle") == "tailles":
            r["valeur"] = "62 · 54 px"
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
    print("Tailles du titre et des sous-titres mises à jour (62 · 54 px).")
# 1.7.2 : duo Apple (SF Pro) par défaut. Seulement si la DA n'a jamais été enregistrée (« maj » d'origine).
if d.get("maj") == "2026-10-28T10:53:06+01:00" and duo.get("id") == "moderne":
    cat = json.load(open(p.replace("da.json", "catalogue.json")))
    apple = next(x for x in cat["duos"] if x["id"] == "apple")
    d["commun"]["duo"] = {k: apple[k] for k in ("id", "nom", "principale", "secondaire")}
    for r in d.get("_resume", {}).get("montage", []) + d.get("_resume", {}).get("carrousels", []):
        if r.get("cle") == "duo":
            r["valeur"] = "Apple"
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
    print("Police par défaut : SF Pro (duo Apple).")
PYDA
  [[ -f "$ADEST/superveille/ma-marque.md" ]] || cp "$ADEST/superveille/ma-marque.exemple.md" "$ADEST/superveille/ma-marque.md"
  mkdir -p "$ADEST/superda/img" "$MONT/MONTAGES" "$MONT/PUBLICATION"
  [[ -f "$ADEST/superda/img/frame.jpg" ]] || cp "$ASRC/superda/img/frame.jpg" "$ADEST/superda/img/frame.jpg"
  chmod +x "$ADEST"/*/lancer.sh "$ADEST/ouvrir.command" "$ADEST/ouvrir-super.sh" "$ADEST/superda/connecter-claude.command"
fi

# Skills super et superveille : remplacés à chaque mise à jour
for s in super superveille; do
  if [[ -d "$(dirname "$SRC")/$s" ]]; then mkdir -p "$HOME/.claude/skills/$s"; rsync -a --delete "$(dirname "$SRC")/$s/" "$HOME/.claude/skills/$s/"; fi
done

bash "$DEST/scripts/setup.sh"
# SF Pro (police Apple) : jamais livrée avec Super, prise sur CE Mac (elle y est déjà), pour le Monteur et SuperDA
if [[ -f /System/Library/Fonts/SFNS.ttf ]]; then
  for f in "$DEST/fonts" "$ADEST/superda/fonts"; do [[ -d "$f" ]] && cp /System/Library/Fonts/SFNS.ttf "$f/SF-Pro.ttf"; done
else
  echo "Attention : SF Pro introuvable sur ce Mac, le duo Apple utilisera une autre police."
fi
# SuperVeille : yt-dlp (télécharge les reels) et son module Python (lit les enregistrés Instagram)
mkdir -p "$HOME/.local/bin"
[[ -x "$HOME/.local/bin/yt-dlp" ]] || curl -fsSL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o "$HOME/.local/bin/yt-dlp" && chmod +x "$HOME/.local/bin/yt-dlp" || echo "Attention : yt-dlp pas installé (SuperVeille)."
/usr/bin/python3 -c "import yt_dlp" 2>/dev/null || /usr/bin/python3 -m pip install --user -q yt-dlp || echo "Attention : module yt-dlp pas installé (SuperVeille)."
# modules en plus pour les carrousels (lecture d'un reel, détourage)
python3 -c "import scipy, cv2" 2>/dev/null || python3 -m pip install --user -q scipy opencv-python-headless || echo "Attention : scipy / opencv pas installés (carrousels depuis un reel)."
# 1.7 (juge 1.6 : 1er démarrage du Carrousel = 188 s) : le tout 1er chargement de ces modules est long, on le fait ici
echo "Préparation du Carrousel (jusqu'à 3 min la première fois)…"
/usr/bin/python3 -c "import numpy, scipy.ndimage, PIL" 2>/dev/null || true
echo "Super installé (version $(cat "$DEST/VERSION")). Dans Claude, onglet Code : « Ouvre Super »."
if [[ -d "$PDEST" ]]; then echo "Publieur installé. Dans Claude : « Programme ma semaine »."; fi
if [[ -d "$ADEST" ]]; then echo "Super installé dans ~/Documents/SuperApps. Double-clic sur ouvrir.command (ou dans Claude : « Ouvre Super »). Publication en mode essai : rien ne part tant que tu ne l'actives pas."; fi
