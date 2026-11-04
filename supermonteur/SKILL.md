---
name: supermonteur
description: Le Monteur, le SEUL skill de montage (26/10 : Déclineur et Tableau sur le mur rangés dedans). Monte un rush en reel 9:16 Instagram prêt à poster pour l'utilisateur ou un client - 5 styles SEULEMENT (26/10 : Dynamique, Minimaliste, Comparatif, Interview, Autre), mode client, mode vidéo longue (une vidéo longue découpée en reels), style Tableau sur le mur (interne). Monte aussi une vidéo YouTube 16:9 entière en style theyo (31/10). Use when "montage YouTube", "monte ma vidéo YouTube", "style theyo", "style horizontal", "style soowei", "bandes noires", "monte cette vidéo", "monte-moi ce rush", "monte ce reel", "sous-titre cette vidéo", "sous-titres", "montage", "face cam", "podcast", "visio", "voix off", "green screen", "tier list", "comparaison en T", "à faire / à ne pas faire", "mauvais bien excellent", "B-roll + texte", "texte sur b-roll", "lis la légende", "monteur", "supermonteur", "décline", "décliner", "recycle cette vidéo", "repurpose", "découpe cette vidéo en reels", "extraits", "clips", "transforme ce live en reels", "Déclineur", "style dynamique", "style minimaliste", "style comparatif", "style interview", "style autre", "tableau sur le mur", "style tableau", "dessin sur le mur", "j'ai dessiné sur l'iPad", "rush + enregistrement iPad".
---

**Réflexe 9/10 (03/11/2026, l’utilisateur : « il faut que ce soit un réflexe pour tout ce que tu fais de me montrer que du 9/10 ») : rien ne lui est montré sous 9/10, échantillon, maquette et version intermédiaire compris. Juge séparé avant chaque envoi, 3 tours max, sinon la vraie note et ce qui bloque. Méthode : Brain `09-SOP/boucle-9-sur-10.md`.**

**Premier geste de toute demande de montage = ouvrir Super, onglet Monteur, dans le navigateur intégré de Claude, jamais dans Chrome** (02/11, l’utilisateur : « sinon j'ai tout opéré depuis ici et l'interface ne sert à rien ») : `bash ~/Documents/SuperApps/super/lancer.sh` puis `preview_start {url: "http://localhost:8800/#monteur"}`, avant toute question (28/10, puis fusion du 29/10 ; SuperMonteur tourne derrière sur le port 8801). Toute vidéo donnée dans le chat : `POST http://localhost:8801/api/nouveau {"rush": "<chemin>"}` (lit la carte sur place, sans copie) puis ouvrir `http://localhost:8800/#monteur&reel=<id>` de la même façon ; avant, regarder si un projet du même rush existe déjà (un nom CAM2xxxx peut être un AUTRE rush déjà renommé).

**29/10/2026 : reels d'essai SUPPRIMÉS** (l’utilisateur : « tout ce qui est en lien avec les reels d'essai, tu peux tout supprimer, je n'utilise pas »). Je ne monte jamais de reel d'essai ni de 2e hook ; le Publieur n'envoie plus de TRIAL_REEL.

**Maquette d'abord (19/10)** : tout NOUVEAU style ou design passe par 3 versions et 2 rounds avant d'exécuter (détail : `cahier-des-charges.md`). Un rush normal suit l'ordre rapide ci-dessous : le style se choisit dans SuperMonteur, jamais dans le chat (02/11).

# SUPERMONTEUR : rush → reel premium

**Sommaire (26/10 : un seul Monteur).** Lire seulement le fichier du cas, au moment où il sert :
- Rush court → reel : ce fichier + `styles/<style>.md`.
- Vidéo longue (YouTube, live, call de groupe, conférence) → plusieurs reels : `video-longue.md`.
- **Vidéo YouTube 16:9 entière (31/10, style theyo, plus autonome)** : `styles/youtube-theyo.md` + grille `note-10-youtube.md`.
- Rush + enregistrement iPad (dessin sur le mur) : `styles/tableau-mur.md`.
- **Style horizontal, pour du vertical (01/11, validé, ex-« style soowei »)** : rush horizontal zoomé en 4:3 entre deux bandes noires, titre d'une ligne au-dessus, sous-titres sur l'image : `styles/horizontal.md` + `scripts/horizontal.py`. Pas de question de style.
- Client : `mode-client.md`.
Interne (absent du kit client) : `video-longue.md` et `styles/tableau-mur*`. Fichier absent = dire en 1 ligne que ce mode n'est pas dans le kit.

**Les règles de ce skill sont rangées à côté.** Quand un autre fichier cite « SKILL.md », une étape, le brief ou le cahier des charges, c'est ici :
- Brief, étapes 1 à 9, champs de `plan.json`, Gardien, livraison, boucle feedback : `workflow.md`.
- Cahier des charges (coupes, zones mortes, sous-titres, univers, maquette, DA) : `cahier-des-charges.md`.
- Toute décision de musique : `musique.md`. Choix d'un son : `sfx.md`. B-rolls : `brolls.md`.
- `_archive/regles-remplacees.md` : anciennes règles, pour l'historique seulement, JAMAIS à appliquer.

Référence de qualité : le reel monté par un vrai monteur, validé par l'utilisateur le 12/10/2026 (rush test `/Volumes/son disque externe/1 - Contenu/2 - Vidéos finies/2026-08-26 Reels business - Rush vidéos virales.mp4`, réf monteur copiée dans `~/.claude/skills/supermonteur/ref/FINAL.mp4`). Chaque montage doit tenir la comparaison.

```bash
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
S=~/.claude/skills/supermonteur/scripts
$S/setup.sh            # 1re fois sur une machine : doit afficher SETUP OK
```
Réglages machine (bibliothèques B-roll / musique / SFX, Higgsfield oui/non) : `python3 $S/reglages.py` les affiche = `config.json` du skill (défauts du kit) écrasé par `~/Documents/Brain/00-Moi/reglages/supermonteur.json` (cette machine). DA de l'utilisateur : `~/Documents/Brain/00-Moi/reglages/da-montage.json`.
Dossiers : `<dossier>` = `dossier` de `~/Documents/Brain/00-Moi/marque.json` (sinon ~/Documents/Contenu) ; `<sorties>` = son `sorties` (sinon `<dossier>`).
Annoncer la durée au lancement et à la fin (titre + sous-titres : ~1 min ; avec rendu : 2 à 3 min pour 1 min de vidéo).

## Photos et vidéos de l'utilisateur
Seulement des images qu'il accepte : ses interdits (shooting, look, période) sont dans `feedback.md` et passent avant tout ; dans la bibliothèque B-roll, la période exclue des réglages (`brolls_periode_exclue`) est écartée par `scripts/broll_tri.py`. Vaut pour tout : site, carrousel, slides, montage, B-roll, cover, pub, référence Higgsfield.

## Ordre de lecture (dans le dossier du skill)
1. **`feedback.md`** = le SEUL carnet des retours de l'utilisateur. Il passe avant le reste ; si deux lignes se contredisent, la plus RÉCENTE gagne.
2. **`regles-experts.md`** (12 domaines d'experts sourcés). Partie A = à appliquer dans chaque plan ; parties B et C = seulement avec l'accord de l'utilisateur. Si un expert contredit `feedback.md`, l'utilisateur gagne.
3. Chez un client (`config.json` → `client` rempli) : **`mode-client.md`** puis `retours-client.md` (SES retours passent avant tout).
4. Après le brief : **UNIQUEMENT le fichier du style choisi** (ne pas lire les autres).
5. Étape 8 : `note-10.md` (31/10 : 9/10 minimum, juge L'Œil Gemini). Modifier un script ou rendu cassé : `moteur.md`.
6. Face cam validé étape par étape (« 5 passes », « passe par passe », reel qui a déjà fait des allers-retours) : **`methode-5-passes.md`** (1 passe = 1 aperçu, on attend « next »).

**LES 5 STYLES, LES SEULS (26/10, dicté par l'utilisateur ; renommés le même jour : « c'est plus des formats mais des styles »).** On ne propose rien d'autre, toujours sous CES noms. **Les 5 ont TOUJOURS une musique** (26/10 : « ils ont tous une musique les vidéos »).

| Style | Ce qu'on voit | Fichier |
|---|---|---|
| 1. Dynamique (face caméra) | MIX à équilibrer de 4 plans : split screen (face cam + animation), face cam seule, carton plein écran en dégradé propre, animation plein écran | `styles/face-cam.md` |
| 2. Minimaliste (clip, FAQ, selfie) | titre ou question qui RESTE jusqu'à la fin + sous-titres + musique, rien d'autre | `styles/raw.md` |
| 3. Comparatif (tier list, mauvais / bien / excellent, comparaison en T) | sous-titres + fondu sombre au-dessus de la tête avec le titre + le tableau | `styles/montage-viral.md` |
| 4. Interview | MIX split screen (les 2 personnes) + plein écran sur celle qui parle (déjà établi) | `styles/a-plusieurs.md` |
| 5. Autre | style perso configuré, ou copié d'un créateur (`style_createur.py`, mémoire style-createur) ; les anciens styles y sont rangés : voix off `styles/voix-off.md`, green screen `styles/green-screen.md`, B-roll + texte `styles/broll-texte.md`, tableau sur le mur `styles/tableau-mur.md` (interne) | selon le choix |

**Après le style : les cases à cocher, sur le 1er écran de SuperMonteur** (`devine-format.md` 3 bis, 02/11 : plus dans le chat) : il garde tout (« La totale ») ou décoche (ex. Minimaliste sans le titre). Musique toujours là.

## ORDRE RAPIDE : 1 SEULE PAUSE POUR L'UTILISATEUR (21/10, après Titanic : 87 min pour 1 reel)
1. **« Monte cette vidéo » = j'ouvre SuperMonteur, et le chat ne pose AUCUNE question de style** (02/11, l’utilisateur : « ne propose pas à la fois le style dans Claude chat et dans SuperMonteur »). Le style, les cases et « Monter le reel » se font sur son 1er écran, qui devine et entoure le style conseillé. Dans le chat : une ligne, puis un seul bouton « Suivant » pour le moment où ses retours sont faits (`mcp__ccd_turn__wrap_up`). DA = la sienne, ambiance = choisie par moi d'après le sujet. Le brief de `workflow.md` ne sert que pour un client.
   **Quand il clique « Suivant » dans le chat** : lire `etat.json` du reel. `statut` = `correction` : Claude corrige déjà, je ne relance rien. Sinon : `POST http://localhost:8801/api/suivant/<id>` (même effet que le bouton de l'écran), et l'ouvrier remonte la version suivante. Puis de nouveau un seul bouton « Suivant ». Validation et publication : boutons de l'écran. Consigne donnée dans sa demande (ex. un titre) : SuperMonteur ne la reçoit pas, je l'écris dans `plan.json` et je la monte à ce même « Suivant ».
2. **Dérush** (`workflow.md`, étapes 1 à 3) → durée exacte et seconde de la punchline connues. **29/10 21h32 : Derush Lab RETIRÉ** (l’utilisateur : « enlève le Derush Lab de SuperMonteur et reviens comme c'était avant, parce que c'était ça, le problème ») : le dérush part direct au montage, dans SuperMonteur comme dans un chat. Ne plus lancer cockpit.py --lab avant de monter.
3. **En même temps** : les B-rolls (seulement s'il en veut, choisis par moi, `brolls.md`) ET la musique (`musique.md`).
**28/10 nuit : l'appli SuperMonteur est CODÉE** (écran 0 style → montage → retours → Publier, Ma DA en tiroir) : `~/Documents/SuperApps/supermonteur/` ; « corrige mes retours » = mode d'emploi `apps/supermonteur/CLAUDE.md`.
4. **La pause = l'écran Retours de l'appli** (façon Cut Notes, Apple clair) : vidéo + retours accrochés à l'image (écrire ou dicter), « Corrigé ✓ ▶ Revoir », « Suivant : corrige mes retours » / « C'est parfait, on publie », « Ma DA » en tiroir, puis Publier (Metricool branché : 5 réseaux dont LinkedIn activés, Publier maintenant / Programmer / Juste télécharger ; pas branché : Télécharger seul). Les 5 styles ET leurs aperçus respectent la zone interdite d'Instagram (haut 270, bas 1480, côtés 65, 120 à droite sous 1100 px). Règles complètes : Brain `01-Projets/superda-supermonteur.md`.
5. **Titre + sous-titres seuls (rien d'autre dans plan.json) : `python3 $S/express.py .`** (29/10, PAR DÉFAUT, validé par l’utilisateur) = même découpage des sous-titres, même mix, même Gardien, mais sans rendu Chrome : IMG_6945 en 1 min 3 s au lieu de 6 min 9 s. Il sort en code 2 si le plan a autre chose -> monte.sh. SuperMonteur (monter.py) le choisit seul.
   Sinon **`bash $S/monte.sh .`** = toute la partie machine d'un coup (B-rolls, composition, Gardien AVANT rendu, 1 rendu, mix, Gardien final, planche). S'il s'arrête avant le rendu : corriger plan.json et relancer, sans rien rendre. Pendant le rendu : RIEN de lourd à côté (pas de Suno, pas de Chrome qui travaille : Mac 8 Go, 1er rendu de Titanic = 15 min au lieu de 3).
6. **Validation** : la vidéo finale + la note /10. La publication se fait dans un autre chat (Le Publieur), pas dans le chat du montage. Les réparations d'outils aussi.

## Non négociable, tous les styles (détail : `cahier-des-charges.md`)
- Images et vidéos générées par IA : JAMAIS, dans aucun style.
- Zones mortes Instagram : `node $S/zones.mjs .` attendu « OK : 0 ».
- Jamais de coupe au milieu d'une phrase. Cuts au ras de la voix entre deux phrases, queue du mot entière (30/10).
- Zéro silence audible, zéro micro-coupure, chaque plan ≥ 2 s ou phrase entière.
- Jamais d'étalonnage ni de traitement du son du rush sans sa demande.
- Le Gardien est BLOQUANT : `python3 $S/gardien.py .`, un seul ❌ = on corrige, JAMAIS on livre.
- Rush renommé après la v1 (`renommer_rush.py`, SuperMonteur le fait seul).
- Note `note-10.md` obligatoire. Livraison : la vraie vidéo seulement.

**Règles de travail (comme tous les employés)** : ne publie rien, n'envoie rien (Le Publieur, après le OK). Une info absente du Brain ou du rush : dis « je ne l'ai pas », ne l'invente pas. Ce que seul l'utilisateur peut faire (retourner une prise, brancher son disque externe) : 1 ligne dans son fichier `actions` (00-Moi/marque.json ; vide : dis-le dans le chat), sans doublon. Reel livré : 1 ligne en bas de ~/Documents/Brain/log.md. En cas d'échec (rendu raté, Gardien bloqué, outil manquant) : une ligne dans ~/Documents/Brain/04-Audits/erreurs-taches.md (date, tâche, erreur) et dis-le en une ligne.

**Après chaque reel : boucle feedback** (`workflow.md`, étape 9) : chaque retour = 1 ligne datée dans `feedback.md` et dans le carnet Brain `00-Moi/regles-agents/supermonteur.md`, le fichier de règles concerné corrigé pour qu'il n'y ait jamais deux versions, et une note mesurable = 1 contrôle de plus dans `gardien.py`.
