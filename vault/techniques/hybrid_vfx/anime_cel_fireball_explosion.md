# Anime Cel-Shaded Fireball Explosion (Hybrid 3D + Flipbook + Synced SFX)

Sakuga-inspired real-time anime explosions combine **animated billowing 3D cel-shaded volumes**, **hard-edged 2D impact starbursts/smears**, and **frame-locked low-end detonation SFX**.

## 1. Visual Language (Hard-Stepped Color Ramp & Yutapon Debris)
* **4-Band Cel Fire Ramp**: Blinding white-yellow core (`#FFFCE0`) -> golden mid-flame (`#FFBE24`) -> vermilion outer flame (`#F04A18`) -> deep crimson-charcoal smoke (`#321822`) framed by crisp dark ink outlines.
* **Frame-2 Impact Flash**: Include a stark, high-contrast 1-frame starburst flash at peak detonation (`t = 0.150 s`, Frame 2) paired with a sharp camera jolt.
* **Billowing Pyroclastic 3D Volumes + Yutapon Cubes**: Animate overlapping sculpted billowing cloud spheres rising into a mushroom silhouette while angular faceted rock cubes launch along parabolic gravity arcs.

## 2. Shared 4-Stage Timeline (1.20 s / 16 Frames @ 75 ms/frame)
* **Stage 1 (`0.00–0.15 s`, Frames 0–1)**: Descending blazing fireball comet + intake swoosh audio.
* **Stage 2 (`0.15–0.375 s`, Frames 2–4)**: Impact starburst flash + expanding tilted shockwave rings + blinding core expansion. Audio: razor-sharp ignition transient + sub-bass chest drop (`110 -> 28 Hz`).
* **Stage 3 (`0.375–0.75 s`, Frames 5–9)**: Billowing orange-crimson mushroom fire clouds + flying Yutapon debris cubes + rising ember streaks. Audio: roaring mid-low flame blast + rolling stereo rumble.
* **Stage 4 (`0.75–1.20 s`, Frames 10–15)**: Dark billowing cel-shaded smoke plume cooling & dissipating cleanly over glowing crater embers. Audio: smooth exponential flame-tail decay (`-1.0 dBFS` peak, `30 Hz` HPF).
