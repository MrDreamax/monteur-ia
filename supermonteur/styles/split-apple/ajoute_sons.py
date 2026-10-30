"""29/10 CAM20065 écran coupé : pose les sons d'iPhone (sons.json : t en secondes du clip, src dans la bibliothèque Sons de son disque externe
ou dans ce dossier, db = gain, duree = coupé à n s) sur le son de la vidéo. python3 ajoute_sons.py entree.mp4 sortie.mp4 [duree_max]"""
import json, os, subprocess, sys
ICI = os.path.dirname(os.path.abspath(__file__))
LIB = "/Volumes/son disque externe/1 - Contenu/1 - Bibliothèque/Sons"
src, out = sys.argv[1], sys.argv[2]
fin = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9
S = [s for s in json.load(open(os.path.join(ICI, "sons.json"))) if s["t"] < fin]
cmd, fc = ["ffmpeg", "-v", "error", "-y", "-i", src], []
for k, s in enumerate(S, 1):
    p = os.path.join(ICI, s["src"]) if os.path.exists(os.path.join(ICI, s["src"])) else os.path.join(LIB, s["src"])
    cmd += ["-i", p]
    coupe = "atrim=0:%s,afade=t=out:st=%s:d=0.3," % (s["duree"], round(s["duree"] - .3, 3)) if s.get("duree") else ""
    fc.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s['db']}dB,{coupe}adelay={int(s['t'] * 1000)}:all=1[s{k}]")
fc.append("[0:a]aformat=sample_rates=48000:channel_layouts=stereo[v];[v]" + "".join(f"[s{k}]" for k in range(1, len(S) + 1))
          + f"amix=inputs={len(S) + 1}:normalize=0:duration=first[a]")
subprocess.run(cmd + ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out], check=True)
print(f"{len(S)} sons posés -> {out}")
