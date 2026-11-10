# Tubular Bells and Hollow Metal Chimes

Governs the acoustics of hollow brass, bronze, and aluminum cylindrical tubes.

---

## 1. Acoustic Physics & Transverse Modes

Unlike solid bars, a hollow cylindrical tube possesses a circular cross section with high geometric moment of inertia relative to mass. In orchestral chimes, the transverse modes follow the modified shell-beam dispersion relation:
$$\frac{f_k}{f_1} = [1.000, 4.200, 9.700, 17.000]$$

Despite the high mathematical inharmonicity between Mode 1 and Mode 2, the human auditory system perceives the virtual strike pitch from the higher frequency clusters (modes 2, 3, and 4), which approximate frequency intervals of $2 : 3 : 4$ relative to an apparent missing fundamental.

---

## 2. Decay Constants

Because hollow tubes have low air drag per unit cross-sectional stiffness:
- $d_1 \approx 3.0 \text{ to } 5.0\text{ s}^{-1}$ (long sustained ring)
- $d_2 \approx 6.0 \text{ to } 9.0\text{ s}^{-1}$
- $d_3 \approx 12.0 \text{ to } 16.0\text{ s}^{-1}$

---

## 3. Python Synthesis Recipe

```python
from asset_pipeline import SoundSynthesizer

def synthesize_tubular_chime(duration: float = 2.0, f0: float = 523.25, seed: int = 7):
    synth = SoundSynthesizer(rate=48000, seed=seed)
    chime = synth.tubular_chime_resonator(f0=f0, duration=duration)
    # Hard phenolic mallet strike
    click = synth.transient_click(duration=duration, decay_rate=80.0)
    samples = chime.samples + 0.30 * click.samples
    return synth.Sound(samples, rate=48000)
```
