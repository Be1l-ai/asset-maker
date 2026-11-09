#!/usr/bin/env python3
"""
generate_sfx.py — render natural-sounding procedural SFX with the
nature-helpers toolkit. Demos: wind, explosion, breaking glass, forest.

Outputs normalized 16-bit WAVs into output/sfx/. Uses a shared pyo offline
server, one room per sound via naturalize().
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers.audio_helpers import boot_server, shutdown_server
from helpers import audio_natural_helpers as nah

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "sfx")
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")


# ── Sound recipes (each returns the pyo objects to stop) ─────

def wind(dur=3.0, amp=0.55, seed=7):
    """Gusting wind: deep bed + wandering mid air + faint hiss, one big room."""
    from helpers.audio_natural_helpers import air_noise, grain_cluster, mix_and_out
    objs, sigs = [], []
    o, s = air_noise(140, 2.2, amp, dur, sweep_from=120, sweep_to=170, wobble_rate=0.11)
    objs += o; sigs += s
    o, s = air_noise(620, 7, amp * 0.6, dur, sweep_from=480, sweep_to=760, wobble_rate=0.23)
    objs += o; sigs += s
    o, s = air_noise(2600, 1.4, amp * 0.18, dur, sweep_from=2100, sweep_to=2900, wobble_rate=0.3)
    objs += o; sigs += s
    o, s = grain_cluster(seed, 28, dur * 0.6, (400, 1200), 5, amp * 0.12)
    objs += o; sigs += s
    objs += mix_and_out(sigs, drive=0.03, size=0.7, damp=0.5, verb_mix=0.28,
                        pre_delay_s=0.02, haas_ms=9.0, pan_center=0.5)
    return objs


def explosion(dur=3.4, amp=0.95, seed=13):
    """Sub-boom + noise boom + crack + debris — big hall reverb."""
    from helpers.audio_natural_helpers import (sine_drop, air_noise, transient,
                                               grain_cluster, mix_and_out)
    objs, sigs = [], []
    o, s = sine_drop(120, 32, 1.2, dur, amp, fi=0.0, fo=0.5)
    objs += o; sigs += s
    o, s = air_noise(2600, 3.0, amp * 0.9, dur * 0.9, sweep_from=2600, sweep_to=90,
                     wobble_rate=0.1, fi=0.003, fo=0.4)
    objs += o; sigs += s
    o, s = transient(3400, 10, amp * 0.7, 0.03, offset=0.0)
    objs += o; sigs += s
    o, s = grain_cluster(seed, 36, 1.2, (300, 2200), 6, amp * 0.3)
    objs += o; sigs += s
    objs += mix_and_out(sigs, drive=0.14, size=0.9, damp=0.28, verb_mix=0.5,
                        pre_delay_s=0.0, haas_ms=12.0, pan_center=0.5)
    return objs


def glass_break(dur=2.6, amp=0.75, seed=23):
    """Crack transient + bright inharmonic tings + falling shards."""
    from helpers.audio_natural_helpers import (transient, modal_body, grain_cluster,
                                               mix_and_out)
    objs, sigs = [], []
    o, s = transient(7400, 22, amp * 0.6, 0.025, offset=0.0)
    objs += o; sigs += s
    # bright inharmonic tings across 1.8-7 kHz, staggered micro-timing
    import random
    rng = random.Random(seed)
    for i in range(9):
        f = rng.uniform(1800, 7000)
        o, s = modal_body(f, ((1.0, 1.0), (1.51, 0.5), (2.4, 0.35), (2.93, 0.3)),
                          dur * (0.3 + rng.uniform(0, 0.25)),
                          amp * rng.uniform(0.12, 0.4), seed=seed + i,
                          glide=0.03, offset=rng.uniform(0.0, 0.03))
        objs += o; sigs += s
    o, s = grain_cluster(seed + 1, 40, 0.9, (3000, 7200), 22, amp * 0.25)
    objs += o; sigs += s
    objs += mix_and_out(sigs, drive=0.02, size=0.35, damp=0.4, verb_mix=0.22,
                        pre_delay_s=0.004, haas_ms=5.0, pan_center=0.5)
    return objs


def forest(dur=5.0, amp=0.5, seed=31):
    """Distant wind bed + rustle grains + sparse descending bird warble."""
    from helpers.audio_natural_helpers import (air_noise, grain_cluster, bird_chirp,
                                               mix_and_out)
    objs, sigs = [], []
    o, s = air_noise(220, 2.5, amp, dur, sweep_from=190, sweep_to=250, wobble_rate=0.09)
    objs += o; sigs += s
    o, s = grain_cluster(seed, 46, dur * 0.8, (900, 2400), 4, amp * 0.14)
    objs += o; sigs += s
    import random
    rng = random.Random(seed)
    for i in range(5):
        off = rng.uniform(0.4, dur - 1.2)
        o, s = bird_chirp(seed + i, off, dur=rng.uniform(0.2, 0.35),
                          amp=amp * rng.uniform(0.1, 0.2), base=rng.uniform(2500, 3800))
        objs += o; sigs += s
    objs += mix_and_out(sigs, drive=0.02, size=0.75, damp=0.55, verb_mix=0.35,
                        pre_delay_s=0.03, haas_ms=10.0, pan_center=0.5)
    return objs


SOUNDS = [
    ("wind.wav",          wind,            3.0),
    ("explosion.wav",     explosion,       3.4),
    ("glass_break.wav",   glass_break,     2.6),
    ("forest.wav",        forest,          5.0),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    s = boot_server()
    print(f"Rendering {len(SOUNDS)} SFX -> {OUT}/")
    try:
        for idx, (filename, fn, dur) in enumerate(SOUNDS, 1):
            print(f"[{idx}/{len(SOUNDS)}] {filename}")
            path = os.path.join(OUT, filename)
            nah.render_natural(s, path, dur, fn)
    finally:
        shutdown_server(s)
    print("Done.")


if __name__ == "__main__":
    main()