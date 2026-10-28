#!/bin/zsh
# Double-clic : connecte Claude Code à ton compte (une seule fois). Sert à « Demande à Claude » et « Inspiration » dans SuperDA.
E_CLAUDE=$(command -v claude)
if [ -z "$E_CLAUDE" ]; then
  E_CLAUDE=$(ls -d "$HOME/Library/Application Support/Claude/claude-code"/*/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1)
fi
if [ -z "$E_CLAUDE" ]; then echo "Claude Code introuvable sur ce Mac."; read -k1; exit 1; fi
"$E_CLAUDE" auth login
echo ""
"$E_CLAUDE" auth status | grep -q '"loggedIn": true' && echo "C'est bon : SuperDA peut parler à Claude. Tu peux fermer cette fenêtre." || echo "Pas encore connecté. Relance ce fichier."
read -k1
