#!/bin/bash
# Double-clic : lance SuperDA, SuperMonteur et SuperCarrousel, puis ouvre SuperMonteur dans le navigateur.
cd "$(dirname "$0")" || exit 1
bash superda/lancer.sh
bash supermonteur/lancer.sh
bash supercarrousel/lancer.sh
open "http://localhost:8801"
