# VOIX OFF (ex « Sans visage ») : voix off, objets, mèmes (validée par Cyril le 14/10, v3, ne plus y toucher)

Lu après `SKILL.md`.
**Zones mortes (16/10)** : conforme tel quel (sous-titres à 1 150 px, rien d'autre à l'écran).

La voix pilote, les images remplissent tout l'écran : **1 plan par idée (1-3,5 s, moyenne ~1,6 s), coupe franche en fin de phrase ou de mot**, poussée lente sur chaque plan (1,00 → 1,04), aucune tête qui parle.
**Règles Cyril 14/10 (après le test v1) :**
- **AUCUN contenu généré par IA** (ni image, ni vidéo).
- Que des B-rolls VIDÉO où on voit un VISAGE et de l'ACTION (surtout les 3 plans du hook) ; pas de photo fixe (sinon toujours animée, zoom ou dézoom léger).
- Musique avec de l'ÉMOTION (triste ou motivante, engagée : ex. « Venturing through Time »).
- 6-8 SFX sur 20-30 s (Cyril 17/10, remplace 3-4) : impact d'ouverture, whoosh sur les grosses coupes, impact sur quelques mots forts, montée + frappe au tournant, frappe finale ; ≥ 1,5 s d'écart.
- Musique ÉPIQUE QUI MONTE jusqu'à la dernière phrase (Cyril 17/10), ~14 dB sous la voix. La vidéo finit quand la musique finit (jamais d'image muette à la fin).
- Plans = SES vrais B-rolls (bibliothèque, ≥ 2024, stables, bruts) ; rien qui colle → Pexels (gratuit, usage Instagram OK, pas de mention ; vérifier que la personne n'est pas montrée sous un mauvais jour), jamais d'IA. Vérifier que la personne visible est bien Cyril (l'index dit seulement « personne visible » ; plans bannis : `broll_exclus.txt`).
- Sous-titres au centre-bas (y 1150) sur une bande sombre fondue (40 % max). SFX dans `plan.sfx` à partir du kit `config.json` (`{...kit[k], "at": t}`).

1. **Voix** : un rush face cam (on n'en garde que le son) ou un mémo vocal. Transcrire, dérusher (étapes 2-3) → `voice.mp4` + `words.json`.
2. **Un plan par phrase** : lire la transcription, pour chaque idée chercher LE plan qui montre ce qui est dit (`broll.py search <mots>` ; contraste = 2 plans opposés : « aller à la salle » salle / « être en surpoids » assiette lourde). Une personne visible = Cyril (même visage, `brolls_min_date`). Pas de plan qui contredit la phrase (sourire sur « sans aimer ce que tu vois » = refusé).
3. **plan.json** : fixes, keywords (5-6 mots forts sur 30 s), music, + `"voixoff": {"voice": "voice.mp4", "beats": [{"src": "<chemin absolu>", "from": "auto", "end": 1.57}, ...]}` (`end` = fin du plan, entre deux mots ; le dernier va jusqu'au bout ; image = .jpg/.png ; `"band": 0` = sans bande).
```bash
python3 $S/voixoff.py build plan.json        # clip.mp4 + plan.cam / zoom:false / subY ; « !! instable » ou « trop court » -> changer de plan
node $S/build.mjs --plan plan.json --out index.html && npx --yes hyperframes@0.6.81 render . -q high
python3 $S/mix.py plan.json renders/<x>.mp4 voice.mp4 final.mp4
```
4. **Vérifier la planche** : chaque plan colle à sa phrase, aucun inconnu en vedette, aucun plan qui tremble.
Réf VALIDÉE : `~/Documents/Stratosphere/style-lab/sans-visage/voixoff-difficile-v3.mp4`. Test moteur : `livrables/montage-voixoff-difficile-test/final.mp4` (v2, 32,7 s, 20 plans vidéo, 4 SFX, -14,1 LUFS ; v1 rejetée gardée en `final-v1.mp4`).
Limites : sous-titres jusqu'à 26 car/s quand la voix va vite (dérush moins serré si besoin) ; ciels / sable parfois brûlés (P99 251, plans bruts : `match_look.py --fix` possible) ; pas encore de cartons texte plein écran ni de mèmes.
