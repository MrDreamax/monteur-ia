"""Haut de la tête (cheveux compris) sur une plage, pour poser le mot géant DERRIÈRE la tête (Style Lab R4, 13/10).
  python3 headtop.py clip.mp4 START END          -> imprime le y (px, 1080x1920) du haut des cheveux
  python3 headtop.py clip.mp4 START END --json   -> {"top", "cx", "hw", "visage"} (aperçu du cockpit : il imite le détourage)
23/10 (retour n6 de l'utilisateur, « les mots géants ne sont pas bien derrière la tête ») : le haut des cheveux est MESURÉ sur
la silhouette détourée (Robust Video Matting, le modèle de matte.py) au-dessus du visage (MediaPipe). Avant : front - 0,45 x hauteur
du visage, une estimation faite sur Meta Verified ; sur des cheveux courts elle tombait ~50 px trop haut (IMG_6799 : 465 contre 512
mesuré) et le mot flottait au-dessus de la tête au lieu de passer derrière.
Sort en erreur (« pas de visage ») si la tête n'est pas vue sur au moins la moitié de la plage (plan sur le décor, caméra retournée) :
build.mjs pose alors le mot devant, lisible, sans faire semblant de le passer derrière une tête absente (retour n2, 23/10).
"""
import json, os, subprocess, sys
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

src, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "face_landmarker.task")
RVM = os.path.expanduser("~/.cache/supermonteur/rvm_mobilenetv3_fp32.onnx")
W, H, FPS, WARM = 540, 960, 10, 0.5
a0 = max(0.0, t0 - WARM)   # comme matte.py : le détourage chauffe 0,5 s avant (contour stable)
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", str(a0), "-t", str(max(t1 - a0, 0.2)), "-i", src,
                               "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MOD), running_mode=vision.RunningMode.IMAGE))
sess = None
try:
    import onnxruntime as ort
    if os.path.exists(RVM):
        sess = ort.InferenceSession(RVM, providers=["CPUExecutionProvider"])
except Exception:
    pass
rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
tops, cxs, hws, vus = [], [], [], 0
for i, f in enumerate(fr):
    pha = None
    if sess:
        x = (f.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        _, pha, *rec = sess.run(None, {"src": x, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                       "downsample_ratio": np.array([0.4], np.float32)})
    if a0 + i / FPS < t0 - 1e-3:
        continue
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)))
    if not r.face_landmarks:
        continue
    vus += 1
    L = r.face_landmarks[0]
    xs = [p.x * W for p in L]
    cx, hw = (min(xs) + max(xs)) / 2, (max(xs) - min(xs)) / 2
    estime = (L[10].y - 0.45 * (L[152].y - L[10].y)) * H   # l'ancienne estimation, en secours si pas de détourage
    y = estime
    if pha is not None:
        a = pha[0, 0] > 0.5
        cols = [c for c in range(int(cx - 0.5 * hw), int(cx + 0.5 * hw)) if 0 <= c < W and a[:int(L[10].y * H), c].any()]
        if cols:   # 10e centile : le haut des cheveux au centre de la tête, sans qu'une mèche ou une main isolée compte
            y = float(np.percentile([np.argmax(a[:, c]) for c in cols], 10))
    tops.append(y); cxs.append(cx); hws.append(hw)
n = sum(1 for i in range(len(fr)) if a0 + i / FPS >= t0 - 1e-3)
if not tops or vus < 0.5 * max(n, 1):
    sys.exit("pas de visage")
k = 1920 / H
if "--json" in sys.argv:
    print(json.dumps({"top": int(round(np.median(tops) * k)), "cx": int(round(np.median(cxs) * k)),
                      "hw": int(round(np.median(hws) * k)), "visage": round(vus / max(n, 1), 2)}))
else:
    print(int(round(np.median(tops) * k)))
