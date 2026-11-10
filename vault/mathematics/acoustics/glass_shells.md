# Glass Shells, Wine Glasses, and Quartz Crystals

Governs the acoustic flexural modes of thin-walled glass vessels, crystal singing bowls, and quartz resonators.

---

## 1. Acoustic Physics & Circumferential Waves

Glass is an isotropic, highly elastic silicate with extraordinarily low internal friction (high mechanical quality factor $Q > 1000$). Vibrations occur primarily as flexural shell deformations along the rim:

Modes are characterized by circumferential wave number $m$ (number of nodal diameters):
- $m = 1$: Rigid body lateral translation (no sound emission).
- $m = 2$: Primary flexural quadrupolar mode (opposite rims oscillate inward/outward as an ellipse).
- $m = 3$: Hexapolar deformation.
- $m = 4$: Octapolar deformation.

For a thin-walled cylindrical or hemispherical glass bowl:
$$\frac{f_m}{f_2} \approx \sqrt{\frac{m^2(m^2-1)^2}{12(m^2+1)}} \implies \frac{f_k}{f_2} \approx [1.000, 2.320, 4.150, 6.700]$$

When excited continuously by friction (e.g. wet finger around a glass rim), the $m=2$ mode is stimulated as an almost pure sinusoidal tone. When struck with a mallet, all inharmonic modes sound simultaneously with very slow decay.

---

## 2. Low-Damping Constants
- $d_1 \approx 2.5 \text{ to } 4.5\text{ s}^{-1}$ (very long sustain)
- $d_2 \approx 5.0 \text{ to } 8.0\text{ s}^{-1}$
- $d_3 \approx 9.0 \text{ to } 14.0\text{ s}^{-1}$

---

## 3. Python Synthesis Recipe

```python
from asset_pipeline import SoundSynthesizer

def synthesize_crystal_singing_bowl(duration: float = 2.0, f0: float = 587.33, seed: int = 7):
    synth = SoundSynthesizer(rate=48000, seed=seed)
    glass = synth.glass_resonator(f0=f0, duration=duration)
    # Glass striker transient tap
    tap = synth.transient_click(duration=duration, decay_rate=140.0)
    samples = glass.samples + 0.12 * tap.samples
    return synth.Sound(samples, rate=48000)
```
