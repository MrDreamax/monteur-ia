---
name: carrousel
description: Le Carrousel. Carrousel Instagram de 8 slides (1080x1440) au modèle validé - bleu-blanc, vraies photos de l'utilisateur + illustrations 2D SVG, jamais d'image IA. Livre PNG + légende, ne publie jamais. Use when "carrousel", "carousel", "fais-moi un carrousel", "carrousel de la semaine", "transforme ce reel en carrousel", "carrousel sur X", "carousel maker".
---

**RÈGLE 28/10/2026 : premier geste de toute demande de carrousel = ouvrir SuperCarrousel** (`bash ~/Documents/SuperApps/supercarrousel/lancer.sh` puis http://localhost:8797 dans le navigateur intégré), avant toute question.


## Règle n°1 : maquette d'abord (19/10/2026)
Avant de coder, monter, générer en volume ou exécuter quoi que ce soit : montre d'abord une MAQUETTE (une image, un écran, 1 slide, 10 s, 3 lignes) et attends que l'utilisateur la valide. Toujours PLUSIEURS versions (3 en général, ma recommandée en premier, chacune nommée en 3 mots) qui CHALLENGENT la direction artistique : 3 directions vraiment différentes (couleurs, typo, mise en page, ambiance), jamais 3 variantes du même style. Vote : un seul bouton « Garder celle-ci » (il en garde une, les autres sont jetées) + une note facultative, rien d'autre (pas de Peut-être ni de Jeter). DEUX rounds avant validation : round 1 = aspect global, styles vraiment différents ; round 2 = plein de détails de la maquette gardée (plusieurs parties dans le même round, une option gardée par partie). Vaut aussi pour le montage vidéo. Pour passer au round suivant, l'utilisateur dit « suivant » (plus « done ») : le bouton s'appelle « Suivant ». Pas de validation = pas d'exécution. Vaut pour tout : site, tunnel de vente, montage, PDF, scripts, pubs.

# Le Carrousel : une grande idée, 8 slides, la DA de la marque

Modèle validé le 16/10/2026 après 5 versions refusées. Ne pas le redécider : l'appliquer.
Référence visuelle : la planche que nomme ton carnet (le carrousel validé).
Référence technique : `exemples/exemple-v4.json` (le skill la reconstruit au pixel près).

## Photos et vidéos de l'utilisateur
Seulement des images qu'il accepte : ses interdits (shooting, look, période) sont dans son carnet et passent avant tout. Vaut pour tout : site, carrousel, slides, montage, B-roll, cover, pub, référence Higgsfield.

## Carnet d'apprentissage
- Avant de commencer : lis `~/Documents/Brain/00-Moi/regles-agents/carrousel.md`. Ses règles passent AVANT ce fichier.
- Si l'utilisateur corrige, note ou refuse ton travail (même en passant) : ajoute UNE ligne dans ce carnet, `JJ/MM/AAAA · correction · ce qui n'allait pas → règle`. Si elle contredit une ancienne, remplace l'ancienne. Dis-le en une ligne : « Noté dans mon carnet : ... ».

## MAJ 26/10/2026 : SuperCarrousel (maquettes validées, CODÉ le 28/10/2026)
**L'appli existe** : `~/Documents/SuperApps/supercarrousel/` (http://localhost:8797, lancer `bash .../apps/supercarrousel/lancer.sh` ; mode d'emploi côté Claude : son `README.md` et `python3 sc.py a-faire`). Pour l’utilisateur, un carrousel passe par elle : je lis ses demandes avec `sc.py`, j'écris la description, elle rend avec ce moteur.
Le carrousel se fera dans l'interface **SuperCarrousel**, qui lit la DA de SuperDA (onglet Carrousels). Règles complètes : `~/Documents/Brain/01-Projets/superda-supermonteur.md`.
- 3 départs : **Un reel** (fichier OU lien Instagram / TikTok / YouTube : images + texte du reel, voir 3 bis) · **Un carrousel à reprendre** (lien d'un carrousel qui marche, 29/10 : FIDÈLE à son concept et son style : mise en page, couleurs, ordre, rythme ; on change SEULEMENT la police et les mots ; images : je les propose ou je les demande à l’utilisateur, slide par slide) · **Une idée** (sujet écrit ou dicté).
- Je fabrique tout d'un coup (pas de validation du texte avant), les slides apparaissent une par une.
- Puis écran de retours (une slide en grand, retour accroché à la slide, « Corrigé ✓ ▶ Revoir », « Suivant : corrige mes retours » / « C'est parfait, on publie ») ; « Ma DA » en tiroir.
- Publier via Metricool sur 4 réseaux (Instagram, TikTok en mode photos, Facebook, LinkedIn en document), jamais YouTube ; sans Metricool = Télécharger seul (images + 4 légendes). Légende écrite par moi, une par réseau. Toujours son OK avant de publier.
- **Plus d'alternance obligatoire photo / dessin** (26/10) : chaque slide prend le visuel qui sert son idée.
- Pas de nombre de slides imposé. Jamais de ponctuation seule en fin de ligne.

## MAJ 22/10/2026 : nouveau modèle style Apple (validé par l’utilisateur)
Remplace le tableau ci-dessous pour l’utilisateur : blanc, SF Pro, photo bord à bord + cheveux détourés qui dépassent, dessins sur cercle bleu clair, fin = 3 bulles iMessage. Branché dans le moteur le 22/10 : mettre `"style": "apple"` dans la description → `carrousel.py` appelle `scripts/apple.py` (rendu local par Chrome, **pas besoin d'Open Carrusel**, ~20 s pour 8 slides).
Exemple complet : `exemples/exemple-apple.json` (copier, adapter). Types : `cover` (kicker, title, photo, note), `photo` (title, body ou steps ; `"pop": false` si la personne est petite dans l'image), `art` (title, body, steps, ou `cta` + `cta_q` + `cta_line` pour la fin en 3 bulles). Note manuscrite : `note` + `note_pos`.
Le détourage ne garde que la tête au-dessus de la photo (mains et bruit effacés). Vérifier quand même le haut de chaque slide photo en grand.
Détail du style : `~/Documents/Brain/00-Moi/da-apple-livrables.md`.

## Le modèle (ce qui est validé)
| Élément | Règle |
|---|---|
| Format | 3:4, 1080x1440, 8 slides par défaut (6 minimum) |
| Ambiance | blanc + les couleurs de la marque (00-Moi/marque.json : `foncee` pour le texte, `principale` pour les accents). Appoint en petites touches : jaune #FFC845, corail #FF6B5B, menthe #2EC4A6, vert pomme |
| Polices | Montserrat 700 majuscules (couverture, CTA) + Instrument Serif italique (titres), Montserrat 500 (phrases) |
| Alternance | PAS obligatoire depuis le 26/10 : photo ou dessin selon l'idée de la slide (couverture = photo) |
| Photos | VRAIES photos de l'utilisateur (dossier `photos` de marque.json), variées (plusieurs shootings), teintes naturelles, légère touche bleue dans les ombres (`prep.py`) |
| Illustrations | 2D motion design dessinées en SVG (`art.py`) : fond blanc, grand cercle bleu très clair, aplats, 2 à 4 petits éléments déco |
| Interdit | images générées par IA (Higgsfield ou autre) : refusées le 16/10, « trop IA ». Pas de @, pas de numéro de slide |
| Couverture | photo + mot géant serif DERRIÈRE la tête + 1 ligne en majuscules, 7 mots max au total |
| Slides | 1 idée par slide : titre serif + 1 phrase courte (ou liste 1-2-3 de 3 lignes courtes). Jamais de pavé |
| Fin | « Commente MOT » + la ressource promise. Flèche de swipe partout sauf sur la dernière |

## Étapes (⏱ ~25 min : annonce-le au début, dis le temps réel à la fin)

### 1. La grande idée (une seule par carrousel)
Dans l'ordre : ce que l'utilisateur demande ; un sujet de la veille carrousels (`~/Documents/Brain/04-Audits/*veille-carrousels*.md`, on copie le sujet et la structure, jamais la posture) ; un script de reel validé (`06-Contenu/`) ; une vraie question de client (`06-Contenu/questions-clients-*.md`).
Le sujet doit toucher un problème de la cible de sa stratégie (00-Moi/strategie-contenu.md, ou celle que nomme son carnet).
Mot-clé de fin : un freebie qui EXISTE (sa stratégie ou son carnet les liste) ou son mot-clé (`mot_cle` de marque.json). N'invente jamais une ressource.

### 2. Le texte
- Lis d'abord `~/Documents/Brain/02-Formations/experts-copywriting-carrousels.md` (méthode Chris Do AIDA + titre ROT, fil par « … ») et `~/Documents/Brain/00-Moi/voix-contenu.md`.
- Couverture : écris 10 titres (Résultat, Objection ou Temps, chiffre si possible), garde le meilleur. Elle et la slide 2 doivent accrocher seules.
- Chaque slide ouvre la suivante (« … », question, « mais »). Une slide de preuve vers la fin.
- Preuves autorisées seulement : celles de son Brain (00-Moi/profil.md, son carnet) et des cas clients chiffrés SANS nom tirés du Brain. Rien d'inventé.
- Voix : celle de 00-Moi/voix-contenu.md, zéro gros mot, aucun concurrent nommé.
- Dernière passe : skill `anti-ia`.
- Légende : 4 à 6 lignes qui prolongent (pas un copier-coller des slides), finit par le CTA. 5 hashtags max.

### 3. Les photos (4 slides)
- Ses photos : le dossier `photos` de 00-Moi/marque.json (sinon ~/Documents/Contenu/medias/photos), rangé à plat, le mot-clé est dans le nom du fichier. Les mots-clés de ses shootings et ses interdits : dans son carnet.
- Jamais : vie intime, photos où quelqu'un d'autre est au premier plan, portraits retouchés ou possiblement IA.
- Planches pour choisir : `python3 scripts/planches.py <dossier_scratchpad> "<mot-clé 1>" "<mot-clé 2>"`, puis lis les planches.
- Chaque photo doit coller à SA slide (ex. preuve = scène devant une salle, posture = sourire en costume). Varie les shootings.
- Couverture : la tête doit laisser de la place au-dessus (« tête y≈ » entre 300 et 450 dans la sortie de `prep.py`).

### 3 bis. Pas de photos perso ? Les images viennent d'un reel (23/10/2026)
La plupart des gens n'ont pas de shooting : le carrousel se fait depuis un reel déjà tourné.
- Vidéo : le RUSH d'abord (avant montage, zéro texte sur l'image ; chez l’utilisateur `~/Documents/Montage/MONTAGES/<projet>/clip.mp4`, transcription `words.json` à côté). Le reel fini seulement s'il n'y a rien d'autre, et alors seulement des images sans texte sur le visage.
- `python3 scripts/reel2frames.py <video> <out>/_reel --words <words.json>` (~30 s) : 16 images nettes prises entre deux mots (bouche au repos), étalées dans le temps, + `00-candidates.jpg` (planche numérotée) + `texte.txt` (la transcription).
- Lis la planche, garde 4 images variées (gestes différents, pas les yeux fermés, pas la main devant le visage), mets-les en `"src"` des `photos` d'une description `"style": "apple"`.
- Le texte des slides vient du script du reel (`texte.txt`) : même idée, découpée en 8 slides, avec la méthode de l'étape 2.
- Image face caméra = visage très gros : mets la note manuscrite du côté opposé à la tête.
Exemple réel : `~/Documents/Contenu/carrousels/2026-10-23-sans-teleprompteur/description.json`.

### 4. Les illustrations (4 slides)
- `scripts/art.py` : `apples_grid` (tous pareils / `red_at` = celui qui est différent), `copies` (copier les gros comptes), `stairs` (3 étapes), `chart_up` (résultats, croissance), `chat` (DM, setting), `checklist` (erreurs, étapes), `camera` (tourner face caméra, le trac), `script_long` (script appris par cœur, barré).
- Sujet nouveau : écris une nouvelle fonction dans `art.py` (mêmes couleurs, `frame()`, dessin entre y 80 et 820, 2 à 4 éléments `deco`) et ajoute-la à `ARTS` pour la réutiliser. Ou un fichier `.svg` à côté de la description (`"svg": "mon-dessin.svg"`).

### 5. La description puis le montage
- Copie `exemples/exemple-v4.json` dans le scratchpad, adapte : `photos` (source + recadrage), `slides`, `caption`, `hashtags`, `out` = `<sorties>/carrousels/AAAA-MM-JJ-<sujet>` (<sorties> = `sorties` de 00-Moi/marque.json, sinon ~/Documents/Contenu).
- Lance Open Carrusel : `preview_start` avec `name: "open-carrusel"` (config dans le `.claude/launch.json` du dossier de travail). En dernier recours : `cd ~/open-carrusel && npm run dev -- -p 3210` en arrière-plan.
- `python3 ~/.claude/skills/carrousel/scripts/carrousel.py <spec.json>` (SANS `-I` : les scripts s'importent entre eux). ~1 min. Il prépare les photos, monte, exporte les PNG, la planche, la légende et `spec.json`.

### 6. Vérifier (jamais livrer sans)
Lis `00-planche.png`, puis en grand chaque slide douteuse. Contrôle :
- texte lisible, pas de mot seul sur une ligne (force avec `<br>` et `&nbsp;`) ;
- mot de couverture lisible : la tête ne cache pas une lettre entière (ajuste `word_top`) ;
- illustration qui ne touche pas le texte ; photo qui colle au sujet de la slide ;
- bon mot-clé à la fin ; 8 PNG en 1080x1440.
Corrige la description et relance.

### 7. Livrer
- `SendUserFile` de la planche + 3 à 5 lignes : sujet, d'où il vient (veille, script…), ce qui reste à faire.
- Brain : 1 ligne en bas de `log.md` ; dans son fichier `actions` (00-Moi/marque.json ; vide : dis-le dans le chat) : valider le carrousel, vérifier que le mot-clé répond dans ManyChat, feu vert pour Metricool.
- Ne publie et ne programme JAMAIS sans son feu vert explicite.
- Une info absente du Brain : dis « je ne l'ai pas ». Ne l'invente pas.
- En cas d'échec (photos introuvables, SSD débranché, rendu vide) : une ligne dans ~/Documents/Brain/04-Audits/erreurs-taches.md (date, tâche, erreur) et dis-le en une ligne.

## Technique
- Open Carrusel : `~/open-carrusel` (open source, MIT), patché pour le 3:4 et les vraies italiques. L'éditeur sur http://localhost:3210 permet à l'utilisateur de voir ou retoucher.
- `prep.py` utilise le modèle de détourage du skill supermonteur (`~/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx`). Le SSD doit être branché.
- Porte cash : un carrousel apporte confiance et enregistrements, pas un deal sous 7 jours. Si l'utilisateur y passe plus d'une demi-journée, dis-le une fois (avec le chiffre de son fichier `actions` s'il en a un).
