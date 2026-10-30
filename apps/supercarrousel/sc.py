"""SuperCarrousel côté Claude : ce que l'écran attend de moi, et comment je le donne.
  python3 sc.py a-faire              liste les demandes en attente (texte à écrire, retours à corriger, demandes de DA)
  python3 sc.py attendre             bloque jusqu'à la prochaine demande, puis l'affiche (à lancer avec Monitor)
  python3 sc.py ecrire <id> <fichier.json>   pose la description de la version suivante (le serveur la rend tout seul)
  python3 sc.py rendre <id>          rend la dernière version sans le serveur (secours)
  python3 sc.py metricool oui|non [compte]   note le résultat de la vérification Metricool (lecture seule, getBrandSettings)

La description = celle du skill carrousel (style Apple) : photos {nom: {src, fx, fy, zoom}}, slides [cover|photo|art],
caption, plus :
  "name"        titre court du carrousel (affiché en haut de l'écran)
  "legendes"    {instagram, tiktok, facebook, linkedin} : 1-2 phrases, 0 hashtag (règle legende-courte)
  "corrections" [{"retour": 2, "ligne": "photo où tu souris", "slide": 3}] : une ligne par retour corrigé (version 2+)
Les "src" des photos peuvent être relatifs au projet (ex. "_reel/image-04.jpg"). Jamais d'image IA.
"""
import json
import os
import sys
import time

import moteur as m


def demandes():
    out = []
    for pid in sorted(os.listdir(m.PROJETS)) if os.path.isdir(m.PROJETS) else []:
        if pid.startswith("_") or not os.path.isdir(m.chemin(pid)):
            continue
        e = m.etat(pid)
        st = e.get("statut")
        if st == "attente_texte" and not m.versions(pid):
            out.append(("texte", pid))
        elif st == "attente_corrections":
            v = m.version_rendue(pid)
            if not os.path.exists(m.chemin(pid, f"v{v + 1}", "description.json")):
                out.append(("corrections", pid))
    for i, d in enumerate(m.lire(os.path.join(m.PROJETS, "_demandes-da.json"), [])):
        if not d.get("faite"):
            out.append(("da", str(i)))
    return out


def montrer(kind, pid):
    if kind == "da":
        d = m.lire(os.path.join(m.PROJETS, "_demandes-da.json"))[int(pid)]
        print(f"\n## Demande de DA ({d['quand']}) : « {d['texte']} »\n   -> à faire dans SuperDA (apps/superda/da.json), puis marquer faite.")
        return
    d = m.lire(m.chemin(pid, "demande.json"))
    print(f"\n## {'Texte à écrire' if kind == 'texte' else 'Retours à corriger'} · projet {pid} · départ « {d['depart']} »")
    print(f"   dossier : {m.chemin(pid)}")
    if d.get("idee"):
        print(f"   idée : {d['idee']}")
    if d.get("lien"):
        print(f"   lien : {d['lien']}")
    if d.get("video"):
        print(f"   vidéo : {d['video']}")
    reel = m.chemin(pid, "_reel")
    if os.path.isdir(reel):
        print(f"   images du reel : {reel}/00-candidates.jpg (planche) · image-01..16.jpg · texte : {reel}/texte.txt")
    mod = m.chemin(pid, "_modele")
    if os.path.isdir(mod):
        print(f"   carrousel à reprendre : {mod}/ ({len(os.listdir(mod))} images) : FIDÈLE à son concept et son style (mise en page, couleurs, ordre, rythme) ; on change SEULEMENT la police (duo SuperDA) et les mots pour la cible ; images : les proposer ou les demander à l’utilisateur, slide par slide")
    da = m.resume_da()
    print(f"   DA : {da['pastille']} (modèle rendu : {m.modele_rendu(m.lire_da())})")
    if kind == "corrections":
        v = m.version_rendue(pid)
        print(f"   version actuelle : {m.chemin(pid, f'v{v}', 'description.json')}")
        for r in m.lire(m.chemin(pid, "retours.json"), []):
            if r["statut"] == "envoye":
                print(f"   - retour {r['id']} · slide {r['slide']} : {r['texte']}")
        print(f"   -> écris v{v + 1} (copie de v{v} + corrections) : python3 sc.py ecrire {pid} <fichier.json>")
    else:
        print(f"   -> écris v1 : python3 sc.py ecrire {pid} <fichier.json>  (méthode : skill carrousel étapes 1-2, 3 bis)")


def ecrire(pid, fichier):
    desc = json.load(open(fichier))
    assert desc.get("slides"), "pas de slides"
    for s in desc["slides"]:
        assert s.get("type") in ("cover", "photo", "art"), f"type inconnu : {s.get('type')}"
        if s.get("photo"):
            assert s["photo"] in desc.get("photos", {}), f"photo inconnue : {s['photo']}"
    for nom, p in desc.get("photos", {}).items():
        src = p["src"] if os.path.isabs(os.path.expanduser(p["src"])) else m.chemin(pid, p["src"])
        assert os.path.exists(os.path.expanduser(src)), f"photo introuvable : {src}"
    v = m.version_rendue(pid)
    if m.etat(pid).get("statut") == "attente_texte" or not v:
        v = 0
    m.ecrire(m.chemin(pid, f"v{v + 1}", "description.json"), desc)
    print(f"v{v + 1} posée : le serveur la rend (écran « Je fabrique »).")


def main():
    a = sys.argv[1:]
    if not a or a[0] == "a-faire":
        ds = demandes()
        if not ds:
            print("Rien en attente.")
        for k, pid in ds:
            montrer(k, pid)
    elif a[0] == "attendre":
        while True:
            ds = demandes()
            if ds:
                for k, pid in ds:
                    montrer(k, pid)
                return
            time.sleep(2)
    elif a[0] == "ecrire":
        ecrire(a[1], a[2])
    elif a[0] == "rendre":
        v = m.version_rendue(a[1]) or max(m.versions(a[1]))
        print(m.rendre(a[1], v, lambda i, n: print(f"slide {i}/{n}")), "slides")
    elif a[0] == "metricool":
        m.ecrire(os.path.join(m.ICI, "metricool.json"), {"branche": a[1] == "oui", "compte": a[2] if len(a) > 2 else "",
                                                       "verifie_le": time.strftime("%Y-%m-%d %H:%M"), "verifie_ts": time.time()})
        print("Metricool noté :", a[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
