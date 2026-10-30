"""Ouvrier Claude des applis Super (28/10/2026) : SuperCarrousel et SuperMonteur appellent Claude Code tout seuls,
sans chat ouvert. Un seul Claude à la fois sur le Mac (8 Go). Chaque passage est noté dans <app>/_claude.log.
"""
import glob
import os
import shutil
import subprocess
import contextlib
import threading
import time

UN_A_LA_FOIS = threading.Lock()


def trouver_claude():
    """Même recherche que SuperDA (server.py) : PATH, puis les dossiers connus, puis Claude Code de l'appli Claude."""
    p = shutil.which("claude")
    if p:
        return p
    for c in [os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"),
              "/opt/homebrew/bin/claude", "/usr/local/bin/claude"]:
        if os.path.exists(c):
            return c
    base = os.path.expanduser("~/Library/Application Support/Claude/claude-code")
    trouves = glob.glob(os.path.join(base, "*", "*", "claude.app", "Contents", "MacOS", "claude"))

    def cle(chemin):
        v = chemin[len(base) + 1:].split(os.sep)[0]
        return [int(x) if x.isdigit() else 0 for x in v.split(".")]
    trouves.sort(key=cle)
    return trouves[-1] if trouves else None


def lancer(prompt, dossier, outils, delai=900, modele="opus", autres_dossiers=(), attendre_son_tour=True):
    """Lance `claude -p` dans le dossier de l'appli, avec seulement les outils donnés. Renvoie (ok, fin de la sortie)."""
    exe = trouver_claude()
    if not exe:
        return False, "Je ne trouve pas Claude Code sur ce Mac."
    cmd = [exe, "-p", prompt, "--model", modele, "--output-format", "text", "--permission-mode", "acceptEdits",
           "--allowedTools", ",".join(outils), "--disallowedTools", "WebFetch,WebSearch,Agent,NotebookEdit"]
    for a in autres_dossiers:  # dossiers où Claude a aussi le droit d'écrire (ex. le carnet du skill)
        cmd += ["--add-dir", os.path.expanduser(a)]
    # Sans les variables de la session qui a lancé le serveur : Claude utilise le compte connecté sur le Mac
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "ANTHROPIC")) and k not in ("AI_AGENT", "BAGGAGE")}
    debut = time.strftime("%Y-%m-%d %H:%M:%S")
    # attendre_son_tour=False : une tâche courte et pressée (la Recherche rapide de SuperVeille) passe sans attendre la file
    with UN_A_LA_FOIS if attendre_son_tour else contextlib.nullcontext():
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=delai, cwd=dossier, env=env, stdin=subprocess.DEVNULL)
            sortie, ok = (r.stdout or "") + (r.stderr or ""), r.returncode == 0
        except subprocess.TimeoutExpired:
            sortie, ok = "Claude a mis plus de %d min." % (delai // 60), False
    if "Not logged in" in sortie or "/login" in sortie:
        sortie, ok = "Claude n'est pas connecté sur ce Mac : double-clique apps/superda/connecter-claude.command.", False
    with open(os.path.join(dossier, "_claude.log"), "a", encoding="utf-8") as f:
        f.write("\n===== %s -> %s (%s)\n%s\n" % (debut, time.strftime("%H:%M:%S"), "ok" if ok else "ÉCHEC", sortie[-4000:]))
    return ok, sortie.strip()[-400:]
