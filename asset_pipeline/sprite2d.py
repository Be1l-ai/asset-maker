"""2D sprite, icon, and texture generation classes and helpers."""

import colorsys
from pathlib import Path
from typing import Optional, Sequence, Tuple
import aggdraw
import numpy as np
from PIL import Image, ImageDraw


class SpriteCanvas:
    """Super-sampled 2D drawing canvas with antialiasing and premultiplied-alpha downsampling."""

    def __init__(self, size: int = 256, super_sample: int = 2):
        self.target_size = size
        self.scale = size * super_sample
        self.image = Image.new("RGBA", (self.scale, self.scale), (0, 0, 0, 0))
        self.agg = aggdraw.Draw(self.image)
        self.draw = ImageDraw.Draw(self.image)

    def flush(self) -> None:
        """Flush aggdraw operations to underlying PIL image."""
        self.agg.flush()

    def draw_path(
        self,
        path: aggdraw.Path,
        brush_color: Optional[Tuple[int, int, int, int]] = None,
        pen_color: Optional[Tuple[int, int, int, int]] = None,
        pen_width: float = 1.0,
    ) -> "SpriteCanvas":
        """Draw an aggdraw Bezier or polygon path."""
        brush = aggdraw.Brush(brush_color) if brush_color else None
        pen = aggdraw.Pen(pen_color, pen_width) if pen_color else None
        self.agg.path(path, brush, pen)
        return self

    def downsample(self) -> Image.Image:
        """Flush and downsample to target size using premultiplied alpha."""
        self.flush()
        return downsample_rgba(self.image, self.target_size)

    def export(self, path: Path | str) -> Path:
        """Export downsampled RGBA image to disk."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img = self.downsample()
        img.save(out)
        return out

    def export_dual_preview(self, path: Path | str) -> Path:
        """Export side-by-side dark and light background preview."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img = self.downsample()
        create_dual_preview(img).save(out)
        return out


class SeamlessTile:
    """Procedural tile generator ensuring seamless tiling across boundaries."""

    def __init__(self, size: int = 256, seed: int = 7):
        self.size = size
        self.rng = np.random.default_rng(seed)

    def generate_toroidal_grid(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate normalized (0..2pi) toroidal coordinate matrices for seamless periodic math."""
        y, x = np.mgrid[0:self.size, 0:self.size] / self.size
        theta = 2.0 * np.pi * x
        phi = 2.0 * np.pi * y
        return theta, phi

    def create_tiled_preview(self, tile: Image.Image, grid: Tuple[int, int] = (3, 3)) -> Image.Image:
        """Tile the image across an N x M grid to verify boundary seams."""
        return create_tiled_preview(tile, grid=grid)


def downsample_rgba(image: Image.Image, target_size: int) -> Image.Image:
    """Downsample super-sampled image using premultiplied alpha with clean 1px border gutter."""
    premult = image.convert("RGBa").resize((target_size, target_size), Image.Resampling.LANCZOS)
    result = premult.convert("RGBA")
    draw = ImageDraw.Draw(result)
    draw.rectangle((0, 0, target_size - 1, target_size - 1), outline=(0, 0, 0, 0))
    return result


def create_dual_preview(
    image: Image.Image,
    dark_bg: Tuple[int, int, int] = (20, 24, 36),
    light_bg: Tuple[int, int, int] = (235, 237, 242),
) -> Image.Image:
    """Create side-by-side preview on dark and light backgrounds."""
    w, h = image.size
    preview = Image.new("RGB", (w * 2, h))
    for i, bg_color in enumerate([dark_bg, light_bg]):
        bg = Image.new("RGBA", (w, h), bg_color + (255,))
        comp = Image.alpha_composite(bg, image.convert("RGBA")).convert("RGB")
        preview.paste(comp, (i * w, 0))
    return preview


def create_tiled_preview(tile: Image.Image, grid: Tuple[int, int] = (3, 3)) -> Image.Image:
    """Tile image across a grid to inspect seams."""
    cols, rows = grid
    tw, th = tile.size
    preview = Image.new(tile.mode, (tw * cols, th * rows))
    for r in range(rows):
        for c in range(cols):
            preview.paste(tile, (c * tw, r * th))
    return preview


def hsv_to_rgb(h_deg: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convert HSV (0..360, 0..1, 0..1) to RGB (0..255)."""
    r, g, b = colorsys.hsv_to_rgb((h_deg % 360) / 360.0, s, v)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
