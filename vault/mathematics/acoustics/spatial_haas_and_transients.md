# Spatial Stereo Panning, Haas Precedence, and Mallet Strike Transients

Mathematical formulations for constant-power stereo panning, psychoacoustic interaural time delay (Haas precedence effect), and physical mallet impact exciter transients (`assets/crystal_bell_chime_v2`).

---

## 1. Constant-Power Sine/Cosine Panning Law

Linear stereo panning ($L = 1 - p, R = p$) produces a $-3\text{ dB}$ acoustic power dip at center pan ($p = 0.5$) because incoherent acoustic intensity sums as $L^2 + R^2$. To preserve constant perceived loudness across the stereo field for pan parameter $p \in [-1, 1]$:

$$\theta(p) = \frac{\pi}{4}(p + 1) \in \left[0, \frac{\pi}{2}\right]$$

$$g_L(p) = \cos\theta(p), \quad g_R(p) = \sin\theta(p), \quad g_L^2(p) + g_R^2(p) = 1$$

At center pan ($p = 0, \theta = \pi/4$), both channels receive $g_L = g_R = \frac{\sqrt{2}}{2} \approx 0.7071$ ($-3.01\text{ dB}$).

---

## 2. The Psychoacoustic Haas Precedence Effect

By **Helmut Haas's (1951)** auditory precedence effect, when two identical or strongly correlated wavefronts arrive at the listener's ears within the **fusion window** $\Delta t \in [1\text{ ms}, 30\text{ ms}]$:
1. The auditory cortex fuses the two arrivals into a **single perceptual event** (no discrete echo is heard below $\sim 30\text{ ms}$ for percussive clicks or $\sim 40\text{ ms}$ for sustained chimes).
2. Directional localization is dominated by the **leading (earliest) ear**, while the delayed arrival expands perceived room width and acoustic envelopment.

Given sample rate $f_s$ and interaural Haas delay $\tau_{\text{haas}} \in [0.001, 0.015]\text{ s}$ ($N_d = \lfloor \tau_{\text{haas}} \cdot f_s \rfloor$ samples):
- For right-panned sources ($p > 0$), the left channel is delayed by $N_d$ samples:
  $$L[n] = g_L(p)\,x[n - N_d], \quad R[n] = g_R(p)\,x[n]$$
- For left-panned sources ($p < 0$), the right channel is delayed by $N_d$ samples:
  $$L[n] = g_L(p)\,x[n], \quad R[n] = g_R(p)\,x[n - N_d]$$

| Haas Delay $\tau_{\text{haas}}$ | Samples at $44.1\text{ kHz}$ | Psychoacoustic Perceptual Effect |
| :--- | :--- | :--- |
| $0.1\text{--}0.7\text{ ms}$ | $4\text{--}31$ samples | Pure Interaural Time Difference (ITD) lateralization |
| $1.5\text{--}8.0\text{ ms}$ | $66\text{--}353$ samples | Tight studio stereo widening for bells, UI chimes, and impacts |
| $8.0\text{--}18.0\text{ ms}$ | $353\text{--}794$ samples | Spacious reverberant sanctuary / hall width without slapback |

---

## 3. Mallet & Clapper Strike Exciter Transients

In physical modeling synthesis (Chaigne & Doutaut, 1997), a resonant modal bank requires an initial mechanical impulse transfer function representing the hardness of the striker:

$$x_{\text{strike}}(t) = A_{\text{click}} \sin(2\pi f_{\text{click}} t)\,e^{-t / \tau_{\text{click}}} + A_{\text{noise}} \,\eta_{\text{BP}}(t)\,e^{-t / \tau_{\text{noise}}}$$

- **Hard Glass / Metal Striker** (`crystal_bell_chime_v2`): High carrier frequency $f_{\text{click}} \in [3000, 4800]\text{ Hz}$ with ultra-fast decay rate $1/\tau_{\text{click}} \in [120, 220]\text{ s}^{-1}$ ($\tau_{\text{click}} \approx 4.5\text{--}8\text{ ms}$), exciting upper overtones cleanly.
- **Soft Felt / Wood Mallet**: Lower carrier $f_{\text{click}} \in [600, 1400]\text{ Hz}$ with broader impulse duration $\tau_{\text{click}} \approx 12\text{--}20\text{ ms}$, acting as a low-pass filter on high partials.

---

## 4. Python Usage in `asset_pipeline`

```python
import numpy as np
from asset_pipeline import Sound, SoundSynthesizer, spatial_stereo_pan

synth = SoundSynthesizer(rate=48000, seed=42)
t = synth.time_vector(2.5)

# 1. Synthesize high-register crystal bell + hard mallet strike transient
bell = synth.glass_resonator(f0=1046.5, duration=2.5)
transient = 0.22 * np.sin(2.0 * np.pi * 3800.0 * t) * np.exp(-t * 160.0)
mono_sound = Sound(bell.samples + transient, rate=48000).normalize(headroom_db=-3.0)

# 2. Apply constant-power stereo pan with 4.2 ms Haas precedence widening
stereo_field = spatial_stereo_pan(
    sound=mono_sound,
    pan=0.18,
    haas_delay_ms=4.2,
)
```

---

## 5. References
- Haas, H. (1951). *Über den Einfluss eines Einfachechos auf die Hörsamkeit von Sprache* (On the Influence of a Single Echo on the Intelligibility of Speech). Acustica, 1(2), 49–58.
- Litovsky, R. Y., Colburn, H. S., Yost, W. A., & Guzman, S. J. (1999). *The Precedence Effect*. Journal of the Acoustical Society of America, 106(4), 1633–1654.
- Chaigne, A., & Doutaut, V. (1997). *Numerical Simulations of Xylophones. I. Time-Domain Modeling of the Vibrating Bars and Mallet Contact*. Journal of the Acoustical Society of America, 101(1), 539–557.
