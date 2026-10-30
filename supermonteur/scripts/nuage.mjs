// 29/10 : mode NUAGE de brolltexte.py (collé à la fin de _shot.mjs, les __X__ sont remplacés par Python).
// Pose chaque mot au hasard (graine fixe) hors du texte du centre, du visage et des zones mortes Insta,
// puis capture text.png (texte du centre seul), _w<i>.png (un mot seul) et text-nuage.png (tout, pour contrôle).
const W0 = __WORDS__, SL = __SLOTS__, FB = __FB__, ZL = 90, ZR = __W__ - 90, ZT = __TOP__ + 20, ZB = __BOTTOM__ - 20;
const res = await p.evaluate((W0, SL, FB, ZL, ZR, ZT, ZB, WW) => {
  // 29/10 (l’utilisateur : « plus aléatoire, trop regroupé, respecte les zones Insta ») : zone sûre + 20-25 px de marge,
  // chaque mot tire une taille au hasard, puis parmi 60 places libres tirées au hasard on garde celle la plus
  // éloignée de tout le reste (texte du centre, visage, autres mots) -> éparpillé sur tout l'écran, jamais en paquet.
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const busy = [...document.querySelectorAll("#b span, #c span")].map(e => e.getBoundingClientRect())
    .map(q => [q.left - 30, q.top - 22, q.right + 30, q.bottom + 22]);
  if (FB) busy.push(FB);
  const placed = [];
  const hit = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
  const gap = (a, b) => Math.hypot(Math.max(0, b[0] - a[2], a[0] - b[2]), Math.max(0, b[1] - a[3], a[1] - b[3]));
  const out = [];
  const libre = r => !(r[3] > 1080 && r[2] > WW - 140) && r[0] >= ZL && r[2] <= ZR && r[1] >= ZT && r[3] <= ZB &&
    !busy.some(b => hit([r[0] - 14, r[1] - 6, r[2] + 14, r[3] + 6], b));
  // 29/10 « reprends le positionnement de l'original » : un mot qui a une place de la référence (SL[i] = [cx, cy, h, w])
  // s'y pose ; si elle touche le visage, le texte du centre ou un autre mot, on prend la place libre la plus proche (spirale).
  const reste = [];   // place de la référence introuvable -> posé au hasard ensuite
  const avec = W0.map((w, i) => [w, i]).filter(([, i]) => SL && SL[i]);
  avec.forEach(([w, i]) => {
    const e = document.createElement("div"); e.className = "w"; e.id = "w" + i; e.textContent = w; document.body.appendChild(e);
    const [cx, cy, h, wr] = SL[i];
    let fs = Math.max(34, Math.min(60, Math.round(h * 0.75)));
    e.style.fontSize = fs + "px";
    while (fs > 32 && e.offsetWidth > Math.max(wr * 1.3, 200)) { fs -= 2; e.style.fontSize = fs + "px"; }
    const ew = e.offsetWidth, eh = e.offsetHeight;
    for (let rad = 0; rad <= 600; rad += 8) {
      for (let a = 0; a < (rad ? 32 : 1); a++) {
        const x = cx - ew / 2 + rad * Math.cos(a * Math.PI / 16), y = cy - eh / 2 + rad * Math.sin(a * Math.PI / 16), r = [x, y, x + ew, y + eh];
        if (!libre(r)) continue;
        e.style.left = x + "px"; e.style.top = y + "px"; busy.push(r); placed.push(r); out.push([i, Math.round(x), Math.round(y), fs]); return;
      }
    }
    e.remove(); reste.push([w, i]);
  });
  const ordre = W0.map((w, i) => [w, i]).filter(([, i]) => !(SL && SL[i])).concat(reste).sort((x, y) => y[0].length - x[0].length);   // sans place : les plus longs d'abord
  ordre.forEach(([w, i]) => {
    const e = document.createElement("div"); e.className = "w"; e.id = "w" + i; e.textContent = w; document.body.appendChild(e);
    for (let fs = [54, 48, 42, 38][Math.floor(rnd() * 4)]; fs >= 30; fs -= 4) {
      e.style.fontSize = fs + "px"; const ew = e.offsetWidth, eh = e.offsetHeight;
      if (ew > ZR - ZL) continue;
      let best = null, bs = -1, found = 0;
      for (let k = 0; k < 6000 && found < 60; k++) {
        const x = ZL + rnd() * (ZR - ZL - ew), y = ZT + rnd() * (ZB - ZT - eh), r = [x, y, x + ew, y + eh];
        if (r[3] > 1080 && r[2] > WW - 140) continue;                       // boutons Insta à droite (120 px + marge)
        if (busy.some(b => hit([r[0] - 14, r[1] - 6, r[2] + 14, r[3] + 6], b))) continue;
        found++;
        const sc = Math.min(80, ...placed.map(b => gap(r, b))) * (0.5 + rnd());   // écart aux autres MOTS seulement (sinon tout file vers les bords), plafonné, + hasard
        if (sc > bs) { bs = sc; best = r; }
      }
      if (best) {
        e.style.left = best[0] + "px"; e.style.top = best[1] + "px"; busy.push(best); placed.push(best);
        out.push([i, Math.round(best[0]), Math.round(best[1]), fs]); return;
      }
    }
    e.remove();
  });
  return out.sort((x, y) => x[0] - y[0]);   // ordre d'apparition = ordre de la liste
}, W0, SL, FB, ZL, ZR, ZT, ZB, __W__);
await p.screenshot({path: "__DIR__/text.png", omitBackground: true});
for (const [i] of res) {
  await p.evaluate((i) => {
    document.getElementById("b").style.visibility = "hidden";
    const c = document.getElementById("c"); if (c) c.style.visibility = "hidden";
    document.querySelectorAll(".w").forEach(e => e.style.visibility = e.id === "w" + i ? "visible" : "hidden");
  }, i);
  await p.screenshot({path: "__DIR__/_w" + i + ".png", omitBackground: true});
}
await p.evaluate(() => {
  document.getElementById("b").style.visibility = "visible";
  const c = document.getElementById("c"); if (c) c.style.visibility = "visible";
  document.querySelectorAll(".w").forEach(e => e.style.visibility = "visible");
});
await p.screenshot({path: "__DIR__/text-nuage.png", omitBackground: true});
console.log(JSON.stringify(res));
