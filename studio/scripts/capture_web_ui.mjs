#!/usr/bin/env node
/**
 * Headless Playwright transparent PNG capture for Track 3 (2d_web_ui) React/HTML/CSS/SVG assets.
 * Usage: node studio/scripts/capture_web_ui.mjs <path/to/index.html> <out.png> [width] [height]
 */
import path from 'node:path';
const [htmlArg, outArg, wArg = '512', hArg = '512'] = process.argv.slice(2);
if (!htmlArg || !outArg) {
  console.error('Usage: node studio/scripts/capture_web_ui.mjs <index.html> <out.png> [width] [height]');
  process.exit(1);
}
const { chromium } = await import('playwright');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: Number(wArg), height: Number(hArg) }, deviceScaleFactor: 2 });
await page.goto(`file://${path.resolve(htmlArg)}`, { waitUntil: 'networkidle' });
await page.screenshot({ path: path.resolve(outArg), omitBackground: true });
await browser.close();
console.log(`✓ Captured transparent 2D Web UI asset -> ${outArg}`);
