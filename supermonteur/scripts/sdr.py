"""Rush iPhone HDR (HLG ou PQ, BT.2020 10 bits) -> couleurs standard (SDR bt709) AVANT tout traitement (25/10/2026).
  python3 sdr.py <rush>            -> affiche le fichier à utiliser (la rush elle-même si elle est déjà SDR)
  from sdr import sdr; src = sdr(src)
Pourquoi : le 16/10 (vidéo protocole de David), une passe ffmpeg sur une rush HLG a perdu les étiquettes de couleur :
peau pâle, lampe verdâtre. Sur 4 conversions testées (avconvert Apple, tonemap hable, mobius, zscale), celle d'Apple
est la plus naturelle. On la garde : avconvert, même définition (4K reste 4K pour la marge de recadrage de cadre.py),
rotation du téléphone appliquée à l'image, puis le SON D'ORIGINE recollé tel quel (-c copy, aucune réécriture).
Résultat mis de côté dans le dossier du reel (<nom>_sdr.mov) : cadre.py, derush.py et les autres le réutilisent.
Rush déjà SDR : rendue telle quelle, rien n'est touché.
"""
import json, os, subprocess, sys

HDR_TRC = ("arib-std-b67", "smpte2084")   # HLG, PQ


def _video(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,color_transfer,color_primaries", "-of", "json", path], capture_output=True, text=True).stdout
    st = (json.loads(out or "{}").get("streams") or [{}])[0]
    return st


def hdr(path):
    st = _video(path)
    return st.get("color_transfer") in HDR_TRC or st.get("color_primaries") == "bt2020"


def sdr(src, dest=None):
    if src.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")) or not hdr(src): return src
    st = _video(src)
    out = os.path.join(dest or os.getcwd(), os.path.splitext(os.path.basename(src))[0] + "_sdr.mov")
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src) and not hdr(out): return out
    preset = "Preset3840x2160" if max(st["width"], st["height"]) > 1920 else "Preset1920x1080"   # le cadre se lit dans les 2 sens
    tmp = out + ".video.mov"
    print(f"  HDR -> SDR (conversion Apple, {preset}) : {os.path.basename(src)}", file=sys.stderr)
    subprocess.check_call(["avconvert", "-s", src, "-p", preset, "-o", tmp, "--replace"], stdout=subprocess.DEVNULL)
    has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", src],
                           capture_output=True, text=True).stdout.strip()
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", tmp] + (["-i", src, "-map", "0:v:0", "-map", "1:a:0"] if has_a else ["-map", "0:v:0"])
                          + ["-c", "copy", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", out])
    os.remove(tmp)
    return out


# À ajouter à chaque encodage qui suit : la vidéo sort étiquetée en couleurs standard (sinon le lecteur devine et se trompe).
BT709 = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]

if __name__ == "__main__":
    print(sdr(sys.argv[1]))
