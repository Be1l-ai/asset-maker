# Uniform Free-Free Metal Bars (Glockenspiel, Steel Anvils)

Governs the flexural vibration modes of straight, uniform bars with unsupported ends.

---

## 1. Acoustic Physics & Modal Frequencies

For a uniform thin rectangular or cylindrical bar of length $L$, thickness $h$, Young's modulus $E$, and density $\rho$ undergoing transverse flexural vibrations, the governing Euler-Bernoulli equation is:
$$\frac{\partial^4 y}{\partial x^4} + \frac{\rho A}{E I} \frac{\partial^2 y}{\partial t^2} = 0$$

For free-free boundary conditions ($y'' = y''' = 0$ at $x = 0, L$), the modal eigenvalues $m_k$ are roots of:
$$\cosh(m) \cos(m) = 1 \implies m_1 \approx 4.730, \, m_2 \approx 7.853, \, m_3 \approx 10.996, \, m_4 \approx 14.137$$

The resulting modal frequency ratios relative to fundamental $f_1$:
$$\frac{f_k}{f_1} = \left(\frac{m_k}{m_1}\right)^2$$

$$\frac{f_k}{f_1} = [1.000, 2.757, 5.404, 8.933, 13.345]$$

Notice these are non-integer multiples ($2.757$ is roughly an octave and a diminished fifth), which gives struck steel bars, swords, and anvils their distinctive clanky, inharmonic chime.

---

## 2. Exponential Decay Constants

High partials experience greater internal friction and air damping:
$$d_k = d_1 \cdot \left(\frac{f_k}{f_1}\right)^\gamma, \quad \gamma \approx 0.6 \text{ to } 0.8$$
- Glockenspiel / Steel plate: $d_1 \approx 4.0\text{--}8.0\text{ s}^{-1}$
- Metal anvil impact: $d_1 \approx 15.0\text{--}25.0\text{ s}^{-1}$

---

## 3. Python Synthesis Recipe

```python
from asset_pipeline import SoundSynthesizer

def synthesize_metal_bar(duration: float = 1.0, f0: float = 440.0, seed: int = 7):
    synth = SoundSynthesizer(rate=48000, seed=seed)
    # Euler-Bernoulli ratios
    freqs = [f0 * 1.000, f0 * 2.757, f0 * 5.404, f0 * 8.933]
    decays = [5.0, 10.0, 18.0, 30.0]
    amps = [1.0, 0.45, 0.20, 0.08]

    modal = synth.modal_resonator(duration, freqs, decays, amps)
    click = synth.transient_click(duration, decay_rate=90.0)
    sound = modal.samples + 0.25 * click.samples
    return synth.Sound(sound, rate=48000)
```
