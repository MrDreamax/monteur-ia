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
  Inspiration: {l: "Copie le montage d'un reel que tu aimes", html: `<div class="sty aut"><div class="m">Le reel<br>que tu aimes</div><div class="fl">↓</div><div class="m on">Ton reel</div></div>`},
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
  for (const id of ["accueil", "style", "images", "derush", "retours", "publier"]) $(`#v-${id}`).hidden = id !== v;
  if (v !== "images") $("#im-ref")?.pause();
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
  if (R.statut === "images" && R.images) return ecranImages();
  if (R.statut === "derush" && !R.derush_ok) return ecranDerush();
  if (R.statut === "valide") return ecranPublier();
  return ecranRetours();
}

// ------------------------------------------- écran « Tes images pour ce reel » (29/10, reprise fidèle : reprise-r1 A + r2 B)
// Un plan de la référence = une ligne : sa vignette, puis 3 de ses b-rolls à égalité + « ta vidéo » ; 1 clic = choisi.
// Plan qu'il n'a pas : le plus proche est mis + « Pour coller pile : filme-toi… ». À droite, le brouillon qui se joue.
let IM = {rid: null, pris: {}, cle: ""};
const md = f => `/media/${rid}/${f}`;
function ecranImages() {
  montrer("images");
  const I = R.images;
  if (IM.rid !== rid) IM = {rid, pris: {}, cle: ""};
  for (const p of I.plans) if (!(IM.pris[p.n] >= 0 && IM.pris[p.n] < p.choix.length)) IM.pris[p.n] = p.pris;
  const aIll = I.plans.filter(p => p.type === "image" && p.choix.length), manque = aIll.filter(p => !p.exact).length;
  $("#im-sous").textContent = `J'ai copié le montage de la référence : ${I.plans.length} plan${I.plans.length > 1 ? "s" : ""}. ` +
    `Pour chaque plan à illustrer, 3 de tes b-rolls : un clic et c'est choisi.`;
  $("#im-liste").innerHTML = I.plans.map(p => {
    const tete = `<div class="im-h"><span class="im-n">${p.n}</span><div><b>${tc(p.de)} → ${tc(p.a)}</b><span>Réf. : ${esc(p.desc || "un plan")}</span></div></div>`;
    const ref = `<div class="im-th im-refimg" style="background-image:url(${md(p.ref_img)})"></div>`;
    if (p.type !== "image" || !p.choix.length)
      return `<div class="im-plan im-fixe">${tete}<div class="im-r">${ref}<span class="gris">${p.type === "cam" ? "Toi face caméra : ton rush, rien à choisir"
        : "Carton de la référence : je le refais à l'identique avec ta police"}</span></div></div>`;
    const ch = p.choix.map((c, k) => {
      const tag = c.perso ? `<span class="im-tag">Ta vidéo</span>` : k ? "" : p.exact ? `<span class="im-tag">Conseillé</span>` : `<span class="im-tag or">Le plus proche</span>`;
      return `<button class="im-th im-c${IM.pris[p.n] === k ? " sel" : ""}" data-n="${p.n}" data-k="${k}" title="${esc(c.nom)}" style="background-image:url(${md(c.img)})">${tag}</button>`;
    }).join("");
    const plus = `<label class="im-th im-plus" title="Glisse ou choisis ta vidéo">+<br>ta vidéo<input type="file" accept="video/*" hidden data-n="${p.n}"></label>`;
    const cons = !p.exact && p.consigne ? `<div class="im-cons"><b>Pour coller pile :</b> ${esc(p.consigne)}<label class="im-film">Je le filme<input type="file" accept="video/*" hidden data-n="${p.n}"></label></div>` : "";
    return `<div class="im-plan" data-n="${p.n}">${tete}<div class="im-r">${ref}<i class="im-sep"></i>${ch}${plus}</div><div class="im-nom">${esc(p.choix[IM.pris[p.n]]?.nom || "")}</div>${cons}</div>`;
  }).join("");
  document.querySelectorAll(".im-c").forEach(b => b.onclick = () => { IM.pris[+b.dataset.n] = +b.dataset.k; ecranImages(); });
  document.querySelectorAll("#im-liste input[type=file]").forEach(i => i.onchange = () => i.files[0] && imageFichier(+i.dataset.n, i.files[0]));
  document.querySelectorAll(".im-plan[data-n]").forEach(z => {
    z.ondragover = ev => { ev.preventDefault(); z.style.borderColor = "var(--bleu)"; };
    z.ondragleave = () => z.style.borderColor = "";
    z.ondrop = ev => { ev.preventDefault(); z.style.borderColor = ""; const f = ev.dataTransfer.files[0]; if (f) imageFichier(+z.dataset.n, f); };
  });
  $("#im-compte").textContent = `${aIll.length} plan${aIll.length > 1 ? "s" : ""} à illustrer` + (manque ? ` · ${manque} sans plan exact (j'ai mis le plus proche)` : "");
  $("#im-monter").disabled = false;
  $("#im-monter").onclick = async () => {
    $("#im-monter").disabled = true;
    try { R = await api(`/api/images/${rid}`, {pris: IM.pris}); IM.rid = null; rendre(); }
    catch (x) { toast(`Pas envoyé : ${x.message}`); $("#im-monter").disabled = false; }
  };
  brouillon();
}
async function imageFichier(n, f) {
  toast(`J'importe ta vidéo pour le plan ${n}…`, 60000);
  try {
    const r = await fetch(`/api/image-fichier/${rid}/${n}`, {method: "POST", headers: {"X-Nom": encodeURIComponent(f.name)}, body: f});
    const j = await r.json(); if (!r.ok) throw new Error(j.erreur || r.status);
    const p = j.images?.plans.find(x => x.n === n); if (p) IM.pris[n] = p.pris;
    R = j; toast("Ta vidéo est choisie pour ce plan ✓"); ecranImages();
  } catch (x) { toast(`Import raté : ${x.message}`); }
}
function brouillon() {
  // les couches (une par plan) ne sont refaites que si un choix change : le brouillon ne se coupe pas à chaque rafraîchissement
  const I = R.images, cle = rid + JSON.stringify(IM.pris) + I.plans.map(p => p.choix.length).join();
  const rv = $("#im-ref");
  if (IM.cle === cle) return;
  IM.cle = cle;
  if (!rv.src.endsWith(md(I.ref))) rv.src = md(I.ref);
  $("#im-ov").hidden = !I.titre; $("#im-ov").textContent = I.titre || "";
  $("#im-vids").innerHTML = I.plans.map(p => {
    const c = p.type === "image" ? p.choix[IM.pris[p.n]] : null;
    if (c) return `<video class="im-lay" data-n="${p.n}" data-from="0" src="${md(c.clip)}" muted loop playsinline preload="auto"></video>`;
    if (p.type === "cam") return `<video class="im-lay" data-n="${p.n}" data-from="${p.de}" src="${md("clip.mp4")}" muted playsinline preload="auto"></video>`;
    return `<div class="im-lay im-img" data-n="${p.n}" style="background-image:url(${md(p.ref_img)})"></div>`;
  }).join("");
  let cour = 0;
  const caler = () => {
    const t = rv.currentTime, p = I.plans.find(x => t >= x.de && t < x.a) || I.plans[I.plans.length - 1];
    $("#im-bar-p").style.width = `${Math.min(100, t / (rv.duration || 1) * 100)}%`;
    $("#im-tc").textContent = tc(t);
    if (p.n === cour) return;
    cour = p.n;
    document.querySelectorAll(".im-lay").forEach(l => {
      const on = +l.dataset.n === p.n;
      l.classList.toggle("on", on);
      if (l.tagName !== "VIDEO") return;
      if (on) { l.currentTime = +l.dataset.from; if (!rv.paused) l.play().catch(() => {}); } else l.pause();
    });
  };
  rv.ontimeupdate = caler;
  rv.onplay = () => { $("#im-play").textContent = "❚❚"; document.querySelector("video.im-lay.on")?.play().catch(() => {}); };
  rv.onpause = () => { $("#im-play").textContent = "▶"; document.querySelectorAll("video.im-lay").forEach(v => v.pause()); };
  rv.onended = () => { rv.currentTime = 0; cour = 0; caler(); };
  $("#im-play").onclick = () => rv.paused ? rv.play() : rv.pause();
  caler();
}

// ------------------------------------------- écran « Vérifie ton dérush » (29/10) : le Derush Lab du skill, dans un cadre
// Le 1er dérush de Claude est déjà posé. l’utilisateur retouche, « ✓ Valider le dérush » (dans le Lab), puis « Monter le reel ».
function ecranDerush() {
  montrer("derush");
  const L = R.lab || {}, f = $("#dr-lab");
  if (L.erreur) { $("#dr-txt").textContent = `Le Derush Lab ne s'ouvre pas : ${L.erreur}`; return; }
  const src = `http://${location.hostname}:${L.port}/`;   // même nom que la page (localhost) : le navigateur de Claude bloque 127.0.0.1
  if (L.port && f.dataset.src !== src) { f.dataset.src = src; f.src = src; }   // jamais rechargé à chaque rafraîchissement
  const B = $("#dr-monter"), rouge = L.valide === "rouge";
  if (!B.dataset.arme) B.textContent = rouge ? "Monter quand même ›" : "Monter le reel ›";
  B.disabled = !L.valide;
  B.classList.toggle("rouge", rouge);
  $("#dr-txt").className = L.valide === "ok" ? "ok" : rouge ? "ko" : "";
  $("#dr-txt").textContent = L.valide === "ok" ? "✅ Dérush validé par le Gardien. Tu peux monter."
    : rouge ? `Le Gardien voit 1 point : ${L.rouge}. Écoute-le dans le Lab, retouche, ou monte quand même.`
    : "Retouche les coupes si besoin, clique « ✓ Valider le dérush » en bas, puis monte.";
}
$("#dr-monter").onclick = async () => {
  const B = $("#dr-monter"), rouge = R.lab?.valide === "rouge";
  if (rouge && !B.dataset.arme) {   // Gardien rouge : 1er clic arme, 2e clic dans les 4 s = monter quand même
    B.dataset.arme = "1"; B.textContent = "Sûr ? Clique encore";
    clearTimeout(B.k); B.k = setTimeout(() => { delete B.dataset.arme; ecranDerush(); }, 4000);
    return;
  }
  delete B.dataset.arme; B.disabled = true;
  try { R = await api(`/api/derush_ok/${rid}`, {forcer: rouge}); $("#dr-lab").dataset.src = ""; $("#dr-lab").src = "about:blank"; rendre(); }
  catch (x) { toast(x.message); B.disabled = false; }
};

// ------------------------------------------------------------------------------------------------------ accueil
// 29/10 : ElevenLabs refuse (crédit vide, clé) = bandeau rouge sur tous les écrans, vérifié à chaque page et chaque minute
async function alerte() {
  const a = await api("/api/alerte").catch(() => ({}));
  const el = $("#alerte");
  el.hidden = !a.raison;
  if (a.raison) el.innerHTML = `ElevenLabs : ${esc(a.raison)} depuis le ${esc(a.depuis)}. Tes montages passent sur le Mac (plus lent, plus de fautes). <a href="https://elevenlabs.io/app/subscription" target="_blank">Recharger</a>`;
}
alerte(); setInterval(alerte, 60000);

async function accueil() {
  montrer("accueil");
  $("#fichier").textContent = ""; $("#pill-style").hidden = true;
  const L = await api("/api/reels").catch(() => []);
  const lib = {regarde: "je regarde", choix: "style à choisir", derush: "dérush à vérifier", montage: "en montage", retours: "retours", correction: "Claude corrige", images: "images à choisir", valide: "validé ✓", erreur: "bloqué"};
  $("#liste-reels").innerHTML = L.length ? `<p class="lbl" style="font-size:12px;color:#86868B;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Tes reels</p>` +
    `<div class="grille">` + L.map(r => {
      const jour = (r.cree || r.id).slice(0, 10).split("-").reverse().slice(0, 2).join("/");  // 2026-10-28 -> 28/10
      return `<div class="rc"><a href="/?reel=${r.id}">${r.vignette ? `<img src="${r.vignette}" alt="" loading="lazy">` : `<i class="vide"></i>`}
        <b>${esc(r.titre || r.nom)}</b><span>${esc(r.nom)} · ${jour}</span><span>${r.version ? "Version " + r.version + " · " : ""}${lib[r.statut] || r.statut}</span></a>
        <button class="suppr" data-id="${r.id}" title="Supprimer ce projet" aria-label="Supprimer ce projet">×</button></div>`;
    }).join("") + `</div>` : "";
  // 29/10 : 1er clic sur × = « Supprimer ? » en rouge, 2e clic dans les 4 s = le projet est caché (fichiers et rush gardés)
  $("#liste-reels").querySelectorAll(".suppr").forEach(b => b.onclick = async () => {
    if (!b.classList.contains("arme")) {
      b.classList.add("arme"); b.textContent = "Supprimer ?";
      clearTimeout(b.k); b.k = setTimeout(() => { b.classList.remove("arme"); b.textContent = "×"; }, 4000);
      return;
    }
    clearTimeout(b.k); b.disabled = true;
    try { await api(`/api/cacher/${b.dataset.id}`, {}); b.closest(".rc").remove(); toast("Projet supprimé de la liste. Ta vidéo d'origine n'est pas touchée."); }
    catch (x) { b.disabled = false; toast(`Pas supprimé : ${x.message}`); }
  });
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
  const insp = choix.style === "Inspiration";
  $("#ref").hidden = !insp;
  $("#cases").innerHTML = (insp ? `<span class="rien">Colle le lien ou glisse la vidéo juste au-dessus : je monte ton reel comme elle, avec ta police.</span>`
    : `<span class="l">Dans ce style :</span>` + (C.length ? C.map(([k, l]) => `<button class="ck${choix.cases[k] ? "" : " off"}" data-k="${k}"><i>✓</i>${l}</button>`).join("")
      : `<span class="rien">choisis un style</span>`)) +
    `<button class="go" id="monter">${R.statut === "regarde" ? "Je regarde ta vidéo…" : "Monter le reel"}</button>`;
  majMonter();
  document.querySelectorAll(".ck").forEach(b => b.onclick = () => { choix.cases[b.dataset.k] = !choix.cases[b.dataset.k]; ecranStyle(); });
  $("#monter").onclick = async () => {
    $("#monter").disabled = true;
    const ref = insp ? {lien: choix.fichier ? "" : $("#ref-lien").value.trim(), fichier: choix.fichier || ""} : {};
    try { R = await api(`/api/monter/${rid}`, {style: choix.style, cases: choix.cases, ...ref}); rendre(); }
    catch (e) { toast(e.message); majMonter(); }
  };
}
// « Monter le reel » : prêt quand la vidéo est regardée et un style choisi ; Inspiration attend en plus son lien ou sa vidéo
const LIEN_OK = /^https?:\/\/([\w-]+\.)?(instagram\.com|tiktok\.com|youtube\.com|youtu\.be)\/\S+$/;
function majMonter() {
  const b = $("#monter");
  if (!b) return;
  const ref = choix.style !== "Inspiration" || choix.fichier || LIEN_OK.test($("#ref-lien").value.trim());
  b.disabled = !(R.statut !== "regarde" && choix.style && ref);
}
// 29/10 : un montage à reprendre pour CE reel : lien Instagram (TikTok, YouTube) ou une vidéo glissée. Claude le reprend en v2.
function refPris(nom) {
  $("#ref-z").hidden = !!nom; $("#ref-pris").hidden = !nom; $("#ref-nom").textContent = nom || "";
  majMonter();
}
async function refFichier(f) {
  if (!f || !rid) return;
  toast(`J'importe ${f.name}…`, 60000);
  try {
    const r = await fetch(`/api/ref-fichier/${rid}`, {method: "POST", headers: {"X-Nom": encodeURIComponent(f.name)}, body: f}).then(r => r.json());
    if (!r.fichier) throw new Error(r.erreur || "import raté");
    choix.fichier = r.fichier; $("#ref-lien").value = ""; refPris(`Vidéo à reprendre : ${f.name}`); toast("Vidéo à reprendre ajoutée ✓");
  } catch (e) { toast(e.message); }
}
const refDrop = $("#ref-drop");
$("#ref-input").onchange = e => refFichier(e.target.files[0]);
refDrop.ondragover = e => { e.preventDefault(); refDrop.classList.add("sur"); };
refDrop.ondragleave = () => refDrop.classList.remove("sur");
refDrop.ondrop = e => { e.preventDefault(); refDrop.classList.remove("sur"); refFichier(e.dataTransfer.files[0]); };
$("#ref-lien").oninput = majMonter;
$("#ref-lien").onchange = () => {
  const l = $("#ref-lien").value.trim();
  if (!l) return;
  if (!LIEN_OK.test(l)) return toast("Colle un lien Instagram, TikTok ou YouTube");
  refPris(`Reel à reprendre : ${l.replace(/^https?:\/\/(www\.)?/, "")}`);
};
$("#ref-x").onclick = () => { choix.fichier = null; $("#ref-lien").value = ""; refPris(null); };

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
      <small data-t="${n.t}">${tc(n.t)}${n.statut === "a_faire" && n.version && n.version !== R.version ? ` · version ${n.version}` : ""}</small>${n.auto === "reference"
        ? "Copier le montage de la référence avec tes images, seule ta police change" : esc(n.texte)}
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
  const RF = R.reference?.erreur;
  $("#ref-info").hidden = !RF;
  $("#ref-info").innerHTML = RF ? `<b>Montage à reprendre :</b> ${esc(RF)}` : "";
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
const PUB = {off: new Set(), quand: null};   // ses choix tiennent quand l'écran se redessine
async function ecranPublier() {
  montrer("publier");
  vid.pause();
  const der = R.versions.slice(-1)[0];
  if (vid2.dataset.f !== der.fichier) { vid2.dataset.f = der.fichier; vid2.src = `/media/${rid}/${der.fichier}`; }
  $("#pret-titre").textContent = "Ton reel est prêt ✓";
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
    <div class="nets">${R5.map(n => `<div class="net">${n}<button class="tg${PUB.off.has(n) ? " off" : ""}" data-n="${n}" aria-label="${n}"></button></div>`).join("")}</div>
    <div class="dt"><span>Programmer le</span><input type="datetime-local" id="quand" value="${PUB.quand || iso}"></div>
    <div class="end"><button class="now" id="p-now">Publier maintenant</button><button class="prog" id="p-prog"></button>
      <a class="dl" href="/api/telecharger/${rid}" download>Juste télécharger</a>
      <p class="confirme">Ça part pour de vrai : 2e clic pour confirmer.</p></div>`;
  const reseaux = () => [...S.querySelectorAll(".nets .tg:not(.off)")].map(t => t.dataset.n);
  const lib = () => { const d = new Date($("#quand").value); $("#p-now").textContent = "Publier maintenant";
    $("#p-prog").textContent = `Programmer ${d.toLocaleDateString("fr-FR", {weekday: "short", day: "2-digit", month: "2-digit"})} · ${d.toLocaleTimeString("fr-FR", {hour: "2-digit", minute: "2-digit"})}`; };
  lib(); $("#quand").onchange = () => { PUB.quand = $("#quand").value; lib(); };
  S.querySelectorAll(".nets .tg").forEach(t => t.onclick = () => { t.classList.toggle("off"); PUB.off[t.classList.contains("off") ? "add" : "delete"](t.dataset.n); lib(); });
  // 1er clic = arme le bouton (« Confirmer… »), 2e clic dans les 6 s = envoi réel. Déjà publié = 3e étape « Republier quand même ».
  const envoyer = async (bouton, quand, forcer = false) => {
    if (!reseaux().length) return toast("Choisis au moins un réseau.");
    if (!bouton.classList.contains("arme")) {
      const avant = bouton.textContent, n = reseaux().length;
      bouton.classList.add("arme");
      bouton.textContent = `Confirmer : ça part sur ${n} réseau${n > 1 ? "x" : ""}`;
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
