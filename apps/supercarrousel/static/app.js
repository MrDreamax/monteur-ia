// SuperCarrousel : un seul fichier, 4 écrans (départ, je fabrique, tes retours, publier) + le tiroir Ma DA.
const $ = (id) => document.getElementById(id);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const S = { depart: "reel", video: null, images: [], pid: null, projet: null, i: 0, accueil: null, poll: null, vue: null };

async function api(url, corps) {
  const r = await fetch(url, corps === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.erreur || "erreur");
  return j;
}

// typo française à l'écran aussi : jamais « ? », « : » ou « » » seuls en début de ligne
const fr = (t) => (t || "").replace(/ ([?!:;»])/g, "\u00a0$1").replace(/« /g, "«\u00a0");

function toast(t) {
  const el = $("toast");
  el.textContent = t;
  el.classList.add("on");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove("on"), 3200);
}

function montrer(vue) {
  S.vue = vue;
  $("e-depart").hidden = vue !== "depart";
  $("e-fab").hidden = vue !== "fab";
  $("e-travail").hidden = !(vue === "retours" || vue === "publier");
  $("side-retours").hidden = vue !== "retours";
  $("side-publier").hidden = vue !== "publier";
  $("form-retour").hidden = vue !== "retours";
  $("pret").hidden = vue !== "publier";
}

// ------------------------------------------------------------ en-tête + DA
function entete() {
  const p = S.projet, da = S.accueil && S.accueil.da;
  if (da) $("btn-da").textContent = "Ma DA · " + da.duo;
  if (!p) {
    $("hd-titre").textContent = "Nouveau carrousel";
    $("hd-modele").hidden = true;
    return;
  }
  const v = p.version;
  const titre = (p.etat.titre || "Carrousel");
  const valide = p.etat.statut === "valide";
  $("hd-titre").innerHTML = "";
  $("hd-titre").append(titre);
  if (v) {
    const b = document.createElement("b");
    b.textContent = " · Version " + v + (valide ? " · validée ✓" : "");
    $("hd-titre").append(b);
  }
  const mod = { epure: "Épuré", cinema: "Cinéma" }[p.modele_rendu] || (da && da.modele);
  $("hd-modele").textContent = mod || "";
  $("hd-modele").hidden = !mod;
}

async function chargerAccueil() {
  S.accueil = await api("/api/accueil");
  $("pastille-txt").textContent = S.accueil.da.pastille;
  entete();
  remplirTiroir();
  mesCarrousels();
}

// les carrousels déjà faits, à rouvrir d'un clic
function mesCarrousels() {
  const l = S.accueil.projets || [];
  $("mes").hidden = !l.length;
  $("mes-l").replaceChildren(...l.map((p) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "mc";
    b.innerHTML = `<img src="${p.vignette}" alt="" loading="lazy"><b></b><small></small>`;
    b.querySelector("b").textContent = p.titre;
    b.querySelector("small").textContent = "Version " + p.version + (p.valide ? " · validée ✓" : "");
    b.onclick = () => ouvrirProjet(p.id);
    return b;
  }));
}

// ------------------------------------------------------------ écran 0
const TEXTES = {
  reel: ["Dépose ta vidéo ici", true, "Colle un lien Instagram, TikTok ou YouTube"],
  reprendre: ["Dépose les captures du carrousel ici", false, "Colle le lien du carrousel (Instagram, TikTok)"],
};

function choisirDepart(d) {
  S.depart = d;
  document.querySelectorAll(".c").forEach((c) => {
    const on = c.dataset.depart === d;
    c.classList.toggle("on", on);
    c.setAttribute("aria-checked", on);
  });
  $("zone-fichier").hidden = d === "idee";
  $("zone-idee").hidden = d !== "idee";
  if (d !== "idee") {
    const [titre, montages, ph] = TEXTES[d];
    $("drop-titre").textContent = titre;
    $("drop-sous").hidden = !montages;
    $("lien").placeholder = ph;
    $("fichier").accept = d === "reel" ? "video/*" : "image/*";
    $("fichier").multiple = d === "reprendre";
  } else {
    setTimeout(() => $("idee").focus(), 50);
  }
  S.video = null; S.images = [];
  $("drop").classList.remove("plein");
  $("choix").hidden = true;
  verifier();
}

function verifier() {
  const lien = $("lien").value.trim();
  let ok = false;
  if (S.depart === "idee") ok = $("idee").value.trim().length > 3;
  else if (S.depart === "reel") ok = !!S.video || /^https?:\/\//.test(lien);
  else ok = S.images.length > 0 || /^https?:\/\//.test(lien);
  $("fabriquer").disabled = !ok;
  $("err-depart").textContent = "";
}

function choisi(texte) {
  $("choix").textContent = "✓ " + texte;
  $("choix").hidden = false;
  $("drop").classList.add("plein");
  verifier();
}

function envoyerFichier(f) {
  return new Promise((ok, ko) => {
    const x = new XMLHttpRequest();
    x.open("PUT", "/api/depot?nom=" + encodeURIComponent(f.name));
    x.upload.onprogress = (e) => { if (e.lengthComputable) $("choix").textContent = "Envoi… " + Math.round(e.loaded / e.total * 100) + " %"; };
    x.onload = () => (x.status === 200 ? ok(JSON.parse(x.responseText).chemin) : ko(new Error("envoi raté")));
    x.onerror = () => ko(new Error("envoi raté"));
    x.send(f);
  });
}

async function deposer(fichiers) {
  const liste = [...fichiers];
  if (!liste.length) return;
  $("choix").hidden = false;
  try {
    if (S.depart === "reel") {
      const f = liste.find((x) => x.type.startsWith("video/")) || liste[0];
      S.video = await envoyerFichier(f);
      choisi(f.name);
    } else {
      const imgs = liste.filter((x) => x.type.startsWith("image/"));
      S.images = [];
      for (const f of imgs) S.images.push(await envoyerFichier(f));
      choisi(imgs.length + " capture" + (imgs.length > 1 ? "s" : "") + " du carrousel");
    }
  } catch (e) {
    $("err-depart").textContent = "L'envoi a raté. Réessaie.";
  }
}

async function ouvrirMontages(e) {
  e.preventDefault();
  e.stopPropagation();
  const vids = await api("/api/videos");
  $("liste-videos").innerHTML = "";
  for (const v of vids) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "vid";
    b.innerHTML = `<img loading="lazy" alt="" src="${v.vignette}">`;
    b.append(v.nom);
    b.onclick = () => { S.video = v.video; $("pop-montages").hidden = true; choisi(v.nom); };
    $("liste-videos").append(b);
  }
  $("pop-montages").hidden = false;
}

async function fabriquer() {
  $("fabriquer").disabled = true;
  const d = { depart: S.depart };
  const lien = $("lien").value.trim();
  if (S.depart === "idee") d.idee = $("idee").value.trim();
  else if (S.depart === "reel") { if (S.video) d.video = S.video; else d.lien = lien; }
  else { if (S.images.length) d.images = S.images; else d.lien = lien; }
  try {
    const r = await api("/api/fabriquer", d);
    ouvrirProjet(r.id);
  } catch (e) {
    $("err-depart").textContent = e.message;
    $("fabriquer").disabled = false;
  }
}

// ------------------------------------------------------------ projet : suivi
function ouvrirProjet(pid) {
  S.pid = pid;
  history.replaceState(null, "", "#p=" + pid);
  S.i = 0;
  rafraichir();
}

async function rafraichir() {
  clearTimeout(S.poll);
  if (!S.pid) return;
  let p;
  try { p = await api("/api/projet/" + S.pid); } catch (e) { S.poll = setTimeout(rafraichir, 2000); return; }
  S.projet = p;
  entete();
  const st = p.etat.statut;
  if (["prepa", "attente_texte", "attente_corrections", "fabrication", "erreur", "besoin_images"].includes(st)) {
    if (st === "besoin_images") {
      montrer("depart");
      choisirDepart("reprendre");
      $("err-depart").textContent = p.etat.message;
      S.pid = null; S.projet = null; history.replaceState(null, "", "#");
      entete();
      return;
    }
    vueFab(p);
    S.poll = setTimeout(rafraichir, 800);
    return;
  }
  if (st === "valide") vuePublier(p);
  else vueRetours(p);
}

function vueFab(p) {
  montrer("fab");
  const e = p.etat, st = e.statut, fab = e.fab || {};
  const corrige = (e.version_en_cours || 1) > 1 || st === "attente_corrections";
  const total = st === "fabrication" ? fab.total : (p.slides.length || 8);
  const faites = st === "fabrication" ? fab.faites : 0;
  let titre = e.message || "Je prépare…";
  if (st === "fabrication") titre = (corrige ? "Je corrige la slide " : "J'écris la slide ") + Math.min(faites + 1, total) + " sur " + total + "…";
  if (st === "erreur") titre = e.message;
  $("fab-titre").textContent = titre;
  $("fab-sous").textContent = st === "erreur" ? (e.detail || "") : corrige ? "Je refais la version " + ((p.version || 0) + 1) + " avec tes retours. Environ 1 min." : "Ton carrousel se construit. Environ 1 min.";
  const g = $("grille");
  if (g.children.length !== total) {
    g.innerHTML = "";
    for (let k = 0; k < total; k++) g.append(Object.assign(document.createElement("div"), { className: "case vide" }));
  }
  const imgs = st === "fabrication" ? (p.en_cours || []) : [];
  [...g.children].forEach((c, k) => {
    if (imgs[k] && !c.querySelector("img")) {
      c.className = "case faite";
      c.innerHTML = `<img alt="Slide ${k + 1}" src="${imgs[k]}">`;
    } else if (!imgs[k]) {
      c.className = "case vide" + (st === "fabrication" && k === faites ? " courante" : "");
      c.innerHTML = "";
    }
  });
  const barre = $("barre").parentElement;
  barre.classList.toggle("indet", st !== "fabrication" && st !== "erreur");
  $("barre").style.width = st === "fabrication" ? Math.round(faites / total * 100) + "%" : "";
  const aide = $("fab-aide");
  aide.hidden = !(p.attente_s > 90);
  if (!aide.hidden) aide.textContent = "Claude n'a pas encore pris la main. Dans le chat, dis : « go carrousel ».";
}

// ------------------------------------------------------------ écran 2 : retours
function pins(i) {
  return (S.projet.retours || []).filter((r) => r.slide === i + 1)
    .map((r) => `<i class="pin${r.statut === "corrige" ? " ok" : ""}"><span>${r.id}</span></i>`).join("");
}

function dessinerSlides() {
  const p = S.projet, n = p.slides.length;
  S.i = Math.max(0, Math.min(S.i, n - 1));
  const g = $("grande");
  if (g.getAttribute("src") !== p.slides[S.i]) {
    g.style.opacity = 0;
    g.onload = () => (g.style.opacity = 1);
    g.src = p.slides[S.i];
  }
  g.alt = "Slide " + (S.i + 1);
  $("compteur").textContent = "Slide " + (S.i + 1) + " sur " + n;
  $("at").textContent = "slide " + (S.i + 1);
  $("prec").disabled = S.i === 0;
  $("suiv").disabled = S.i === n - 1;
  $("strip").innerHTML = p.slides.map((src, k) =>
    `<button type="button" class="sl${k === S.i ? " on" : ""}" data-k="${k}" aria-label="Slide ${k + 1}"><img alt="" src="${src}">${S.vue === "retours" ? pins(k) : ""}</button>`).join("");
}

function vueRetours(p) {
  montrer("retours");
  dessinerSlides();
  const rs = p.retours || [];
  const aFaire = rs.filter((r) => r.statut === "a_faire").length;
  const corr = rs.filter((r) => r.statut === "corrige").length;
  $("compte-retours").textContent = rs.length ? aFaire + " à faire · " + corr + " corrigé" + (corr > 1 ? "s" : "") : "";
  $("vide-retours").hidden = rs.length > 0;
  $("liste-retours").innerHTML = "";
  for (const r of rs) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "note" + (r.statut === "corrige" ? " ok" : r.statut === "envoye" ? " envoye" : "");
    const t = document.createElement("div");
    t.innerHTML = `<small>Slide ${r.slide}</small>`;
    t.append(fr(r.texte));
    if (r.statut === "corrige") {
      const rep = document.createElement("div");
      rep.className = "rep";
      rep.innerHTML = "<b>Corrigé ✓</b> ";
      rep.append(fr(r.reponse));
      t.append(rep);
      t.insertAdjacentHTML("beforeend", '<span class="rv">▶ Revoir</span>');
    }
    b.innerHTML = `<span class="num">${r.id}</span>`;
    b.append(t);
    b.onclick = () => { S.i = r.slide - 1; dessinerSlides(); };
    $("liste-retours").append(b);
  }
  $("fin-txt").textContent = "Fini ? Je corrige tout et je te renvoie la version " + (p.version + 1) + ".";
  $("suivant").disabled = aFaire === 0;
}

async function ajouterRetour(e) {
  e.preventDefault();
  const t = $("retour").value.trim();
  if (!t) return;
  $("retour").value = "";
  S.projet = await api(`/api/projet/${S.pid}/retour`, { slide: S.i + 1, texte: t });
  vueRetours(S.projet);
}

// ------------------------------------------------------------ écran 4 : publier
function vuePublier(p) {
  montrer("publier");
  dessinerSlides();
  $("pret-sous").textContent = p.slides.length + " slides · 1080 × 1440";
  $("nb-img").textContent = p.slides.length;
  const mc = S.accueil.metricool;
  $("pub-branche").hidden = !mc.branche;
  $("pub-dl-seul").hidden = mc.branche;
  if (mc.branche) {
    $("compte").textContent = "compte " + (mc.compte || "Metricool");
    $("essai").hidden = !S.accueil.mode_essai;
    $("vrai").hidden = S.accueil.mode_essai;
    etatPublication(p);
    if (!$("quand").value) {
      const d = new Date(Date.now() + 86400000);
      d.setHours(18, 0, 0, 0);
      $("quand").value = new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    }
    majProgrammer();
  }
}

function majProgrammer() {
  const d = new Date($("quand").value);
  $("pub-prog").textContent = isNaN(d) ? "Programmer" : "Programmer " + d.toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "2-digit" }) + " · " + d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

// ce que Claude a fait de la publication (publication.json) : en cours, envoyé, en partie, pas envoyé
function etatPublication(p) {
  const P = p.publication || {}, e = $("pub-etat");
  const enCours = ["a_faire", "en_cours"].includes(P.statut);
  ["pub-now", "pub-prog"].forEach((id) => ($(id).disabled = enCours));
  let h = "";
  if (enCours) h = `<div class="pub-encours"><i class="spin"></i><div><b>Envoi en cours</b><br>${esc(P.etape || "Claude envoie à Metricool…")}</div></div>`;
  else if (P.statut) h = `<div class="pub-res ${P.statut === "programme" ? "ok" : "ko"}"><b>${{ programme: "Envoyé ✓", partiel: "Envoyé en partie", erreur: "Pas envoyé" }[P.statut] || esc(P.statut)}</b>`
    + `${P.heure ? " · " + esc(String(P.heure).replace("T", " ").slice(0, 16)) : ""}<br>${esc(P.message || "")}`
    + (P.posts || []).map((x) => `<a href="${esc(x.planner)}" target="_blank">Voir dans Metricool (${esc((x.reseaux || []).join(", "))})</a>`).join("")
    + ((P.manque || []).length ? `<br>Pas parti : ${esc(P.manque.join(", "))}` : "") + `</div>`;
  if (p.deja_publie && !enCours) h += `<p class="pub-deja">Déjà publié : ${esc(p.deja_publie)}</p>`;
  e.innerHTML = h;
  clearTimeout(etatPublication.k);
  if (enCours) etatPublication.k = setTimeout(async () => {
    if (S.vue !== "publier" || !S.pid) return;
    const q = await api("/api/projet/" + S.pid).catch(() => null);
    if (q) { S.projet = q; etatPublication(q); }
  }, 4000);
}

// 1er clic = arme le bouton, 2e clic dans les 6 s = envoi réel ; déjà publié = « Republier quand même »
async function publier(quand, bouton, forcer = false) {
  const reseaux = [...document.querySelectorAll(".sw:checked")].map((x) => x.dataset.res);
  if (!reseaux.length) return toast("Choisis au moins un réseau.");
  if (!S.accueil.mode_essai && !bouton.classList.contains("arme")) {
    const avant = bouton.textContent;
    bouton.classList.add("arme");
    bouton.textContent = `Confirmer : ça part sur ${reseaux.length} réseau${reseaux.length > 1 ? "x" : ""}`;
    clearTimeout(bouton.k);
    bouton.k = setTimeout(() => { bouton.classList.remove("arme"); bouton.textContent = avant; bouton.onclick = () => publier(quand === "maintenant" ? "maintenant" : $("quand").value, bouton); }, 6000);
    return;
  }
  clearTimeout(bouton.k);
  bouton.disabled = true;
  const r = await fetch(`/api/projet/${S.pid}/publier`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reseaux, quand, forcer }) });
  const j = await r.json().catch(() => ({}));
  bouton.disabled = false;
  if (r.status === 409) {
    bouton.textContent = "Republier quand même";
    bouton.onclick = () => publier(quand, bouton, true);
    return toast(`Déjà publié (${j.deja}). Reclique pour republier quand même.`, 6000);
  }
  bouton.classList.remove("arme");
  toast(j.message || "Erreur", 5000);
  if (j.projet) { S.projet = j.projet; etatPublication(j.projet); majProgrammer(); }
}

async function telecharger() {
  $("telecharger").disabled = true;
  try {
    const r = await api(`/api/projet/${S.pid}/telecharger`, {});
    const nom = r.chemin.split("/").pop();
    $("dl-ok").textContent = "Rangé dans Téléchargements ✓ " + nom;
    $("dl-ok").hidden = false;
  } finally {
    $("telecharger").disabled = false;
  }
}

// ------------------------------------------------------------ écran 3 : Ma DA
function remplirTiroir() {
  const a = S.accueil;
  if (!a) return;
  const sd = a.superda;
  const fr = $("tiroir-iframe");
  fr.hidden = !sd.en_ligne;
  document.querySelector(".t-hd").hidden = sd.en_ligne;  // SuperDA a son propre en-tête « Ma DA ×»
  $("tiroir-repli").hidden = sd.en_ligne;
  if (sd.en_ligne && fr.getAttribute("src") !== sd.url) fr.src = sd.url;
  $("lignes-da").innerHTML = "";
  for (const [nom, val, partage] of a.da.lignes) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "ligne";
    b.innerHTML = `<span></span><b></b>`;
    b.firstChild.textContent = nom;
    if (partage) b.firstChild.insertAdjacentHTML("beforeend", "<em>partagé</em>");
    b.lastChild.textContent = val + " ›";
    b.onclick = () => aideDA();
    $("lignes-da").append(b);
  }
}

function aideDA() {
  const el = $("da-aide");
  el.textContent = "SuperDA n'est pas ouvert. Dis « ouvre SuperDA » dans le chat, ou demande ton changement à Claude ci-dessous.";
  el.hidden = false;
}

async function ouvrirTiroir() {
  await chargerAccueil();
  const fr = $("tiroir-iframe");  // SuperDA relit da.json à chaque ouverture (changé ailleurs entre-temps)
  if (!fr.hidden && fr.contentWindow) fr.contentWindow.postMessage({ type: "superda:recharger" }, "*");
  $("tiroir").classList.add("ouvert");
  $("tiroir").setAttribute("aria-hidden", "false");
}

async function fermerTiroir() {
  $("tiroir").classList.remove("ouvert");
  $("tiroir").setAttribute("aria-hidden", "true");
  await chargerAccueil();
  appliquerDA(false);
}

async function appliquerDA(dire) {
  const p = S.projet;
  if (!p || !p.version || !["retours", "valide"].includes(p.etat.statut)) return;
  if (p.da_rendue === S.accueil.da.empreinte) {
    if (dire) toast("Ton carrousel a déjà cette DA.");
    return;
  }
  await api(`/api/projet/${S.pid}/da`, {});
  rafraichir();
}

// ------------------------------------------------------------ dictée (micro)
function dicter(btn) {
  const R = window.SpeechRecognition || window.webkitSpeechRecognition;
  const champ = $(btn.dataset.mic);
  if (!R) { toast("Dictée indisponible ici : appuie deux fois sur Fn pour la dictée du Mac."); champ.focus(); return; }
  const rec = new R();
  rec.lang = "fr-FR";
  rec.interimResults = true;
  const avant = champ.value ? champ.value + " " : "";
  btn.classList.add("ecoute");
  rec.onresult = (e) => { champ.value = avant + [...e.results].map((r) => r[0].transcript).join(""); verifier(); };
  rec.onend = rec.onerror = () => btn.classList.remove("ecoute");
  rec.start();
}

// ------------------------------------------------------------ branchements
document.querySelectorAll(".c").forEach((c) => (c.onclick = () => choisirDepart(c.dataset.depart)));
$("lien").oninput = verifier;
$("idee").oninput = verifier;
$("fichier").onchange = (e) => deposer(e.target.files);
const drop = $("drop");
drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("survol"); };
drop.ondragleave = () => drop.classList.remove("survol");
drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("survol"); deposer(e.dataTransfer.files); };
$("lien-montages").onclick = ouvrirMontages;
document.querySelectorAll("[data-ferme]").forEach((b) => (b.onclick = () => ($(b.dataset.ferme).hidden = true)));
$("pop-montages").onclick = (e) => { if (e.target.id === "pop-montages") e.target.hidden = true; };
$("fabriquer").onclick = fabriquer;
$("pastille").onclick = ouvrirTiroir;
$("btn-da").onclick = () => ($("tiroir").classList.contains("ouvert") ? fermerTiroir() : ouvrirTiroir());
$("tiroir-x").onclick = fermerTiroir;
$("prec").onclick = () => { S.i--; dessinerSlides(); };
$("suiv").onclick = () => { S.i++; dessinerSlides(); };
$("strip").onclick = (e) => { const b = e.target.closest(".sl"); if (b) { S.i = +b.dataset.k; dessinerSlides(); } };
$("form-retour").onsubmit = ajouterRetour;
$("suivant").onclick = async () => { S.projet = await api(`/api/projet/${S.pid}/suivant`, {}); rafraichir(); };
$("parfait").onclick = async () => {
  const reste = (S.projet.retours || []).filter((r) => r.statut === "a_faire").length;
  if (reste && !confirm(reste + " retour" + (reste > 1 ? "s" : "") + " pas encore corrigé" + (reste > 1 ? "s" : "") + ". Publier quand même ?")) return;
  await api(`/api/projet/${S.pid}/valider`, {});
  rafraichir();
};
$("rouvrir").onclick = async () => { await api(`/api/projet/${S.pid}/rouvrir`, {}); rafraichir(); };
$("telecharger").onclick = telecharger;
$("pub-dl").onclick = telecharger;
$("pub-now").onclick = () => publier("maintenant", $("pub-now"));
$("pub-prog").onclick = () => publier($("quand").value, $("pub-prog"));
$("quand").oninput = majProgrammer;
$("form-da").onsubmit = async (e) => {
  e.preventDefault();
  const t = $("da-txt").value.trim();
  if (!t) return;
  await api("/api/da/demande", { texte: t });
  $("da-txt").value = "";
  toast("Noté pour Claude : il le change dans ta DA.");
};
$("da-grand").onclick = () => (S.accueil.superda.en_ligne ? window.open(S.accueil.superda.url.replace("?tiroir=carrousels", "?onglet=carrousels"), "_blank") : aideDA());
$("da-enreg").onclick = () => appliquerDA(true);
document.querySelectorAll("[data-mic]").forEach((b) => (b.onclick = () => dicter(b)));
// SuperDA dans le tiroir parle par messages : fermer, et maj = DA enregistrée -> le carrousel se refait avec
window.addEventListener("message", async (e) => {
  const t = e.data && e.data.type;
  if (t === "superda:fermer") fermerTiroir();
  if (t === "superda:maj") { await chargerAccueil(); appliquerDA(false); toast("DA enregistrée : je refais ton carrousel avec."); }
});

document.addEventListener("keydown", (e) => {
  if (e.target.matches("input,textarea")) return;
  if (S.vue === "retours" || S.vue === "publier") {
    if (e.key === "ArrowLeft" && S.i > 0) { S.i--; dessinerSlides(); }
    if (e.key === "ArrowRight" && S.projet && S.i < S.projet.slides.length - 1) { S.i++; dessinerSlides(); }
  }
  if (e.key === "Escape") { if ($("tiroir").classList.contains("ouvert")) fermerTiroir(); $("pop-montages").hidden = true; }
});

(async () => {
  await chargerAccueil();
  const m = location.hash.match(/p=([\w-]+)/);
  const da = /[#&]da=1/.test(location.hash);  // lien direct vers le tiroir Ma DA
  if (m) ouvrirProjet(m[1]);
  else { montrer("depart"); choisirDepart("reel"); }
  if (da) ouvrirTiroir();
})();
