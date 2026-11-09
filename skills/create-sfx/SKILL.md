---
name: create-sfx
description: Deep procedural SFX audio synthesis skill. Synthesize physical impacts, UI tones, weapons, footsteps, and ambience using NumPy and SciPy with modal resonance, transient shaping, and -3 dBFS headroom.
---

# Procedural SFX Audio Synthesis

Synthesize game sound effects using physical modeling, modal resonance, and noise filtering via `numpy` and `scipy`.

## Architectural Guidelines

### 1. Physical Modal Synthesis
- **Resonant Bodies**: Physical objects (metal, wood, crystal, stone) vibrate as a superposition of damped sinusoidal modes:
  $$s(t) = \sum_{k=1}^M A_k \sin(2\pi f_k t) \cdot e^{-d_k t}$$
- **Material Inharmonic Ratios**:
  - **Metal / Bell**: $f_k / f_0 \in [1.0, 2.76, 5.40, 8.90]$, long decay times ($d_k \approx 4\text{--}15\text{ s}^{-1}$).
  - **Glass / Crystal**: $f_k / f_0 \in [1.0, 2.32, 4.15, 6.70]$, very low damping ($d_k \approx 3\text{--}10\text{ s}^{-1}$).
  - **Wood**: $f_k / f_0 \in [1.0, 1.48, 2.15, 3.20]$, high damping ($d_k \approx 25\text{--}60\text{ s}^{-1}$).
  - **Stone / Concrete**: $f_k / f_0 \in [1.0, 1.25, 1.62, 2.10]$, steep decay ($d_k \approx 30\text{--}80\text{ s}^{-1}$).

### 2. Transient Strike & Impact Noise
- Physical strikes require an instantaneous initial excitation: high-pass filtered white noise shaped by an aggressive exponential envelope ($e^{-60t}$ to $e^{-120t}$).
- Mix transient click ($10\text{--}30\%$) with resonant modal body ($70\text{--}90\%$).

### 3. Headroom, DC Offset & Zero Crossings
- **Headroom**: Never normalize to $0\text{ dBFS}$ full scale. Always normalize to $-3.0\text{ dBFS}$ peak headroom to avoid inter-sample clipping on consumer DACs.
- **Zero Crossings**: Always force audio sample endpoints $s[0] = 0$ and $s[-1] = 0$ with micro-ramps to prevent speaker pop artifacts on playback start/stop.
- **Sample Rate & Encoding**: Standardize on 48 kHz, 16-bit signed integer mono PCM (`scipy.io.wavfile.write`). Duration in seconds is $\text{len}(s) / \text{rate}$.

## Code Example: `SoundSynthesizer`

```python
from asset_pipeline import Sound, SoundSynthesizer

def synthesize_metal_strike(duration: float = 0.5, rate: int = 48000, seed: int = 7) -> Sound:
    synth = SoundSynthesizer(rate=rate, seed=seed)
    
    # Metal modal body
    body = synth.modal_resonator(
        duration=duration,
        frequencies=[420.0, 420.0 * 2.76, 420.0 * 5.40],
        decays=[10.0, 16.0, 22.0],
        amplitudes=[1.0, 0.45, 0.20],
    )
    
    # Sharp impact click
    click = synth.transient_click(duration=duration, decay_rate=80.0)
    
    combined = body.samples + 0.35 * click.samples
    return Sound(combined, rate=rate)
```

## Scaffolding & Generation

```sh
# Scaffold a new SFX sound effect:
.venv-code-assets/bin/python -m asset_pipeline new sfx_sound assets/<asset_name>

# Execute generator and produce 48 kHz PCM16 WAV:
cd assets/<asset_name> && python generate.py
```

## Validation & Quality Checklist

1. **Audio Metrics**: Confirm sample rate (48 kHz), mono channel, peak dBFS ($\le -3.0$), and absence of silence/clipping with `AssetValidator.validate_wav(path)`.
2. **DC Offset & Clicks**: Confirm zero DC bias and zero-crossing endpoints.
3. **Playback Audition**: Listen to the generated WAV to verify natural acoustic timbre and decay curve.
