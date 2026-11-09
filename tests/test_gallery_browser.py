import functools
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Install Playwright to run optional browser checks")
class GalleryBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright

        if not all((ROOT / relative).exists() for relative in ("gallery/catalog.json", "gallery/expansion/catalog.json")):
            raise unittest.SkipTest("Generate both gallery collections before browser checks")
        cls.original = json.loads((ROOT / "gallery" / "catalog.json").read_text())["assets"]
        cls.expansion = json.loads((ROOT / "gallery" / "expansion" / "catalog.json").read_text())["assets"]
        cls.catalog = {"assets": cls.expansion + cls.original}
        cls.asset_count = len(cls.catalog["assets"])
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        from playwright.sync_api import expect

        self.expect = expect
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.allow_errors = False
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", lambda message: self.errors.append(message.text) if message.type == "error" else None)
        self.page.goto(self.url, wait_until="networkidle")
        self.expect(self.page.locator(".asset-card")).to_have_count(self.asset_count)

    def tearDown(self):
        if not self.allow_errors:
            self.assertEqual(self.errors, [])

    def test_collection_and_capability_sections(self):
        self.expect(self.page).to_have_title("FORM / Procedural asset lab")
        self.expect(self.page.locator(".capability-grid article")).to_have_count(4)
        self.expect(self.page.locator("#motion-toggle")).to_have_text("Resume motion")
        self.assertEqual({asset["category"] for asset in self.catalog["assets"]}, {"3d", "2d", "vfx", "sfx"})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 1440)
        for image in self.page.locator(".asset-visual > img").all():
            image.scroll_into_view_if_needed()
            self.expect(image).to_be_visible()
            self.assertTrue(image.evaluate("image => image.complete && image.naturalWidth > 0"))

    def test_offscreen_previews_have_initial_content(self):
        self.page.wait_for_function("""() => [...document.querySelectorAll('.asset-visual canvas')].every(c => {
            const pixels = c.getContext('2d').getImageData(0,0,c.width,c.height).data;
            let count = 0; for(let i=3;i<pixels.length;i+=4) if(pixels[i]) count++;
            return count > c.width*c.height*.001;
        })""")
        self.expect(self.page.locator('[data-asset="moss-tile"] .visual-label')).to_have_text("SEAMLESS TILE / PNG")

    def test_generation_command_copy(self):
        self.context.grant_permissions(["clipboard-read", "clipboard-write"])
        self.page.locator('[data-asset="crystal-cluster"] .asset-visual').click()
        self.page.locator("#copy-command").click()
        command = self.page.evaluate("navigator.clipboard.readText()")
        self.assertIn("generate_gallery.py --out gallery-next", command)

    def test_category_filters_and_empty_search(self):
        for category in ["3d", "2d", "vfx", "sfx"]:
            self.page.locator(f'.filters [data-category="{category}"]').click()
            count = sum(asset["category"] == category for asset in self.catalog["assets"])
            self.expect(self.page.locator(".asset-card")).to_have_count(count)
        self.page.locator("#search").fill("no-asset-matches-this-query")
        self.expect(self.page.locator(".asset-card")).to_have_count(0)
        self.expect(self.page.locator("#empty-state")).to_be_visible()
        self.page.get_by_role("button", name="Clear filters").click()
        self.expect(self.page.locator(".asset-card")).to_have_count(self.asset_count)

    def test_search_keyboard_shortcut(self):
        self.page.keyboard.press("/")
        self.expect(self.page.locator("#search")).to_be_focused()
        asset = self.catalog["assets"][0]
        self.page.locator("#search").fill(asset["name"])
        self.expect(self.page.locator(f'[data-asset="{asset["id"]}"]')).to_be_visible()

    def test_model_inspection_rotation_and_download(self):
        self.page.locator('[data-asset="crystal-cluster"] .asset-visual').click()
        self.expect(self.page.locator("#asset-dialog")).to_be_visible()
        canvas = self.page.locator("#inspector-stage canvas")
        self.expect(canvas).to_be_visible()
        self.page.wait_for_function("""() => {
            const c = document.querySelector('#inspector-stage canvas');
            const p = c.getContext('2d').getImageData(0,0,c.width,c.height).data;
            let n = 0; for(let i=3;i<p.length;i+=4) if(p[i]) n++;
            return n > c.width*c.height*.04;
        }""")
        before = canvas.screenshot()
        canvas.focus()
        self.page.keyboard.press("ArrowRight")
        after = canvas.screenshot()
        self.assertNotEqual(before, after)
        self.page.locator('[aria-label="Model zoom"]').fill("1.2")
        self.page.get_by_role("button", name="Reset view").click()
        self.expect(self.page.locator('[aria-label="Model zoom"]')).to_have_value("1")
        with self.page.expect_download() as download:
            self.page.locator("#asset-download").click()
        self.assertTrue(download.value.suggested_filename.endswith(".glb"))
        self.assertGreater(Path(download.value.path()).stat().st_size, 100)
        self.page.keyboard.press("Escape")
        self.expect(self.page.locator("#asset-dialog")).not_to_be_visible()

    def test_vfx_frame_scrubbing_and_playback(self):
        self.page.locator('.filters [data-category="vfx"]').click()
        self.page.locator('[data-asset="arcane-portal"] .asset-visual').click()
        slider = self.page.locator('[aria-label="Animation frame"]')
        slider.fill("7")
        self.expect(self.page.locator(".frame-counter")).to_have_text("08 / 16 FRAMES")
        frozen = self.page.locator("#inspector-stage canvas").screenshot()
        self.assertEqual(frozen, self.page.locator("#inspector-stage canvas").screenshot())
        self.page.locator("#preview-controls button").first.click()
        self.expect(self.page.locator(".frame-counter")).not_to_have_text("08 / 16 FRAMES")
        self.page.locator("#close-dialog").click()

    def test_audio_playback_and_switching(self):
        self.page.locator('.filters [data-category="sfx"]').click()
        first = self.page.locator('[data-play="metal-impact"]')
        first.click()
        self.page.wait_for_function("!document.querySelector('#audio-player').paused && document.querySelector('#audio-player').currentTime > 0")
        self.expect(first).to_have_attribute("aria-pressed", "true")
        second = self.page.locator('[data-play="glass-chime"]')
        second.click()
        self.page.wait_for_function("document.querySelector('#audio-player').currentSrc.includes('glass-chime') && !document.querySelector('#audio-player').paused")
        self.expect(first).to_have_attribute("aria-pressed", "false")
        second.click()
        self.assertTrue(self.page.locator("#audio-player").evaluate("audio => audio.paused"))

    def test_png_background_switch(self):
        self.page.locator('.filters [data-category="2d"]').click()
        self.page.locator('[data-asset="potion"] .asset-visual').click()
        self.page.get_by_role("button", name="Dark background").click()
        self.expect(self.page.locator(".inspector-view")).to_have_class("inspector-view dark")
        self.page.get_by_role("button", name="Light background").click()
        self.expect(self.page.locator(".inspector-view")).to_have_class("inspector-view")

    def test_collection_download(self):
        with self.page.expect_download() as download:
            self.page.locator(".download-pack").click()
        self.assertEqual(download.value.suggested_filename, "asset-collection.zip")
        import zipfile
        with zipfile.ZipFile(download.value.path()) as archive:
            self.assertIsNone(archive.testzip())
            self.assertTrue(any(name.endswith("model.glb") for name in archive.namelist()))
            self.assertTrue(any(name.endswith("sound.wav") for name in archive.namelist()))
            self.assertTrue(any(name.endswith("pine-tree/model.glb") for name in archive.namelist()))
            self.assertIn("fx_pipeline/generate_gallery_expansion.py", archive.namelist())

    def test_original_collection_still_downloads(self):
        with self.page.expect_download() as download:
            self.page.locator('.collection-tools a[download]').click()
        import zipfile
        with zipfile.ZipFile(download.value.path()) as archive:
            self.assertIsNone(archive.testzip())
            self.assertTrue(any(name.endswith("crystal-cluster/model.glb") for name in archive.namelist()))

    def test_mobile_layout_and_dialog(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)
        self.expect(self.page.locator(".sidebar")).not_to_be_visible()
        self.page.locator('[data-asset="crystal-cluster"] .asset-visual').click()
        self.expect(self.page.locator("#asset-dialog")).to_be_visible()
        bounds = self.page.locator("#asset-dialog").bounding_box()
        self.assertGreaterEqual(bounds["x"], 0)
        self.assertLessEqual(bounds["x"] + bounds["width"], 390)
        self.page.locator("#close-dialog").click()
        self.expect(self.page.locator("#asset-dialog")).not_to_be_visible()

    def test_load_error_and_retry(self):
        self.allow_errors = True
        self.page.route("**/gallery/catalog.json", lambda route: route.abort())
        self.page.reload()
        self.expect(self.page.locator("#load-error")).to_be_visible()
        self.page.unroute("**/gallery/catalog.json")
        self.page.get_by_role("button", name="Try again").click()
        self.expect(self.page.locator(".asset-card")).to_have_count(self.asset_count)
        self.expect(self.page.locator("#load-error")).not_to_be_visible()

    def test_study_sets_and_combined_filters(self):
        self.page.locator("#collection-select").select_option("expansion")
        self.expect(self.page.locator(".asset-card")).to_have_count(8)
        self.page.locator('.filters [data-category="3d"]').click()
        self.expect(self.page.locator(".asset-card")).to_have_count(2)
        self.page.locator("#collection-select").select_option("original")
        self.expect(self.page.locator(".asset-card")).to_have_count(3)
        self.page.locator("#search").fill("no matching study")
        self.page.get_by_role("button", name="Clear filters").click()
        self.expect(self.page.locator("#collection-select")).to_have_value("all")
        self.expect(self.page.locator(".asset-card")).to_have_count(self.asset_count)

    def test_expansion_recipe_and_review(self):
        self.context.grant_permissions(["clipboard-read", "clipboard-write"])
        self.page.locator('[data-asset="treasure-chest"] .asset-visual').click()
        self.expect(self.page.locator("#asset-review")).to_be_visible()
        self.page.locator("#copy-command").click()
        command = self.page.evaluate("navigator.clipboard.readText()")
        self.assertIn("generate_gallery_expansion.py --out gallery-expansion-next --seed 19", command)
        self.page.locator("#close-dialog").click()
        self.page.locator('.collection-tools a[href="#quality-review"]').click()
        self.expect(self.page.locator("#quality-review")).to_be_in_viewport()
        self.expect(self.page.locator(".review-grid article")).to_have_count(4)
        self.page.locator('[data-review-asset="gravel-step"]').click()
        self.expect(self.page.locator("#asset-dialog")).to_be_visible()
        self.expect(self.page.locator("#asset-review")).to_be_visible()

    def test_nine_slice_preview(self):
        self.page.locator('[data-asset="dialog-panel"] .asset-visual').click()
        self.page.get_by_role("button", name="Test wide 9-slice").click()
        image = self.page.locator("#inspector-stage img")
        self.page.wait_for_function("document.querySelector('#inspector-stage img').naturalWidth === 768")
        self.expect(image).to_have_attribute("src", "gallery/expansion/assets/dialog-panel/preview-wide.png")
        self.page.get_by_role("button", name="Show source panel").click()
        self.page.wait_for_function("document.querySelector('#inspector-stage img').naturalWidth === 384")

    def test_new_effect_scrubbing_and_light_background(self):
        self.page.locator('[data-asset="dust-puff"] .asset-visual').click()
        slider = self.page.locator('[aria-label="Animation frame"]')
        slider.fill("0")
        self.expect(self.page.locator(".frame-counter")).to_have_text("01 / 16 FRAMES")
        empty = self.page.locator("#inspector-stage canvas").screenshot()
        slider.fill("5")
        self.expect(self.page.locator(".frame-counter")).to_have_text("06 / 16 FRAMES")
        self.assertNotEqual(empty, self.page.locator("#inspector-stage canvas").screenshot())
        self.page.get_by_role("button", name="Light background").click()
        self.expect(self.page.locator(".inspector-view")).not_to_have_class("inspector-view dark")
        self.page.get_by_role("button", name="Dark background").click()
        self.expect(self.page.locator(".inspector-view")).to_have_class("inspector-view dark")

    def test_expansion_audio_playback(self):
        for identifier in ("gravel-step", "charge-release"):
            self.page.locator(f'[data-play="{identifier}"]').click()
            self.page.wait_for_function("id => { const a=document.querySelector('#audio-player'); return a.currentSrc.includes(id) && !a.paused && a.currentTime>0; }", arg=identifier)
            self.page.locator("#audio-player").evaluate("audio => audio.pause()")

    def test_expansion_load_failure_and_retry(self):
        self.allow_errors = True
        self.page.route("**/gallery/expansion/catalog.json", lambda route: route.abort())
        self.page.reload()
        self.expect(self.page.locator("#load-error")).to_be_visible()
        self.expect(self.page.locator(".asset-card")).to_have_count(0)
        self.page.unroute("**/gallery/expansion/catalog.json")
        self.page.get_by_role("button", name="Try again").click()
        self.expect(self.page.locator(".asset-card")).to_have_count(self.asset_count)

    def test_intersecting_triangles_use_per_pixel_depth(self):
        samples = self.page.evaluate("""() => {
            const canvas = document.createElement('canvas'); canvas.width=256; canvas.height=256;
            const data = {
                vertices: [[-.4,.4,-.3],[.4,-.4,-.3],[0,0,.4],[-.4,-.4,-.3],[.4,.4,-.3],[0,0,.4]],
                faces: [[0,1,2],[3,4,5]], normals: [[0,1,0],[0,1,0]], colors: [[255,0,0,255],[0,0,255,255]]
            };
            const view = {data,yaw:0,pitch:0,zoom:1};
            const context = canvas.getContext('2d'); drawModel(view,context,256,256);
            const left = [...context.getImageData(95,150,1,1).data];
            const right = [...context.getImageData(160,150,1,1).data];
            modelRenderer.gl.deleteBuffer(view.buffer);
            return {left,right};
        }""")
        self.assertGreater(samples["left"][0], samples["left"][2] + 100)
        self.assertGreater(samples["right"][2], samples["right"][0] + 100)

    def test_gallery_without_webgl_keeps_other_categories(self):
        self.page.add_init_script("""(() => {
            const original = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(kind,...args) {
                return kind === 'webgl' ? null : original.call(this,kind,...args);
            };
        })();""")
        self.page.reload(wait_until="networkidle")
        self.expect(self.page.locator(".asset-card")).to_have_count(self.asset_count)
        self.assertTrue(self.page.evaluate("modelRenderer === null"))
        self.page.locator('.filters [data-category="2d"]').click()
        self.expect(self.page.locator(".asset-card")).to_have_count(5)

    def test_mobile_studies_and_review(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.locator("#collection-select").select_option("expansion")
        self.expect(self.page.locator(".asset-card")).to_have_count(8)
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)
        self.page.locator('[data-asset="dialog-panel"] .asset-visual').click()
        self.page.get_by_role("button", name="Test wide 9-slice").click()
        bounds = self.page.locator("#asset-dialog").bounding_box()
        self.assertLessEqual(bounds["x"] + bounds["width"], 390)
        self.page.locator("#close-dialog").click()
        self.page.locator("#quality-review").scroll_into_view_if_needed()
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)


if __name__ == "__main__":
    unittest.main()
