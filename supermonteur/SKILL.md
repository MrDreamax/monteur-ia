---
name: supermonteur
description: Le Monteur. Monte un rush en reel 9:16 Instagram prêt à poster pour Cyril ou un client - 8 styles (face caméra en 3 degrés, à plusieurs, voix off, green screen, montage viral, B-roll + texte), mode client. Use when "monte-moi ce rush", "monte ce reel", "sous-titre cette vidéo", "sous-titres", "montage", "face cam", "podcast", "visio", "voix off", "green screen", "tier list", "comparaison en T", "à faire / à ne pas faire", "mauvais bien excellent", "B-roll + texte", "texte sur b-roll", "lis la légende", "monteur", "supermonteur".
---

# SUPERMONTEUR : rush → reel premium

Référence de qualité : le reel monté par un vrai monteur, validé par Cyril le 12/10/2026 (rush test `/Volumes/SSD Dreamax/1 - Contenu/2 - Vidéos finies/2026-08-26 Reels business - Rush vidéos virales.mp4`, réf monteur copiée dans `~/.claude/skills/supermonteur/ref/FINAL.mp4`). Chaque montage doit tenir la comparaison.

```bash
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"
S=~/.claude/skills/supermonteur/scripts
$S/setup.sh            # 1re fois sur une machine : doit afficher SETUP OK
```
Réglages machine (bibliothèques B-roll / musique / SFX, Higgsfield oui/non) : `~/.claude/skills/supermonteur/config.json`.
Annoncer la durée au lancement et à la fin (~5 min pour 40 s de vidéo).

## Ordre de lecture (dans le dossier du skill)
1. **`feedback.md`** = le SEUL carnet des retours de Cyril. Il passe avant le reste ; si deux lignes se contredisent, la plus RÉCENTE gagne.
2. **`regles-experts.md`** (12 domaines d'experts sourcés). Partie A = à appliquer dans chaque plan ; parties B et C = seulement avec l'accord de Cyril. Si un expert contredit `feedback.md` ou le Style Lab, Cyril gagne.
3. Chez un client (`config.json` → `client` rempli) : **`mode-client.md`** puis `retours-client.md` (SES retours passent avant tout).
4. Après le brief : **UNIQUEMENT le fichier du style choisi** (ne pas lire les autres) :

| Style | Fichier |
|---|---|
| Face caméra · sous-titres | `styles/face-cam-soustitres.md` |
| Face caméra · minimaliste | `styles/face-cam-minimaliste.md` |
| Face caméra · high prod | `styles/face-cam-high-prod.md` |
| À plusieurs (podcast, visio, split screen, débat) | `styles/a-plusieurs.md` |
| Voix off | `styles/voix-off.md` |
| Green screen | `styles/green-screen.md` |
| Montage viral (T, mauvais / bien / excellent, tier list) | `styles/montage-viral.md` |
| B-roll + texte | `styles/broll-texte.md` |

5. Étape 8 : `note-10.md`. Modifier un script ou rendu cassé : `moteur.md`.

## 0. BRIEF AVANT TOUT MONTAGE (obligatoire, en boutons QCM via AskUserQuestion, option recommandée en 1er)
Toujours premium. Ne monter qu'après les réponses.
1. **Style** : proposer les 4 styles qui collent au rush (4 boutons max, le reste via « Autre ») parmi Face caméra / À plusieurs / Voix off / Green screen / Montage viral / B-roll + texte. Le montage viral se décide au script (la vidéo doit être écrite pour). Selfie (= minimaliste) et démo filmée : SUPPRIMÉS par Cyril le 16/10, ne plus les proposer.
2. **Degré** (face caméra, Cyril 16/10) : option recommandée = celle qui colle à la vidéo.
   - **Sous-titres** → dérush + sous-titres + musique, rien d'autre. Conseil court, volume (7 → 14 reels/sem).
   - **Minimaliste** → cartons typo mot par mot, icônes au trait, captures + cercle à la main. Explication avec chiffres, preuves, captures.
   - **High prod** → chiffres géants, B-rolls, preuves, CTA. Reel phare. + question **Style** : Sobre / Dynamique.
3. **DA** : seulement chez un nouveau client (DA existante `da/<prenom>.json` / nouvelle DA). Cyril = `da/cyril.json`, ne pas demander.
- **Format** : 9:16 seulement, ne pas poser la question. 16:9 PAS GÉRÉ (Cyril « plus tard » le 12/10) : si le rush est en 16:9 (hors podcast / visio), le dire et monter en 9:16.
- **Images générées** : Higgsfield, sans demander, SEULEMENT là où le style en prévoit (high prod, green screen, icônes de tier list). Jamais en sous-titres, minimaliste, à plusieurs, voix off ; B-roll + texte : jamais avec un visage. Modèles Gemini (Nano Banana) inclus dans Higgsfield : pas d'outil Gemini séparé (sauf client sans Higgsfield, `mode-client.md`).

## LE PROCESS (refondu le 13/10 après un 4/10 : « la DA n'est pas en cohérence avec la vidéo, on regarde le montage au lieu de l'idée »)
Étalon : la version de son monteur humain quand elle existe (`/Volumes/SSD Dreamax/1 - Contenu/2 - Vidéos finies/Reels business/<titre>.mp4`, Meta Verified = 7,5/10 pour Cyril : animations, SFX et tracking bons ; musique pas adaptée, sous-titres un peu gros, assez basique). Le but : faire mieux que lui.
1. **Univers = le RUSH.** Regarder le rush d'abord : décor, lumière, couleurs, tenue. Tout ce qu'on ajoute doit sembler filmé dans CETTE pièce (`plan.colors` pour coller). La charte Quiet Luxury (champ `charte`) sert au TOURNAGE et au branding, jamais plaquée au montage sur un rush d'un autre univers.
2. **Illustrations DANS la scène, accrochées aux gestes** (tracking `track.py`) : badge au bout du doigt quand il pointe, logos à côté de la tête sur « réseaux », mot derrière la tête. Objets réels = vraie forme et vraie couleur, détourés, éclairés comme la scène. Jamais une scène séparée (bureau noyer, papier crème... = 4/10).
3. **B-rolls = ses vrais plans, BRUTS, STABLES, courts** (1-2,5 s, `broll.py steady` / `"from": "auto"`), jamais de filtre. Peu de temps hors de son plan (monteur : ~8 s sur 39 s). Preuves = vrais objets (vraie capture de commentaires, vrai profil).
4. **Sous-titres** (verrouillés dans Style Lab le 13/10, détail `~/Documents/Stratosphere/style-lab/STYLE.md`) : police de la DA (`fonts.sub`, `subSize`, `subTrack` si fournis ; Cyril = Montserrat 700, 52 px, espacement 0,5 px, Oswald testé et rejeté le 13/10) ; **mot fort = serif italique blanc 132 px, SEUL à l'écran** (la phrase s'efface, il arrive seul quand il est dit, jamais de mot normal à côté), groupe de 1 à 3 mots possible ; entrée fondu + petite montée ; hauteur **au niveau du col, jamais sur le cou ni le menton** (`subzone.py` : menton + 0,41 x visage, Meta Verified = 1310 px).
5. **Serré, sans gadget** : dérush serré (monteur 42 → 39 s, 276 mots/min) ; REC, bandes noires, mot serif géant : seulement si la vidéo le justifie.
6. **Comparer à l'étalon avant d'envoyer** (high prod) : planches 1 i/s côte à côte + `analyse_ref.py` sur les deux (coupes, débit, SFX sur les coupes ~60 %). Musique seule 15-17 dB sous la voix (16/10 ; les ~25 dB du monteur étaient trop bas).
**DA de la personne** : `da/<prenom>.json` (polices, couleurs, ambiances musicales, style B-roll + prompt Higgsfield). Cyril = `da/cyril.json` (défaut). Nouveau client sans fiche → `mode-client.md`. Mettre `"da": "<chemin>"` dans plan.json pour un client. Tout prompt Higgsfield finit par `broll.prompt_higgsfield`.

## Le cahier des charges (non négociable, tous les styles)
- **Zones mortes Instagram (Cyril 16/10, choix « zone organique »)** : aucun texte ni élément animé au-dessus de **270 px** (14 %, chiffre officiel Meta Ads Guide Reels), à moins de **65 px** des bords (6 %), sous **1 480 px** (pseudo + légende), et sous-titres entre 120 et 960 px en largeur (boutons à droite). Les fonds / voiles / décors peuvent déborder. Les 35 % du bas de Meta (1 248 px) ne valent que si un reel part en pub. **Contrôle** : `node $S/zones.mjs .` après build (et après `viral.py inject`) = chaque texte (encre réelle) et élément animé, toutes les 0,25 s ; attendu « OK : 0 ». Détail par élément : `moteur.md`.
- Couper silences et répétitions. **Jamais de coupe au milieu d'une phrase.** Enlever la respiration en début de phrase.
- **Zéro silence audible** (Cyril 17/10 v2 : pire qu'une coupe) : pas de `--pause`, une hésitation sous un B-roll se coupe, une reprise hésitante = prendre la prise fluide.
- **Zéro micro-cut** (Cyril 17/10, Tesla : « micro rush inutile qui saccade ») : aucun bout de face cam < 0,6 s entre deux coupes, aucune coupe qui ne gagne que 0,1-0,3 s (derush.py le fait seul : MINSEG / MINCUT). Chaque début / fin de B-roll se cale à 0,02 s sur la coupe de dérush voisine (`cut.segments.json`) : sinon on voit la tête 0,1 s puis un saut. B-rolls enchaînés : fondu 0,3 s, pas 3 coupes sèches.
- Rush **déjà dérushée** seulement si Cyril le dit ou si aucun blanc > 0.2 s → sauter l'étape 3. Sinon on resserre (13/10 : le rush Meta Verified avait des blancs de 0,3-0,46 s, son monteur l'a passée de 42 à 39 s, plus vivante).
- **Musique TOUJOURS ÉMOTIONNELLE** (Cyril 14/10 puis 16/10, tous styles) : motivation, tristesse, nostalgie, espoir… une émotion qu'on SENT (mélodie piano / cordes qui monte). Jamais une nappe neutre, d'ambiance ou de suspense sans mélodie (« Your Greatest Adversary » sur la conf = refusé). Sujet grave = piano lent qui monte ; business / tension = **dark cinématique** (orchestral hybride épique sombre, cordes) avec une COUPURE puis une FRAPPE sur la punchline (« Invictus ») ; la motivation lumineuse (« It Can Be Done ») a été remplacée. Le champ `music` de la DA n'est qu'un indice. Musique et SFX : **Epidemic Sound, toujours** (connecteur MCP, plan Creator = organique OK, PAS pub Meta). Jamais la bibliothèque SSD (`music_root`) pour la musique (Cyril 13/10). SFX minimalistes.
- **Son Noctivum** (Cyril 18/10, il adore @noctivum sur TikTok : phonk sombre + chœurs épiques sous une voix grave) : pour les reels mindset / tension / motivation sombre, piocher d'abord dans `<music_epidemic>/Noctivum-Phonk-Sombre/` (PIXEL8, Outbreak, INFERNO, RESILIENCIA, HEALING, Eagle ; HEALING = le plus calme sous la voix). Ne pas reprendre le morceau du reel précédent. Ses originaux (FRACTURE - RFTN, Dies Irae - Aloboi, Cyberwave - Mazzo, BRIGHTNESS - The Afridi, liste dans `ORIGINAUX-Noctivum.txt`) ne vont JAMAIS dans le montage : pas de licence. Dans la fiche de publication, proposer « version originale : ajouter <titre> dans l'appli Insta en organique » quand Cyril préfère l'original.
- Police minimaliste : Montserrat. 2e police pour les mots importants : **serif italique** (Instrument Serif).
- **Jamais de B-roll juste pour mettre du B-roll** (Cyril 13/10 : « des fois ça sort de la vidéo »). Par défaut AUCUN. Un B-roll seulement quand il montre ce que la tête ne peut pas montrer (lieu, résultat, objet, action dite à cet instant). Dans le doute : face cam. S'il y en a : peu mais réparti, jamais groupé dans un seul passage.
- **Visuels générés = Higgsfield** (Cyril 13/10, choix « mix »), seulement dans les styles qui en prévoient : VIDÉO générée seulement pour un gros moment SANS visage (hook, preuve : Cinema Studio Video 3.0 / Seedance 2.0 / Kling 3.0, ~6 crédits / 5 s), IMAGES animées par le moteur pour le reste (Nano Banana 2 / GPT Image 2, < 1 crédit). **Jamais de plan de Cyril généré** (Cyril 13/10 après Meta Verified, refsheet `ref/cyril-refsheet-lunettes.png` comprise) : partir d'un de SES vrais B-rolls (amélioré Seedance si utile). Ses vrais plans d'abord, Higgsfield pour ce qu'ils ne peuvent pas montrer. Zéro chrome, zéro néon, zéro glow ; 1 visuel test validé avant le reste. Annoncer les crédits dépensés.
- **Jamais saccadé** (Cyril 13/10) : pas de zoom brusque, pas de changements de plan trop rapides. Le moteur ne zoome que lentement (1,4 s) quand l'idée change. **Jamais la tête visible une fraction de seconde entre deux pleins écrans** : enchaînés direct ou ≥ 1,5 s de face cam (garde-fou anti-flash dans build.mjs, il affiche ce qu'il corrige).
- **Méthode (Cyril 13/10, pour lui ; chez un client : `mode-client.md`)** : AVANT de monter et AVANT chaque modification, montrer le plan (moments, visuels, sons, silence) et attendre son OK. Corriger par retouches ciblées (remix audio seul, plan.json + re-rendu) au lieu de tout regénérer.

## Workflow commun (le fichier du style dit quelles étapes il change)
Un dossier par reel, tout se lance depuis ce dossier.

**1. Caler en 1080×1920, 30 i/s + recadrer si filmée trop large** (choix Cyril 13/10 : automatique ; montage viral : SANS `cadre.py`)
```bash
python3 $S/cadre.py <rush ORIGINALE, 4K> --apply     # ~45 s -> clip.mp4
```
Rush filmé large (yeux sous 40 % ou visage < 28 % de la largeur) → recadrage fixe depuis la 4K : yeux à 35 %, visage à 33 % (cadre serré du rush « vidéos virales », reel validé 7,75/10). Déjà serrée → simple mise au format. Toujours partir du rush ORIGINALE 4K (zoom > 1,10 sur du 1080 = flou ; le script plafonne alors à 1,10). Plan large de scène (conférence, écran géant derrière) : cadrer à la main (voir `feedback.md` 16/10).

**2. Transcrire** (Whisper local, gratuit ; chaque mot est recalé sur l'énergie de la voix, utile en salle qui résonne)
```bash
python3 $S/transcribe.py clip.mp4 words.json
```

**3. Dérusher** (sauf rush déjà dérushé)
Lire la transcription. Repérer les répétitions et phrases ratées : on garde la **dernière** prise. Les noter en plages d'indices de mots dans `drop.json` (`[[12,18]]`, ou `[]`).
```bash
python3 $S/derush.py clip.mp4 words.json cut.mp4 --drop drop.json
python3 $S/transcribe.py cut.mp4 words.json && mv cut.mp4 clip.mp4      # on retravaille sur la version coupée
```
**Entrée / sortie** (Cyril 16/10 : « ça coupe un peu sec au niveau du hook et à la fin ») : le dérush garde 0,15 s avant le 1er mot et 0,6 s après le dernier (`--lead` / `--tail`). Il écrit aussi `cut.words.json` = la transcription du RUSH recalée sur la version coupée (souvent meilleure qu'une transcription refaite sur le montage coupé) : on peut la prendre au lieu de retranscrire.
Le script ne coupe que dans les blancs entre deux mots : fin de phrase = blanc + respiration supprimés ; milieu de phrase = blanc resserré à 0.15 s. Chaque coupe : micro-fondu son de 0,03 s (anti-clic) et plages calées sur la grille des images (image et son exactement de la même durée, la bouche ne se décale jamais). Testé 13/10.
**LA pause avant la punchline** (s'il y en a une ; la musique continue dessous, Cyril 17/10) : repérer la punchline AVANT le dérush et ajouter `--pause <indice du mot punchline>` : la vraie pause avant ce mot est gardée (jusqu'à 0,9 s). Pas de pause dans le rush = pas de silence (le dire à Cyril : marquer un temps avant la phrase choc au tournage).

**4. Écrire `plan.json`** en lisant la transcription (c'est là que se joue la qualité). Champs communs (le fichier du style ajoute les siens) :
```json
{
  "cam": "clip.mp4", "words": "words.json",
  "fixes": {"boulettes": "bullet"},
  "keywords": ["dangereux", "illégal", "hook", "succès", "virales"],
  "music": {"src": "<config music_epidemic>/<ambiance>/<titre>.wav", "from": 0, "fin": "naturelle"},
}
```
- **fixes** : relire TOUTE la transcription et corriger les erreurs de Whisper (`{"boulettes": "bullet"}`). Obligatoire : une faute dans un sous-titre = reel raté. `fixes` change CHAQUE occurrence du mot (17/10 : « Dis » → « 10 » aurait aussi changé « tu dis oui ») : un mot courant se corrige directement dans `words.json` (son indice).
- **keywords** : 6-10 mots forts, ou groupes de 2-3 mots (`"badge bleu"`) → serif italique blanc 132 px, affichés SEULS à l'écran (les petits mots devant restent dans le bloc d'avant). Jamais en couleur.
- **title** : `{"l1": "Le badge bleu Meta", "l2": "une arnaque ?", "start": 0, "end": 4}` = titre-question pendant le hook (petites MAJUSCULES + serif italique, voile sombre, fondu ; `top` pour le placer, ex. 1300 = en bas quand la tête touche le haut du cadre). **Règle Cyril (Style Lab) : vidéo AVEC titre = ni mot fort ni mot géant ; vidéo SANS titre = mots forts + mots géants derrière la tête.** Avec un titre, `keywords` et `bigwords` sont ignorés sur toute la vidéo (le moteur le dit). Proposer le titre dans le plan de chaque reel.
- **cta** : `{"start", "end", "word": "HOOK", "count": "1 284", "user": "toi", "comments": [["pseudo", "texte", "2 min"], ...]}` = sur « commente MOT » : vraie feuille de commentaires qui monte du bas, le mot se tape lettre par lettre (clavier qui s'allume), puis se publie en haut de la liste. Commentaires par défaut = des gens qui tapent le mot (pas de faux témoignages).
- **music** : d'abord l'ÉMOTION à faire ressortir (jamais « neutre », « ambiance », « suspense » seul), puis Epidemic : `SearchRecordings` (terme d'émotion, `vocals: false` ; pour coller à une réf : `SearchExternalReferences` → recherche par id Spotify), présélection 10-15 titres → `EditRecording` à la durée exacte (`forceDuration`, `preferenceRegions` sur le meilleur passage) → `DownloadRecordingEdit` (WAV) dans `music_epidemic/<ambiance>/` avec une ligne dans `_LICENCE.txt` → `"fin": "naturelle"` (le morceau finit tout seul, pas de long fondu). Ne pas reprendre la musique du reel précédent. Niveau : `target` (niveau de la musique SEULE en LUFS, sous la voix à -14 ; défaut `config.json` → `music_target_lufs` = -29 depuis le 16/10 : à -31 la musique « n'existait pas » sur un morceau contrasté ; elle est aussi resserrée, LRA 6, pour ne jamais disparaître dans ses creux ; `lra: 11` pour garder une coupure voulue) ; `lufs` n'est plus qu'un point de départ, `mix.py` mesure et recale chaque segment. La musique est creusée de -4 dB vers 1,2 kHz (place pour la voix) et s'efface de 5 dB pendant ~1 s sous chaque gros effet (impact, sub drop, plein écran, CTA). Historique validé : Hensonn « Sahara » (12/10), Epidemic « Estimations » (13/10), « Invictus » (16/10, conf). Musique perso de Cyril (« Grounded », hors Epidemic) : gardée sur la conf seulement (vidéo à part, Cyril 16/10) ; ailleurs, Epidemic.
- **Changement de musique** (Cyril 13/10) : quand le sujet, l'ambiance ou le plan change DANS la vidéo, `music` devient une liste de segments `[{"src", "from", "start", "end", "emotion"}, {..., "transition": "douce" | "sec"}]`. Douce = fondu enchaîné 1,5 s ; sec = coupe nette + impact. Le choix suit l'émotion voulue. Un seul sujet du début à la fin → un seul morceau.
- **Frappe de la musique sur le tournant** (voix off 17/10) : trouver la frappe dans le morceau (enveloppe à 0,05 s) et la caler sur le mot du tournant. `EditRecording` avec `requiredRegionsAtOffsets` : offset > 0 = souvent aucun edit, offset 0 = la frappe glisse de 0,3 à 1 s → TOUJOURS remesurer la frappe sur le WAV reçu ; sinon morceau entier (`DownloadRecording`) + `from`. Couper le plan pile sur la frappe ; sub drop calé dessus en `"kind": "subdrop-frappe"` (la musique ne s'efface pas : la frappe EST la musique). Morceau très contrasté (piano intime puis orchestre) : 2 segments du même morceau, `"transition": "sec"` sur la frappe, une `target` chacun, puis Demucs hors SFX = 15-17 dB sous la voix dans CHAQUE partie.
- **silences** : NE PLUS UTILISER (Cyril 17/10, Tesla : « pause sans musique, on dirait que c'est un bug »). La musique ne se coupe JAMAIS. On garde la vraie pause avant la punchline (`--pause` au dérush) et on cale la FRAPPE de la musique sur le mot punchline (voir « Frappe de la musique sur le tournant »). Ancienne règle (musique coupée 0,6-0,9 s + riser) : abandonnée.

**5. Ajouts du style** : voir le fichier du style (B-rolls, images, tableau, source…).

**6. Compo + rendu + son**
```bash
node $S/build.mjs --plan plan.json --out index.html
npx --yes hyperframes@0.6.81 lint                                # 0 erreur (warning "overlap 0 s" sur #camwrap = sans effet)
node $S/zones.mjs .                                              # zones mortes Insta : « OK : 0 » attendu (~3 s)
npx --yes hyperframes@0.6.81 render . -q high                    # ~2 min 30 pour 40 s
python3 $S/mix.py plan.json renders/<x>.mp4 clip.mp4 final.mp4   # voix (config voice_lufs, -14) + musique recalée par morceau + SFX auto
```
(High prod : `matte.py` avant le build, voir son fichier.)
**Son de salle** (conférence, micro de scène capté par la caméra) : `python3 $S/voix_propre.py clip.mp4 voix/doux.wav words.json` = sa voix ORIGINALE + EQ douce vers sa voix studio (`config.voice_ref`), ±3,5 dB max (Cyril 16/10 : la version forte Demucs + expandeur + exciteur rendait sa voix « bizarre et déformée », « +10 dB c'est trop, +3 ou +4 »). `--fort` seulement avec son accord. Puis `mix.py ... voix/doux.wav final.mp4`. Client : sa voix studio en `--ref`.
**Choix de la musique à l'oreille** (Cyril 16/10 : « je sais pas comment te dire quelle bonne musique prendre ») : dès que la musique est refusée une fois, monter 4 versions A-D de SA vidéo (une musique chacune, toutes calées sur la punchline, même voix), copies légères envoyées ensemble, il répond une lettre. Ou il donne un titre / lien Spotify qu'il aime → `SearchExternalReferences` → équivalent Epidemic.
**Couleur** (seulement si Cyril le demande, 16/10) : 2 options en avant / après sur 2 images AVANT de rendre (`couleur/avant-apres.jpg`), noirs P1 1-8 vérifiés (`lookstats.py`), puis `ffmpeg -vf "$(cat couleur/<option>.txt)"` sur clip.mp4 → clip_grade.mp4 = `plan.cam`. Validée sur la conf : « Naturel » (peau plus chaude, violet calmé).
**Écran noir au départ** : corrigé dans mix.py le 16/10 (la vidéo commençait à 0,021 s, QuickTime / iPhone / Instagram n'avaient aucune image à 0 s). Contrôle : ffprobe `start_time` = 0.

**7. Vérifier (obligatoire avant de dire "c'est fait")**
```bash
ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt,start_time -of compact final.mp4   # h264 1080x1920 yuv420p + aac, start_time 0
ffmpeg -y -v error -i final.mp4 -vf "fps=2,scale=150:-1,tile=10x8" -frames:v 1 check.jpg
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep " I:" | tail -1     # final ~ -14 LUFS
```
`mix.py` mesure CHAQUE morceau sous la voix et le recale tout seul sur sa cible (`target`, défaut -29 ; -27 sur la conf) à ±1 LU ; il affiche une ligne par morceau (OK / trop fort / TROP BAS) puis « final : -14 LUFS, crête vraie ≤ -2 dBTP ». Pour un CTA plus calme : `"target": -33` sur le dernier segment. **Mesurer la musique SEULE dans le final (Demucs)** : 15-17 dB sous la voix, sinon on ne l'entend pas.
Regarder `check.jpg` : un seul bloc de sous-titre à la fois, tête devant chaque chiffre, listes lisibles, B-rolls répartis régulièrement, pas de visage coupé. Échec → corriger, refaire.

**8. Note /10** : `note-10.md` (obligatoire).

**9. Boucle feedback (après chaque reel)**
Source : Christian Peverelli, montage automatisé avec Claude Code (règles accumulées par retours).
1. Retours = **Cut Notes** : envoyer un lien où Cyril (ou le client) tape ses notes accrochées à l'image exacte. Process : `outils/cut-notes/CUT-NOTES.md` (1 artifact par vidéo, URL dans `cut-notes.url` du dossier du reel ; « done » = lire les notes, corriger, répondre sous chaque note, round suivant). « done » avec 0 note ≠ validé : demander en une ligne s'il a laissé des retours.
2. Corriger le reel (retouches ciblées).
3. Chaque retour ou note (« 6/10, musique trop forte ») = **une ligne datée dans `feedback.md`** (règle générale + historique des notes), et une ligne dans le carnet Brain `00-Moi/regles-agents/supermonteur.md`. Si la règle change une règle de ce skill, corriger le fichier concerné (SKILL.md ou le fichier du style) pour qu'il n'y ait jamais deux versions. Une erreur corrigée ne revient jamais.
