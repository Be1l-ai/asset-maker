"""Seeded straight-alpha effects and mono PCM16 sounds without recordings or simulation engines."""
from __future__ import annotations

from numbers import Integral

import numpy as np
from PIL import Image
from scipy import signal

__all__ = ["dust_puff_frame", "lightning_frame", "gravel_step", "charge_release", "RECIPES"]


def _smooth(value):
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def _grid(size, phase):
    if isinstance(size, bool) or not isinstance(size, Integral) or size < 16:
        raise ValueError("size must be an integer >=16")
    if not np.isfinite(phase) or not 0 <= phase <= 1:
        raise ValueError("phase must be finite and in [0, 1]")
    axis = (np.arange(size, dtype=np.float64) + .5) * 2 / size - 1
    return np.meshgrid(axis, axis, indexing="xy")


def _rgba(rgb, alpha, x, y):
    # Fade before the image boundary; force border zero even at small sizes.
    edge = _smooth((.94 - np.maximum(np.abs(x), np.abs(y))) / .08)
    alpha = np.clip(alpha, 0, 1) * edge
    alpha[[0, -1], :] = 0
    alpha[:, [0, -1]] = 0
    rgba = np.rint(np.dstack([np.clip(rgb, 0, 255), alpha * 255])).astype(np.uint8)
    rgba[rgba[..., 3] == 0] = 0
    return Image.fromarray(rgba)


def dust_puff_frame(size, phase, seed=19) -> Image.Image:
    """Asymmetric pigment billows with fixed identities, rapid expansion, and a settling tail."""
    x, y = _grid(size, phase)
    if phase == 0 or phase == 1:
        return Image.new("RGBA", (size, size))
    rng = np.random.default_rng(seed)
    premult = np.zeros((*x.shape, 3))
    alpha = np.zeros_like(x)
    # Rear/high lobes first, then the low spreading foreground billows.
    lobes = [(-.22, .40, .25, .24), (.03, .59, .26, .28),
             (.30, .45, .25, .25), (-.45, .21, .24, .20),
             (.46, .22, .24, .19), (-.15, .11, .29, .19),
             (.20, .14, .28, .19)]
    for index, (offset, rise, rx, ry) in enumerate(lobes):
        jitter = rng.uniform(-.025, .025, 2)
        angle, drift, speed = rng.uniform(-.35, .35), rng.uniform(.025, .075), rng.uniform(.85, 1.15)
        waves = rng.uniform(0, 2 * np.pi, 4)
        spread = 1 - np.exp(-8 * phase * speed)
        scale = .23 + .77 * spread + .15 * phase
        cx = (offset + jitter[0]) * spread + drift * phase
        cy = .43 - (rise + jitter[1]) * spread + .14 * phase ** 2
        u, v = (x - cx) / (rx * scale), (y - cy) / (ry * scale)
        roll = angle + (-1 if index % 2 else 1) * .85 * phase
        u, v = np.cos(roll) * u - np.sin(roll) * v, np.sin(roll) * u + np.cos(roll) * v
        # Smooth, material-space domain warp: features roll with each billow.
        u = u + .10 * np.sin(2.4 * v + waves[0])
        v = v + .09 * np.sin(2.7 * u + waves[1])
        field = (.55 * np.sin(3.1 * u + 2.3 * v + waves[0])
                 + .27 * np.sin(5.8 * u - 4.2 * v + waves[1])
                 + .12 * np.sin(10.1 * u + 7.6 * v + waves[2])
                 + .06 * np.sin(18.3 * u - 12.1 * v + waves[3]))
        theta = np.arctan2(v, u)
        radius = np.hypot(u, v) + .07 * np.sin(3 * theta + waves[2]) + .045 * field
        density = _smooth((1.18 - radius) / .43) * (.84 + .16 * field)
        envelope = _smooth(phase / .095) * (1 - phase) ** 1.45 * np.exp(-.35 * phase)
        opacity = .83 * envelope * density
        # Diffuse pigment shading, not additive/emissive edges.
        shade = np.clip(.58 - .13 * u - .23 * v + .19 * field, 0, 1)[..., None]
        rgb = np.array([104., 87., 67.]) * (1 - shade) + np.array([211., 193., 161.]) * shade
        premult = rgb * opacity[..., None] + premult * (1 - opacity[..., None])
        alpha = opacity + alpha * (1 - opacity)
    rgb = np.divide(premult, alpha[..., None], out=np.zeros_like(premult), where=alpha[..., None] > 0)
    return _rgba(rgb, alpha, x, y)


def _bolt_paths(seed):
    """Stable connected trunk, five forks, and three secondary twigs."""
    rng = np.random.default_rng(seed)
    ys = np.linspace(-.77, .72, 15)
    xs = .09 * np.sin(np.arange(15) * 1.6) + rng.uniform(-.10, .10, 15)
    xs[[0, -1]] = [-.07, .04]
    trunk = np.column_stack([xs, ys])
    paths = [(trunk, .010, 1.0)]
    for index, node in enumerate((3, 5, 7, 9, 11)):
        start = trunk[node]
        side = -1 if index % 2 == 0 else 1
        end = np.array([side * rng.uniform(.40, .59), min(.76, start[1] + rng.uniform(.18, .31))])
        branch = start + np.linspace(0, 1, 5)[:, None] * (end - start)
        branch[1:-1] += rng.uniform(-.035, .035, (3, 2))
        paths.append((branch, .0065, .64))
        if index in (0, 1, 3):
            twig_start = branch[2]
            twig_end = twig_start + [-side * .04, .18]
            twig = np.array([twig_start, (twig_start + twig_end) / 2 + [side * .04, -.015], twig_end])
            paths.append((twig, .004, .36))
    return paths


def _stroke_distance(x, y, points):
    distance2 = np.full_like(x, np.inf)
    for start, end in zip(points[:-1], points[1:]):
        dx, dy = end - start
        along = np.clip(((x - start[0]) * dx + (y - start[1]) * dy) / (dx * dx + dy * dy), 0, 1)
        candidate = (x - start[0] - along * dx) ** 2 + (y - start[1] - along * dy) ** 2
        distance2 = np.minimum(distance2, candidate)
    return distance2


def lightning_frame(size, phase, seed=19) -> Image.Image:
    """Fixed forks re-strike twice, with faint residual channels between flashes."""
    x, y = _grid(size, phase)
    if phase == 0 or phase == 1:
        return Image.new("RGBA", (size, size))
    pulse = (np.exp(-((phase - .10) / .051) ** 2)
             + .88 * np.exp(-((phase - .33) / .025) ** 2)
             + .70 * np.exp(-((phase - .535) / .021) ** 2))
    onset = _smooth(phase / .035)
    residual = .08 * np.exp(-1.8 * phase) * (1 - phase) ** .4
    core, halo = np.zeros_like(x), np.zeros_like(x)
    for points, width, strength in _bolt_paths(seed):
        distance2 = _stroke_distance(x, y, points)
        # Pixel-aware analytic coverage; no RGBA resizing/fringes.
        core_width = np.hypot(width, .45 / size)
        core = np.maximum(core, strength * np.exp(-distance2 / core_width ** 2))
        halo = np.maximum(halo, strength * (.74 * np.exp(-distance2 / .029 ** 2)
                                           + .26 * np.exp(-distance2 / .070 ** 2)))
    white = onset * (pulse + residual) * core
    cyan = onset * (.39 * pulse + .055 * np.exp(-3 * phase) * (1 - phase) ** .5) * halo
    alpha = 1 - np.exp(-2.4 * (white + cyan))
    hot = np.divide(white, white + cyan, out=np.zeros_like(white), where=white + cyan > 0)[..., None]
    rgb = np.array([44., 158., 239.]) * (1 - hot) + np.array([232., 253., 255.]) * hot
    return _rgba(rgb, alpha, x, y)


def _time(duration, rate):
    if isinstance(rate, bool) or not isinstance(rate, Integral) or rate < 16000:
        raise ValueError("rate must be an integer >=16000 Hz")
    return np.arange(round(duration * rate), dtype=np.float64) / rate


def _noise(rng, count, rate, low, high):
    # Hz cutoffs always stay below Nyquist; padding removes filter startup bias.
    sos = signal.butter(2, [low, min(high, .43 * rate)], btype="bandpass", fs=rate, output="sos")
    padding = round(.05 * rate)
    return signal.sosfilt(sos, rng.standard_normal(count + padding), axis=0)[padding:]


def _event(t, onset, attack, decay):
    age = np.maximum(t - onset, 0)
    return -np.expm1(-age / attack) * np.exp(-age / decay)


def _pcm(samples, rate, fade_in, fade_out):
    """Smooth boundaries, remove weighted DC, attenuate only, quantize safely."""
    fade = np.ones_like(samples)
    ni, no = round(fade_in * rate), round(fade_out * rate)
    fade[:ni] = _smooth(np.linspace(0, 1, ni))
    fade[-no:] = _smooth(np.linspace(1, 0, no))
    # Weighted centering preserves both zero mean and the faded endpoints.
    samples = (samples - np.sum(samples * fade) / np.sum(fade)) * fade
    peak = np.max(np.abs(samples))
    ceiling = 10 ** (-3 / 20)
    samples *= min(1.0, ceiling / peak) if peak else 1.0
    return np.rint(samples * 32767).astype(np.int16)


def gravel_step(seed=19, rate=48000) -> np.ndarray:
    """One 0.55s footfall composed of filtered heel/sole noise and thirty grit grains."""
    t = _time(.55, rate)
    rng = np.random.default_rng(seed)
    heel = _noise(rng, len(t), rate, 45, 235)
    sole = _noise(rng, len(t), rate, 180, 1100)
    grit = _noise(rng, len(t), rate, 1300, 9500)
    samples = 2.7 * heel * _event(t, .009, .0035, .034)
    samples += .68 * sole * _event(t, .034, .007, .060)
    samples += .34 * grit * _event(t, .022, .006, .092)
    # Overlapping tiny contacts within ONE footfall, not repeated thumps.
    for _ in range(30):
        onset = .025 + .36 * rng.beta(1.4, 3.8)
        duration = rng.uniform(.005, .021)
        begin, length = round(onset * rate), round(duration * rate)
        grain = _noise(rng, length, rate, rng.uniform(650, 1800), rng.uniform(5800, 10500))
        window = np.sin(np.linspace(0, np.pi, length)) ** 2
        gain = rng.uniform(.10, .28) * np.exp(-onset / .24)
        samples[begin:begin + length] += gain * grain * window
    return _pcm(samples, rate, .004, .075)


def charge_release(seed=19, rate=48000) -> np.ndarray:
    """A 1.40s integrated sweep anticipates a broadband discharge at 0.94s."""
    t = _time(1.40, rate)
    rng = np.random.default_rng(seed)
    progress = np.clip(t / .94, 0, 1)
    frequency = 145 * (2100 / 145) ** progress
    # Integrate instantaneous Hz: f(t)*t would create the wrong sweep.
    angle = 2 * np.pi * np.cumsum(frequency) / rate
    envelope = _smooth(t / .075) * _smooth((.972 - t) / .065) * (.10 + .90 * progress ** 1.7)
    sweep = .23 * np.sin(angle) + .045 * np.sin(2.013 * angle + .4)
    low_air = _noise(rng, len(t), rate, 250, 2100)
    high_air = _noise(rng, len(t), rate, 2700, 9500)
    samples = envelope * (sweep + .12 * (1 - progress) * low_air + .19 * progress ** 2 * high_air)
    release = .79 * _noise(rng, len(t), rate, 130, 11500) * _event(t, .94, .0018, .050)
    release += 1.75 * _noise(rng, len(t), rate, 48, 330) * _event(t, .941, .004, .072)
    release += .23 * _noise(rng, len(t), rate, 900, 6800) * _event(t, .95, .010, .135)
    samples += release
    # Sparse low-level reflections are only a synthetic tail, not room reverb.
    for delay, gain in ((.021, .16), (.047, .095), (.083, .055)):
        shift = round(delay * rate)
        samples[shift:] += release[:-shift] * gain
    return _pcm(samples, rate, .012, .080)


RECIPES = {
    "dust-puff": {
        "name": "Settling Sand",
        "description": "Seven overlapping warm, desaturated billows expand quickly, roll asymmetrically and settle into a dissipating tail.",
        "tags": ["dust", "sand", "billows", "one-shot", "alpha"],
        "parameters": {"seed": 19, "frame_size": 128, "frames": 16, "columns": 4,
                       "fps": 16, "loop": False, "billows": 7, "blend": "alpha",
                       "phase_sampling": "i/15; transparent endpoints", "duration_seconds": 1.0},
        "review": "Stylized 2D pigment fields, not fluid dynamics. Overlapping lobes can look soft or sculpted rather than turbulent. No ground collision or depth sorting against a scene; light backgrounds reduce tail contrast. Scene compositing and target-engine review remain pending."
    },
    "forked-lightning": {
        "name": "Forked Discharge",
        "description": "A cyan-white vertical trunk and connected forks flash, re-strike twice along stable paths, then leave a faint afterglow.",
        "tags": ["lightning", "branching", "cyan", "one-shot"],
        "parameters": {"seed": 19, "frame_size": 128, "frames": 16, "columns": 4,
                       "fps": 16, "loop": False, "forks": 5, "secondary_twigs": 3,
                       "pulse_phases": [.10, .33, .535], "duration_seconds": 1.0,
                       "phase_sampling": "i/15; transparent endpoints",
                       "blend": "alpha; additive optional"},
        "review": "Stylized fixed polyline topology, not dielectric breakdown. Faint residual channels intentionally keep interior frames nonempty; late frames may be nearly invisible on light backgrounds. 16 FPS undersamples fast flashes; additive blend and engine timing need review."
    },
    "gravel-step": {
        "name": "Gravel Contact",
        "description": "One compact noise-based heel/thump under an overlapping sole crunch and thirty short grit grains.",
        "tags": ["footstep", "gravel", "filtered-noise", "mono", "one-shot"],
        "parameters": {"seed": 19, "rate": 48000, "duration_seconds": .55,
                       "channels": 1, "encoding": "PCM16", "grains": 30,
                       "peak_ceiling_dbfs": -3, "gain_policy": "attenuate only",
                       "fade_in_seconds": .004, "fade_out_seconds": .075},
        "review": "Mathematical synthesis with no recorded surfaces or resonant stone model. Filtered grains may read as generic crunch or static; footwear, weight and gravel scale need listening review. Mono, no spatial acoustics. No listening or target-engine review performed."
    },
    "charge-release": {
        "name": "Gather and Release",
        "description": "A rising integrated-frequency charge and brightening noise anticipate a late broadband discharge with a short synthetic tail.",
        "tags": ["charge", "release", "sweep", "sci-fi", "mono"],
        "parameters": {"seed": 19, "rate": 48000, "duration_seconds": 1.4,
                       "channels": 1, "encoding": "PCM16", "sweep_hz": [145, 2100],
                       "release_seconds": .94, "peak_ceiling_dbfs": -3,
                       "gain_policy": "attenuate only", "fade_in_seconds": .012,
                       "fade_out_seconds": .080},
        "review": "Designed sci-fi signal, not realistic electricity. Anticipation is intentionally tonal; the release can sound like filtered noise rather than a physical blast. Sparse delayed copies are not a room simulation. No listening or target-engine review performed."
    }
}
