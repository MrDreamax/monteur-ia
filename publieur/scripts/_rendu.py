"""Rendu HTML -> PNG avec Chrome headless, dans un dossier temporaire (Chrome ne lit pas ~/Documents à cause des droits macOS)."""
import os, shutil, subprocess, tempfile
from PIL import Image

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def rendre(html, fichiers, sortie, largeur, hauteur, rogner_blanc=False):
    """html : texte de la page. fichiers : {nom_dans_la_page: chemin_source}. Les polices M et I sont fournies."""
    tmp = tempfile.mkdtemp(prefix="publieur-")
    try:
        for nom in ("Montserrat.ttf", "InstrumentSerif-Italic.ttf"):
            shutil.copy(os.path.join(ASSETS, nom), os.path.join(tmp, nom))
        for nom, src in fichiers.items():
            shutil.copy(src, os.path.join(tmp, nom))
        page = os.path.join(tmp, "page.html")
        with open(page, "w") as f:
            f.write(html)
        png = os.path.join(tmp, "out.png")
        subprocess.run([CHROME, "--headless=new", "--use-mock-keychain", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", f"--window-size={largeur},{hauteur}",
                        f"--screenshot={png}", "file://" + page],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        im = Image.open(png).convert("RGB")
        if rogner_blanc:
            w, h = im.size
            px = im.load()
            y = h - 1
            while y > 0 and all(px[x, y] == (255, 255, 255) for x in range(0, w, 20)):
                y -= 1
            if y >= h - 2:
                raise SystemExit(f"Page coupée : agrandir la hauteur de rendu ({hauteur}px)")
            im = im.crop((0, 0, w, min(h, y + 60)))
        os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
        im.save(sortie)
        return sortie
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
