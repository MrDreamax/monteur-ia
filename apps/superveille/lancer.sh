#!/bin/bash
# Lance SuperVeille s'il ne tourne pas déjà, puis donne le lien. (Le navigateur intégré de Claude ne peut pas lancer
# un serveur qui lit ~/Documents : macOS le bloque. On le lance donc d'ici, et launch.json « superveille » s'y branche.)
cd "$(dirname "$0")" || exit 1
if ! curl -s -o /dev/null http://localhost:8811/api/accueil; then
  PATH="$HOME/.local/bin:$PATH" nohup /usr/bin/python3 serveur.py 8811 > serveur.log 2>&1 &
  for i in $(seq 1 40); do sleep 0.5; curl -s -o /dev/null http://localhost:8811/api/accueil && break; done
fi
curl -s -o /dev/null http://localhost:8811/api/accueil && echo "SuperVeille : http://localhost:8811" || { echo "SuperVeille ne démarre pas :"; tail -5 serveur.log; exit 1; }
