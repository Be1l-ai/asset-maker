"""
audio_natural_helpers.py — natural-sounding synthesis for game SFX.

Why the old audio_helpers.py sounds "synthetic":
  * single static oscillators (no body/transient/air separation)
  * fixed-frequency tones (no pitch drift / glide / jitter)
  * amplitude only via linear Fader ramps
  * no spatial processing beyond a centered Pan

This module fixes that with the same four-layer recipe every decent foley
designer uses:

  1. TRANSIENT  — tiny resonant noise click that starts the sound (the "hit")
  2. BODY       — inharmonic partial bank with detune + per-partial glide and
                  independent exponential decays
  3. AIR        — resonant/band-passed noise that gives the sound "room"
  4. SPACE      — a naturalize() chain (saturation -> pre-delay -> reverb ->
                  Haas width) that plants the dry synth in real space

Every layer builder returns (objs, sigs): `objs` are pyo objects to stop
after render, `sigs` are mono pyo signals ready to be mixed. The composer then
mixes them and runs one naturalize() chain, so the whole sound shares one
room instead of ten glued reverbs.

No `.out()` is called by the builders — only the composer's final Pan/Mix
outputs. This keeps the naturalize chain clean and lets you rebuild sounds
Urs from JSON-like material presets.

Sample layering: sample_layer() / mix_synth_and_sample() let you place real
recorded audio under the synth layers. If the file is missing they degrade
gracefully (the runner prints a note) instead of crashing.
"""

import os
import random
import struct
import wave

import pyo

from helpers.audio_helpers import env


# ── Rendering + normalization ────────────────────────────────

def normalize_wav(path, headroom_db=-3.0):
    """Scale a generated 16-bit WAV so its peak hits the headroom target."""
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        sw = w.getsampwidth()
        rate = w.getframerate()
        n = w.getnframes()
        data = w.readframes(n)
    if sw != 2:
        return  # only normalizing 16-bit int audio
    vals = struct.unpack("<%dh" % (len(data) // 2), data)
    peak = max((abs(v) for v in vals), default=1)
    target = int(32767 * (10 ** (headroom_db / 20.0)))
    if peak <= target:
        return
    gain = target / peak
    scaled = struct.pack("<%dh" % len(vals),
                         *(int(v * gain) for v in vals))
    with wave.open(path, "wb") as w:
        w.setparams((channels, sw, rate, n, "NONE", "not compressed"))
        w.writeframes(scaled)


def render_natural(s, path, dur, fn, headroom_db=-3.0):
    """render() + peak normalization. fn() returns the list of pyo objs."""
    s.recordOptions(dur=dur, filename=path, sampletype=0)
    objs = fn()
    s.recstart()
    s.start()
    s.recstop()
    for obj in objs:
        obj.stop()
    normalize_wav(path, headroom_db=headroom_db)
    print(f"  {os.path.basename(path):30s}  dur={dur:>4.1f}s  size={os.path.getsize(path):>7d}b  PASS")


# ── Raw layer builders (mono sigs, NO .out()) ────────────────

def transient(freq=4000, q=6, amp=0.5, dur=0.03, offset=0.0, fi=0.0005, fo=0.01):
    """Sharp resonant noise click — the physical 'attack' of an impact."""
    e = pyo.Expseg([(0, 0.0001), (0.004, amp), (dur, 0.0001)], exp=18)
    e.play(delay=offset)
    sig = pyo.Reson(pyo.Noise(), freq=freq, q=q, mul=e)
    return [e], [sig]


def transient_with_fi(freq=4000, q=6, amp=0.5, dur=0.03, offset=0.0, fi=0.0005, fo=0.01):
    return transient(freq, q, amp, dur, offset, fi, fo)


def modal_body(fundamental, ratios, dur, amp, seed=0, glide=0.02, detune=0.004,
               offset=0.0):
    """Inharmonic partial bank — the 'body'. Each partial: detune + glide + exp decay.
    ratios: list of (multiplier, rel_amp). Fundamentals in Hz.
    offset: stagger all partials by this delay (natural transient touch).
    """
    rng = random.Random(seed)
    objs = []
    sigs = []
    for mult, rel in ratios:
        jit = rng.uniform(-detune, detune)
        gl = pyo.Expseg([(0, fundamental * mult * rng.uniform(0.01, 0.03)),
                         (min(0.06, dur * 0.3), 0)], exp=4)
        gl.play(delay=offset)
        e = pyo.Expseg([(0, amp * rel), (dur, 0.0001)], exp=6)
        e.play(delay=offset)
        s = pyo.Sine(freq=fundamental * mult * (1 + jit) + gl, mul=e)
        objs += [gl, e]
        sigs.append(s)
    return objs, sigs


def sine_drop(f0, f1, drop_t, dur, amp, fi=0.01, fo=0.25, curve_exp=3.0):
    """Pitched fall — the sub-boom underneath explosions. Frequency glides down."""
    fi = max(fi, 0.005)
    glide = pyo.Linseg([(0, f0), (drop_t, f1)])
    glide.play()
    e = pyo.Fader(fadein=fi, fadeout=fo, dur=dur, mul=amp)
    e.play()
    sig = pyo.Sine(freq=glide, mul=e)
    return [glide, e], [sig]


def air_noise(cf, q, amp, dur, sweep_from=None, sweep_to=None, wobble_rate=0.3,
              fi=0.1, fo=0.3):
    """Resonant band-passed noise with optional slow center sweep + breathing."""
    objs = []
    e = pyo.Fader(fadein=fi, fadeout=fo, dur=dur, mul=amp)
    e.play()
    objs.append(e)
    if sweep_from is not None and sweep_to is not None:
        freq = pyo.Linseg([(0, sweep_from), (dur, sweep_to)])
        freq.play()
        objs.append(freq)
    else:
        freq = cf
    breath = pyo.Sine(freq=wobble_rate, mul=amp * 0.35, add=1.0)
    sig = pyo.Reson(pyo.Noise(), freq=freq, q=q, mul=e * breath)
    objs.append(breath)
    return objs, [sig]


def grain_cluster(seed, count, spread, lp_range, q, amp):
    """Scattered short resonant noise grains — dust, debris, shards, rustle.
    Reuses audio_helpers.noise_cluster but returns sigs instead of outs."""
    from helpers.audio_helpers import noise_burst
    objs = []
    sigs = []
    rng = random.Random(seed)
    for i in range(count):
        offset = rng.uniform(0, spread * 0.95)
        gdur = 0.004 + rng.uniform(0, 0.02)
        cf = lp_range[0] + rng.random() * (lp_range[1] - lp_range[0])
        e = pyo.Expseg([(0, 0), (0.002, amp * rng.uniform(0.4, 1.0)),
                        (gdur, 0.0001)], exp=24)
        e.play(delay=offset)
        sig = pyo.Reson(pyo.Noise(), freq=cf, q=q, mul=e)
        objs.append(e)
        sigs.append(sig)
    return objs, sigs


def bird_chirp(seed, offset, dur=0.28, amp=0.18, base=3200):
    """Two slight-detuned descending warble tones — reads as a distant bird."""
    rng = random.Random(seed)
    objs = []
    sigs = []
    for i in range(2):
        f = base * rng.uniform(0.9, 1.15)
        frq = pyo.Linseg([(0, f * 1.15), (dur * 0.45, f * 0.72), (dur, f * 0.95)])
        frq.play(delay=offset)
        vib = pyo.Sine(freq=rng.uniform(28, 42), mul=f * 0.012)
        e = pyo.Fader(fadein=dur * 0.12, fadeout=dur * 0.5, dur=dur,
                      mul=amp * rng.uniform(0.6, 1.0))
        e.play(delay=offset)
        sig = pyo.Sine(freq=frq + vib, mul=e)
        objs += [frq, vib, e]
        sigs.append(sig)
    return objs, sigs


# ── Space chain / naturalize ─────────────────────────────────

def naturalize(sig, drive=0.07, size=0.6, damp=0.5, verb_mix=0.22,
               pre_delay_s=0.02, haas_ms=7.0, pan_center=0.5):
    """One room for the whole mix: saturation -> pre-delay -> reverb -> Haas width.

    Returns the list of pyo objects to stop. Only the final Pans output audio.
    """
    sat = pyo.Disto(sig, drive=drive, slope=0.7, mul=1.0)
    pre = pyo.Delay(sat, delay=pre_delay_s, feedback=0)
    verb = pyo.Freeverb(pre, size=size, damp=damp, bal=verb_mix)

    d = pyo.Delay(verb, delay=haas_ms / 1000.0, feedback=0)
    p1 = pyo.Pan(verb, outs=2, pan=max(0.0, pan_center - 0.12)).out()
    p2 = pyo.Pan(d, outs=2, pan=min(1.0, pan_center + 0.12)).out()
    return [sat, pre, verb, d, p1, p2]


def mix_and_out(sigs, **space_kwargs):
    """Mix mono sigs and run the space chain. Returns objs to stop."""
    mix = pyo.Mix([s for s in sigs if s is not None], mul=1.0)
    return [mix] + naturalize(mix, **space_kwargs)


# ── Sample layering support (degrades gracefully) ────────────

def sample_layer(path, amp=1.0, loop=False, pan=0.5, gain_db=0.0):
    """Load a real recording and place it in the mix. Returns (objs, [sig]).
    If the file is missing, returns ([], []) so composers treat it as silent.
    """
    if not os.path.exists(path):
        print(f"  [skip] sample not found, layered silently: {path}")
        return [], []
    e = pyo.Fader(fadein=0.02, fadeout=0.15, dur=20.0, mul=amp * (10 ** (gain_db / 20)))
    e.play()
    player = pyo.SfPlayer(path, loop=loop, mul=e)
    return [e, player], [player]


def mix_synth_and_sample(sigs, sample_path, amp=0.7, loop=True, **space_kwargs):
    """Compose synth layers + a real sample floor into one naturalized mix."""
    sobs, ssigs = sample_layer(sample_path, amp=amp, loop=loop)
    return sobs + mix_and_out(list(sigs) + ssigs, **space_kwargs)


# ── Material presets (recipe tables, not hardcoded sound code) ──

MATERIALS = {
    "stone": dict(drive=0.06, size=0.5, damp=0.5, verb_mix=0.18,
                  body=((1.0, 1.0), (2.76, 0.5), (4.52, 0.3), (1.51, 0.6)),
                  transient_freq=2400, trans_q=8,
                  air=(1800, 8, 0.12)),
    "metal": dict(drive=0.05, size=0.65, damp=0.3, verb_mix=0.25,
                  body=((1.0, 1.0), (2.0, 0.7), (3.01, 0.4), (4.04, 0.35), (5.08, 0.2)),
                  transient_freq=5200, trans_q=14,
                  air=(3000, 10, 0.08)),
    "wood":  dict(drive=0.08, size=0.4, damp=0.6, verb_mix=0.14,
                  body=((1.0, 1.0), (2.32, 0.45), (3.11, 0.3), (4.55, 0.2)),
                  transient_freq=1500, trans_q=6,
                  air=(900, 5, 0.10)),
    "glass": dict(drive=0.02, size=0.35, damp=0.4, verb_mix=0.2,
                  body=((1.0, 1.0), (1.51, 0.6), (2.4, 0.5), (2.92, 0.4), (3.8, 0.35), (4.5, 0.3)),
                  transient_freq=7200, trans_q=20,
                  air=(5000, 16, 0.05)),
    "ice":   dict(drive=0.03, size=0.55, damp=0.35, verb_mix=0.24,
                  body=((1.0, 1.0), (1.9, 0.55), (2.85, 0.45), (3.9, 0.35), (5.1, 0.25)),
                  transient_freq=6200, trans_q=16,
                  air=(4200, 12, 0.06)),
    "water": dict(drive=0.04, size=0.5, damp=0.45, verb_mix=0.22,
                  body=((1.0, 1.0), (1.4, 0.6), (2.1, 0.4), (3.2, 0.3)),
                  transient_freq=3800, trans_q=10,
                  air=(2600, 9, 0.08)),
    "fire":  dict(drive=0.08, size=0.6, damp=0.5, verb_mix=0.2,
                  body=((1.0, 0.4), (2.4, 0.3), (1.6, 0.2)),
                  transient_freq=1100, trans_q=4,
                  air=(700, 3, 0.18)),
}


def material_impact(material, fund_hz=180, dur=1.2, amp=0.8, seed=0, pre_hit=0.0):
    """One layered impact for a material table entry — the natural-resin preset."""
    cfg = MATERIALS[material]
    objs, sigs = [], []
    o, s = transient(cfg["transient_freq"], cfg["trans_q"], amp * 0.6,
                     dur * 0.05, offset=pre_hit)
    objs += o; sigs += s
    af, aq, arel = cfg["air"]
    o, s = air_noise(af, aq, amp * 0.15, dur, sweep_to=af * 0.35, wobble_rate=0.2)
    objs += o; sigs += s
    o, s = modal_body(fund_hz, cfg["body"], dur, amp, seed=seed, glide=0.02)
    objs += o; sigs += s
    objs += mix_and_out(sigs, drive=cfg["drive"], size=cfg["size"],
                        damp=cfg["damp"], verb_mix=cfg["verb_mix"], pre_delay_s=0.01)
    return objs