---
name: create-sfx
description: Deep procedural SFX audio synthesis skill. Synthesize physical impacts, UI tones, weapons, footsteps, and ambience using NumPy and SciPy with modal resonance, transient shaping, and -3 dBFS headroom.
---

# Procedural SFX Audio Synthesis

Synthesize game sound effects using physical modal resonance, transient exciters, and psychoacoustic stereo panning via `numpy` and `scipy`. Follow [`create-game-assets`](../create-game-assets/SKILL.md) for the master verification loop.

## Architectural Guidelines

### 1. Physical Modal Synthesis & Exciter Transients
- Model resonant bodies (bells, crystal shells, wooden bars, chimes) as damped sinusoidal mode banks $s(t) = \sum_k A_k \sin(2\pi f_k t) e^{-d_k t}$ excited by a short mallet/clapper strike transient.
- Declare physical constants (`F0_HZ`, modal ratios, `CLICK_HZ`, `CLICK_DECAY`, `HAAS_MS`, `PAN`) at module level and record them in `manifest.json` parameters.

### 2. Headroom, Zero Crossings & Encoding
- Normalize peak amplitude to $-3.0\text{ dBFS}$ headroom (`Sound.export(path, headroom_db=-3.0)`) with forced zero-crossing endpoints ($s[0] = s[-1] = 0$) at $48\text{ kHz}$ 16-bit signed PCM.

### 3. Knowledge Vault References
- **Cast Bronze Bells**: [`vault/mathematics/acoustics/church_bells_bronze.md`](../../vault/mathematics/acoustics/church_bells_bronze.md) (`synth.bell_resonator()`).
- **Glass & Crystal Shells**: [`vault/mathematics/acoustics/glass_shells.md`](../../vault/mathematics/acoustics/glass_shells.md) (`synth.glass_resonator()`).
- **Spatial Haas Panning & Transients**: [`vault/mathematics/acoustics/spatial_haas_and_transients.md`](../../vault/mathematics/acoustics/spatial_haas_and_transients.md) (`spatial_stereo_pan()`, `synth.transient_click()`).
- **Undercut Wood & Tubular Chimes**: [`vault/mathematics/acoustics/undercut_bars_wood.md`](../../vault/mathematics/acoustics/undercut_bars_wood.md) (`synth.wood_resonator()`), [`vault/mathematics/acoustics/tubular_chimes.md`](../../vault/mathematics/acoustics/tubular_chimes.md) (`synth.tubular_chime_resonator()`), [`vault/mathematics/acoustics/uniform_bars_metal.md`](../../vault/mathematics/acoustics/uniform_bars_metal.md).

## Code Example: `SoundSynthesizer`

```python
from asset_pipeline import Sound, SoundSynthesizer, spatial_stereo_pan

def synthesize_chime(duration: float = 1.5, rate: int = 48000, seed: int = 7) -> tuple[Sound, Sound]:
    synth = SoundSynthesizer(rate=rate, seed=seed)
    body = synth.glass_resonator(f0=880.0, duration=duration)
    click = synth.transient_click(duration=duration, decay_rate=110.0)
    mono = Sound(body.samples + 0.20 * click.samples, rate=rate)
    stereo = Sound(spatial_stereo_pan(mono, pan=0.18, haas_delay_ms=4.5), rate=rate)
    return mono, stereo
```

## Domain Acceptance Checks

1. **Measured WAV Validation**: Run `AssetValidator.validate_wav(path)` on **every** exported WAV file (both mono and stereo) to verify $48\text{ kHz}$ sample rate, non-silent finite samples, zero-crossing endpoints, and $\le -3.0\text{ dBFS}$ peak headroom.
