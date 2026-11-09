# AssetMaking / fx_pipeline — Notes & Progress Log

Project: Roblox FX asset pipeline (procedural SFX + flipbook VFX).
Goal of this file: record every generation, what was good/bad, and the exact
current state, so future sessions can progress without repeating mistakes.
Updated: 2026-08-20.

---

## 1 · Current state (as of 2026-08-20 22:40)

| Area | State | Code provenance |
|---|---|---|
| `generate_sfx.py` | **FIRST GENERATION** recipe (4 sounds) | DB replay of 16:26:10 write + 16:26:39 edit |
| `helpers/audio_natural_helpers.py` | **FIRST GENERATION** (gen-1, 11390 B) | DB replay of 16:25:26 write + edits ≤16:28:25 |
| `helpers/audio_helpers.py` | untouched since 15:18 (pre-gen-1 copy) | as-is on disk |
| `generate_flipbooks.py` | 17:27–17:28 era (styles table, 11 sheets) | untouched by revert session |
| `helpers/flipbook_effects.py` | 17:27:26 era (rich fireball/lightning) | DB replay (14577 B) |
| `helpers/artstyles.py` | never touched (16:18–17:27 writes) | as-is on disk |
| `output/sfx/` | gen-1 renders (4 files) + 2 stale files | see §5 |
| `output/flipbooks/` | 11 sheets, deterministic | see §5 fingerprints |
| `helpers/fx_engine.py` | DEAD CODE (11530 B, created 21:02 in overhaul attempt) | keep or delete — unused |

### Known-good fingerprints (verify renders against these)

SFX (gen-1, stereo 44.1 kHz; peaks vary ±0.5% — pyo noise is unseeded, see §5):

| file | size | dur | peak | tail>300 |
|---|---|---|---|---|
| wind.wav | 529452 | 3.0012s | ~4080 | ~2.97s |
| explosion.wav | 600108 | 3.4017s | ~23197 | ~3.4s |
| glass_break.wav | 458796 | 2.6006s | ~16220 | ~0.58s |
| forest.wav | 882732 | 5.0039s | ~6461 | ~5.0s |

Flipbooks (512×512, md5 deterministic):

- dust_cel 2801f6c09d3b8139 · dust_neon 6d81cdd2bf83ebc2 · dust_painterly 613e846b8331b868
- fireball_cel a8c9c8acd162cfc6 · fireball_neon 6f99cc7e971a77c2 · fireball_painterly d6b338d054cbc38e
- lightning_cel 6447d921d106ae52 · lightning_neon fbf8ac06800aaebe
- waterfall_cel 904977daa7fd820c · waterfall_neon dd36153b91b1683c · waterfall_painterly 3bdf1685813c646a

---

## 2 · Generation history (SFX)

| Gen | When | What changed | Verdict that matters |
|---|---|---|---|
| 1 | 16:25–16:29 | `audio_natural_helpers.py` 11250 B ("natural-sounding"), `generate_sfx.py` 4 sounds: wind 3.0s, explosion 3.4s, **glass_break 2.6s** (9× `modal_body` tings + grains), forest 5.0s. `air_noise` = Reson bandpass. `naturalize()` via `mix_and_out(**space_kwargs)` with `haas_ms`/`pan_center`. Headroom -3 dB. First render ~16:29 (glass_break.wav 458796 preserved as reference). | **THE ONE THE USER WANTS BACK** (reverted here 22:38). Quiet ambient character (wind peak ~4k), tings not pings. |
| 2 | 17:04–17:10 | Full rewrite "studio-grade": `wander_cv` v1 (sum of incommensurate sines) then v2 (unseeded `Noise` → `ButLP` @~0.7 Hz + boost gain 2.5–4.0), `tink_ping`/`tink_burst` (sine pings), non-attenuating `normalize_wav` rewrite... | Wander v2 docstring idea was right ("no fixed sine period"), but user later judged the whole era as the wrong direction for SFX. |
| 3 | 17:11–17:23 | glass "cascade" idea reverted (16+8 ping bursts), forest re-tuning, `studio_chain` (mud_cut/air/drive…) replaces `naturalize`; `glass_chime`, `glass_shatter` recipes. 17:24 renders praised at the time (wind peak ~1722). | Best of the later era, but user's final call: revert to gen-1 anyway. |
| 4 | 20:40–21:30 (this assistant) | Overhaul: glass 3-wave cascade, `_actor_cycle`/`_flame_lick` VFX, `fx_engine.py`. User: **"everything just got worst"**. | Full revert to gen-3 era, then per user → gen-1 for SFX. |

### Flipbook generations (VFX)

| Gen | When | Change | Verdict |
|---|---|---|---|
| 0 | 16:20–16:29 | Original helpers write + fireball/lightning hardcoded styles, 11-sheet runner | – |
| 1 | 17:27–17:28 | Rich frames: `_flame_lick` loops, `progress_ease`, `_bolt_path`, `build_flipbook(background=)` + style table | **CURRENT ON DISK** — user did not ask to revert these. |
| 2 | 20:53–21:26 (this assistant) | `_actor_cycle`, fx_engine-driven pilot, exp-based bolt | Reverted (was part of "worst"). |

---

## 3 · Good / bad lessons (IMPORTANT — read before rendering)

### Good to keep
- Seed-driven deterministic VFX (PIL + `random.Random(seed)`) → byte-reproducible outputs; store md5s.
- Parallel structure generic → thin recipes on top of helpers. Keep it.
- When in doubt, verify with size + peak + tail-position fingerprints, not just "PASS".
- Everything code-related is recoverable byte-exact from the opencode DB replay (see §4) — snapshots at `~/.local/share/opencode/snapshot/` are STALE (old project tree; `session_diff/*.json` empty). ALWAYS use DB replay, never restore "from memory".

### Bad / pitfalls
- **`pyo.Noise()` is UNSEEDED** in this pyo version → every SFX render differs in content; peaks vary ~±0.5% run-to-run even with identical code. Sizes are content-independent (fixed dur/rate) so sizes matching ≠ identical audio. Only seed-independent character is reproducible. Never promise byte-identical SFX.
- **pyo API on this box:** `Noise(mul=1, add=0)` — NO `seed` kwarg, and the first positional IS `mul` (`Noise(rng.randint(...), mul=1.0)` → TypeError). Don't try to seed it.
- Rendered WAVs are **stereo 44.1 kHz** — any verify script must divide time by channel count and use the real rate; a mono-22050 assumption produced phantom "14s of noise" readings.
- `normalize_wav` in gen-1 is attenuate-only with -3 dB headroom (quiet ambiences must NOT be boosted). If a render's peak = 32767·10^(db/20) exactly, the render itself was hot — investigate the recipe, don't "fix" the normalizer.
- Don't "improve" what was praised until the praise has been quantified to a file (fingerprint). "Sounds nice" without a fingerprint cannot be re-targeted later.

---

## 4 · Recovery recipe (how to resurrect any previous generation)

The opencode DB stores EVERY full write and edit verbatim:
`~/.local/share/opencode/opencode.db` — table `part`, column `data` = JSON
`{type, tool, state.input}` where input has either `content` (full write) or
`oldString`/`newString` (edit). Each row has `time_created` (ms epoch).

To rebuild generation G of file F:
1. Find F's last full `content` write BEFORE G's edits → base.
2. Apply every `oldString`→`newString` edit with timestamp between base write and the generation cutoff, in order (assert each `oldString` is found).
3. `diff` against disk; never hand-retype.

Existing reconstruction artifacts in `/tmp/opencode/`:
- `gen1_audio_natural_helpers.py`, `gen1_generate_sfx.py` (SFX gen-1)
- `presession_audio_natural_helpers.py`, `presession_generate_sfx.py`, `presession_flipbook_effects.py`, `presession_generate_flipbooks.py` (17:23–17:28 era)
- `orig_helpers.py` (17:04 "studio-grade" rewrite v1)
- `reference_glass_break_1629.wav` (first-generation render, back-up)

---

## 5 · Outstanding / next steps

- [ ] Listen to gen-1 wind / explosion / glass_break / forest and confirm "yes, this is the one" — then STOP rewriting and lock fingerprints in §1.
- [x] Decide fate of stale `output/sfx/glass_shatter.wav` + `glass_chime.wav` (17:24-era outputs, not in gen-1 recipe) — deleted during repo cleanup.
- [x] Decide fate of dead `helpers/fx_engine.py` (create_at 21:02, unused) — deleted during repo cleanup.
- [ ] Add whichever of these fingerprints the user listens to and approves; keep notes updated with EVERY subsequent generation.

---

## 6 · Code-only skill foundation (2026-11-06)

Keep the historical generators and outputs above unchanged. New asset work has a separate Python 3.12+ environment and project-local agent skills:

- [create-game-assets](skills/create-game-assets/SKILL.md): shared source-study, reproducibility, and validation workflow.
- [create-sfx](skills/create-sfx/SKILL.md): NumPy/SciPy synthesis and measured WAV exports.
- [create-vfx](skills/create-vfx/SKILL.md): periodic fields, transparent atlases, and animation previews.
- [create-3d-assets](skills/create-3d-assets/SKILL.md): Trimesh/Manifold solids, GLB/OBJ, and headless previews.
- [create-2d-assets](skills/create-2d-assets/SKILL.md): Pillow/aggdraw paths, masks, and RGBA exports.

Read the [GitHub library catalog](skills/create-game-assets/references/libraries.md) for verified upstreams, licenses, source maps, and optional-library limitations. The skills require studying APIs and composing new recipes, not just generating preset variants.

```sh
python3 -m venv .venv-code-assets
.venv-code-assets/bin/python -m pip install -r requirements-code-assets.txt
.venv-code-assets/bin/python -m unittest discover -s tests -v
```

Invoke `/create-game-assets` or a specialist skill; restart the agent session if the project skills are not visible. Executable starter commands are in each skill. Use new output directories: starters reject existing destinations and save the recipe, parameters, versions, and hashes alongside assets. Example renders live under `fx_pipeline/output/code_examples/`; they are API/structural demonstrations, not approved replacements for earlier assets. Review their manifests for generation fingerprints.

No authoring applications, hosted generation, recorded samples, UV unwrapping, rigging, or automatic engine integration are included. Structural validation is not an artistic-quality assessment; audio listening and target-engine acceptance remain separate review steps.