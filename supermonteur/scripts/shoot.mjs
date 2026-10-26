// Capture pleine page (largeur mobile 540 css px, x2 = 1080 px) de pages publiques, bannière cookies REFUSÉE si possible.
// node shoot.mjs out.png URL [maxHeightCss]
import { createRequire } from "node:module";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
const NPX = join(homedir(), ".npm", "_npx"), CH = [join(homedir(), ".cache", "hyperframes", "chrome", "chrome-headless-shell"), join(homedir(), ".cache", "puppeteer", "chrome-headless-shell")];   // 0.8 range Chrome dans ~/.cache/hyperframes, 0.6 dans ~/.cache/puppeteer (25/10)
const mod = existsSync(NPX) && readdirSync(NPX).map(d => join(NPX, d, "node_modules")).find(d => existsSync(join(d, "puppeteer-core")));
if (!mod) { console.log("puppeteer-core introuvable : lancer une fois « npx --yes hyperframes@0.8.149 browser ensure »"); process.exit(1); }
const puppeteer = createRequire(mod + "/")("puppeteer-core");
const GC = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const HS = CH.filter(existsSync).flatMap(c => readdirSync(c).sort().reverse().map(v => join(c, v))).flatMap(v => readdirSync(v).map(x => join(v, x, "chrome-headless-shell"))).find(existsSync);
const [out, url, maxH = "5000"] = process.argv.slice(2);
const browser = await puppeteer.launch({
  executablePath: existsSync(GC) ? GC : HS,
  headless: "new", args: ["--no-first-run", "--hide-scrollbars"],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 540, height: 960, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await page.goto(url, { waitUntil: "networkidle2", timeout: 45000 }).catch(e => console.log("goto:", e.message));
  // refuser les cookies non essentiels (option la plus respectueuse de la vie privée)
  const clicked = await page.evaluate(() => {
    const re = /^(reject|decline|refuse|refuser|tout refuser|reject all|decline all|only necessary|necessary only|essential only|deny)/i;
    for (const b of document.querySelectorAll("button, a[role=button], [role=button]")) {
      if (re.test((b.innerText || "").trim())) { b.click(); return b.innerText.trim(); }
    }
    return null;
  });
  if (clicked) console.log("cookies :", clicked);
  await new Promise(r => setTimeout(r, 2500));
  const h = Math.min(+maxH, await page.evaluate(() => document.documentElement.scrollHeight));
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 540, height: h }, captureBeyondViewport: true });
  console.log(out, "540x" + h + " css");
} finally { await browser.close(); }
