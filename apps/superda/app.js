/* SuperDA : la DA de tout (Montage + Carrousels). Lit / écrit da.json via server.py. */
(function () {
  "use strict";

  const Q = new URLSearchParams(location.search);
  const TIROIR = Q.get("tiroir"); // "montage" | "carrousels" | null
  const PHOTO = "img/frame.jpg";
  const SUB = "tout le monde la fait";

  let C = null;          // catalogue
  let da = null;         // DA en cours (peut être pas encore enregistrée)
  let daSauvee = "";     // JSON de la dernière version enregistrée
  let onglet = TIROIR || (Q.get("onglet") === "carrousels" ? "carrousels" : "montage");
  let section = Q.get("section") || (TIROIR ? null : "duo");
  let slideVue = null;   // slide affichée en grand (carrousels), null = celle de la section
  let reponse = { texte: "", err: false };
  try { const t = sessionStorage.getItem("superda-reponse"); if (t) { reponse = { texte: t, err: false }; sessionStorage.removeItem("superda-reponse"); } } catch (e) {}
  let attente = false;
  let flash = false; // « Enregistré ✓ » pendant 1,6 s
  const DEPUIS = { supermonteur: "SuperMonteur", supercarrousel: "SuperCarrousel" }[Q.get("depuis")];
  const bloque = { titre: false, sous: false }; // texte poussé contre la zone Insta

  const SECTIONS = {
    montage: [
      { id: "duo", nom: "Duo de polices", partage: true },
      { id: "tailles", nom: "Tailles et position" },
      { id: "mots", nom: "Mots par ligne" },
      { id: "couleurs", nom: "Couleur de marque", partage: true },
      { id: "texte", nom: "Couleurs du texte" },
      { id: "cartons", nom: "Cartons" },
      { id: "univers", nom: "Univers du motion" },
      { id: "motion", nom: "Réglages du motion" },
      { id: "inspiration", nom: "Inspiration" },
    ],
    carrousels: [
      { id: "duo", nom: "Duo de polices", partage: true },
      { id: "couleurs", nom: "Couleur de marque", partage: true },
      { id: "texte", nom: "Couleur du texte" },
      { id: "modele", nom: "Modèle" },
      { id: "couverture", nom: "Couverture" },
      { id: "photos", nom: "Slides photo" },
      { id: "dessins", nom: "Dessins" },
      { id: "derniere", nom: "Dernière slide" },
      { id: "inspiration", nom: "Inspiration" },
    ],
  };

  /* ---------- outils ---------- */
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const par = (l, id) => l.find((x) => x.id === id);
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const propre = (d) => { const x = clone(d); delete x._resume; delete x.maj; return JSON.stringify(x); };
  const sale = () => propre(da) !== daSauvee;

  function lum(hex) {
    if (!hex) return 1;
    const n = parseInt(hex.slice(1), 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  }
  function nomCouleur(hex) {
    if (hex == null) return "aucune";
    const H = hex.toUpperCase();
    for (const g of Object.values(C.couleurs)) for (const x of g) if (x.hex.toUpperCase() === H) return x.nom;
    for (const g of Object.values(C.cartons)) for (const x of g) if (x.hex.toUpperCase() === H) return x.nom;
    return "perso";
  }
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  async function api(chemin, corps) {
    const r = await fetch(chemin, corps ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) } : {});
    const j = await r.json();
    if (!r.ok) throw new Error(j.erreur || "Erreur");
    return j;
  }
  function parent(type, extra) {
    if (window.parent !== window) window.parent.postMessage(Object.assign({ type: "superda:" + type }, extra || {}), "*");
  }

  /* ---------- calculs (mêmes règles que server.py) ---------- */
  function calcule() {
    const zi = C.zone_interdite, m = da.montage;
    const t = m.titre, s = m.sous_titres;
    const ht = Math.round(t.taille * 0.5 * 1.05 + t.taille * 1.1);
    const yt = C.positions.titre[t.position] + t.decalage;
    t._y = Math.max(zi.haut, Math.min(zi.bas - ht, yt));
    bloque.titre = t._y !== yt;
    const demi = Math.round(s.taille * 0.7);
    const ys = C.positions.sous_titres[s.position] + s.decalage;
    s._y = Math.max(zi.haut + demi, Math.min(zi.bas - demi, ys));
    bloque.sous = s._y !== ys;
    const mo = m.motion;
    if (mo.palette !== "perso") mo.couleurs = clone(par(C.palettes, mo.palette)[mo.mode]);
    const de = da.carrousels.dessins;
    if (de.style === "comme_motion") de.univers = m.univers;
  }

  function resume() {
    const co = da.commun, m = da.montage, k = da.carrousels, cl = co.couleurs;
    const duo = co.duo.id === "perso" ? "Perso" : co.duo.nom;
    const acc = nomCouleur(cl.accent);
    const marque = acc === "aucune" ? "Aucune" : cap(acc.toLowerCase());
    const pal = m.motion.palette === "perso" ? "Perso" : par(C.palettes, m.motion.palette).nom;
    const ds = k.derniere_slide;
    return {
      montage: {
        duo, tailles: m.titre.taille + " · " + m.sous_titres.taille, mots: String(m.mots_par_ligne),
        couleurs: marque, texte: cap(nomCouleur(cl.titre)),
        cartons: nomCouleur(m.cartons.depart) + " → " + nomCouleur(m.cartons.arrivee),
        univers: par(C.univers, m.univers).nom, motion: pal, inspiration: "",
      },
      carrousels: {
        duo, couleurs: marque, texte: cap(nomCouleur(cl.texte)),
        modele: par(C.modeles, k.modele).nom,
        couverture: { haut: "Titre en haut", bas: "Titre en bas", derriere_tete: "Derrière la tête" }[k.couverture.place_titre],
        photos: { sombres: "Sombres", naturelles: "Naturelles", noir_blanc: "Noir et blanc" }[k.slides_photo.photos],
        dessins: cap(k.dessins.fond),
        derniere: ds.active ? { bulles: "3 bulles", mot_geant: "Mot en géant", bouton: "Bouton" }[ds.forme] : "Aucune",
        inspiration: "",
      },
    };
  }

  /* ---------- polices ---------- */
  function f1() { const p = da.commun.duo.principale; return `font-family:'${p.famille}';font-weight:${p.graisse || 700};${p.famille === "Archivo" ? "font-stretch:125%;" : ""}`; }
  function f2() { const s = da.commun.duo.secondaire; return `font-family:'${s.famille}';font-weight:${s.graisse || 400};font-style:${s.italique ? "italic" : "normal"};`; }
  const maj1 = () => !!da.commun.duo.principale.majuscules;
  const maj2 = () => !!da.commun.duo.secondaire.majuscules;

  /* ---------- scène de motion design (Hook → Preuve → Vente) ---------- */
  function scene(univId, reg, W, H, uid) {
    const U = par(C.univers, univId);
    const c = reg.couleurs || par(C.palettes, reg.palette)[reg.mode];
    const k = W / 1080;
    const tw = ({ fin: 2.2, moyen: 4.5, epais: 8 }[reg.trait] || 2.2) * k * (W < 400 ? 2.2 : 1);
    const r = reg.formes === "arrondies" ? 34 * k * (W < 400 ? 1.6 : 1) : (univId === "elegant" ? 6 * k : 0);
    const gid = "g" + uid, sid = "s" + uid;
    let g = `<defs><linearGradient id="${gid}" x1="0" y1="0" x2=".6" y2="1"><stop offset="0" stop-color="${c.fond}"/><stop offset="1" stop-color="${c.fond2}"/></linearGradient><filter id="${sid}" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="${10 * k}" stdDeviation="${14 * k}" flood-opacity=".14"/></filter></defs><rect width="${W}" height="${H}" fill="url(#${gid})"/>`;
    if (U.deco === "grille") {
      const pas = 68 * k * (W < 400 ? 2 : 1);
      for (let x = 0; x < W; x += pas) g += `<path d="M${x} 0V${H}" stroke="${c.trait}" stroke-opacity=".16" stroke-width="${Math.max(0.6, 2 * k)}"/>`;
      for (let y = 0; y < H; y += pas) g += `<path d="M0 ${y}H${W}" stroke="${c.trait}" stroke-opacity=".16" stroke-width="${Math.max(0.6, 2 * k)}"/>`;
    }
    const bw = W * 0.22, bh = H * 0.3, y = H * 0.34, xs = [W * 0.06, W * 0.39, W * 0.72];
    const lab = ["Hook", "Preuve", "Vente"];
    const fs = Math.max(W * 0.045, 7);
    const p = da.commun.duo.principale;
    const fstyle = `font-family:'${p.famille}';font-weight:${p.graisse || 700};font-size:${fs}px`;
    xs.forEach((x, i) => {
      const last = i === 2;
      let fill, stroke = "none", sw = 0, tc, filt = "";
      if (U.plein) {
        if (U.ombre) { fill = last ? c.touche : c.fond2 === c.fond ? "#FFFFFF" : c.fond2; tc = last ? "#FFFFFF" : c.texte; filt = ` filter="url(#${sid})"`; if (!last) { stroke = c.trait; sw = Math.max(0.5, tw * 0.25); } }
        else { fill = last ? c.touche2 : c.texte; tc = lum(fill) > 0.6 ? "#111111" : "#FFFFFF"; }
      } else {
        fill = last ? c.touche : "none"; stroke = c.trait; sw = tw;
        tc = last ? (lum(c.touche) > 0.6 ? "#111111" : "#FFFFFF") : c.trait;
      }
      g += `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${filt}/>`;
      g += `<text x="${x + bw / 2}" y="${y + bh / 2 + fs * 0.35}" text-anchor="middle" fill="${tc}" style="${fstyle}">${lab[i]}</text>`;
      if (i < 2) {
        const x1 = x + bw + W * 0.015, x2 = xs[i + 1] - W * 0.015, yy = y + bh / 2;
        if (U.deco === "papier") g += `<path d="M${x1} ${yy} Q${(x1 + x2) / 2} ${yy - H * 0.08} ${x2} ${yy}" stroke="${c.trait}" stroke-width="${Math.max(1.4, tw)}" fill="none" stroke-linecap="round"/>`;
        else g += `<path d="M${x1} ${yy}H${x2}" stroke="${U.plein && !U.ombre ? c.texte : c.touche}" stroke-width="${Math.max(1.5, tw)}"${U.plein ? "" : ` stroke-dasharray="${W * 0.016} ${W * 0.012}"`}/>`;
      }
    });
    const pfs = Math.max(W * 0.04, 6);
    if (U.deco === "papier") {
      g += `<rect x="${xs[2] - W * 0.01}" y="${y + bh + H * 0.06}" width="${bw + W * 0.02}" height="${H * 0.1}" fill="${c.touche2}" opacity=".8"/>`;
      g += `<text x="${xs[2] + bw / 2}" y="${y + bh + H * 0.06 + H * 0.075}" text-anchor="middle" fill="${c.texte}" style="${f2()}font-size:${pfs * 1.3}px">le cash est ici</text>`;
    } else if (U.deco === "magazine") {
      g += `<path d="M${W * 0.06} ${H * 0.22}H${W * 0.94}" stroke="${c.texte}" stroke-width="${Math.max(2, 7 * k)}"/>`;
      g += `<text x="${W * 0.06}" y="${H * 0.17}" fill="${c.texte}" style="${f1()}font-size:${pfs * 1.2}px">N°3</text>`;
    } else if (U.deco === "grille") {
      g += `<text x="${W * 0.06}" y="${H * 0.2}" fill="${c.touche}" style="${f1()}font-size:${pfs}px">SYS://FUNNEL 03</text>`;
    } else if (univId === "elegant") {
      g += `<path d="M${W * 0.06} ${H * 0.2}H${W * 0.2}" stroke="${c.touche}" stroke-width="${Math.max(1, 2 * k)}"/>`;
    }
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${g}</svg>`;
  }
  const regDefaut = (u) => { const d = par(C.univers, u).defaut; return { mode: d.mode, palette: d.palette, trait: d.trait, formes: d.formes, couleurs: par(C.palettes, d.palette)[d.mode] }; };

  /* ---------- aperçu reel (scène 1080 x 1920, réduite) ---------- */
  function zoneInterdite() {
    const z = C.zone_interdite;
    return `<div class="zone" style="left:0;top:0;width:1080px;height:${z.haut}px"></div>
      <div class="zone" style="left:0;top:${z.bas}px;width:1080px;height:${1920 - z.bas}px"></div>
      <div class="zone" style="left:0;top:${z.haut}px;width:${z.cotes}px;height:${z.bas - z.haut}px"></div>
      <div class="zone" style="left:${1080 - z.cotes}px;top:${z.haut}px;width:${z.cotes}px;height:${z.droite_bas.sous_y - z.haut}px"></div>
      <div class="zone" style="left:${1080 - z.droite_bas.marge}px;top:${z.droite_bas.sous_y}px;width:${z.droite_bas.marge}px;height:${z.bas - z.droite_bas.sous_y}px"></div>
      <div class="zone-lab" style="top:${z.haut / 2 - 18}px">Caché par Insta</div>
      <div class="zone-lab" style="top:${z.bas + 160}px">Caché par Insta</div>`;
  }
  function titreReel() {
    const t = da.montage.titre, cl = da.commun.couleurs, p = da.commun.duo.principale;
    const l1 = "L'erreur qui ruine", l2 = "ton image";
    const ombre = "text-shadow:0 4px 30px rgba(0,0,0,.35)";
    return `<div style="position:absolute;left:65px;right:65px;top:${t._y}px;text-align:center;${ombre}">
      <div style="${f1()}font-size:${t.taille * 0.5}px;line-height:1.05;letter-spacing:${(p.interlettrage || 0) * 2}px;color:${cl.titre};${maj1() ? "text-transform:uppercase;" : ""}">${l1}</div>
      <div style="${f2()}font-size:${t.taille}px;line-height:1.1;color:${cl.ligne2};${maj2() ? "text-transform:uppercase;" : ""}">${l2}</div></div>`;
  }
  function sousTitre(ecranCoupe, fort) {
    const s = da.montage.sous_titres, cl = da.commun.couleurs;
    const y = ecranCoupe ? Math.max(s._y, 1430) : s._y; // écran coupé : sous le visage, jamais dessus
    const l = SUB.split(" ").slice(0, da.montage.mots_par_ligne);
    if (fort && cl.accent) l[l.length - 1] = `<span style="color:${cl.accent}">${l[l.length - 1]}</span>`; // mot fort = couleur de marque
    const mots = l.join(" ");
    return `<div style="position:absolute;left:65px;right:65px;top:${y}px;transform:translateY(-50%);text-align:center;${f1()}font-size:${s.taille}px;line-height:1.15;color:${cl.sous_titres};${s.majuscules !== false ? "text-transform:uppercase;" : ""}text-shadow:0 3px 18px rgba(0,0,0,.45)">${mots}</div>`;
  }
  function reel(sec) {
    const m = da.montage;
    let inner;
    if (sec === "cartons") {
      const cl = da.commun.couleurs;
      inner = `<div style="position:absolute;inset:0;background:linear-gradient(180deg,${m.cartons.depart},${m.cartons.arrivee})"></div>
        <div style="position:absolute;left:65px;right:65px;top:760px;text-align:center">
          <div style="${f1()}font-size:60px;letter-spacing:6px;color:${cl.titre};opacity:.82;${maj1() ? "text-transform:uppercase;" : ""}">La vérité</div>
          <div style="${f2()}font-size:170px;line-height:1.05;color:${cl.ligne2};margin-top:10px">personne<br>ne regarde</div></div>`;
    } else if (sec === "univers" || sec === "motion") {
      inner = `<div style="position:absolute;left:0;top:0;width:1080px;height:960px">${scene(m.univers, m.motion, 1080, 960, "big")}</div>
        <div style="position:absolute;left:0;top:960px;width:1080px;height:960px;background:url(${PHOTO}) center 50%/cover"></div>` + sousTitre(true);
    } else {
      inner = `<div style="position:absolute;inset:0;background:url(${PHOTO}) center/cover"></div>` + titreReel() + sousTitre(false, sec === "couleurs") + (sec === "tailles" ? zoneInterdite() : "");
    }
    return `<div class="tel"><div class="scene" style="width:1080px;height:1920px;transform:scale(${320 / 1080})">${inner}</div></div>`;
  }
  function legendeReel(sec) {
    const m = da.montage;
    return {
      duo: "Aperçu en direct sur ton dernier reel", tailles: "Zones rayées = cachées par Insta, ton texte n'y va jamais",
      mots: m.mots_par_ligne + (m.mots_par_ligne > 1 ? " mots à la fois" : " mot à la fois"), couleurs: "Le mot fort prend ta couleur de marque", texte: "Aperçu en direct sur ton dernier reel",
      cartons: "Aperçu d'un carton avec ta DA", univers: "Univers « " + par(C.univers, m.univers).nom + " » en écran coupé",
      motion: "Tes réglages en direct", inspiration: "Ta DA actuelle",
    }[sec] || "";
  }

  /* ---------- aperçu carrousel (scène 1080 x 1440) ---------- */
  function filtrePhoto() {
    return { sombres: "brightness(.72) contrast(1.06)", naturelles: "none", noir_blanc: "grayscale(1) contrast(1.12) brightness(.9)" }[da.carrousels.slides_photo.photos];
  }
  function photo(extra, pos) {
    return `<div style="position:absolute;${extra};background:url(${PHOTO}) ${pos || "center 30%"}/cover;filter:${filtrePhoto()}"></div>`;
  }
  function couleursSlide(fondClair) {
    const cl = da.commun.couleurs;
    let txt = cl.texte;
    if (fondClair && lum(txt) > 0.6) txt = "#111111";
    if (!fondClair && lum(txt) < 0.35) txt = "#FFFFFF";
    const acc = cl.accent || txt;
    return { txt, acc, tou: null }; // petites touches supprimées le 28/10
  }
  function touches(tou, clair) {
    if (!tou) return "";
    return `<div style="position:absolute;left:770px;top:160px;width:44px;height:44px;border-radius:50%;background:${tou}"></div>
      <div style="position:absolute;left:100px;top:300px;width:24px;height:24px;border-radius:50%;background:${tou}"></div>
      <div style="position:absolute;left:770px;top:420px;width:96px;height:16px;border-radius:8px;background:${tou};opacity:${clair ? 1 : 0.95}"></div>`;
  }
  function titreCouv(col, acc, align, taille) {
    const cv = da.carrousels.couverture;
    const t = taille || cv.taille_titre;
    const petite = cv.petite_ligne ? `<div style="${f1()}font-size:34px;letter-spacing:7px;color:${col};opacity:.9;margin-bottom:14px;text-transform:uppercase">5 erreurs qui</div>` : "";
    const fleche = cv.fleche_glisse ? `<div style="display:inline-block;margin-top:34px;background:${acc};color:${lum(acc) > 0.6 ? "#111" : "#fff"};${f1()}font-size:36px;padding:18px 34px;border-radius:999px;text-transform:none;letter-spacing:0">Glisse pour voir</div>` : "";
    return `<div style="text-align:${align || "left"}">${petite}<div style="${f2()}font-size:${t}px;line-height:1.02;color:${col};${maj2() ? "text-transform:uppercase;" : ""}"><span style="color:${acc}">ruinent</span> ton image</div>${fleche}</div>`;
  }
  function slideCouverture(modele) {
    const cv = da.carrousels.couverture;
    const place = cv.place_titre;
    const pos = place === "haut" ? "top:110px" : place === "derriere_tete" ? "top:70px" : "bottom:120px";
    let h = "";
    if (modele === "epure") {
      const c = couleursSlide(true);
      h = `<div style="position:absolute;inset:0;background:#FFFFFF"></div>` + photo("left:0;right:0;bottom:0;height:56%", "center 28%") +
        `<div style="position:absolute;left:90px;right:90px;${place === "bas" ? "top:120px" : pos}">${titreCouv(c.txt, c.acc)}</div>` + touches(c.tou, true);
    } else if (modele === "collage") {
      const c = couleursSlide(true);
      h = `<div style="position:absolute;inset:0;background:#F4F1EA"></div>
        <div style="position:absolute;left:600px;top:150px;width:330px;height:330px;border-radius:50%;background:${c.acc};opacity:.9"></div>
        <div style="position:absolute;left:150px;top:${place === "haut" ? 560 : 170}px;width:620px;height:760px;background:#fff;padding:22px;transform:rotate(-3deg);box-shadow:0 18px 40px rgba(0,0,0,.18)"><div style="position:relative;width:100%;height:100%;overflow:hidden">${photo("inset:0", "center 25%")}</div></div>
        <div style="position:absolute;left:330px;top:${place === "haut" ? 535 : 145}px;width:200px;height:56px;background:rgba(255,238,170,.85);transform:rotate(4deg)"></div>
        <div style="position:absolute;left:90px;right:90px;${place === "haut" ? "top:110px" : "bottom:90px"}">${titreCouv(c.txt, c.acc, "left", cv.taille_titre * 0.85)}</div>` + touches(c.tou, true);
    } else if (modele === "carnet") {
      const c = couleursSlide(true);
      h = `<div style="position:absolute;inset:0;background:#F3EFE8;background-image:repeating-linear-gradient(180deg,transparent 0 78px,rgba(29,95,191,.12) 78px 80px)"></div>
        <div style="position:absolute;left:90px;right:90px;${place === "bas" ? "bottom:110px" : "top:120px"}"><div style="position:relative;display:inline">${titreCouv(c.txt, c.acc)}</div></div>
        <div style="position:absolute;left:90px;${place === "bas" ? "top:150px" : "bottom:120px"};width:430px;height:520px;border-radius:16px;overflow:hidden;transform:rotate(2deg);box-shadow:0 10px 24px rgba(0,0,0,.15)">${photo("inset:0", "center 25%")}</div>
        ${c.tou ? `<div style="position:absolute;left:600px;${place === "bas" ? "top:330px" : "bottom:330px"};${f2()}font-size:54px;color:${c.txt};transform:rotate(-5deg)">← lui</div><div style="position:absolute;left:590px;${place === "bas" ? "top:400px" : "bottom:300px"};width:230px;height:22px;background:${c.tou};opacity:.7;border-radius:6px"></div>` : ""}`;
    } else if (modele === "impact") {
      const acc = da.commun.couleurs.accent || "#FFD43B";
      const txtc = lum(acc) > 0.6 ? "#111111" : "#FFFFFF";
      h = photo("left:0;right:0;bottom:0;height:54%", "center 25%") +
        `<div style="position:absolute;left:0;right:0;${place === "bas" ? "bottom:0" : "top:0"};height:46%;background:${acc};padding:90px 80px;display:flex;align-items:center">
          <div style="${f1()}font-size:${cv.taille_titre * 0.95}px;line-height:.98;color:${txtc};text-transform:uppercase;letter-spacing:-1px">5 erreurs<br>qui ruinent<br>ton image</div></div>` +
        (da.commun.couleurs.touches ? `<div style="position:absolute;right:80px;${place === "bas" ? "bottom:70px" : "top:70px"};width:70px;height:70px;background:${da.commun.couleurs.touches}"></div>` : "");
    } else if (modele === "post_texte") {
      const c = couleursSlide(true);
      h = `<div style="position:absolute;inset:0;background:#FFFFFF"></div>
        <div style="position:absolute;left:100px;right:100px;top:${place === "bas" ? 620 : 300}px">
          <div style="display:flex;align-items:center;gap:30px;margin-bottom:46px"><div style="width:140px;height:140px;border-radius:50%;background:url(${PHOTO}) center 22%/260%"></div>
          <div><div style="font:700 46px var(--ui);color:#111">Ton nom</div><div style="font:400 40px var(--ui);color:#86868B">@toncompte</div></div></div>
          <div style="${f1()}font-size:${Math.round(cv.taille_titre * 0.48)}px;line-height:1.3;color:#111;font-weight:500">5 erreurs <span style="color:${c.acc}">ruinent</span> ton image sur Insta.<br><br>La 3e, tout le monde la fait sans le savoir.</div></div>`;
    } else { // cinema
      const c = couleursSlide(false);
      const behind = place === "derriere_tete";
      h = photo("inset:0", "center 30%") + `<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,${place === "haut" || behind ? ".55" : "0"}) 0%,rgba(0,0,0,0) 40%,rgba(0,0,0,0) 55%,rgba(0,0,0,${place === "bas" ? ".7" : "0"}) 100%)"></div>` +
        `<div style="position:absolute;left:84px;right:84px;${pos};${behind ? "opacity:.95;" : ""}">${titreCouv(c.txt, c.acc, behind ? "center" : "left", behind ? cv.taille_titre * 1.5 : cv.taille_titre)}</div>` + touches(c.tou, false);
    }
    return h;
  }
  function slidePhoto(n) {
    const sp = da.carrousels.slides_photo, cl = da.commun.couleurs;
    const c = couleursSlide(false);
    const t = sp.taille_texte * 1.4;
    const contenu = sp.texte === "liste"
      ? `<div style="${f2()}font-size:${t * 1.5}px;color:${c.txt};margin-bottom:24px">Ton décor parle avant toi</div>` +
        ["Range le fond", "Une lampe chaude", "Rien derrière la tête"].map((x, i) => `<div style="display:flex;gap:22px;align-items:center;margin-top:16px"><span style="flex:none;width:${t * 1.3}px;height:${t * 1.3}px;border-radius:50%;background:${cl.accent || c.txt};color:${lum(cl.accent || c.txt) > 0.6 ? "#111" : "#fff"};${f1()}font-size:${t * 0.7}px;display:flex;align-items:center;justify-content:center">${i + 1}</span><span style="${f1()}font-weight:500;font-size:${t}px;color:${c.txt}">${x}</span></div>`).join("")
      : `<div style="${f2()}font-size:${t * 1.6}px;line-height:1.05;color:${c.txt}">Ton décor parle<br>avant toi</div><div style="${f1()}font-weight:500;font-size:${t * 0.85}px;color:${c.txt};opacity:.85;margin-top:20px">Un fond rangé dit « je suis pro » avant le premier mot</div>`;
    return photo("inset:0", n % 2 ? "center 26%" : "center 34%") +
      `<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 35%,rgba(0,0,0,.78) 100%)"></div>
      <div style="position:absolute;left:84px;right:84px;bottom:110px">${contenu}</div>`;
  }
  function slideDessin() {
    const de = da.carrousels.dessins;
    const reg = de.style === "comme_motion" ? Object.assign({}, da.montage.motion) : regDefaut(de.univers);
    reg.mode = de.fond === "nuit" ? "sombre" : "clair";
    reg.couleurs = reg.palette === "perso" && reg.mode === da.montage.motion.mode ? da.montage.motion.couleurs : par(C.palettes, reg.palette === "perso" ? "glacier" : reg.palette)[reg.mode];
    const col = reg.couleurs;
    return `<div style="position:absolute;inset:0;background:linear-gradient(170deg,${col.fond},${col.fond2})"></div><div style="position:absolute;left:0;top:330px;width:1080px;height:860px">${scene(de.univers, reg, 1080, 860, "d" + Math.random().toString(36).slice(2, 7)).replace(/<rect width="1080" height="860" fill="url\(#[^"]+\)"\/>/, "")}</div>
      <div style="position:absolute;left:84px;right:84px;top:120px;${f2()}font-size:96px;line-height:1.05;color:${col.texte}">La méthode<br>en 3 temps</div>
      <div style="position:absolute;left:84px;right:84px;bottom:120px;${f1()}font-weight:500;font-size:40px;color:${col.texte};opacity:.8">Hook, preuve, vente : dans cet ordre</div>`;
  }
  function slideFin() {
    const ds = da.carrousels.derniere_slide, cl = da.commun.couleurs;
    const acc = cl.accent || "#0A84FF";
    const c = couleursSlide(false);
    const av = ds.photo ? `<div style="width:150px;height:150px;border-radius:50%;border:${ds.contour * 0.75}px solid #fff;background:url(${PHOTO}) ${ds.cadrage.x}% ${ds.cadrage.y}%/${ds.cadrage.zoom}%;margin-bottom:40px"></div>` : "";
    let corps;
    if (ds.forme === "mot_geant") corps = `<div style="${f1()}font-size:44px;color:${c.txt};opacity:.85">Commente</div><div style="${f1()}font-size:230px;line-height:1;color:${acc};text-transform:uppercase;letter-spacing:-4px;margin:10px 0">DÉCOR</div><div style="${f1()}font-weight:500;font-size:44px;color:${c.txt}">je t'envoie la checklist en DM</div>`;
    else if (ds.forme === "bouton") corps = `<div style="${f2()}font-size:120px;line-height:1.05;color:${c.txt};margin-bottom:50px">Tu la veux ?</div><div style="display:inline-block;background:${acc};color:${lum(acc) > 0.6 ? "#111" : "#fff"};${f1()}font-size:52px;padding:34px 60px;border-radius:999px">Commente DÉCOR</div>`;
    else corps = `<div style="${f2()}font-size:120px;line-height:1.05;color:${c.txt};margin-bottom:50px">Tu la veux ?</div>
      <div style="display:flex;flex-direction:column;gap:24px;align-items:flex-start;${f1()}font-weight:500;font-size:44px">
        <div style="background:#2C2C2E;color:#fff;padding:24px 36px;border-radius:44px">Tu veux ma checklist décor ?</div>
        <div style="background:${acc};color:${lum(acc) > 0.6 ? "#111" : "#fff"};padding:24px 36px;border-radius:44px;align-self:flex-end">DÉCOR</div>
        <div style="background:#2C2C2E;color:#fff;padding:24px 36px;border-radius:44px">Je te l'envoie en DM</div></div>
      <div style="${f1()}font-weight:500;font-size:36px;color:${c.txt};opacity:.85;margin-top:48px">Écris <b style="color:${acc}">DÉCOR</b> en commentaire</div>`;  // = le vrai rendu (supercarrousel/modeles.py)
    return `<div style="position:absolute;inset:0;background:linear-gradient(180deg,#0E1220,#161D2F)"></div><div style="position:absolute;left:150px;right:150px;top:50%;transform:translateY(-50%)">${av}${corps}</div>`;
  }
  function slides() {
    const k = da.carrousels;
    const l = [() => slideCouverture(k.modele), () => slidePhoto(1), () => slideDessin(), () => slidePhoto(2), () => slideDessin(), () => slidePhoto(3), () => slideDessin()];
    if (k.derniere_slide.active) l.push(() => slideFin());
    return l;
  }
  function carte(html, w, h) {
    return `<div class="scene" style="width:1080px;height:1440px;transform:scale(${w / 1080})">${html}</div>`;
  }
  function carrousel(sec) {
    const l = slides();
    const auto = { duo: 0, couleurs: 0, texte: 0, modele: 0, couverture: 0, photos: 1, dessins: 2, derniere: l.length - 1, inspiration: 0 }[sec];
    if (slideVue == null || slideVue >= l.length) slideVue = auto;
    const html = l[slideVue]();
    const planche = l.map((f, i) => `<button aria-label="Slide ${i + 1}" data-slide="${i}" aria-current="${i === slideVue}">${carte(f(), 58)}</button>`).join("");
    return `<div class="slide">${carte(html, 300)}</div><small>${legendeCarrousel(sec)}</small><div class="planche">${planche}</div>`;
  }
  function legendeCarrousel(sec) {
    const k = da.carrousels, cl = da.commun.couleurs;
    if (sec === "couleurs") return cl.accent ? "Exemple : accent " + nomCouleur(cl.accent).toLowerCase() : "Exemple sans couleur d'accent";
    if (sec === "texte") return "Couleur du texte des slides";
    if (sec === "modele") return "Modèle « " + par(C.modeles, k.modele).nom + " »";
    if (sec === "photos") return "Slide photo";
    if (sec === "dessins") return "Slide dessin, univers « " + par(C.univers, k.dessins.univers).nom + " »";
    if (sec === "derniere") return k.derniere_slide.active ? "Dernière slide" : "Pas de dernière slide";
    if (sec === "inspiration") return "Ta DA actuelle";
    return "Ta couverture";
  }

  /* ---------- contrôles ---------- */
  const seg = (cle, opts, val) => `<div class="seg" role="group">${opts.map(([v, n]) => `<button data-set="${cle}" data-val="${esc(JSON.stringify(v))}" aria-pressed="${v === val}">${n}</button>`).join("")}</div>`;
  const pm = (cle, val, unite, pas) => `<div class="pm"><button data-pas="${cle}" data-d="${-pas}" aria-label="Moins">−</button><output>${val}${unite}</output><button data-pas="${cle}" data-d="${pas}" aria-label="Plus">+</button></div>`;
  // Cadrage de la photo ronde : les flèches bougent ton visage dans le rond
  const cadrage = (ca) => `<h3>Cadrage de ta photo</h3><div class="pas"><div><div class="lab">Zoom</div>${pm("carrousels.derniere_slide.cadrage.zoom", ca.zoom, " %", 10)}</div>
    <div><div class="lab">Monter / descendre</div><div class="pm"><button data-pas="carrousels.derniere_slide.cadrage.y" data-d="4" aria-label="Monter le visage">↑</button><output>${ca.y}</output><button data-pas="carrousels.derniere_slide.cadrage.y" data-d="-4" aria-label="Descendre le visage">↓</button></div></div>
    <div><div class="lab">Gauche / droite</div><div class="pm"><button data-pas="carrousels.derniere_slide.cadrage.x" data-d="4" aria-label="Visage à gauche">←</button><output>${ca.x}</output><button data-pas="carrousels.derniere_slide.cadrage.x" data-d="-4" aria-label="Visage à droite">→</button></div></div></div>`;
  const fleches = (cle, val) => `<div class="pm"><button data-pas="${cle}" data-d="-10" aria-label="Monter">↑</button><output>${val}</output><button data-pas="${cle}" data-d="10" aria-label="Descendre">↓</button></div>`;
  const inter = (cle, val, nom) => `<div class="ligne-inter"><span>${nom}</span><button class="inter" role="switch" aria-checked="${!!val}" data-bascule="${cle}" aria-label="${esc(nom)}"></button></div>`;
  function dots(cle, liste, val, opts) {
    opts = opts || {};
    const V = val == null ? null : String(val).toUpperCase();
    let h = liste.map((x) => `<button class="dot" style="background:${x.hex}" data-set="${cle}" data-val="${esc(JSON.stringify(x.hex))}" aria-pressed="${V === x.hex.toUpperCase()}" aria-label="${esc(x.nom)}" title="${esc(x.nom)}"></button>`).join("");
    const perso = val != null && !liste.some((x) => x.hex.toUpperCase() === V);
    if (opts.aucune) h += `<button class="dot aucune" data-set="${cle}" data-val="null" aria-pressed="${val == null}" aria-label="Aucune couleur" title="Aucune"></button>`;
    if (opts.roue !== false) h += `<label class="dot roue" title="Couleur libre" aria-pressed="${perso}" style="${perso ? `box-shadow:0 0 0 2px #fff,0 0 0 4px #1D1D1F` : ""}"><input type="color" data-couleur="${cle}" value="${val || "#ffffff"}" aria-label="Couleur libre"></label>`;
    return `<div class="dots">${h}</div>`;
  }
  function choixDuo() {
    const d = da.commun.duo;
    let h = C.duos.map((x) => `<button class="choix" data-duo="${x.id}" aria-pressed="${d.id === x.id}"><b style="font-family:'${x.principale.famille}';font-weight:${x.principale.graisse};${x.id === "affirme" ? "font-stretch:125%;" : ""}">${x.nom}</b><small>${x.desc}</small></button>`).join("");
    const pp = C.polices_perso;
    const opt1 = pp.principales.map((x) => `<option value="${esc(x.famille)}" ${d.id === "perso" && d.principale.famille === x.famille ? "selected" : ""}>${x.famille}</option>`).join("");
    const opt2 = pp.secondaires.map((x) => `<option value="${esc(x.fichier)}" ${d.id === "perso" && d.secondaire.fichier === x.fichier ? "selected" : ""}>${x.nom}</option>`).join("");
    h += `<div class="perso" aria-pressed="${d.id === "perso"}"><button data-duo="perso"><span>+ Mon combo perso</span>${d.id === "perso" ? "" : "<small>principale + secondaire</small>"}</button>
      ${d.id === "perso" || onglet === "montage" ? `<div class="duo2"><div><div class="lab">Police principale</div><select data-perso="principale" aria-label="Police principale">${opt1}</select></div><div><div class="lab">Police secondaire</div><select data-perso="secondaire" aria-label="Police secondaire">${opt2}</select></div></div>` : ""}</div>`;
    return h;
  }
  function choixUnivers(cle, val) {
    return C.univers.map((u, i) => `<button class="choix img" data-set="${cle}" data-val="${esc(JSON.stringify(u.id))}" data-univers="${cle === "montage.univers" ? 1 : 0}" aria-pressed="${val === u.id}">${scene(u.id, regDefaut(u.id), 240, 126, "u" + cle.length + i)}<span class="txt"><b>${u.nom}</b><small>${u.desc}</small></span></button>`).join("");
  }

  function panneau(sec) {
    const m = da.montage, k = da.carrousels, cl = da.commun.couleurs;
    const O = onglet;
    switch (O + ":" + sec) {
      case "montage:duo": case "carrousels:duo":
        return { t: "Duo de polices", s: O === "montage" ? "Un seul duo pour le titre et les sous-titres. Partagé avec tes carrousels." : "Le même partout : changer ici change aussi l'onglet Montage.", h: choixDuo() };
      case "montage:tailles": {
        const al = (b) => b ? `<div class="alerte">Bloqué ici : plus loin, Insta cache le texte.</div>` : "";
        return { t: "Tailles et position", s: "Toujours centré. Les zones cachées par Insta sont bloquées.", h:
          `<h4>Titre</h4><div class="pas"><div><div class="lab">Taille</div>${pm("montage.titre.taille", m.titre.taille, " px", 2)}</div><div><div class="lab">Ajuster haut / bas</div>${fleches("montage.titre.decalage", m.titre.decalage)}</div></div>
           <div class="lab" style="margin-top:12px">Position</div>${seg("montage.titre.position", [["haut", "Haut"], ["milieu", "Milieu"], ["bas", "Bas"]], m.titre.position)}${al(bloque.titre)}
           <h4 style="margin-top:26px">Sous-titres</h4><div class="pas"><div><div class="lab">Taille</div>${pm("montage.sous_titres.taille", m.sous_titres.taille, " px", 2)}</div><div><div class="lab">Ajuster haut / bas</div>${fleches("montage.sous_titres.decalage", m.sous_titres.decalage)}</div></div>
           <div class="lab" style="margin-top:12px">Position</div>${seg("montage.sous_titres.position", [["col", "Au col"], ["poitrine", "Poitrine"], ["bas", "Bas"]], m.sous_titres.position)}${al(bloque.sous)}
           <div style="margin-top:14px">${inter("montage.sous_titres.majuscules", m.sous_titres.majuscules !== false, "Sous-titres en majuscules")}</div>` };
      }
      case "montage:mots":
        return { t: "Mots par ligne", s: "Combien de mots s'affichent à la fois dans tes sous-titres.", h: seg("montage.mots_par_ligne", [1, 2, 3, 4, 5].map((n) => [n, String(n)]), m.mots_par_ligne) + `<p class="note">Le texte ne s'anime jamais : il apparaît net, puis disparaît en fondu.</p>` };
      case "montage:couleurs":
      case "carrousels:couleurs":
        return { t: "Couleur de marque", s: "La même dans tes reels et tes carrousels : mots forts, tableaux, mot-clé, bouton. La case barrée = aucune.", h:
          `<h3>Accent</h3>${dots("commun.couleurs.accent", C.couleurs.accent_carrousel, cl.accent, { aucune: true })}` };
      case "montage:texte":
        return { t: "Couleurs du texte", s: "Le texte posé sur ta vidéo. Propre aux reels.", h:
          `<h3>Titre</h3>${dots("commun.couleurs.titre", C.couleurs.texte_reel, cl.titre)}<h3>Ligne 2 du titre</h3>${dots("commun.couleurs.ligne2", C.couleurs.texte_reel, cl.ligne2)}<h3>Sous-titres</h3>${dots("commun.couleurs.sous_titres", C.couleurs.texte_reel, cl.sous_titres)}` };
      case "montage:cartons":
        return { t: "Cartons plein écran", s: "Le dégradé derrière tes cartons. Jamais de couleur unie.", h:
          `<h3>Couleur de départ</h3>${dots("montage.cartons.depart", C.cartons.depart, m.cartons.depart)}<h3>Couleur d'arrivée</h3>${dots("montage.cartons.arrivee", C.cartons.arrivee, m.cartons.arrivee)}${m.cartons.depart.toUpperCase() === m.cartons.arrivee.toUpperCase() ? `<div class="alerte">Départ et arrivée identiques = couleur unie. Change l'une des deux.</div>` : ""}` };
      case "montage:univers":
        return { t: "Univers de motion design", s: "Formes, traits, couleurs et rythme. Le texte prend ton duo de polices. Toutes les animations sont dispo : SuperMonteur choisit la bonne à chaque moment.", h: choixUnivers("montage.univers", m.univers) };
      case "montage:motion": {
        const mo = m.motion;
        const pals = C.palettes.map((p) => `<button class="choix" data-set="montage.motion.palette" data-val="${esc(JSON.stringify(p.id))}" aria-pressed="${mo.palette === p.id}" style="padding:8px 12px"><b style="font-size:14px">${p.nom}</b><span class="pal">${["fond", "texte", "touche", "touche2"].map((x) => `<span style="background:${p[mo.mode][x]}"></span>`).join("")}</span></button>`).join("");
        return { t: "Réglages du motion", s: "Ton univers « " + par(C.univers, m.univers).nom + " », à ta main. Le texte reste dans ton duo de polices.", h:
          `<h3>Mode</h3>${seg("montage.motion.mode", [["sombre", "Sombre"], ["clair", "Clair"]], mo.mode)}<h3>Palette (fond, traits, petites touches)</h3>${pals}
           <h3>Trait</h3>${seg("montage.motion.trait", [["fin", "Fin"], ["moyen", "Moyen"], ["epais", "Épais"]], mo.trait)}
           <h3>Formes</h3>${seg("montage.motion.formes", [["arrondies", "Arrondies"], ["carrees", "Carrées"]], mo.formes)}
           <h3>Rythme</h3>${seg("montage.motion.rythme", [["pose", "Posé"], ["normal", "Normal"], ["nerveux", "Nerveux"]], mo.rythme)}` };
      }
      case "carrousels:texte":
        return { t: "Couleur du texte", s: "Le texte de tes slides. Propre aux carrousels.", h:
          `<h3>Texte</h3>${dots("commun.couleurs.texte", C.couleurs.texte_carrousel, cl.texte)}` };
      case "carrousels:modele":
        return { t: "Modèle de carrousel", s: "Une ambiance par modèle. Polices et couleurs = ta marque.", h: C.modeles.map((x) => `<button class="choix img" data-set="carrousels.modele" data-val="${esc(JSON.stringify(x.id))}" aria-pressed="${k.modele === x.id}"><span class="mini v">${carte(slideCouverture(x.id), 44)}</span><span class="txt"><b>${x.nom}</b><small>${x.desc}</small></span></button>`).join("") };
      case "carrousels:couverture":
        return { t: "Couverture", s: "La slide qui fait arrêter le pouce. 7 mots max.", h:
          `<h3>Place du titre</h3>${seg("carrousels.couverture.place_titre", [["haut", "En haut"], ["bas", "En bas"], ["derriere_tete", "Derrière la tête"]], k.couverture.place_titre)}
           <h3>Taille du titre</h3>${pm("carrousels.couverture.taille_titre", k.couverture.taille_titre, " px", 4)}
           <div style="margin-top:14px">${inter("carrousels.couverture.petite_ligne", k.couverture.petite_ligne, "Petite ligne au-dessus du titre")}${inter("carrousels.couverture.fleche_glisse", k.couverture.fleche_glisse, "Flèche « glisse »")}</div>` };
      case "carrousels:photos":
        return { t: "Slides photo", s: "Tes vraies photos, jamais d'image IA. Jamais de ponctuation qui traîne en fin de ligne.", h:
          `<h3>Photos</h3>${seg("carrousels.slides_photo.photos", [["sombres", "Sombres"], ["naturelles", "Naturelles"], ["noir_blanc", "Noir et blanc"]], k.slides_photo.photos)}
           <h3>Texte</h3>${seg("carrousels.slides_photo.texte", [["phrase", "1 phrase"], ["liste", "Liste 1-2-3"]], k.slides_photo.texte)}
           <h3>Taille du texte</h3>${pm("carrousels.slides_photo.taille_texte", k.slides_photo.taille_texte, " px", 2)}` };
      case "carrousels:dessins": {
        const de = k.dessins;
        return { t: "Dessins", s: "Les schémas des slides sans photo.", h:
          `<h3>Jour ou nuit</h3>${seg("carrousels.dessins.fond", [["nuit", "Nuit"], ["jour", "Jour"]], de.fond)}
           <h3>Style</h3>
           <button class="choix" data-set="carrousels.dessins.style" data-val='"comme_motion"' aria-pressed="${de.style === "comme_motion"}"><b>Comme ton motion design</b><small>univers ${par(C.univers, m.univers).nom}</small></button>
           <button class="choix" data-set="carrousels.dessins.style" data-val='"autre"' aria-pressed="${de.style === "autre"}"><b>Autre univers</b><small>juste pour les carrousels</small></button>
           ${de.style === "autre" ? `<div style="margin-top:8px">${choixUnivers("carrousels.dessins.univers", de.univers)}</div>` : ""}
           <p class="note">Lié à « Univers du motion » (onglet Montage) : changer l'un change l'autre.</p>` };
      }
      case "carrousels:derniere": {
        const ds = k.derniere_slide;
        return { t: "Dernière slide", s: "Ce qui fait commenter.", h:
          inter("carrousels.derniere_slide.active", ds.active, "Mettre une dernière slide") +
          (ds.active ? `<h3>Forme</h3>${seg("carrousels.derniere_slide.forme", [["bulles", "3 bulles"], ["mot_geant", "Mot en géant"], ["bouton", "Bouton"]], ds.forme)}${inter("carrousels.derniere_slide.photo", ds.photo, "Ta photo sur la dernière slide")}${ds.photo ? `<h3>Contour blanc de ta photo</h3>${pm("carrousels.derniere_slide.contour", ds.contour, " px", 2)}` + cadrage(ds.cadrage) : ""}` : "") +
          `<p class="note">Le mot-clé et la ressource changent à chaque carrousel : SuperCarrousel les remplit.</p>` };
      }
      case "montage:inspiration": case "carrousels:inspiration":
        return { t: "Inspiration", s: O === "montage" ? "Colle le lien d'un créateur, d'un reel ou d'une marque que tu aimes. Je propose une DA qui s'en inspire, que tu peux modifier." : "Colle le lien d'un compte ou d'un carrousel dont tu aimes le style. Je propose une DA qui s'en inspire, que tu peux modifier.", h:
          `<div class="lien"><input id="lien" type="url" placeholder="${O === "montage" ? "https://www.instagram.com/reel/…" : "https://www.instagram.com/p/…"}" aria-label="Lien d'inspiration"><button data-action="analyser">Analyser</button></div>
           <label class="depot" id="depot"><input type="file" id="fichier" hidden accept="image/*,video/*,application/pdf"><b>Ou dépose une ressource</b><span>capture, vidéo, PDF, image</span></label>
           <p class="note">Ça propose une nouvelle DA : tu choisis ce que tu gardes avant que ça remplace l'actuelle.</p>${da.inspiration && da.inspiration.resume ? `<p class="note">Dernière inspiration : ${esc(da.inspiration.resume)}</p>` : ""}` };
    }
    return { t: "", s: "", h: "" };
  }

  function blocClaude() {
    return `<div class="claude${attente ? " charge" : ""}"><span class="av">C</span><textarea id="demande" rows="2" placeholder="${attente ? "Claude travaille… (jusqu'à 10 min s'il ajoute un réglage)" : "Demande à Claude de modifier quelque chose…"}" aria-label="Demande à Claude" ${attente ? "disabled" : ""}></textarea><button class="go" data-action="claude" aria-label="Envoyer à Claude" ${attente ? "disabled" : ""}>↑</button></div>${reponse.texte ? `<p class="rep${reponse.err ? " err" : ""}">${esc(reponse.texte)}</p>` : ""}`;
  }

  /* ---------- rendu ---------- */
  function rendre() {
    calcule();
    const R = resume();
    if (TIROIR) return rendreTiroir(R);
    const secs = SECTIONS[onglet];
    if (!secs.some((x) => x.id === section)) section = secs[0].id;
    const p = panneau(section);
    const estSale = sale();
    $("#app").innerHTML = `
      <header class="top"><h1>SuperDA</h1>
        <div class="tabs" role="tablist">${["montage", "carrousels"].map((o) => `<button role="tab" data-onglet="${o}" aria-selected="${onglet === o}">${o === "montage" ? "Montage" : "Carrousels"}</button>`).join("")}</div>
        <div class="etat${estSale ? " sale" : ""}"><span class="pt"></span><span class="t">${estSale ? "Pas encore enregistré" : "Enregistré"}</span>${DEPUIS ? `<a href="javascript:history.back()">← Retour à ${DEPUIS}</a>` : ""}</div>
      </header>
      <div class="cols">
        <nav class="sections" aria-label="Sections"><p>${onglet === "montage" ? "Réglée une fois. Tous tes reels la suivent." : "Même marque, réglages des carrousels."}</p>
          ${secs.map((x) => `<button data-section="${x.id}" aria-current="${x.id === section}"><span>${x.nom}${x.partage ? `<span class="chip">partagé</span>` : ""}</span><span class="v">${esc(R[onglet][x.id] || "")}</span></button>`).join("")}
        </nav>
        <main class="apercu" aria-label="Aperçu">${onglet === "montage" ? reel(section) + `<small>${legendeReel(section)}</small>` : carrousel(section)}</main>
        <aside class="reglages"><h2>${p.t}</h2><div class="sous">${p.s}</div>${p.h}
          <div class="bloc-bas">${blocClaude()}<button class="btn" data-action="enregistrer">${flash ? "Enregistré ✓" : "Enregistrer ma DA"}</button></div>
        </aside>
      </div>`;
    brancherDepot();
  }

  function rendreTiroir(R) {
    document.body.classList.add("tiroir");
    const secs = SECTIONS[TIROIR].filter((x) => x.id !== "inspiration");
    const estSale = sale();
    const bouton = TIROIR === "montage" ? "Enregistrer pour tous mes reels" : "Enregistrer pour tous mes carrousels";
    let corps;
    if (section && secs.some((x) => x.id === section)) {
      const p = panneau(section);
      const mini = TIROIR === "montage"
        ? `<div class="tel" style="width:160px;height:284px;border-radius:16px"><div class="scene" style="width:1080px;height:1920px;transform:scale(${160 / 1080})">${$tmpReel(section)}</div></div>`
        : `<div class="slide" style="width:180px;height:240px;border-radius:10px">${carte(slides()[{ derniere: slides().length - 1, photos: 1, dessins: 2 }[section] || 0](), 180)}</div>`;
      corps = `<button class="retour" data-section="">‹ Ma DA</button><h2 style="font-size:18px">${p.t}</h2><div class="sous">${p.s}</div><div class="apercu-mini">${mini}</div>${p.h}`;
    } else {
      const R2 = resumeTiroir(R);
      corps = `<header><h2>Ma DA</h2><button class="x" data-action="fermer" aria-label="Fermer">×</button></header>
        <div class="sous">${TIROIR === "montage" ? "Tu changes ici, ton reel se met à jour." : "Tu changes ici, ton carrousel se met à jour."}</div>
        ${secs.map((x) => `<button class="rang" data-section="${x.id}"><span>${x.nom}</span><b>${esc(R2[x.id])} ›</b></button>`).join("")}`;
    }
    $("#app").innerHTML = `<div class="tir">${corps}<div class="bloc-bas">${blocClaude()}
      <a class="btn contour" href="/?onglet=${TIROIR}${section ? "&section=" + section : ""}" target="_blank" rel="noopener" style="text-align:center;line-height:44px;text-decoration:none">Ouvrir SuperDA en grand</a>
      <button class="btn" data-action="enregistrer">${flash ? "Enregistré ✓" : bouton}</button></div></div>`;
  }
  function resumeTiroir(R) {
    const r = Object.assign({}, R[TIROIR]);
    if (TIROIR === "montage") {
      r.tailles = da.montage.titre.taille + " · " + da.montage.sous_titres.taille + " px";
      r.motion = cap(da.montage.motion.mode);
    }
    return r;
  }
  function $tmpReel(sec) {
    // contenu de la scène reel sans le cadre (réutilisé par le tiroir)
    const h = reel(sec);
    const i = h.indexOf('transform:scale(');
    return h.slice(h.indexOf('">', i) + 2, h.lastIndexOf("</div></div>"));
  }

  /* ---------- modifier la DA ---------- */
  function poser(chemin, v) {
    const k = chemin.split(".");
    let o = da;
    for (let i = 0; i < k.length - 1; i++) o = o[k[i]];
    o[k[k.length - 1]] = v;
  }
  function lireVal(chemin) { return chemin.split(".").reduce((o, x) => o[x], da); }
  function change(sansRendu) {
    calcule();
    if (!sansRendu) rendre();
    if (TIROIR) parent("apercu", { da: da });
  }
  function appliquerUnivers(u) {
    const d = par(C.univers, u).defaut;
    Object.assign(da.montage.motion, { mode: d.mode, palette: d.palette, trait: d.trait, formes: d.formes, rythme: d.rythme });
  }

  document.addEventListener("click", async (e) => {
    const b = e.target.closest("button, a");
    if (!b) return;
    if (b.dataset.onglet) { onglet = b.dataset.onglet; section = "duo"; slideVue = null; reponse.texte = ""; history.replaceState(null, "", "?onglet=" + onglet); return rendre(); }
    if (b.dataset.section !== undefined) { section = b.dataset.section || null; slideVue = null; reponse.texte = ""; return rendre(); }
    if (b.dataset.slide) { slideVue = +b.dataset.slide; return rendre(); }
    if (b.dataset.set) {
      const v = JSON.parse(b.dataset.val);
      poser(b.dataset.set, v);
      if (b.dataset.set === "montage.univers") appliquerUnivers(v);
      if (b.dataset.set === "montage.titre.position") da.montage.titre.decalage = 0;
      if (b.dataset.set === "montage.sous_titres.position") da.montage.sous_titres.decalage = 0;
      if (b.dataset.set === "montage.motion.palette" || b.dataset.set === "montage.motion.mode") { if (da.montage.motion.palette === "perso") da.montage.motion.palette = "glacier"; }
      if (b.dataset.set.startsWith("carrousels.")) slideVue = null;
      return change();
    }
    if (b.dataset.pas) {
      const k = b.dataset.pas, v = lireVal(k) + (+b.dataset.d);
      const lim = { "montage.titre.taille": [40, 200], "montage.sous_titres.taille": [24, 120], "carrousels.couverture.taille_titre": [40, 200], "carrousels.slides_photo.taille_texte": [24, 120], "carrousels.derniere_slide.contour": [0, 20], "carrousels.derniere_slide.cadrage.zoom": [100, 400], "carrousels.derniere_slide.cadrage.x": [0, 100], "carrousels.derniere_slide.cadrage.y": [0, 100] }[k] || [-600, 600];
      poser(k, Math.max(lim[0], Math.min(lim[1], v)));
      if (k.endsWith("decalage")) { calcule(); if (k.indexOf("titre.") === 8 ? bloque.titre : bloque.sous) poser(k, v - (+b.dataset.d)); }
      return change();
    }
    if (b.dataset.bascule) { poser(b.dataset.bascule, !lireVal(b.dataset.bascule)); slideVue = null; return change(); }
    if (b.dataset.duo) {
      const id = b.dataset.duo;
      if (id === "perso") {
        if (da.commun.duo.id !== "perso") da.commun.duo = { id: "perso", nom: "Mon combo perso", principale: clone(da.commun.duo.principale), secondaire: clone(da.commun.duo.secondaire) };
      } else { const x = par(C.duos, id); da.commun.duo = { id: x.id, nom: x.nom, principale: clone(x.principale), secondaire: clone(x.secondaire) }; }
      return change();
    }
    const a = b.dataset.action;
    if (a === "enregistrer") return enregistrer();
    if (a === "claude") return demanderClaude();
    if (a === "analyser") return analyser({ source: $("#lien").value.trim() });
    if (a === "fermer") return parent("fermer");
  });
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (t.dataset.perso) {
      const pp = C.polices_perso;
      if (da.commun.duo.id !== "perso") da.commun.duo = { id: "perso", nom: "Mon combo perso", principale: clone(da.commun.duo.principale), secondaire: clone(da.commun.duo.secondaire) };
      if (t.dataset.perso === "principale") { const x = pp.principales.find((y) => y.famille === t.value); da.commun.duo.principale = { famille: x.famille, fichier: x.fichier, graisse: x.graisse, majuscules: true, interlettrage: 1 }; }
      else { const x = pp.secondaires.find((y) => y.fichier === t.value); da.commun.duo.secondaire = { famille: x.famille, fichier: x.fichier, graisse: x.graisse, italique: x.italique, majuscules: false }; }
      return change();
    }
    if (t.dataset.couleur) { poser(t.dataset.couleur, t.value.toUpperCase()); return change(); }
    if (t.id === "fichier" && t.files[0]) lireFichier(t.files[0]);
  });
  document.addEventListener("input", (e) => {
    if (e.target.dataset && e.target.dataset.couleur) { poser(e.target.dataset.couleur, e.target.value.toUpperCase()); calcule(); majApercuSeul(); }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); enregistrer(); }
    if (e.target.id === "demande" && e.key === "Enter" && !e.shiftKey) { e.preventDefault(); demanderClaude(); }
    if (e.target.id === "lien" && e.key === "Enter") { e.preventDefault(); analyser({ source: e.target.value.trim() }); }
  });
  function majApercuSeul() {
    const m = $("main.apercu");
    if (!m) return;
    m.innerHTML = onglet === "montage" ? reel(section) + `<small>${legendeReel(section)}</small>` : carrousel(section);
  }

  async function enregistrer() {
    try {
      const d = await api("/api/da", da);
      da = d; calcule(); daSauvee = propre(da);
      reponse = { texte: "", err: false };
      flash = true; rendre();
      setTimeout(() => { flash = false; rendre(); }, 1600);
      parent("maj", { da: da });
    } catch (err) { reponse = { texte: "Pas enregistré : " + err.message, err: true }; rendre(); }
  }

  async function demanderClaude() {
    const champ = $("#demande");
    const texte = champ ? champ.value.trim() : "";
    if (!texte || attente) return;
    attente = true; reponse = { texte: "", err: false }; rendre();
    try {
      const r = await api("/api/claude", { onglet, section, demande: texte, da });
      da = r.da; calcule(); daSauvee = propre(da);
      reponse = { texte: r.explication || "C'est fait.", err: false };
      parent("maj", { da: da });
      if (r.recharger) { // Claude a ajouté un réglage dans l'appli : on recharge pour le voir
        try { sessionStorage.setItem("superda-reponse", reponse.texte); } catch (e) {}
        reponse = { texte: reponse.texte + " La page se recharge…", err: false }; attente = false; rendre();
        return setTimeout(() => location.reload(), 3000);
      }
    } catch (err) { reponse = { texte: "Claude n'a pas pu : " + err.message, err: true }; }
    attente = false; slideVue = null; rendre();
  }

  /* ---------- Inspiration ---------- */
  function brancherDepot() {
    const d = $("#depot");
    if (!d) return;
    d.addEventListener("dragover", (e) => { e.preventDefault(); d.classList.add("survol"); });
    d.addEventListener("dragleave", () => d.classList.remove("survol"));
    d.addEventListener("drop", (e) => { e.preventDefault(); d.classList.remove("survol"); if (e.dataTransfer.files[0]) lireFichier(e.dataTransfer.files[0]); });
  }
  function lireFichier(f) {
    if (f.size > 45 * 1024 * 1024) { reponse = { texte: "Fichier trop lourd (45 Mo max).", err: true }; return rendre(); }
    const r = new FileReader();
    r.onload = () => analyser({ fichier: r.result, nom: f.name });
    r.readAsDataURL(f);
  }
  const GARDER = {
    montage: [["duo", "Mon duo de polices"], ["couleurs", "Ma couleur de marque"], ["texte", "Mes couleurs du texte"], ["tailles", "Mes tailles et positions"], ["mots", "Mes mots par ligne"], ["cartons", "Mes cartons"], ["motion", "Mon motion design"]],
    carrousels: [["duo", "Mon duo de polices"], ["couleurs", "Ma couleur de marque"], ["texte", "Ma couleur du texte"], ["modele", "Mon modèle"], ["couverture", "Ma couverture"], ["photos", "Mes slides photo"], ["dessins", "Mes dessins"], ["derniere", "Ma dernière slide"]],
  };
  async function analyser(corps) {
    if (!corps.source && !corps.fichier) { reponse = { texte: "Colle un lien ou dépose une ressource.", err: true }; return rendre(); }
    attente = true; reponse = { texte: "J'analyse l'inspiration… (1 à 3 minutes)", err: false }; rendre();
    try {
      const r = await api("/api/inspiration", Object.assign({ onglet, da }, corps));
      attente = false; reponse = { texte: "", err: false }; rendre();
      fenetreInspi(r);
    } catch (err) { attente = false; reponse = { texte: "Analyse impossible : " + err.message, err: true }; rendre(); }
  }
  function fenetreInspi(r) {
    const v = document.createElement("div");
    v.className = "voile";
    v.innerHTML = `<div class="fenetre" role="dialog" aria-modal="true" aria-labelledby="fi-t"><h2 id="fi-t">Nouvelle DA trouvée</h2><p>${esc(r.resume)}</p>
      <div class="att">Attention : appliquer cette DA remplace ta DA actuelle. Coche ce que tu veux GARDER.</div>
      ${GARDER[onglet].map(([id, n], i) => `<label><input type="checkbox" value="${id}" ${i < 2 ? "checked" : ""}>${n}</label>`).join("")}
      <div class="act"><button class="btn contour" style="margin:0" data-fi="non">Annuler</button><button class="btn" data-fi="oui">Appliquer</button></div></div>`;
    document.body.appendChild(v);
    v.addEventListener("click", (e) => {
      const b = e.target.closest("[data-fi]");
      if (!b && e.target !== v) return;
      if (b && b.dataset.fi === "oui") {
        const garde = new Set([...v.querySelectorAll("input:checked")].map((x) => x.value));
        const p = r.proposee, n = clone(da);
        const prend = (cond, f) => { if (!garde.has(cond)) f(); };
        prend("duo", () => { n.commun.duo = p.commun.duo; });
        if (onglet === "montage") {
          prend("couleurs", () => { n.commun.couleurs.accent = p.commun.couleurs.accent; });
          prend("texte", () => { ["titre", "ligne2", "sous_titres"].forEach((x) => { n.commun.couleurs[x] = p.commun.couleurs[x]; }); });
          prend("tailles", () => { n.montage.titre = p.montage.titre; n.montage.sous_titres = p.montage.sous_titres; });
          prend("mots", () => { n.montage.mots_par_ligne = p.montage.mots_par_ligne; });
          prend("cartons", () => { n.montage.cartons = p.montage.cartons; });
          prend("motion", () => { n.montage.univers = p.montage.univers; n.montage.motion = p.montage.motion; });
        } else {
          prend("couleurs", () => { n.commun.couleurs.accent = p.commun.couleurs.accent; });
          prend("texte", () => { n.commun.couleurs.texte = p.commun.couleurs.texte; });
          prend("modele", () => { n.carrousels.modele = p.carrousels.modele; });
          prend("couverture", () => { n.carrousels.couverture = p.carrousels.couverture; });
          prend("photos", () => { n.carrousels.slides_photo = p.carrousels.slides_photo; });
          prend("dessins", () => { n.carrousels.dessins = p.carrousels.dessins; });
          prend("derniere", () => { n.carrousels.derniere_slide = p.carrousels.derniere_slide; });
        }
        n.inspiration = { source: r.source, date: new Date().toISOString().slice(0, 10), resume: r.resume };
        da = n;
        v.remove();
        enregistrer();
        return;
      }
      v.remove();
    });
  }

  /* ---------- démarrage ---------- */
  window.addEventListener("message", (e) => {
    if (e.data && e.data.type === "superda:recharger") charger();
  });
  window.addEventListener("beforeunload", (e) => { if (da && sale() && !TIROIR) { e.preventDefault(); e.returnValue = ""; } });
  async function charger() {
    try {
      [C, da] = await Promise.all([api("/api/catalogue"), api("/api/da")]);
      calcule();
      daSauvee = propre(da);
      // charge toutes les polices du catalogue avant le 1er rendu (sinon l'aperçu s'affiche un instant en police de secours)
      const fams = new Set();
      C.duos.forEach((d) => { fams.add(d.principale.famille); fams.add(d.secondaire.famille); });
      C.polices_perso.principales.forEach((x) => fams.add(x.famille));
      C.polices_perso.secondaires.forEach((x) => fams.add(x.famille));
      await Promise.all([...fams].flatMap((f) => [document.fonts.load(`700 40px "${f}"`), document.fonts.load(`italic 400 40px "${f}"`)]).map((p) => p.catch(() => null)));
      await document.fonts.ready;
      rendre();
    } catch (err) {
      $("#app").innerHTML = `<p style="padding:40px">SuperDA ne trouve pas son serveur. Lance-le avec « python3 server.py » dans apps/superda.</p>`;
    }
  }
  charger();
})();
