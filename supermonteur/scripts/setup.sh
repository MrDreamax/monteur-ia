#!/bin/bash
# Vérifie / installe ce qu'il faut (une seule fois par machine). Ne casse rien si c'est déjà là.
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
ok=1
# Il manque un outil = 1 ligne d'action, sources officielles seulement (vérifiées le 25/10/2026) :
# node = nodejs.org (bouton « macOS Installateur (.pkg) ») ; ffmpeg = Homebrew (brew.sh, macOS 15 et plus) ou, avant macOS 15,
# les binaires Intel d'evermeet.cx, seul lien macOS de ffmpeg.org/download.html.
command -v node >/dev/null || { echo "MANQUE node : ouvre https://nodejs.org/fr/download, clique « macOS Installateur (.pkg) », double-clic sur le fichier, puis relance ce setup"; ok=0; }
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  ok=0
  if command -v brew >/dev/null; then echo "MANQUE ffmpeg : dans le Terminal, tape « brew install ffmpeg », puis relance ce setup"
  elif [ "$(sw_vers -productVersion | cut -d. -f1)" -ge 15 ]; then echo "MANQUE ffmpeg : installe Homebrew (https://brew.sh/fr : colle sa ligne dans le Terminal, mot de passe du Mac), puis tape « brew install ffmpeg » et relance ce setup"
  else echo "MANQUE ffmpeg : télécharge ffmpeg ET ffprobe (« Download as ZIP ») sur https://evermeet.cx/ffmpeg (lien officiel de ffmpeg.org), mets les 2 fichiers dans ~/.local/bin, puis relance ce setup"; fi
fi
MODS="numpy onnxruntime faster_whisper mediapipe PIL"
PIPS="numpy onnxruntime faster-whisper mediapipe pillow"
python3 -c "import ${MODS// /, }" 2>/dev/null || python3 -m pip install --user -q $PIPS
python3 -c "import ${MODS// /, }" 2>/dev/null || { echo "MANQUE modules python ($PIPS)"; ok=0; }
# Chrome de rendu + puppeteer-core d'HyperFrames (rendu, contrôle des zones, texte du B-roll + texte)
if command -v npx >/dev/null; then
  npx --yes hyperframes@0.8.149 browser ensure >/dev/null 2>&1 || { echo "MANQUE Chrome de rendu (npx --yes hyperframes@0.8.149 browser ensure)"; ok=0; }
fi
M="$HOME/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx"
if [ ! -s "$M" ]; then
  mkdir -p "$(dirname "$M")"
  curl -sL -o "$M" https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx
fi
[ -s "$M" ] || { echo "MANQUE modèle de détourage"; ok=0; }
[ $ok = 1 ] && echo "SETUP OK" || exit 1
