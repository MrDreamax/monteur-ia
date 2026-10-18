#!/bin/bash
# Vérifie / installe ce qu'il faut (une seule fois par machine). Ne casse rien si c'est déjà là.
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
ok=1
command -v node >/dev/null   || { echo "MANQUE node (https://nodejs.org)"; ok=0; }
command -v ffmpeg >/dev/null || { echo "MANQUE ffmpeg"; ok=0; }
command -v ffprobe >/dev/null || { echo "MANQUE ffprobe"; ok=0; }
MODS="numpy onnxruntime faster_whisper mediapipe PIL"
PIPS="numpy onnxruntime faster-whisper mediapipe pillow"
python3 -c "import ${MODS// /, }" 2>/dev/null || python3 -m pip install --user -q $PIPS
python3 -c "import ${MODS// /, }" 2>/dev/null || { echo "MANQUE modules python ($PIPS)"; ok=0; }
# Chrome de rendu + puppeteer-core d'HyperFrames (rendu, contrôle des zones, texte du B-roll + texte)
if command -v npx >/dev/null; then
  npx --yes hyperframes@0.6.81 browser ensure >/dev/null 2>&1 || { echo "MANQUE Chrome de rendu (npx --yes hyperframes@0.6.81 browser ensure)"; ok=0; }
fi
M="$HOME/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx"
if [ ! -s "$M" ]; then
  mkdir -p "$(dirname "$M")"
  curl -sL -o "$M" https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx
fi
[ -s "$M" ] || { echo "MANQUE modèle de détourage"; ok=0; }
[ $ok = 1 ] && echo "SETUP OK" || exit 1
