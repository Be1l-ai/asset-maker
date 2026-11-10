# SFX Sound Template

Template for procedural modal and additive audio synthesis.

## Quick Start

1. Edit `synthesize(duration, rate, seed)` in `generate.py` to design your audio waveforms and resonance modes.
2. Run generation:
   ```sh
   python generate.py [--duration 0.5] [--rate 48000] [--seed 7]
   ```
3. Artifacts generated:
   - `<asset_name>.wav`: 16-bit PCM WAV normalized to standard -3 dBFS headroom.
   - `manifest.json`: Audio metrics (RMS, peak, channels, DC offset) and checksums.
