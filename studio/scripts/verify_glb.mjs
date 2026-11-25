#!/usr/bin/env node
/**
 * Headless Three.js GLTFLoader round-trip verifier & 5-angle studio renderer.
 * Usage: node studio/scripts/verify_glb.mjs <path/to/model.glb> <out_dir>
 */
import fs from 'node:fs';
import path from 'node:path';

const [glbArg, outArg] = process.argv.slice(2);
if (!glbArg || !outArg) {
  console.error('Usage: node studio/scripts/verify_glb.mjs <model.glb> <out_dir>');
  process.exit(1);
}
const glbPath = path.resolve(glbArg);
const outDir = path.resolve(outArg);
fs.mkdirSync(outDir, { recursive: true });

const { chromium } = await import('playwright');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 960, height: 640 } });
const b64 = fs.readFileSync(glbPath).toString('base64');

await page.setContent(`<!doctype html><html><body style="margin:0;background:#161a24">
<canvas id="c" width="960" height="640"></canvas>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
window.runVerify = async (base64) => {
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
  const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: true, preserveDrawingBuffer: true });
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x3a485c);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.add(new THREE.GridHelper(24, 24, 0x5d728e, 0x48586e));
  scene.add(new THREE.HemisphereLight(0xdce8ff, 0x38322c, 0.9));
  const key = new THREE.DirectionalLight(0xfff4e0, 1.8);
  key.position.set(-5, 8, 6);
  key.castShadow = true;
  scene.add(key);

  const gltf = await new Promise((res, rej) => new GLTFLoader().parse(bytes.buffer, '', res, rej));
  scene.add(gltf.scene);
  const box = new THREE.Box3().setFromObject(gltf.scene);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const r = Math.max(size.length() * 0.5, 0.5);
  const cam = new THREE.PerspectiveCamera(42, 960 / 640, 0.05, r * 30);

  let meshes = 0, tris = 0;
  gltf.scene.traverse(o => {
    if (o.isMesh) {
      meshes++;
      tris += o.geometry.index ? o.geometry.index.count / 3 : o.geometry.attributes.position.count / 3;
    }
  });
  window.__renderAngle = (azDeg, elDeg, zoom = 2.2) => {
    const az = azDeg * Math.PI / 180, el = elDeg * Math.PI / 180;
    cam.position.set(center.x + Math.sin(az) * Math.cos(el) * r * zoom, center.y + Math.sin(el) * r * zoom, center.z + Math.cos(az) * Math.cos(el) * r * zoom);
    cam.lookAt(center);
    renderer.render(scene, cam);
  };
  return { meshes, triangles: Math.round(tris), nodes: gltf.scene.children.map(c => c.name) };
};
</script></body></html>`);

const stats = await page.evaluate(b => window.runVerify(b), b64);
const angles = [['iso', 38, 22, 2.2], ['front', 0, 8, 2.1], ['side', 90, 8, 2.1], ['rear', 180, 12, 2.2], ['deck_top', 20, 52, 2.1], ['closeup', 28, 16, 1.30]];
for (const [name, az, el, zoom] of angles) {
  await page.evaluate(([a, e, z]) => window.__renderAngle(a, e, z), [az, el, zoom]);
  await page.screenshot({ path: path.join(outDir, `view_${name}.png`) });
}
await browser.close();
console.log(JSON.stringify({ glb: path.basename(glbPath), ...stats, views: angles.map(a => `view_${a[0]}.png`) }, null, 2));
