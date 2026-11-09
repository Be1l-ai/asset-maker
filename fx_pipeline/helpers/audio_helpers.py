import pyo
import os


def boot_server():
    s = pyo.Server(duplex=0, audio='offline')
    s.boot()
    return s


def shutdown_server(s):
    s.shutdown()


def render(s, path, dur, fn):
    s.recordOptions(dur=dur, filename=path, sampletype=0)
    objs = fn()
    s.recstart()
    s.start()
    s.recstop()
    for obj in objs:
        obj.stop()
    size = os.path.getsize(path)
    print(f"  {os.path.basename(path):30s}  size={size:>6d}b  PASS")


def env(fi, fo, dur, amp):
    e = pyo.Fader(fadein=fi, fadeout=fo, dur=dur, mul=amp)
    e.play()
    return e


def band_sq(freq, dur, amp, fi=0.002, fo=0.02):
    """Band-limited square wave via Osc + SquareTable."""
    e = env(fi, fo, dur, amp)
    sig = pyo.Osc(pyo.SquareTable(), freq=freq, mul=e).out()
    return [e, sig]


def band_saw(freq, dur, amp, fi=0.002, fo=0.02):
    """Band-limited saw wave via Osc + SawTable."""
    e = env(fi, fo, dur, amp)
    sig = pyo.Osc(pyo.SawTable(), freq=freq, mul=e).out()
    return [e, sig]


def sine(freq, dur, amp, fi=0.01, fo=0.15):
    e = env(fi, fo, dur, amp)
    sig = pyo.Sine(freq=freq, mul=e).out()
    return [e, sig]


def fm_small(carrier, ratio, index, dur, amp, fi=0.005, fo=0.04):
    """FM with musically-useful index range (0-12, not 200-800)."""
    e = env(fi, fo, dur, amp)
    sig = pyo.FM(carrier=carrier, ratio=ratio, index=index, mul=e).out()
    return [e, sig]


def noise_lp(dur, amp, freq, fi=0.002, fo=0.03):
    """White noise through low-pass filter. Keep freq=800-1500 for soft sounds."""
    e = env(fi, fo, dur, amp)
    sig = pyo.ButLP(pyo.Noise(), freq=freq, mul=e).out()
    return [e, sig]


def mix_sine(f1, a1, f2, a2, dur, fi=0.01, fo=0.15):
    e = pyo.Fader(fadein=fi, fadeout=fo, dur=dur, mul=1.0)
    e.play()
    s1 = pyo.Sine(freq=f1, mul=e * a1)
    p1 = pyo.Pan(s1, outs=2, pan=0.5).out()
    s2 = pyo.Sine(freq=f2, mul=e * a2)
    p2 = pyo.Pan(s2, outs=2, pan=0.5).out()
    return [e, s1, p1, s2, p2]


def mix_sq_noise(freq_sq, amp_sq, amp_n, lp, dur, fi=0.002, fo=0.03):
    e = pyo.Fader(fadein=fi, fadeout=fo, dur=dur, mul=1.0)
    e.play()
    sq_sig = pyo.Osc(pyo.SquareTable(), freq=freq_sq, mul=e * amp_sq)
    p_sq = pyo.Pan(sq_sig, outs=2, pan=0.5).out()
    ns = pyo.ButLP(pyo.Noise(), freq=lp, mul=e * amp_n)
    p_ns = pyo.Pan(ns, outs=2, pan=0.5).out()
    return [e, sq_sig, p_sq, ns, p_ns]


def clip(samples):
    """Soft-clip limiter: tames peaks while keeping punch."""
    lim = pyo.Sig(samples)
    lim = pyo.Mirror(lim)
    return lim


# ── Physical modeling helpers (Farnell-style) ─────────────────

def modal_strike(modes, global_amp=1.0, seed=None, pan_spread=0.6, delay=0, stereo=True):
    """Organic modal synthesis — sine bank with excitation, jitter, glide, optional stereo.
    modes: list of (freq_hz, amplitude, decay_seconds)
    seed: fix per-sound-identity for reproducible variation.
    pan_spread: 0=mono, 1=hard L/R spread (only when stereo=True).
    delay: seconds to delay the entire strike (for staggered events).
    stereo: if True, each mode gets a unique pan position via Pan.
    Adds three things pure-Sine modal synthesis misses:
      1. Shared excitation impulse (broadband click before the ring)
      2. Per-mode pitch jitter + downward glide on attack
      3. Optional stereo decorrelation via Pan
    """
    import random as _random
    rng = _random.Random(seed)
    objs = []

    click_amp = global_amp * 0.12
    click_e = pyo.Expseg([(0, click_amp), (0.002, 0.0001)], exp=6)
    click_e.play(delay=delay)
    click_sig = pyo.Reson(pyo.Noise(), freq=2500, q=3, mul=click_e).out()
    objs.extend([click_e, click_sig])

    for freq, amp, decay in modes:
        jitter_depth = freq * rng.uniform(0.002, 0.006)
        jitter_rate = rng.uniform(3, 9)
        jitter = pyo.Sine(freq=jitter_rate, mul=jitter_depth)

        glide_amount = freq * rng.uniform(0.01, 0.03)
        glide = pyo.Expseg([(0, glide_amount), (min(0.05, decay * 0.3), 0)], exp=4)
        glide.play(delay=delay)

        freq_sig = freq + jitter + glide

        onset_delay = delay + rng.uniform(0, 0.003)

        e = pyo.Expseg([(0, amp * global_amp), (decay, 0.0001)], exp=8, inverse=True)
        e.play(delay=onset_delay)

        s = pyo.Sine(freq=freq_sig, mul=e)
        if stereo:
            pan_pos = 0.5 + rng.uniform(-pan_spread, pan_spread) * 0.5
            pan_pos = max(0.0, min(1.0, pan_pos))
            out = pyo.Pan(s, outs=2, pan=pan_pos).out()
        else:
            out = s.out()
        objs.extend([jitter, glide, e, s, out])

    return objs


def reson_sweep(freq_start, freq_end, sweep_dur, q, dur, amp, fi=0.005, fo=0.04):
    """Noise through resonant bandpass filter with frequency sweep.
    freq_start→freq_end: center frequency sweep (Hz)
    sweep_dur: time to sweep from start to end (<= dur)
    q: filter Q/resonance (1-500). Higher = more tonal.
    dur: total duration. fi/fo: fade in/out.
    Sounds like physical friction/scraping/creaking.
    Outputs stereo-centered.
    """
    e = pyo.Fader(fadein=fi, fadeout=fo, dur=dur, mul=amp)
    e.play()
    sweep = pyo.Linseg([(0, freq_start), (sweep_dur, freq_end)])
    sweep.play()
    sig = pyo.Reson(pyo.Noise(), freq=sweep, q=q, mul=e)
    out = pyo.Pan(sig, outs=2, pan=0.5).out()
    return [e, sweep, sig, out]


def glue_chain(input_sig, verb_size=0.5, verb_mix=0.12, drive=0.08):
    """Light saturation + small reverb — makes dry synthesis feel like real space.
    input_sig: a pyo audio signal (e.g. Mix of layers).
    verb_size: 0-1 room size. verb_mix: 0-1 wet amount (keep 0.08-0.2).
    drive: 0-1 soft saturation (keep 0.05-0.15).
    """
    saturated = pyo.Disto(input_sig, drive=drive, slope=0.7, mul=0.9)
    verb = pyo.Freeverb(saturated, size=verb_size, damp=0.6, bal=verb_mix)
    return verb


def noise_burst(freq, q, dur, amp, offset=0):
    """Single short noise grain through resonant bandpass filter.
    freq: filter center frequency. q: resonance. dur: grain duration.
    offset: delay before playing (seconds).
    Outputs stereo-centered.
    """
    trig = pyo.Expseg([(0, 0), (0.003, 1), (dur, 0)], exp=30, mul=amp)
    trig.play(delay=offset)
    sig = pyo.Reson(pyo.Noise(), freq=freq, q=q, mul=trig)
    out = pyo.Pan(sig, outs=2, pan=0.5).out()
    return [trig, sig, out]


def noise_cluster(seed, count, spread, lp_range, q, amp):
    """Cluster of short resonant noise grains scattered over time.
    seed: RNG seed for deterministic output.
    count: number of grains.
    spread: time window to scatter grains across.
    lp_range: (min_hz, max_hz) filter freq range.
    q: filter Q for each grain.
    amp: overall amplitude.
    For dust rattles, hardware chatter, aggregate textures.
    """
    import random
    objs = []
    rng = random.Random(seed)
    for _ in range(count):
        offset = rng.uniform(0, spread * 0.9)
        grain_dur = 0.005 + rng.uniform(0, 0.015)
        freq = lp_range[0] + rng.random() * (lp_range[1] - lp_range[0])
        grain_amp = amp * rng.uniform(0.3, 1.0)
        o = noise_burst(freq, q, grain_dur, grain_amp, offset)
        objs.extend(o)
    return objs
