"""VFX animation, particle fields, and sprite sheet classes and helpers."""

from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple
import numpy as np
from PIL import Image, ImageDraw


class Easing:
    """Standard animation easing functions."""

    @staticmethod
    def linear(t: float) -> float:
        return float(np.clip(t, 0.0, 1.0))

    @staticmethod
    def ease_in(t: float) -> float:
        t = float(np.clip(t, 0.0, 1.0))
        return t ** 2

    @staticmethod
    def ease_out(t: float) -> float:
        t = float(np.clip(t, 0.0, 1.0))
        return 1.0 - (1.0 - t) ** 2

    @staticmethod
    def ease_in_out(t: float) -> float:
        t = float(np.clip(t, 0.0, 1.0))
        return t * t * (3.0 - 2.0 * t)


class Flipbook:
    """Container for managing and packing animated VFX sprite frames."""

    def __init__(self, fps: int = 16):
        self.fps = fps
        self.frames: List[Image.Image] = []

    def add_frame(self, frame: Image.Image) -> "Flipbook":
        """Append an RGBA frame to the sequence."""
        self.frames.append(frame.convert("RGBA"))
        return self

    def generate_frames(
        self,
        count: int,
        frame_generator: Callable[[float], Image.Image],
    ) -> "Flipbook":
        """Generate N frames using a phase function where 0.0 <= phase < 1.0."""
        for i in range(count):
            phase = i / max(1, count)
            self.add_frame(frame_generator(phase))
        return self

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def frame_size(self) -> Tuple[int, int]:
        if not self.frames:
            return (0, 0)
        return self.frames[0].size

    def pack_atlas(self, columns: int = 4) -> Image.Image:
        """Pack all frames into a row-major sprite sheet atlas."""
        if not self.frames:
            raise ValueError("Flipbook has no frames to pack")
        return pack_atlas(self.frames, None, columns=columns)

    def export_atlas(self, path: Path | str, columns: int = 4) -> Path:
        """Save packed atlas to PNG."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        atlas = self.pack_atlas(columns=columns)
        atlas.save(out)
        return out

    def export_gif(self, path: Path | str) -> Path:
        """Export looping GIF animation preview."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_animated_gif(self.frames, path, fps=self.fps)

    def export_preview(self, path: Path | str) -> Path:
        """Export side-by-side contact sheet preview."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        create_atlas_preview(self.frames, out)
        return out


class ParticleEmitter:
    """Procedural generator for bursts, sparks, and energy flows."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def radial_burst(
        self,
        size: int = 128,
        phase: float = 0.0,
        color_rgb: Tuple[int, int, int] = (100, 200, 255),
        particle_count: int = 12,
    ) -> Image.Image:
        """Render a single radial burst frame at a given phase."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        t = float(np.clip(phase, 0.0, 1.0))
        radius = Easing.ease_out(t) * (size * 0.42)
        alpha = int(round(255 * (1.0 - t)))

        if alpha > 0 and radius > 2:
            cx, cy = size / 2.0, size / 2.0
            ring_color = color_rgb + (max(0, min(255, int(alpha * 0.6))),)
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                         outline=ring_color, width=max(1, round(size * 0.03 * (1.0 - t))))

        for i in range(particle_count):
            angle = self.rng.uniform(0, 2 * np.pi) + (i * (2 * np.pi / particle_count))
            speed = self.rng.uniform(0.7, 1.3)
            dist = radius * speed
            px = size / 2.0 + np.cos(angle) * dist
            py = size / 2.0 + np.sin(angle) * dist
            p_radius = max(1.0, (1.0 - t) * size * 0.02)
            p_alpha = max(0, min(255, int(alpha * self.rng.uniform(0.5, 1.0))))
            if p_alpha > 0 and 0 <= px < size and 0 <= py < size:
                draw.ellipse([px - p_radius, py - p_radius, px + p_radius, py + p_radius],
                             fill=color_rgb + (p_alpha,))

        draw.rectangle([0, 0, size - 1, size - 1], outline=(0, 0, 0, 0))
        return img


# Functional helpers for backwards-compatibility
def ease_in_out(t: float) -> float:
    return Easing.ease_in_out(t)


def ease_out(t: float) -> float:
    return Easing.ease_out(t)


def ease_in(t: float) -> float:
    return Easing.ease_in(t)


def pack_atlas(frames: Sequence[Image.Image], path: Optional[Path | str] = None, columns: int = 4) -> Image.Image:
    count = len(frames)
    rows = int(np.ceil(count / columns))
    fw, fh = frames[0].size
    atlas = Image.new("RGBA", (fw * columns, fh * rows), (0, 0, 0, 0))

    for idx, frame in enumerate(frames):
        c = idx % columns
        r = idx // columns
        atlas.paste(frame, (c * fw, r * fh))

    if path:
        atlas.save(path)
    return atlas


def create_animated_gif(frames: Sequence[Image.Image], path: Path | str, fps: int = 16) -> Path:
    out = Path(path)
    rgb_frames = []
    for f in frames:
        bg = Image.new("RGBA", f.size, (18, 22, 32, 255))
        comp = Image.alpha_composite(bg, f).convert("RGB")
        rgb_frames.append(comp)

    duration_ms = int(round(1000.0 / max(1, fps)))
    rgb_frames[0].save(
        out,
        save_all=True,
        append_images=rgb_frames[1:],
        duration=duration_ms,
        loop=0,
    )
    return out


def create_atlas_preview(frames: Sequence[Image.Image], path: Path | str) -> Image.Image:
    count = len(frames)
    fw, fh = frames[0].size
    cols = min(4, count)
    rows = int(np.ceil(count / cols))

    atlas = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))
    for idx, frame in enumerate(frames):
        atlas.paste(frame, ((idx % cols) * fw, (idx // cols) * fh))

    w, h = atlas.size
    preview = Image.new("RGB", (w * 2, h))
    for i, bg_color in enumerate([(20, 24, 36), (235, 237, 242)]):
        bg = Image.new("RGBA", (w, h), bg_color + (255,))
        comp = Image.alpha_composite(bg, atlas).convert("RGB")
        preview.paste(comp, (i * w, 0))

    preview.save(path)
    return preview


def create_radial_burst(
    size: int = 128,
    phase: float = 0.0,
    seed: int = 7,
    color_rgb: Tuple[int, int, int] = (120, 210, 255),
) -> Image.Image:
    emitter = ParticleEmitter(seed=seed)
    return emitter.radial_burst(size=size, phase=phase, color_rgb=color_rgb)
