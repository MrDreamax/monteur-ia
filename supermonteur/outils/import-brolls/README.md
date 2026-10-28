# Import de B-rolls depuis un dossier photos/vidéos (13/10/2026)

Utilisé pour importer SSD Photos/ -> ASSETS/B-ROLLS (+222). Ordre :
1. inventaire_photos.py inv.json : date de tournage (métadonnée / mtime / birth, la plus ancienne), durée, format. Noms de dossiers en NFD sur le SSD : toujours normaliser en NFC avant de comparer.
2. (selection.json = inv filtré : dossiers choisis + date >= 2024)
3. moments.py : vidéos > 60 s -> candidats (pics de réaction salle au son + plans nets). Lecture des images clés avec ffmpeg -discard nokey (8x plus rapide).
4. photos_prep.py : regroupe rafales / quasi-doublons, garde la plus nette par scène (RAW/HEIC via sips).
5. planches.py + planches_longues.py : planches numérotées -> tri visuel par agents Sonnet (consignes_tri.md, consignes_longues.md). Référence visage : une photo RÉCENTE de la personne (planches/ref_visage.jpg) (sinon les agents ne le reconnaissent pas à Singapour).
6. import_brolls.py --dry puis sans --dry : copie / extrait 7 s, vignettes 600 px, index + catalogue + journal, écarte les doublons de la biblio.
