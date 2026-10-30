#!/bin/bash
# Le bouton « Monte » (21/10/2026) : toute la partie machine d'un coup, sans que Claude réfléchisse entre les étapes.
#   bash monte.sh <dossier du reel>
# À lancer quand plan.json est prêt (B-rolls + musique gardés dans Style Lab). S'arrête au 1er problème, AVANT le rendu
# si possible. Pourquoi : le 20/10 (Titanic), 87 min pour 1 reel, dont 5 rendus au lieu d'1 et 171 commandes une par une.
# Étapes : B-rolls (prep) -> composition -> Gardien AVANT rendu -> rendu -> mix -> Gardien final -> planche de contrôle.
D=$(cd "${1:-.}" && pwd) || exit 1; cd "$D" || exit 1
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
# HyperFrames 0.8.149 depuis le 25/10 : la 0.6.81 sautait une image à 4,10 / 8,17 / 16,33 / 32,17 s… (arrondi), sur tous les reels.
S=$(cd "$(dirname "$0")" && pwd); HF="npx --yes hyperframes@0.8.149"
# 30/10 (CAM20063) : Chrome cale vers 400 Mo d'images vidéo reçues, toujours à la même image, même Mac redémarré et calme.
# Rendu par morceaux de 20 s avec un Chrome neuf à chaque morceau : plus de calage, et 2 min au lieu de 6 pour 58 s.
export HF_SEGMENTED_CAPTURE=true HF_SEGMENT_FRAMES=600 HF_SEGMENT_BROWSER_RECYCLE=1
T0=$(date +%s); etape() { echo "▶ $1  ($(( $(date +%s) - T0 )) s)"; }
stop() { echo "⛔ STOP ($(( $(date +%s) - T0 )) s) : $1"; exit 1; }

etape "B-rolls"
python3 -E "$S/broll.py" prep plan.json > prep.log 2>&1 || { tail -5 prep.log; stop "broll.py prep"; }
grep -E "HDR|INSTABLE" prep.log

# 28/10 (CAM20056-57 : « les mots en gros derrière la tête ») : matte.py n'était lancé nulle part, la tête ne passait jamais
# devant les mots géants / chiffres. Il tourne maintenant à chaque montage qui en a (détourage déjà fait = réutilisé).
if python3 -c "import json,sys;p=json.load(open('plan.json'));sys.exit(0 if p.get('numbers') or p.get('bigwords') or any(m.get('kind')=='chiffres' for m in p.get('motions',[])) else 1)"; then
  etape "Détourage (tête devant les mots géants)"
  python3 "$S/matte.py" plan.json > matte.log 2>&1 || { tail -5 matte.log; stop "matte.py"; }
fi

etape "Composition"
node "$S/build.mjs" --plan plan.json --out index.html > build.log 2>&1 || { tail -5 build.log; stop "build.mjs"; }
tail -1 build.log
# 21/10 (CAM20033) : hyperframes écrit « 0 error(s), 2 warning(s) » puis une ligne vide : l'ancien test (dernière ligne
# contient « 0 errors ») bloquait une compo saine. On cherche le compte d'erreurs dans toute la sortie.
$HF lint > lint.log 2>&1; grep -qE "(^|[^0-9])0 error" lint.log || { tail -8 lint.log; stop "lint HyperFrames"; }

etape "Gardien avant rendu"
python3 "$S/gardien.py" . --avant > gardien-avant.log 2>&1
grep -E "❌|GARDIEN" gardien-avant.log
grep -q "le rendu peut partir" gardien-avant.log || stop "corriger plan.json puis relancer monte.sh (aucun rendu lancé)"

etape "Rendu (~3 min, ne rien lancer de lourd à côté : Mac 8 Go)"
mkdir -p _v0; mv renders/*.mp4 _v0/ 2>/dev/null
# 28/10 (CAM20056-57 v2) : rendu calé à l'image 939 (« Chrome stopped answering ») parce qu'un autre chat faisait un ffmpeg
# lourd en même temps. Un 2e essai automatique après 30 s, au lieu de s'arrêter au 1er calage.
$HF render . -q high > render.log 2>&1 || { echo "rendu calé, 2e essai dans 30 s"; sleep 30; rm -f renders/*.mp4; $HF render . -q high > render.log 2>&1; } || { tail -5 render.log; stop "rendu"; }
R=$(ls -t renders/*.mp4 | head -1)

etape "Mix"
python3 "$S/mix.py" plan.json "$R" "$(python3 -c "import json;print(json.load(open('plan.json')).get('cam','clip.mp4'))")" final.mp4 > mix.log 2>&1 || { tail -5 mix.log; stop "mix.py"; }
grep -E "^musique|^final" mix.log

etape "Gardien final"
python3 "$S/gardien.py" . > gardien.log 2>&1; G=$?
grep -E "❌|GARDIEN" gardien.log
ffmpeg -v error -y -i final.mp4 -vf "fps=1,scale=144:-1,tile=10x7" -frames:v 1 planche.jpg
[ $G -eq 0 ] || stop "le Gardien final bloque : NE PAS LIVRER"
echo "✅ final.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4 | cut -c1-5) s) en $(( ($(date +%s) - T0) / 60 )) min $(( ($(date +%s) - T0) % 60 )) s · planche.jpg"
