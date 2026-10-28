#!/bin/bash
# Capture 1440x900 d'un écran de SuperMonteur (preuves comparées aux maquettes) : bash capture.sh <url> <sortie.png>
P=$(mktemp -d)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --use-mock-keychain --disable-gpu --hide-scrollbars \
  --user-data-dir="$P" --window-size=1440,900 --virtual-time-budget=8000 --autoplay-policy=no-user-gesture-required \
  --screenshot="$2" "$1" >/dev/null 2>&1
rm -rf "$P"; ls -la "$2"
