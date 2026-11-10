# Undercut Wooden Bars (Marimbas, Xylophones)

Governs the acoustic tuning of carved and undercut wooden resonators.

---

## 1. Acoustic Physics of Undercutting

A uniform wooden bar natively has the inharmonic roots of a metal bar ($1 : 2.76 : 5.40$). In musical instruments such as the rosewood/padauk marimba and xylophone, master makers selectively carve an arch out of the underside (undercutting).

Because the middle of the bar contains the antinode of the fundamental flexural mode, removing mass from the center lowers the frequency of overtone modes far more aggressively than the fundamental.

### Tuned Ratios
Master tuners shape the underside arch to tune the first overtone to an exact harmonic interval:
- **Marimba tuning**:
  $$\frac{f_k}{f_1} = [1.000, 4.000, 10.000]$$
  Mode 2 is tuned to an exact double octave ($4.0\times$), giving the marimba its warm, resonant, chordal purity.
- **Xylophone tuning**:
  $$\frac{f_k}{f_1} = [1.000, 3.000, 6.000]$$
  Mode 2 is tuned to an octave and a fifth (triple frequency $3.0\times$), giving the xylophone its bright, penetrating, woody cutting timbre.

---

## 2. Wood Damping Constants

Wood exhibits significantly higher internal viscoelastic damping than metal or glass:
$$d_1 \approx 25.0 \text{ to } 50.0\text{ s}^{-1}$$
Higher modes decay almost instantaneously ($d_2 \approx 60.0\text{ s}^{-1}$, $d_3 \approx 100.0\text{ s}^{-1}$).

---

## 3. Python Synthesis Recipe

```python
from asset_pipeline import SoundSynthesizer

def synthesize_marimba_strike(duration: float = 0.5, f0: float = 261.63, seed: int = 7):
    synth = SoundSynthesizer(rate=48000, seed=seed)
    # Marimba double-octave undercut tuning
    sound = synth.wood_resonator(f0=f0, duration=duration)
    # Soft felt mallet transient strike
    mallet = synth.transient_click(duration=duration, decay_rate=120.0)
    combined = sound.samples + 0.15 * mallet.samples
    return synth.Sound(combined, rate=48000)
```
