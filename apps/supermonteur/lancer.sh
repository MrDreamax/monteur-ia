#!/bin/bash
# Lance SuperMonteur s'il ne tourne pas déjà, puis donne le lien. (Le navigateur intégré de Claude ne peut pas lancer
# un serveur qui lit ~/Documents : macOS le bloque. On le lance donc d'ici, et launch.json « supermonteur » s'y branche.)
cd "$(dirname "$0")" || exit 1
if ! curl -s -o /dev/null http://localhost:8801/api/da; then
  nohup python3 serveur.py 8801 > serveur.log 2>&1 &
  for i in 1 2 3 4 5 6 7 8 9 10; do sleep 0.5; curl -s -o /dev/null http://localhost:8801/api/da && break; done
fi
curl -s -o /dev/null http://localhost:8801/api/da && echo "SuperMonteur : http://localhost:8801" || { echo "SuperMonteur ne démarre pas :"; tail -5 serveur.log; exit 1; }
