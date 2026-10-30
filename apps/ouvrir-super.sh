#!/bin/bash
# 29/10 : les 4 Super fusionnés dans UNE fenêtre « Super » (apps/super, http://localhost:8800, 4 onglets).
# Lance Super et les 4 outils s'ils dorment, puis ouvre UN onglet Chrome. Utilisé par l'icône Super du Dock et /super.
cd "$(dirname "$0")" || exit 1
bash super/lancer.sh
open -a "Google Chrome" "http://localhost:8800/${1:+#$1}"
