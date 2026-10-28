#!/bin/bash
# Lance SuperDA s'il ne tourne pas déjà, puis donne le lien.
cd "$(dirname "$0")" || exit 1
PORT=$(/usr/bin/python3 -c "import sys; sys.path.insert(0, '..'); import reglages_apps; print(reglages_apps.port('superda'))" 2>/dev/null || echo 8781)
if ! curl -s -o /dev/null "http://localhost:$PORT/api/da"; then
  SUPERDA_PORT=$PORT nohup /usr/bin/python3 server.py > serveur.log 2>&1 &
  for i in $(seq 1 20); do sleep 0.5; curl -s -o /dev/null "http://localhost:$PORT/api/da" && break; done
fi
curl -s -o /dev/null "http://localhost:$PORT/api/da" && echo "SuperDA : http://localhost:$PORT" || { echo "SuperDA ne démarre pas :"; tail -5 serveur.log; exit 1; }
