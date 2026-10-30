"""SuperVeille : lit les vidéos enregistrées sur Instagram (28/10/2026, l’utilisateur fait la veille lui-même en enregistrant).
On passe par la session Instagram déjà ouverte dans Chrome (cookies lus par yt-dlp sur le Mac) : aucun mot de passe,
rien n'est écrit sur le disque, rien n'est envoyé ailleurs qu'à instagram.com. Lecture seule : on ne désenregistre rien.
Un profil Chrome = un compte Instagram : tous les profils connectés sont lus (l’utilisateur enregistre sur ses deux comptes).
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from yt_dlp.cookies import YDLLogger, extract_cookies_from_browser

CHROME = os.path.expanduser("~/Library/Application Support/Google/Chrome")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/141.0.0.0 Safari/537.36")
APP_ID = "936619743392459"  # l'appli web d'Instagram (même en-tête que le site)
PAGES_MAX = 120  # 1re lecture d'un compte : 21 par page, ~2 500 enregistrés (une fois, ~5 min)
CONNUS = 0.8  # page où 80 % des reels sont déjà connus : le reste est déjà lu, on s'arrête
PAUSE = 1.5  # entre deux pages : le rythme d'un humain qui fait défiler


class Silence(YDLLogger):
    def debug(self, *a, **k):
        pass

    info = warning = error = debug


class Erreur(Exception):
    pass


def profils():
    """Profils Chrome qui ont une session Instagram ouverte."""
    try:
        infos = json.load(open(os.path.join(CHROME, "Local State"))).get("profile", {}).get("info_cache", {})
    except (OSError, ValueError):
        return []
    return [p for p in infos if any(os.path.exists(os.path.join(CHROME, p, f)) for f in ("Cookies", "Network/Cookies"))]


def session(profil):
    jar = extract_cookies_from_browser("chrome", profil, logger=Silence())
    ig = {k.name: k.value for k in jar if k.domain.endswith("instagram.com")}
    if not ig.get("sessionid"):
        return None, None
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", UA), ("X-IG-App-ID", APP_ID), ("X-Requested-With", "XMLHttpRequest"),
                     ("X-CSRFToken", ig.get("csrftoken", "")), ("Referer", "https://www.instagram.com/")]
    return op, ig.get("ds_user_id", profil)


def media(m, compte):
    """Un reel enregistré, au format de l'appli. None pour les photos et carrousels (rien à transcrire)."""
    if m.get("media_type") != 2:
        return None
    images = (m.get("image_versions2") or {}).get("candidates") or []
    return {"code": m["code"], "lien": f"https://www.instagram.com/reel/{m['code']}/", "createur": m["user"]["username"],
            "likes": m.get("like_count") or 0, "vues": m.get("play_count") or m.get("ig_play_count") or 0,
            "date": time.strftime("%Y-%m-%d", time.localtime(m.get("taken_at") or 0)), "duree": round(m.get("video_duration") or 0),
            "legende": ((m.get("caption") or {}).get("text") or "")[:600], "image": images[0]["url"] if images else None,
            "compte": compte}


def lire_compte(op, compte, connus=frozenset()):
    """Enregistrés du plus récent au plus ancien. connus = codes déjà lus (compte lu en entier avant) : on ne lit que les
    pages neuves. Renvoie (reels, complet) ; complet = on est allé jusqu'au bout de la liste."""
    items, suite = [], None
    for page in range(PAGES_MAX):
        url = "https://www.instagram.com/api/v1/feed/saved/posts/" + (f"?max_id={urllib.parse.quote(suite)}" if suite else "")
        try:
            d = json.load(op.open(url, timeout=25))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise Erreur("Instagram freine (trop de lectures). Réessaie dans 10 minutes.")
            if e.code in (401, 403):
                raise Erreur("Instagram demande de te reconnecter : ouvre instagram.com dans Chrome, puis Actualiser.")
            raise Erreur(f"Instagram répond {e.code}.")
        except (OSError, ValueError) as e:
            raise Erreur(f"Instagram ne répond pas ({str(e)[:80]}).")
        neufs = [x for x in (media(it.get("media") or {}, compte) for it in d.get("items", [])) if x]
        items += neufs
        suite = d.get("next_max_id")
        if not d.get("more_available") or not suite:
            return items, True
        if connus and neufs and sum(x["code"] in connus for x in neufs) >= CONNUS * len(neufs):
            return items, True
        time.sleep(PAUSE)
    return items, False


def lire(deja=None):
    """{compte: (reels, complet)} pour chaque profil Chrome connecté à Instagram. deja = {compte: codes connus} pour les
    comptes déjà lus en entier (lecture rapide : seulement les nouveaux)."""
    out = {}
    for p in profils():
        try:
            op, compte = session(p)
        except Exception as e:  # trousseau refusé, Chrome absent...
            raise Erreur(f"Je n'arrive pas à lire ta connexion Chrome ({str(e)[:80]}).")
        if op and compte not in out:
            out[compte] = lire_compte(op, compte, (deja or {}).get(compte, frozenset()))
    if not out:
        raise Erreur("Aucun compte Instagram ouvert dans Chrome : connecte-toi sur instagram.com, puis Actualiser.")
    return out


def reel(code):
    """Les chiffres d'un seul reel (lien collé). 29/10 : yt-dlp ne donne jamais les vues d'un reel Instagram, ils
    arrivaient à « 0 vue ». Le code du lien se convertit en numéro de vidéo (base 64 d'Instagram). None si illisible."""
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    n = 0
    for ch in code[:11]:
        n = n * 64 + alpha.index(ch)
    for p in profils():
        try:
            op, compte = session(p)
            if op:
                d = json.load(op.open(f"https://www.instagram.com/api/v1/media/{n}/info/", timeout=20))
                return media((d.get("items") or [{}])[0], compte)
        except Exception:
            continue
    return None


if __name__ == "__main__":
    for compte, (items, complet) in lire().items():
        print(compte, len(items), "reels enregistrés")
        for x in items[:5]:
            print(" ", x["code"], "@" + x["createur"], x["likes"], x["duree"], "s")
