"""Les commandes de Claude dans SuperVeille (lancé par le serveur, ou depuis un chat). Le mécanique est ici, le jugement chez Claude.
  python3 sv.py contexte <id>                       réglages, cible, anti-doublon, répartition
  python3 sv.py etape <id> "<message>" [--lus N]    ce que l'écran affiche pendant la recherche
  python3 sv.py filtre <id> <brut.json>             likes, période, doublons, stars, boost, pubs + couverture
  python3 sv.py jev <id> --cible "<cible EN>"       tri Jev (cible, vrai créateur, format)
  python3 sv.py selection <id> <fichier.json>       [{"code","marche","format"}] : les cartes partent à l'écran
  python3 sv.py comptes <id>                        comptes vus dans la recherche, à fouiller (2e canal)
  python3 sv.py selection <id> <fichier> --ajout    compléter une veille de moins de 10
  python3 sv.py manque <id> "<pourquoi>"            moins de 10 : on le dit, on n'abaisse pas la barre
  python3 sv.py a-traduire <id>                     transcriptions qui attendent leur traduction
  python3 sv.py traduction <id> <code> <fichier>    {"hook", "phrases": [{"o","f"}]}
  python3 sv.py a-transposer <id>                   références collées (Transposer) : transcription + sujet demandé
  python3 sv.py transposition <id> <code> <fichier> {"format", "plan", "hook", "script"}
  python3 sv.py reperes                             Recherche rapide : comptes déjà repérés (veilles + ses enregistrés), à fouiller
  python3 sv.py trouve <id> <code> --hook "..." --raison "..."   Recherche rapide : 1 reel trouvé, sa carte s'affiche
  python3 sv.py lancer --pour <fichier> [--marches en,es,fr] [--periode 45] [--likes 10000] [--sujet "..."]
Scanner cerveau (1 clic « Scanner ce reel », cerveau.py) :
  python3 sv.py cerveau-a-faire <id> <code>                 les morceaux de 15 s à envoyer à Higgsfield
  python3 sv.py cerveau-envoie <id> <code> <debut> '<url>'  envoie un morceau sur l'upload_url de media_upload
  python3 sv.py cerveau-rapport <id> <code> <debut> '<url>' garde le rapport d'un job fini (result_url)
  python3 sv.py cerveau-calcul <id> <code>                  notes + script phrase par phrase (pour écrire la recette)
  python3 sv.py cerveau-recette <id> <code> <fichier>       {"regles": [{"type","titre","detail"}]} : la fiche s'affiche
  python3 sv.py cerveau-erreur <id> <code> "<raison>"       Higgsfield refuse : la fiche le dit
"""
import argparse
import datetime as dt
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import commun as c

JEV = os.path.join(c.ICI, "jev.py")  # absent de cette version : Claude trie lui-même


def stop(msg):
    print("REFUSÉ : " + msg)
    sys.exit(1)


def charger(vid):
    v = c.veille(vid)
    if not v:
        stop(f"veille {vid} introuvable (dossier veilles/).")
    return v


def repartition(marches):
    return dict(zip(marches, c.REPARTITION[len(marches)]))


def contexte(a):
    v = charger(a.id)
    codes, createurs = c.deja_livres(v["pour"])
    limite = (dt.date.today() - dt.timedelta(days=v["periode"])).isoformat()
    print(json.dumps({
        "veille": a.id, "pour": v["personne"], "fichier": v["pour"], "cible": v["cible"],
        "marches_dans_l_ordre": [f"{m} ({c.NOMS_MARCHES[m]})" for m in v["marches"]],
        "repartition_des_10": repartition(v["marches"]), "periode_jours": v["periode"], "publie_apres": limite,
        "likes_min": v["likes_min"], "sujet_precis": v.get("sujet") or "(aucun : choisis les mots-clés depuis la cible)",
        "deja_livres_codes": codes, "deja_livres_createurs": createurs, "stars": c.STARS,
        "fichiers": {"brut": f"veilles/{a.id}/brut.json", "selection": f"veilles/{a.id}/selection.json"},
    }, ensure_ascii=False, indent=1))


def etape(a):
    champs = {"etape": a.message}
    if a.lus is not None:
        champs["lus"] = a.lus
    c.maj_veille(a.id, **champs)
    print("ok")


def filtre(a):
    v = charger(a.id)
    brut = json.load(open(a.fichier))
    if isinstance(brut, dict):
        brut = brut.get("items", [])
    codes, createurs = c.deja_livres(v["pour"])
    codes, createurs = set(codes), set(createurs)
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=v["periode"])
    gardes, recales, vus = [], {}, set()

    def recale(raison):
        recales[raison] = recales.get(raison, 0) + 1

    for x in brut:
        code, qui = x.get("shortCode") or x.get("code"), (x.get("ownerUsername") or "").lower()
        likes, vues = x.get("likesCount") or 0, x.get("videoPlayCount") or x.get("videoViewCount") or 0
        if not code or code in vus:
            recale("doublon dans la recherche")
            continue
        vus.add(code)
        try:
            quand = dt.datetime.fromisoformat((x.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            quand = None
        if likes < v["likes_min"]:
            recale(f"sous {v['likes_min']} likes")
        elif not quand or quand < limite:
            recale(f"plus vieux que {v['periode']} j")
        elif code in codes or qui in createurs:
            recale("déjà livré")
        elif qui.replace(".", "").replace("_", "") in c.STARS:
            recale("star")
        elif x.get("paidPartnership"):
            recale("pub")
        elif vues and likes / vues < 0.005:
            recale("vues boostées")
        elif x.get("marche") not in v["marches"]:
            recale("marché non coché")
        else:
            gardes.append({"shortCode": code, "ownerUsername": x.get("ownerUsername"), "likesCount": likes, "videoPlayCount": vues,
                           "timestamp": x.get("timestamp"), "caption": (x.get("caption") or "")[:1500], "marche": x["marche"]})
    with ThreadPoolExecutor(6) as ex:
        for g, img in zip(gardes, ex.map(lambda g: c.url_couverture(g["shortCode"]), gardes)):
            g["image"] = img
    avant = [x for x in c.lire(c.chemin(a.id, "candidats.json"), []) if x["shortCode"] not in vus and x["shortCode"] not in codes]
    c.ecrire(c.chemin(a.id, "candidats.json"), avant + gardes)
    with c.verrou(c.chemin(a.id, "brut-tout.json")):  # toutes les recherches de la veille, pour sv.py comptes
        tout = c.lire(c.chemin(a.id, "brut-tout.json"), [])
        connus = {x.get("shortCode") for x in tout}
        c.ecrire(c.chemin(a.id, "brut-tout.json"), tout + [x for x in brut if x.get("shortCode") not in connus])
    c.maj_veille(a.id, lus=max(c.veille(a.id).get("lus") or 0, len(brut)), passent_likes=len(gardes))
    print(f"{len(gardes)} candidats gardés sur {len(brut)} · recalés : " + (", ".join(f"{n} {r}" for r, n in recales.items()) or "aucun"))
    for g in sorted(gardes, key=lambda g: (v["marches"].index(g["marche"]), -g["likesCount"])):
        legende = re.sub(r"\s+", " ", g["caption"])[:90]
        print(f"  {g['marche']} {g['shortCode']} @{g['ownerUsername']} ♥{g['likesCount']} ▶{g['videoPlayCount']} "
              f"{(g['timestamp'] or '')[:10]} | {legende}")


def jev(a):
    if not os.path.exists(c.chemin(a.id, "candidats.json")):
        stop("lance d'abord sv.py filtre.")
    sortie = c.chemin(a.id, "juges.json")
    if not os.path.exists(JEV):
        return print("Jev non branché : trie toi-même sur la cible.")
    r = subprocess.run([sys.executable, JEV, "--preset", "reels", "--items", c.chemin(a.id, "candidats.json"), "--out", sortie,
                        "--cible", a.cible, "--garde", "cible>=0.6,vrai_createur>=0.6"], capture_output=True, text=True, timeout=600)
    print((r.stdout + r.stderr).strip()[-6000:])
    if r.returncode == 3:
        print("Jev non branché : trie toi-même sur la cible.")
    juges = c.lire(sortie, [])
    c.maj_veille(a.id, gardes=sum(1 for j in juges if j.get("jev") and (j["jev"].get("cible") or 0) >= 0.6))


def selection(a):
    v = charger(a.id)
    choix = json.load(open(a.fichier))
    cand = {x["shortCode"]: x for x in c.lire(c.chemin(a.id, "candidats.json"), [])}
    if not isinstance(choix, list) or not choix:
        stop("il faut une liste [{\"code\", \"marche\", \"format\"}].")
    if len(choix) > 10:
        stop(f"{len(choix)} reels : 10 maximum.")
    deja = v.get("reels", []) if a.ajout else []
    comptent = [r for r in deja if r["statut"] != "ecarte"]
    if a.ajout and len(comptent) + len(choix) > 10:
        stop(f"{len(comptent)} reels déjà là : {10 - len(comptent)} de plus au maximum.")
    reels, vus = [], {r["code"] for r in deja}
    for i, ch in enumerate(choix, len(deja) + 1):
        code = (ch.get("code") or "").strip()
        x = cand.get(code)
        if not x:
            stop(f"{code} n'est pas dans les candidats filtrés (sv.py filtre) : chiffres non vérifiés.")
        if code in vus:
            stop(f"{code} deux fois.")
        vus.add(code)
        reels.append({"n": i, "code": code, "lien": f"https://www.instagram.com/reel/{code}/", "marche": x["marche"],
                      "createur": x["ownerUsername"], "likes": x["likesCount"], "vues": x["videoPlayCount"],
                      "date": (x["timestamp"] or "")[:10], "format": ch.get("format", ""), "legende": x["caption"][:600],
                      "image": x.get("image"), "statut": "attente"})
    if v.get("reels") and not a.ajout:
        stop("cette veille a déjà sa sélection (pour compléter : --ajout).")
    c.maj_veille(a.id, reels=deja + reels, statut="transcription", etape="Je prépare les miniatures…")
    print(f"ok : {len(reels)} reels envoyés à l'écran. L'appli fait miniatures + transcription ; la traduction viendra ensuite.")


def reperes(a):
    """Comptes qui ont déjà fait 3 000 likes et plus dans une veille, ou 10 000 et plus dans ses enregistrés Instagram :
    le 2e canal de la Recherche rapide (les mots-clés seuls ramènent trop peu de reels, test du 28/10 : 29 lus, 0 bon)."""
    vus = {}
    def voir(qui, likes, leg, ou):
        q = (qui or "").lower()
        if not q or q.replace(".", "").replace("_", "") in c.STARS:
            return
        x = vus.setdefault(q, {"max": 0, "n": 0, "ou": ou, "leg": ""})
        x["n"] += 1
        if likes > x["max"]:
            x.update(max=likes, leg=re.sub(r"\s+", " ", leg or "")[:80])
    for vid in c.toutes_veilles():
        for r in c.lire(c.chemin(vid, "brut-tout.json"), []):
            if (r.get("likesCount") or 0) >= 3000:
                voir(r.get("ownerUsername"), r["likesCount"], r.get("caption"), "veille")
    for compte in c.lire(c.ENREG, {}).get("comptes", {}).values():
        for r in compte.get("items", []):
            if (r.get("likes") or 0) >= 10000:
                voir(r.get("createur"), r["likes"], r.get("legende"), "enregistré")
    # d'abord les comptes vus dans les veilles (trouvés sur la cible), puis ses enregistrés (beaucoup de viral hors sujet)
    for q, x in sorted(vus.items(), key=lambda kv: (kv[1]["ou"] != "veille", -kv[1]["max"]))[:120]:
        print(f"@{q} ♥{x['max']} ({x['ou']}, {x['n']} reels) | {x['leg']}")


def trouve(a):
    """Recherche rapide (onglet Recherche) : 3 reels au plus, posés un par un pour que les cartes arrivent tout de suite."""
    v = charger(a.id)
    x = {k["shortCode"]: k for k in c.lire(c.chemin(a.id, "candidats.json"), [])}.get(a.code)
    if not x:
        stop(f"{a.code} n'est pas dans les candidats filtrés (sv.py filtre) : chiffres non vérifiés.")
    if any(t["code"] == a.code for t in v.get("trouves", [])):
        stop(f"{a.code} déjà posé.")
    if any(t["code"] == a.code and t.get("retire") for x in c.toutes_veilles() for t in c.veille(x).get("trouves", [])):
        stop(f"{a.code} : l’utilisateur l'a retiré d'une recherche, prends-en un autre.")
    if len(v.get("trouves", [])) >= 3:
        stop("3 reels déjà posés : c'est fini.")
    os.makedirs(c.chemin(a.id, "mini"), exist_ok=True)
    mini = x.get("image") and c.telecharger_couverture(x["image"], c.chemin(a.id, "mini", a.code + ".jpg"))
    t = {"code": a.code, "lien": f"https://www.instagram.com/reel/{a.code}/", "marche": x["marche"], "createur": x["ownerUsername"],
         "likes": x["likesCount"], "vues": x["videoPlayCount"], "date": (x["timestamp"] or "")[:10],
         "hook": a.hook.strip()[:200], "raison": a.raison.strip()[:120], "mini": bool(mini), "image": x.get("image")}
    c.maj_veille(a.id, lambda v: v.setdefault("trouves", []).append(t))
    print(f"ok : carte {len(c.veille(a.id)['trouves'])}/3 affichée.")


def comptes(a):
    """2e canal : les comptes vus dans la recherche qui ont au moins un reel à 3 000 likes. Leurs autres reels récents
    passent souvent la barre (apify/instagram-reel-scraper). Claude garde ceux qui parlent à la cible."""
    v = charger(a.id)
    codes, createurs = c.deja_livres(v["pour"])
    createurs = set(createurs) | {r["createur"].lower() for r in v.get("reels", [])}
    meilleurs = {}
    for x in c.lire(c.chemin(a.id, "brut-tout.json"), []) or c.lire(c.chemin(a.id, "brut.json"), []):
        qui = (x.get("ownerUsername") or "").lower()
        if not qui or qui in createurs or qui.replace(".", "").replace("_", "") in c.STARS or (x.get("likesCount") or 0) < 3000:
            continue
        if (x.get("likesCount") or 0) > meilleurs.get(qui, {}).get("likesCount", -1):
            meilleurs[qui] = x
    print(f"{len(meilleurs)} comptes (déjà livrés et stars retirés), du plus liké au moins liké :")
    for qui, x in sorted(meilleurs.items(), key=lambda kv: -kv[1].get("likesCount", 0)):
        legende = re.sub(r"\s+", " ", x.get("caption") or "")[:90]
        print(f"  {x.get('marche', '?')} @{qui} ♥{x.get('likesCount')} | {legende}")


def manque(a):
    c.maj_veille(a.id, manque=a.pourquoi)
    print("ok")


def a_traduire(a):
    v = charger(a.id)
    n = 0
    for r in v.get("reels", []):
        if r["statut"] == "transcrit":
            n += 1
            t = r.get("transcription", {})
            print(f"\n===== {r['code']} · @{r['createur']} · langue {t.get('langue')} · {len(t.get('segments', []))} segments")
            for s in t.get("segments", []):
                print(f"[{s['debut']:.1f}] {s['texte']}")
    if not n:
        print("Rien à traduire pour l'instant.")


def mots(t):
    return re.findall(r"\w+", c.norm(t))


def traduction(a):
    v = charger(a.id)
    r = next((x for x in v.get("reels", []) if x["code"] == a.code), None)
    if not r:
        stop(f"{a.code} n'est pas dans cette veille.")
    if r["statut"] not in ("transcrit", "pret"):
        stop(f"{a.code} n'est pas encore transcrit (statut {r['statut']}).")
    d = json.load(open(a.fichier))
    phrases = [{"o": (p.get("o") or "").strip(), "f": (p.get("f") or "").strip()} for p in d.get("phrases", [])]
    if not phrases or any(not p["o"] or not p["f"] for p in phrases):
        stop("chaque phrase a besoin de \"o\" (original) et \"f\" (français).")
    if not (d.get("hook") or "").strip():
        stop("il manque \"hook\" (1re phrase en français).")
    source = mots(" ".join(s["texte"] for s in r["transcription"]["segments"]))
    rendu = mots(" ".join(p["o"] for p in phrases))
    ratio = difflib.SequenceMatcher(None, source, rendu, autojunk=False).ratio() if source else 1
    if ratio < 0.85:
        stop(f"l'original ne suit pas la transcription ({ratio:.0%} pareil) : toute la vidéo, mot pour mot, rien coupé.")
    c.maj_reel(a.id, a.code, phrases=phrases, hook=sans_guillemets(d["hook"]), statut="pret")
    print(f"ok : {a.code} prêt ({len(phrases)} phrases, original {ratio:.0%} fidèle).")


def a_transposer(a):
    v = charger(a.id)
    n = 0
    for r in v.get("reels", []):
        if r["statut"] == "transcrit":
            n += 1
            t = r.get("transcription", {})
            mots_ref = sum(len(s["texte"].split()) for s in t.get("segments", []))
            print(f"\n===== {r['code']} · @{r['createur']} · langue {t.get('langue')} · {mots_ref} mots dits"
                  f"\nsujet demandé par l’utilisateur : {r.get('sujet') or '(aucun : tu choisis)'}\nlégende : {(r.get('legende') or '')[:300]}")
            for s in t.get("segments", []):
                print(f"[{s['debut']:.1f}] {s['texte']}")
            if r.get("sans_voix"):  # bureau + texte : le script de la référence est le texte à l'écran
                print(f"AUCUNE VOIX : tout le reel est du texte à l'écran. Lis l'image {os.path.abspath(c.chemin(a.id, '_ecran', r['code'] + '.jpg'))}"
                      " (12 images de la vidéo dans l'ordre : de gauche à droite, puis de haut en bas) et recopie ce texte dans \"ecran\".")
    if not n:
        print("Rien à transposer pour l'instant.")


def transposition(a):
    v = charger(a.id)
    r = next((x for x in v.get("reels", []) if x["code"] == a.code), None)
    if not r or not r.get("transpose"):
        stop(f"{a.code} n'est pas une référence à transposer de cette veille.")
    if r["statut"] not in ("transcrit", "pret"):
        stop(f"{a.code} n'est pas encore transcrit (statut {r['statut']}).")
    d = json.load(open(a.fichier))
    plan = [str(x).strip() for x in d.get("plan") or [] if str(x).strip()]
    hook, script, fmt = (sans_guillemets(d.get(k)) for k in ("hook", "script", "format"))
    if not fmt:
        stop("il manque \"format\" (le format repris, en une ligne).")
    if not 3 <= len(plan) <= 7:
        stop("\"plan\" : 3 à 7 étapes.")
    if not hook or len(hook.split()) > 30:
        stop("\"hook\" : la 1re phrase, 30 mots max.")
    ecran = [str(x).strip() for x in d.get("ecran") or [] if str(x).strip()]
    if r.get("sans_voix") and len(ecran) < 2:
        stop("reel sans voix : \"ecran\" = le texte à l'écran de la référence, ligne par ligne, lu sur l'image (2 lignes au moins).")
    if len(script.split()) < (8 if r.get("sans_voix") else 25):
        stop("\"script\" trop court : toute la suite du script après le hook.")
    tout = " ".join([hook, script] + plan)
    if "—" in tout:
        stop("pas de tiret cadratin (—).")
    if "voler" in tout.lower():
        stop("jamais « voler » : « reprendre ».")
    if r.get("sans_voix"):  # le texte à l'écran devient la transcription : la fiche montre l'original, la longueur se compare
        r["transcription"] = {"langue": "texte à l'écran", "segments": [{"debut": 0, "fin": 0, "texte": t} for t in ecran]}
        c.maj_reel(a.id, a.code, transcription=r["transcription"])
    ref = sum(len(s["texte"].split()) for s in r["transcription"]["segments"])
    dit = len((hook + " " + script).split())
    if ref >= 40 and not 0.6 <= dit / ref <= 1.5:
        stop(f"longueur : {dit} mots contre {ref} dans la référence. Même format = même longueur, à ±30 % environ.")
    c.maj_reel(a.id, a.code, format_repris=fmt, plan=plan, hook=hook, script=script, statut="pret")
    print(f"ok : {a.code} prêt ({len(plan)} étapes, {dit} mots, référence {ref}).")

def scan(a):
    import cerveau
    charger(a.id)
    r = cerveau.reel(a.id, a.code)
    if not r or not (r.get("cerveau") or {}).get("statut"):
        stop(f"{a.code} : aucun scan demandé dans cette veille.")
    return cerveau, r


def cerveau_a_faire(a):
    cerveau, r = scan(a)
    parts = c.lire(os.path.join(cerveau.dossier(a.id, a.code), "parts.json"), {}).get("parts", [])
    if not parts:
        stop("les morceaux ne sont pas prêts (le serveur les coupe avant de te lancer).")
    faits = {int(f[8:11]) for f in os.listdir(cerveau.dossier(a.id, a.code)) if f.startswith("rapport-")}
    for p in parts:
        print(f"debut {p['debut']:>3} · {p['duree']:.1f} s · {'FAIT' if p['debut'] in faits else 'à faire'} · {p['fichier']}")


def cerveau_envoie(a):
    cerveau, r = scan(a)
    f = os.path.join(cerveau.dossier(a.id, a.code), f"part-{int(a.debut):03d}.mp4")
    if not os.path.exists(f):
        stop(f"pas de morceau qui commence à {a.debut} s.")
    if not a.url.startswith("https://upload.higgsfield.ai/"):
        stop("l'adresse doit être l'upload_url de media_upload (https://upload.higgsfield.ai/...).")
    # curl, pas urllib : le pare-feu de Higgsfield (Cloudflare, « error code: 1010 ») refuse Python (vu le 28/10).
    # If-None-Match : en-tête signé dans l'adresse, obligatoire.
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "PUT", "-H", "Content-Type: video/mp4",
                        "-H", "If-None-Match: *", "--data-binary", "@" + f, a.url], capture_output=True, text=True, timeout=300)
    if r.stdout.strip() != "200":
        stop(f"envoi refusé (code {r.stdout.strip() or r.stderr.strip()[:80]}) : redemande une upload_url à media_upload.")
    print(f"ok : morceau {a.debut} envoyé.")


def cerveau_rapport(a):
    cerveau, r = scan(a)
    d = cerveau.dossier(a.id, a.code)
    dest = os.path.join(d, f"rapport-{int(a.debut):03d}.html")
    if not a.url.startswith("https://"):
        stop("l'adresse doit être le result_url du job.")
    try:
        subprocess.run(["curl", "-sf", "-o", dest, a.url], check=True, timeout=180)
        cerveau.sp.lire_rapport(dest)
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        stop(f"rapport illisible ({str(e)[:120]}).")
    faits = len([f for f in os.listdir(d) if f.startswith("rapport-")])
    cerveau.maj(a.id, a.code, faits=faits)
    print(f"ok : morceau {a.debut} gardé ({faits}/{r['cerveau'].get('total', '?')}).")


def cerveau_calcul(a):
    cerveau, r = scan(a)
    total = r["cerveau"].get("total") or 0
    faits = len([f for f in os.listdir(cerveau.dossier(a.id, a.code)) if f.startswith("rapport-")])
    if faits < total:
        stop(f"{faits} morceaux sur {total} : finis les autres d'abord.")
    print(cerveau.calcul(a.id, a.code))


def cerveau_recette(a):
    cerveau, r = scan(a)
    if r["cerveau"].get("statut") != "calcul":
        stop("lance d'abord cerveau-calcul.")
    d = json.load(open(a.fichier))
    refus = cerveau.valider_recette(d)
    if refus:
        stop(refus)
    regles = [{k: x[k].strip() for k in ("type", "titre", "detail")} for x in d["regles"]]
    cerveau.maj(a.id, a.code, statut="fini", regles=regles, erreur="")
    cerveau.ranger(a.id, a.code)
    print(f"ok : recette posée ({len(regles)} règles), la fiche s'affiche.")


def cerveau_erreur(a):
    cerveau, r = scan(a)
    cerveau.maj(a.id, a.code, statut="erreur", erreur=a.raison[:200])
    print("ok : la fiche le dit.")


def sans_guillemets(t):
    """Retire seulement des guillemets qui entourent TOUT le texte. Avant (28/10), strip("«»") mangeait le « d'un hook
    qui commence par une citation (« Pourquoi si cher ? » Voilà…) ou le » d'un hook qui finit par une citation."""
    t = (t or "").strip()
    for a, b in (("«", "»"), ('"', '"'), ("“", "”")):
        seul = t.count(a) == 2 if a == b else t.count(a) == 1 and t.count(b) == 1
        if len(t) > 1 and t.startswith(a) and t.endswith(b) and seul:
            return t[1:-1].strip()
    return t


def lancer(a):
    corps = {"pour": a.pour, "sujet": a.sujet or ""}
    if a.marches:
        corps["marches"] = a.marches.split(",")
    if a.periode:
        corps["periode"] = a.periode
    if a.likes:
        corps["likes_min"] = a.likes
    req = urllib.request.Request("http://localhost:8811/api/lancer", data=json.dumps(corps).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        print(urllib.request.urlopen(req, timeout=10).read().decode())
    except urllib.error.HTTPError as e:
        stop(e.read().decode())
    except OSError:
        stop("l'appli ne tourne pas : bash ~/Documents/SuperApps/superveille/lancer.sh")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("contexte").add_argument("id")
    e = s.add_parser("etape")
    e.add_argument("id")
    e.add_argument("message")
    e.add_argument("--lus", type=int)
    f = s.add_parser("filtre")
    f.add_argument("id")
    f.add_argument("fichier")
    j = s.add_parser("jev")
    j.add_argument("id")
    j.add_argument("--cible", required=True)
    se = s.add_parser("selection")
    se.add_argument("id")
    se.add_argument("fichier")
    se.add_argument("--ajout", action="store_true")
    s.add_parser("comptes").add_argument("id")
    s.add_parser("reperes")
    tr = s.add_parser("trouve")
    tr.add_argument("id")
    tr.add_argument("code")
    tr.add_argument("--hook", required=True)
    tr.add_argument("--raison", required=True)
    m = s.add_parser("manque")
    m.add_argument("id")
    m.add_argument("pourquoi")
    s.add_parser("a-traduire").add_argument("id")
    t = s.add_parser("traduction")
    t.add_argument("id")
    t.add_argument("code")
    t.add_argument("fichier")
    la = s.add_parser("lancer")
    la.add_argument("--pour", required=True)
    la.add_argument("--marches")
    la.add_argument("--periode", type=int)
    la.add_argument("--likes", type=int)
    la.add_argument("--sujet")
    s.add_parser("a-transposer").add_argument("id")
    tp = s.add_parser("transposition")
    for ch in ("id", "code", "fichier"):
        tp.add_argument(ch)
    for nom, champs in (("cerveau-a-faire", ()), ("cerveau-envoie", ("debut", "url")), ("cerveau-rapport", ("debut", "url")),
                        ("cerveau-calcul", ()), ("cerveau-recette", ("fichier",)), ("cerveau-erreur", ("raison",))):
        x = s.add_parser(nom)
        for ch in ("id", "code") + champs:
            x.add_argument(ch)
    a = p.parse_args()
    {"contexte": contexte, "etape": etape, "filtre": filtre, "jev": jev, "selection": selection, "manque": manque,
     "a-traduire": a_traduire, "comptes": comptes, "reperes": reperes, "trouve": trouve, "traduction": traduction, "lancer": lancer,
     "a-transposer": a_transposer, "transposition": transposition, "cerveau-a-faire": cerveau_a_faire, "cerveau-envoie": cerveau_envoie, "cerveau-rapport": cerveau_rapport,
     "cerveau-calcul": cerveau_calcul, "cerveau-recette": cerveau_recette, "cerveau-erreur": cerveau_erreur}[a.cmd](a)


if __name__ == "__main__":
    os.chdir(c.ICI)
    main()
