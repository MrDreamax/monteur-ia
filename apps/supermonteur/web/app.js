// SuperMonteur : la page (28/10/2026). Un reel = ?reel=<id>. Les 4 écrans suivent etat.statut :
// regarde / choix -> 0 style ; montage / retours / correction -> 1 retours ; valide -> 3 publier ; « Ma DA » = tiroir.
const $ = s => document.querySelector(s);
const api = (u, corps) => fetch(u, corps === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(corps)})
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.erreur || r.status); return j; });
const tc = s => { s = Math.max(0, s || 0); return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`; };
const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})[c]);
const toast = (t, ms = 3200) => { const e = $("#toast"); e.textContent = t; e.hidden = false; clearTimeout(toast.k); toast.k = setTimeout(() => e.hidden = true, ms); };
const FPS = 30;

let R = null, DA = null, rid = new URLSearchParams(location.search).get("reel");
let choix = {style: null, cases: {}}, vueCourante = null, srcVid = null;

const STYLES = {
  Dynamique: {l: "Toi + animations, cartons, écran coupé", html: `<div class="sty dyn"><div class="bx"><i></i><i></i><i class="on"></i></div><div class="sb">les 3 étapes</div></div>`},
  Minimaliste: {l: "Un titre qui reste + sous-titres", html: `<div class="sty"><div class="tt">Ta question<em>en titre</em></div><div class="sb">sous-titres</div></div>`},
  Comparatif: {l: "Tableau au-dessus de ta tête", html: `<div class="sty cmp"><div class="cam"></div><div class="ct">Tier list</div><div class="tier"><div><b style="background:#FF7F7F">S</b><span></span></div><div><b style="background:#FFBF7F">A</b><span></span></div><div><b style="background:#FFFF7F">B</b><span></span></div></div></div>`},
  Interview: {l: "2 personnes, plein écran sur qui parle", html: `<div class="sty itv"><div class="p1"></div><div class="p2"></div></div>`},
  Autre: {l: "Voix off, green screen, style d'un créateur", html: `<div class="sty aut"><div class="ic">✦</div></div>`},
};

// ------------------------------------------------------------------------------------------------ chargement + vues
async function charger() {
  DA = await api("/api/da").catch(() => null);
  $("#btn-da").textContent = `Ma DA · ${DA?.duo || "?"}`;
  if (!rid) return accueil();
  try { R = await api(`/api/reel/${rid}`); } catch { history.replaceState(null, "", "/"); rid = null; return accueil(); }
  rendre();
  setInterval(rafraichir, 2500);
}
async function rafraichir() {
  if (!rid) return;
  const n = await api(`/api/reel/${rid}`).catch(() => null);
  if (!n) return;
  const avant = JSON.stringify(R); R = n;
  if (JSON.stringify(n) !== avant) rendre();
}
function montrer(v) {
  for (const id of ["accueil", "style", "retours", "publier"]) $(`#v-${id}`).hidden = id !== v;
  vueCourante = v;
}
function entete() {
  const v = R.version || 0;
  const etiquette = R.statut === "valide" ? `Version ${v} · validée ✓` : v ? `Version ${v}` : "nouveau reel";
  $("#fichier").innerHTML = `${esc(R.nom)} · <b>${etiquette}</b>`;
  const st = R.style && R.statut !== "regarde" && R.statut !== "choix" ? R.style : null;
  $("#pill-style").hidden = !st; $("#pill-style").textContent = st || "";
}
function rendre() {
  entete();
  if (["regarde", "choix"].includes(R.statut) || (R.statut === "erreur" && !R.version)) return ecranStyle();
  if (R.statut === "valide") return ecranPublier();
  return ecranRetours();
}

// ------------------------------------------------------------------------------------------------------ accueil
async function accueil() {
  montrer("accueil");
  $("#fichier").textContent = ""; $("#pill-style").hidden = true;
  const L = await api("/api/reels").catch(() => []);
  const lib = {regarde: "je regarde", choix: "style à choisir", montage: "en montage", retours: "retours", correction: "Claude corrige", valide: "validé ✓", erreur: "bloqué"};
  $("#liste-reels").innerHTML = L.length ? `<p class="lbl" style="font-size:12px;color:#86868B;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Tes reels</p>` +
    `<div class="grille">` + L.map(r => {
      const jour = (r.cree || r.id).slice(0, 10).split("-").reverse().slice(0, 2).join("/");  // 2026-10-28 -> 28/10
      return `<a href="/?reel=${r.id}">${r.vignette ? `<img src="${r.vignette}" alt="" loading="lazy">` : `<i class="vide"></i>`}
        <b>${esc(r.titre || r.nom)}</b><span>${esc(r.nom)} · ${jour}</span><span>${r.version ? "Version " + r.version + " · " : ""}${lib[r.statut] || r.statut}</span></a>`;
    }).join("") + `</div>` : "";
}
async function ouvrirRush(chemin) {
  try { const r = await api("/api/nouveau", {rush: chemin}); location.href = `/?reel=${r.id}`; }
  catch (e) { toast(e.message); }
}
$("#f-chemin").onsubmit = e => { e.preventDefault(); if ($("#chemin").value.trim()) ouvrirRush($("#chemin").value); };
const drop = $("#drop");
drop.onclick = () => $("#fichier-input").click();
$("#fichier-input").onchange = e => e.target.files[0] && envoyer(e.target.files[0]);
drop.ondragover = e => { e.preventDefault(); drop.classList.add("sur"); };
drop.ondragleave = () => drop.classList.remove("sur");
drop.ondrop = e => { e.preventDefault(); drop.classList.remove("sur"); e.dataTransfer.files[0] && envoyer(e.dataTransfer.files[0]); };
async function envoyer(f) {
  toast(`J'importe ${f.name}…`, 60000);
  const r = await fetch("/api/upload", {method: "POST", headers: {"X-Nom": encodeURIComponent(f.name)}, body: f}).then(r => r.json());
  if (r.id) location.href = `/?reel=${r.id}`; else toast(r.erreur || "import raté");
}
$(".top h1").onclick = () => location.href = "/";

// ------------------------------------------------------------------------------------------- écran 0 : le style
function ecranStyle() {
  montrer("style");
  const conseil = R.conseil;
  if (!choix.style) choix.style = conseil || null;
  const img = `/media/${rid}/apercu.jpg`;
  $("#conseil-txt").innerHTML = R.statut === "erreur" ? `<span class="erreur">Le montage s'est arrêté : ${esc(R.erreur)}</span>`
    : conseil ? `J'ai regardé ta vidéo : je te conseille ${conseil}. Touche un style pour changer.`
    : esc(R.etape || "Je regarde ta vidéo…");
  $("#cards").innerHTML = Object.entries(STYLES).map(([n, s]) =>
    `<button class="cd${choix.style === n ? " on" : ""}" data-s="${n}" style="--img:url('${img}')">${n === conseil ? `<span class="rk">Conseillé</span>` : ""}${s.html}<b>${n}</b><span class="l">${s.l}</span></button>`).join("");
  document.querySelectorAll(".cd").forEach(b => b.onclick = () => { choix.style = b.dataset.s; choix.cases = {}; ecranStyle(); });
  const C = R.cases_du_style[choix.style] || [];
  for (const [k] of C) if (!(k in choix.cases)) choix.cases[k] = k !== "brolls";   // tout coché, B-rolls décoché
  const pret = R.statut !== "regarde" && choix.style;
  $("#cases").innerHTML = `<span class="l">Dans ce style :</span>` +
    (C.length ? C.map(([k, l]) => `<button class="ck${choix.cases[k] ? "" : " off"}" data-k="${k}"><i>✓</i>${l}</button>`).join("")
      : `<span class="rien">${choix.style === "Autre" ? "pas de cases : dis à Claude quel style dans le chat" : "choisis un style"}</span>`) +
    `<button class="go" id="monter"${pret ? "" : " disabled"}>${R.statut === "regarde" ? "Je regarde ta vidéo…" : "Monter le reel"}</button>`;
  document.querySelectorAll(".ck").forEach(b => b.onclick = () => { choix.cases[b.dataset.k] = !choix.cases[b.dataset.k]; ecranStyle(); });
  $("#monter").onclick = async () => {
    $("#monter").disabled = true;
    try { R = await api(`/api/monter/${rid}`, {style: choix.style, cases: choix.cases}); rendre(); } catch (e) { toast(e.message); $("#monter").disabled = false; }
  };
}

// ------------------------------------------------------------------------------------------ écran 1 : les retours
const vid = $("#vid");
function ecranRetours() {
  montrer("retours");
  const enCours = R.statut === "montage" || (R.statut === "correction");
  const der = (R.versions || []).slice(-1)[0];
  if (der && srcVid !== der.fichier) { srcVid = der.fichier; const t = vid.currentTime; vid.src = `/media/${rid}/${der.fichier}`; vid.currentTime = 0; }
  $("#encours").hidden = !(R.statut === "montage" || !der);
  $("#encours-titre").textContent = R.version ? `Je remonte la version ${R.version + 1}` : "Je monte ton reel";
  $("#encours-etape").textContent = R.statut === "erreur" ? `Bloqué : ${R.erreur}` : (R.etape || "");
  if (R.statut === "erreur" && der) { $("#encours").hidden = false; $("#encours-titre").textContent = "Le montage s'est arrêté"; }
  const N = R.retours || [], af = N.filter(n => n.statut === "a_faire"), ok = N.filter(n => n.statut === "corrige");
  $("#compte").textContent = N.length ? `${af.length} à faire · ${ok.length} corrigé${ok.length > 1 ? "s" : ""}` : "";
  $("#notes").innerHTML = N.length ? N.map((n, i) => `
    <div class="note${n.statut === "corrige" ? " ok" : ""}"><span class="num">${i + 1}</span><div>
      <small data-t="${n.t}">${tc(n.t)}${n.statut === "a_faire" && n.version && n.version !== R.version ? ` · version ${n.version}` : ""}</small>${esc(n.texte)}
      ${n.statut === "corrige" ? `<div class="rep"><b>Corrigé ✓</b> ${esc(n.reponse)}</div><button class="rv" data-t="${n.t}">▶ Revoir</button>` : ""}
    </div>${n.statut === "a_faire" && R.statut !== "correction" ? `<button class="eff" data-id="${n.id}" title="Retirer">×</button>` : ""}</div>`).join("")
    : `<p class="vide">Regarde ton reel. Dès que quelque chose ne va pas, mets pause et écris-le (ou dicte-le) : il s'accroche à l'image.</p>`;
  document.querySelectorAll(".note small").forEach(s => s.onclick = () => aller(+s.dataset.t));
  document.querySelectorAll(".rv").forEach(b => b.onclick = () => { vid.currentTime = Math.max(0, +b.dataset.t - 2); vid.play(); });
  document.querySelectorAll(".eff").forEach(b => b.onclick = async () => { R = await api(`/api/effacer/${rid}`, {id: +b.dataset.id}); rendre(); });
  const dur = vid.duration || der?.duree || 1;
  // deux retours au même moment : les pastilles se rangent côte à côte au lieu de se cacher
  const larg = $("#pins").clientWidth || 600, place = [];
  $("#pins").innerHTML = N.map(n => {
    const x = Math.min(100, n.t / dur * 100) / 100 * larg;
    let dx = 0;
    while (place.some(p => Math.abs(p - (x + dx)) < 22)) dx += 22;
    place.push(x + dx);
    return `<div class="n${n.statut === "corrige" ? " ok" : ""}" style="left:calc(${Math.min(100, n.t / dur * 100)}% + ${dx}px)" data-t="${n.t}"><span>${N.indexOf(n) + 1}</span></div>`;
  }).join("");
  document.querySelectorAll("#pins .n").forEach(p => p.onclick = e => { e.stopPropagation(); aller(+p.dataset.t); });
  const envoye = R.statut === "correction";
  $("#fin-txt").textContent = envoye ? "" : `Fini ? Je corrige tout et je te renvoie la version ${(R.version || 0) + 1}.`;
  $(".end .envoye")?.remove();
  if (envoye) $(".end").insertAdjacentHTML("afterbegin", `<div class="envoye"><b>Retours envoyés ✓</b><br>Claude corrige tes ${af.length} retour${af.length > 1 ? "s" : ""} et remonte la version ${(R.version || 0) + 1}. Dans le chat Claude, dis juste : « corrige mes retours ».</div>`);
  $("#suivant").disabled = !af.length || enCours || !der;
  $("#parfait").disabled = enCours || !der || R.statut === "erreur";
  $("#retour").disabled = !der;
}
function aller(t) { vid.pause(); vid.currentTime = t; }
function majTemps() {
  const d = vid.duration || 0, t = vid.currentTime || 0;
  $("#tc").textContent = `${tc(t)} / ${tc(d)}`;
  const pc = d ? t / d * 100 : 0;
  $("#bar-p").style.width = pc + "%"; $("#bar-k").style.left = pc + "%";
  if (!$("#retour").value) $("#at").textContent = `à ${tc(t)}`;
  $("#play").textContent = vid.paused ? "▶" : "❚❚";
}
vid.ontimeupdate = vid.onseeked = vid.onplay = vid.onpause = majTemps;
const T0 = parseFloat(new URLSearchParams(location.search).get("t"));   // ?t=14 : ouvre la vidéo à cet instant
vid.onloadedmetadata = () => { if (T0 >= 0 && !vid.dataset.t0) { vid.dataset.t0 = 1; vid.currentTime = T0; } majTemps(); if (R) ecranRetours(); };
$("#play").onclick = () => vid.paused ? vid.play() : vid.pause();
$("#img-moins").onclick = () => { vid.pause(); vid.currentTime = Math.max(0, vid.currentTime - 1 / FPS); };
$("#img-plus").onclick = () => { vid.pause(); vid.currentTime = Math.min(vid.duration, vid.currentTime + 1 / FPS); };
$("#bar").onclick = e => { const r = $("#bar").getBoundingClientRect(); vid.currentTime = (e.clientX - r.left) / r.width * (vid.duration || 0); };
function vitesses(sel, v) {
  sel.querySelectorAll("i").forEach(i => i.onclick = () => { v.playbackRate = +i.dataset.v; sel.querySelectorAll("i").forEach(j => j.classList.toggle("on", j === i)); });
}
vitesses($("#spd"), vid);
// écrire = la vidéo se met en pause, le retour s'accroche à cette image
let tRetour = 0;
$("#retour").onfocus = $("#retour").oninput = () => { if (!vid.paused) vid.pause(); if (!$("#retour").dataset.fixe) { tRetour = vid.currentTime; $("#retour").dataset.fixe = 1; } $("#at").textContent = `à ${tc(tRetour)}`; };
$("#retour").onblur = () => { if (!$("#retour").value) delete $("#retour").dataset.fixe; };
$("#f-retour").onsubmit = async e => {
  e.preventDefault();
  const texte = $("#retour").value.trim(); if (!texte) return;
  const t = $("#retour").dataset.fixe ? tRetour : vid.currentTime;
  try { R = await api(`/api/retour/${rid}`, {t, texte}); $("#retour").value = ""; delete $("#retour").dataset.fixe; rendre(); }
  catch (er) { toast(er.message); }
};
// dicter : micro du navigateur (Chrome / Safari), français
const Reco = window.SpeechRecognition || window.webkitSpeechRecognition;
$("#mic").onclick = () => {
  if (!Reco) return toast("Ce navigateur ne dicte pas : ouvre SuperMonteur dans Chrome, ou utilise la dictée du Mac (touche 🎙 du clavier).");
  vid.pause(); tRetour = vid.currentTime; $("#retour").dataset.fixe = 1; $("#at").textContent = `à ${tc(tRetour)}`;
  const r = new Reco(); r.lang = "fr-FR"; r.interimResults = true;
  const base = $("#retour").value ? $("#retour").value + " " : "";
  r.onresult = ev => { $("#retour").value = base + [...ev.results].map(x => x[0].transcript).join(""); };
  r.onend = () => { $("#mic").classList.remove("rec"); $("#retour").focus(); };
  r.onerror = ev => toast(`Micro : ${ev.error}`);
  $("#mic").classList.add("rec"); r.start();
};
$("#suivant").onclick = async () => { try { R = await api(`/api/suivant/${rid}`, {}); rendre(); } catch (e) { toast(e.message); } };
$("#parfait").onclick = async () => { vid.pause(); R = await api(`/api/valider/${rid}`, {}); rendre(); };

// ------------------------------------------------------------------------------------------- écran 3 : publier
const vid2 = $("#vid2");
async function ecranPublier() {
  montrer("publier");
  vid.pause();
  const der = R.versions.slice(-1)[0];
  if (vid2.dataset.f !== der.fichier) { vid2.dataset.f = der.fichier; vid2.src = `/media/${rid}/${der.fichier}`; }
  $("#pret-info").textContent = `${tc(der.duree)} · 1080 × 1920`;
  const M = await api("/api/metricool").catch(() => ({branche: false}));
  const S = $("#pub-side");
  if (!M.branche) {
    // pas branché : AUCUNE possibilité de publier ni de programmer (maquette 3b)
    S.innerHTML = `<h2>Télécharger</h2><p class="gris">Metricool n'est pas branché : tu télécharges la vidéo + ses 5 légendes (une par réseau) et tu postes toi-même.</p>
      <div class="end"><a class="now" href="/api/telecharger/${rid}" download>Télécharger</a></div>`;
    return;
  }
  const P = R.publication || {};
  if (["a_faire", "en_cours"].includes(P.statut)) {
    // envoi en cours : Claude parle à Metricool ; on relit l'état toutes les 4 s
    S.innerHTML = `<h2>Publier</h2><div class="pub-encours"><i class="spin"></i><div><b>Envoi en cours</b><br>${esc(P.etape || "Claude envoie à Metricool…")}</div></div>
      <p class="gris">Sur ${esc((P.reseaux || []).join(", "))}. Tu peux fermer cette page, ça continue.</p>`;
    clearTimeout(ecranPublier.k);
    ecranPublier.k = setTimeout(async () => { if (vueCourante !== "publier") return; R = await api(`/api/reel/${rid}`).catch(() => R); ecranPublier(); }, 4000);
    return;
  }
  const res = P.statut && P.statut !== "a_faire" ? `<div class="pub-res ${P.statut === "programme" ? "ok" : "ko"}">
      <b>${{programme: "Envoyé ✓", partiel: "Envoyé en partie", erreur: "Pas envoyé"}[P.statut] || esc(P.statut)}</b>
      ${P.heure ? ` · ${esc(String(P.heure).replace("T", " ").slice(0, 16))}` : ""}<br>${esc(P.message || "")}
      ${(P.posts || []).map(x => `<a href="${esc(x.planner)}" target="_blank">Voir dans Metricool (${esc((x.reseaux || []).join(", "))})</a>`).join("")}
      ${(P.manque || []).length ? `<br>Pas parti : ${esc(P.manque.join(", "))}` : ""}</div>` : "";
  const deja = R.deja_publie ? `<p class="pub-deja">Déjà publié : ${esc(R.deja_publie)}</p>` : "";
  const dans = new Date(Date.now() + 864e5); dans.setHours(18, 0, 0, 0);
  const iso = new Date(dans - dans.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
  const R5 = ["Instagram", "TikTok", "YouTube Shorts", "Facebook", "LinkedIn"];
  S.innerHTML = `<h2>Publier</h2>
    <div class="mc">✓ <span><b>Metricool branché</b>${M.compte ? " · compte " + esc(M.compte) : ""}</span></div>
    ${res}${deja}
    <div class="nets">${R5.map(n => `<div class="net">${n}<button class="tg" data-n="${n}" aria-label="${n}"></button></div>`).join("")}</div>
    <div class="dt"><span>Programmer le</span><input type="datetime-local" id="quand" value="${iso}"></div>
    <div class="end"><button class="now" id="p-now">Publier maintenant</button><button class="prog" id="p-prog"></button>
      <a class="dl" href="/api/telecharger/${rid}" download>Juste télécharger</a>
      <p class="essai">${M.essai ? "Mode essai : rien ne part (supermonteur/config.json)." : "Ça part pour de vrai : 2e clic pour confirmer."}</p></div>`;
  const lib = () => { const d = new Date($("#quand").value); $("#p-prog").textContent = `Programmer ${d.toLocaleDateString("fr-FR", {weekday: "short", day: "2-digit", month: "2-digit"})} · ${d.toLocaleTimeString("fr-FR", {hour: "2-digit", minute: "2-digit"})}`; };
  lib(); $("#quand").onchange = lib;
  S.querySelectorAll(".tg").forEach(t => t.onclick = () => t.classList.toggle("off"));
  const reseaux = () => [...S.querySelectorAll(".tg:not(.off)")].map(t => t.dataset.n);
  // 1er clic = arme le bouton (« Confirmer… »), 2e clic dans les 6 s = envoi réel. Déjà publié = 3e étape « Republier quand même ».
  const envoyer = async (bouton, quand, forcer = false) => {
    if (!reseaux().length) return toast("Choisis au moins un réseau.");
    if (!bouton.classList.contains("arme")) {
      const avant = bouton.textContent;
      bouton.classList.add("arme");
      bouton.textContent = `Confirmer : ça part sur ${reseaux().length} réseau${reseaux().length > 1 ? "x" : ""}`;
      clearTimeout(bouton.k); bouton.k = setTimeout(() => { bouton.classList.remove("arme"); bouton.textContent = avant; }, 6000);
      return;
    }
    clearTimeout(bouton.k); bouton.disabled = true;
    const r = await fetch(`/api/publier/${rid}`, {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({quand, reseaux: reseaux(), forcer})});
    const j = await r.json().catch(() => ({}));
    bouton.disabled = false;
    if (r.status === 409) {
      bouton.textContent = "Republier quand même"; bouton.classList.add("arme");
      toast(`Déjà publié (${j.deja}). Reclique pour republier quand même.`, 6000);
      bouton.onclick = () => envoyer(bouton, quand, true);
      return;
    }
    toast(j.message || "Erreur", 5000);
    if (j.ok) { R = await api(`/api/reel/${rid}`); ecranPublier(); }
  };
  $("#p-now").onclick = () => envoyer($("#p-now"), "maintenant");
  $("#p-prog").onclick = () => envoyer($("#p-prog"), $("#quand").value);
}
$("#play2").onclick = () => vid2.paused ? vid2.play() : vid2.pause();
vid2.onloadeddata = () => { if (T0 >= 0 && !vid2.dataset.t0) { vid2.dataset.t0 = 1; vid2.currentTime = T0; } };
vid2.ontimeupdate = vid2.onplay = vid2.onpause = vid2.onloadedmetadata = () => { $("#tc2").textContent = `${tc(vid2.currentTime)} / ${tc(vid2.duration)}`; $("#play2").textContent = vid2.paused ? "▶" : "❚❚"; };
vitesses($("#spd2"), vid2);
$("#rouvrir").onclick = async () => { vid2.pause(); R = await api(`/api/rouvrir/${rid}`, {}); rendre(); };

// ------------------------------------------------------------------------------------------ écran 2 : Ma DA
$("#btn-da").onclick = async () => {
  const t = $("#tiroir");
  if (!t.hidden) return fermerDA();
  t.hidden = false; $("#btn-da").classList.add("n");
  const S = await api("/api/superda").catch(() => ({en_marche: false}));
  const C = $("#tiroir-corps");
  if (S.en_marche) {
    // la vraie DA : SuperDA en tiroir, onglet Montage
    t.classList.add("iframe");   // SuperDA a son propre titre « Ma DA » et sa croix
    // un retour a changé les tailles de CE reel : le dire, sinon le tiroir affiche la DA et on croit que rien n'a bougé
    const propre = R?.tailles_reel ? `<p class="propre">Ce reel garde ses tailles à lui : <b>${esc(R.tailles_reel)}</b>. Ta DA ci-dessous vaut pour tes prochains reels.</p>` : "";
    C.innerHTML = `${propre}<iframe src="${S.url}/?tiroir=montage" title="SuperDA"></iframe>`;
    return;
  }
  // repli : SuperDA ne tourne pas -> les 7 lignes de la DA, en lecture
  DA = await api("/api/da").catch(() => DA);
  C.innerHTML = `<div class="sub">Tu changes ici, ton reel se met à jour.</div>
    ${(DA?.lignes || []).map(l => `<div class="dar"><span>${esc(l.ligne)}</span><b>${esc(l.valeur)} ›</b></div>`).join("")}
    <p class="note-da">SuperDA n'est pas lancé : je te montre ta DA actuelle. Pour la changer, demande à Claude ci-dessous ou lance SuperDA.</p>
    <form class="ask" id="ask-da"><span class="c">C</span><input id="ask-txt" placeholder="Demande à Claude de modifier quelque chose…"><button class="go2">↑</button></form>
    <a class="open off" href="${S.url ? S.url + "/?onglet=montage" : "#"}" target="_blank">Ouvrir SuperDA en grand</a>
    <button class="sv" id="sv-da">Enregistrer pour tous mes reels</button>`;
  $("#ask-da").onsubmit = async e => { e.preventDefault(); const v = $("#ask-txt").value.trim(); if (!v) return;
    await api("/api/demande-da", {texte: v, reel: rid}); $("#ask-txt").value = ""; toast("Noté : Claude change ta DA au prochain passage."); };
  $("#sv-da").onclick = () => { toast("Ta DA est déjà enregistrée pour tous tes reels."); fermerDA(); };
};
// SuperDA parle au tiroir : « fermer » (sa croix), « maj » (DA enregistrée -> la prochaine version la prend)
addEventListener("message", e => {
  const ty = e.data?.type;
  if (ty === "superda:fermer") fermerDA();
  if (ty === "superda:maj") { api("/api/da").then(d => { DA = d; $("#btn-da").textContent = `Ma DA · ${d.duo}`; }); toast("DA enregistrée : ta prochaine version la prend."); }
});
function fermerDA() { $("#tiroir").hidden = true; $("#tiroir").classList.remove("iframe"); $("#btn-da").classList.remove("n"); $("#tiroir-corps").innerHTML = ""; api("/api/da").then(d => { DA = d; $("#btn-da").textContent = `Ma DA · ${d.duo}`; }); }
$("#tiroir-x").onclick = fermerDA;
addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  if (e.key === " " && vueCourante === "retours") { e.preventDefault(); vid.paused ? vid.play() : vid.pause(); }
  if (e.key === "ArrowLeft" && vueCourante === "retours") $("#img-moins").click();
  if (e.key === "ArrowRight" && vueCourante === "retours") $("#img-plus").click();
  if (e.key === "Escape") fermerDA();
});

charger();
