# Cast Bronze Bells and Carillons

Governs the acoustic architecture of western church bells and heavy cast bronze idiophones.

---

## 1. The Five Core Partials of a Church Bell

Unlike strings or straight bars, a bell is a flared, thick-walled 3D axisymmetric shell. Historical bell-founders deliberately profile the bell's waist and soundbow so that the primary structural modes produce specific musical intervals relative to the striking pitch (the **Prime**):

| Mode Name | Nominal Interval | Frequency Ratio ($f_k / f_{\text{prime}}$) | Role in Timbre |
|---|---|---|---|
| **Hum Tone** | Octave below Prime | $0.50$ | Deep resonant foundation; rings the longest |
| **Prime** | Fundamental | $1.00$ | Defines the perceived pitch upon striking |
| **Tierce** | Minor Third | $1.20$ ($6/5$) | Gives bells their melancholic, mysterious color |
| **Quint** | Perfect Fifth | $1.50$ ($3/2$) | Harmonic structural stability |
| **Nominal** | Octave above Prime | $2.00$ ($2/1$) | Bright tap pitch when struck by the clapper |

### Coexistence of Major and Minor Intervals
A bell's iconic, majestic, shimmering sound comes from the deliberate clash between its **minor third (Tierce)** and its **perfect fifth (Quint)**.

---

## 2. Damping Characteristics
- **Hum tone**: Extremely low damping ($d \approx 1.5\text{--}3.0\text{ s}^{-1}$), sustains for seconds.
- **Prime & Tierce**: Low damping ($d \approx 3.5\text{--}6.0\text{ s}^{-1}$).
- **Quint & Nominal**: Moderate damping ($d \approx 7.0\text{--}12.0\text{ s}^{-1}$).

---

## 3. Python Synthesis Recipe

```python
from asset_pipeline import Sound, SoundSynthesizer

def synthesize_temple_bell(duration: float = 3.0, f0: float = 330.0, seed: int = 7) -> Sound:
    synth = SoundSynthesizer(rate=48000, seed=seed)
    bell = synth.bell_resonator(f0=f0, duration=duration)
    # Heavy iron clapper strike
    clapper = synth.transient_click(duration=duration, decay_rate=60.0)
    samples = bell.samples + 0.35 * clapper.samples
    return Sound(samples, rate=48000)
```
