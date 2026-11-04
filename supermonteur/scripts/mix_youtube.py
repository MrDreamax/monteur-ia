"""Mix d'une vidéo YouTube 16:9 (31/10, style theyo) : voix du rush sans traitement, musique très basse, un son sur chaque apparition, -14 LUFS.
  python3 mix_youtube.py rendu.mp4 rush.mp4 final.mp4 --sons sons.json [--musique m.mp3] [--debut 12] [--ecart 24]
sons.json = [{"t": 1.1, "src": "epidemic - ui-pop-dull.wav", "db": -6}] ; src = dossier ~/Documents/Montage/SFX (règle : son coupé net au début).
--ecart = dB de la musique sous la voix. Le gain final est un seul chiffre sur tout le mix : la voix n'est ni compressée ni égalisée (rush intouchable).
"""
import json, os, re, subprocess, sys

LIB = os.path.expanduser("~/Documents/Montage/SFX")   # sons du client
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a else d
rendu, rush, out = a[0], a[1], a[2]
sons = json.load(open(opt("--sons"))) if opt("--sons") else []
musique, debut, ecart = opt("--musique"), float(opt("--debut", 0)), float(opt("--ecart", 24))


def lufs(entrees, fc=None):
    sortie = ["-filter_complex", fc + ";[a]loudnorm=print_format=json[b]", "-map", "[b]"] if fc else ["-map", "0:a", "-af", "loudnorm=print_format=json"]
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + entrees + sortie + ["-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r'"input_i"\s*:\s*"(-?[\d.]+)"', e).group(1))


duree = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", rendu]))
voix_i = lufs(["-t", str(duree), "-i", rush])
entrees, fc, voies = ["-i", rendu, "-t", str(duree), "-i", rush], ["[1:a]aformat=sample_rates=48000:channel_layouts=stereo[v]"], ["[v]"]
k = 2
if musique:
    m_i = lufs(["-ss", str(debut), "-t", str(duree), "-i", musique])
    g = round(voix_i - ecart - m_i, 2)
    entrees += ["-ss", str(debut), "-t", str(duree), "-i", musique]
    fc.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={g}dB,afade=t=out:st={max(0, duree - 1):.2f}:d=1[m]")
    voies.append("[m]"); k += 1
for n, s in enumerate(sons):
    p = s["src"] if os.path.isabs(s["src"]) else os.path.join(LIB, s["src"])
    entrees += ["-i", p]
    fc.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s.get('db', -6)}dB,adelay={int(s['t'] * 1000)}:all=1[s{n}]")
    voies.append(f"[s{n}]"); k += 1
mix = ";".join(fc) + ";" + "".join(voies) + f"amix=inputs={len(voies)}:normalize=0:duration=first[a]"
gain = round(-14 - lufs(entrees, mix), 2)
subprocess.run(["ffmpeg", "-v", "error", "-y"] + entrees + ["-filter_complex", mix.replace("[a]", "[x]") + f";[x]volume={gain}dB,alimiter=limit=0.7:level=false,alimiter=limit=0.8:attack=1:level=false,aresample=48000[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(duree), out], check=True)
print(f"voix {voix_i} LUFS · gain {gain} dB · {len(sons)} sons · {out}")
