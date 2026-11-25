# Asset-Maker Shared Studio Harness

One shared Node/Vite/Three.js/React/Tailwind/Playwright workspace at the repository root—so individual Three.js (`3d_threejs_hero`) and Web UI (`2d_web_ui`) assets never duplicate `node_modules`.

```sh
cd studio && npm install
node scripts/verify_glb.mjs ../assets/my_hero/my_hero.glb ../assets/my_hero/renders
node scripts/capture_web_ui.mjs ../assets/my_badge/index.html ../assets/my_badge/image.png 512 512
```
