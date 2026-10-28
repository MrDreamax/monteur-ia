"""Temps forts d'une musique : où la faire démarrer pour qu'elle « frappe » dès la 1re image (28/10, CAM20062 :
« trouve le moment de la musique qui a de l'impact », au lieu d'un bruitage ajouté).

    python3 attaque.py <musique> [début] [fin]     -> les 5 plus fortes attaques entre début et fin (défaut 0-60 s)

Attaque = saut d'énergie sur 50 ms (onde lissée à 10 ms), pondéré par le niveau atteint juste après : un coup de
batterie / un accord plaqué sort en tête, une montée douce non. Mettre music.from = l'instant donné (la musique part pile
sur le coup ; mix.py démarre sec et +4 dB les 2 premières secondes).
"""
import subprocess, sys
import numpy as np

src = sys.argv[1]
a = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
b = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
SR = 8000
x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", src, "-ac", "1", "-ar", str(SR),
                                  "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
h = SR // 100                                                    # 10 ms
e = np.array([np.sqrt(np.mean(x[i:i + h] ** 2)) + 1e-9 for i in range(0, len(x) - h, h)])
db = 20 * np.log10(e)
score = []
for k in range(5, len(db) - 10):
    saut = db[k:k + 2].max() - db[k - 5:k].mean()               # montée en 50 ms
    apres = db[k:k + 10].mean()                                   # niveau tenu 100 ms après
    if saut > 3: score.append((saut + 0.5 * (apres - db.max()), k))
score.sort(reverse=True)
pris = []
for sc, k in score:
    if all(abs(k - j) > 40 for _, j in pris): pris.append((sc, k))   # 1 attaque par 0,4 s
    if len(pris) == 5: break
for sc, k in pris:
    print(f"{a + k / 100:7.2f} s   saut {db[k:k + 2].max() - db[k - 5:k].mean():4.1f} dB   niveau {db[k:k + 10].mean():5.1f} dB")
