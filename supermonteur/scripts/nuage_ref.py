"""29/10 (l’utilisateur : « reprends le positionnement du texte de la vidéo originale », « mot par mot comme le reel original ») :
lit un reel de référence et rend la place et l'instant d'apparition de chaque mot blanc qui s'ajoute à l'écran.
    python3 nuage_ref.py <reference.mp4>     -> JSON [{"t": 5.3, "x": 750, "y": 1307, "w": 372, "h": 78}, ...] (px 1080x1920, ordre d'apparition)
Méthode : 10 images/s ; pixels très clairs (texte blanc) qui apparaissent et RESTENT 0,5 s ; lettres collées en mots ;
les petits restes (< 200 px d'encre) sont ignorés. Utilisé par brolltexte.py ("slots": "ref/reference.mp4").
"""
import json, subprocess, sys
import numpy as np


def detecter(src):
    from scipy import ndimage
    W, H, fps = 540, 960, 10
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={fps},scale={W}:{H}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    br = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).min(axis=3) > 215
    n, out = len(br), []
    for i in range(1, n - 3):
        new = br[i] & ~br[i - 1] & br[i + 2] & br[min(n - 1, i + 5)]
        new = ndimage.binary_closing(new, structure=np.ones((5, 15)))
        lab, _ = ndimage.label(ndimage.binary_dilation(new, structure=np.ones((7, 25))))
        for sl in ndimage.find_objects(lab):
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            if new[sl].sum() > 200 and x1 - x0 > 15:
                out.append({"t": round(i / fps, 2), "x": x0 + x1, "y": y0 + y1, "w": (x1 - x0) * 2, "h": (y1 - y0) * 2})
    return out


if __name__ == "__main__":
    print(json.dumps(detecter(sys.argv[1])))
