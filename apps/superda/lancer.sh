#!/bin/bash
# Lance SuperDA s'il ne tourne pas déjà, puis donne le lien. (Même principe que les lancer.sh des autres Super.)
cd "$(dirname "$0")" || exit 1
if ! curl -s -o /dev/null http://localhost:8781/api/da; then
  nohup /usr/bin/python3 server.py > serveur.log 2>&1 &
  for i in $(seq 1 40); do sleep 0.5; curl -s -o /dev/null http://localhost:8781/api/da && break; done
fi
curl -s -o /dev/null http://localhost:8781/api/da && echo "SuperDA : http://localhost:8781" || { echo "SuperDA ne démarre pas :"; tail -5 serveur.log; exit 1; }
