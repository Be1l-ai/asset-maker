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

    def paste_layer(self, layer: np.ndarray) -> "SpriteCanvas":
        """Alpha-composite a float RGBA layer (H, W, 4; RGB 0..255, alpha 0..1) onto the canvas."""
        self.flush()
        arr = np.concatenate([layer[..., :3], layer[..., 3:4] * 255.0], axis=2).clip(0, 255)
        top = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
        self.image = Image.alpha_composite(self.image, top)
        self.agg = aggdraw.Draw(self.image)
        self.draw = ImageDraw.Draw(self.image)
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


def heightmap_to_normal_map(
    heightmap: np.ndarray,
    strength: float = 1.0,
    invert_y: bool = False,
    tileable: bool = False,
) -> np.ndarray:
    """Generate a tangent-space normal map from a 2D heightfield using a Sobel gradient filter.

    Parameters:
        heightmap: 2D array of heights (float 0..1 or uint8 0..255).
        strength: Bump relief intensity multiplier.
        invert_y: If True, inverts the Y (green) channel (DirectX convention vs OpenGL).
        tileable: If True, gradients wrap around the borders so seamless tiles stay seamless.

    Returns:
        3D uint8 array of shape (H, W, 3) in range [0, 255] with RGB tangent-space vectors.
    """
    from scipy.ndimage import sobel

    hmap = np.asarray(heightmap, dtype=np.float32)
    if hmap.ndim != 2:
        raise ValueError(f"Heightmap must be 2D, got shape {hmap.shape}")
    if hmap.max() > 1.0:
        hmap = hmap / 255.0

    # Sobel gradients: axis 1 is horizontal (X), axis 0 is vertical (Y)
    mode = "wrap" if tileable else "reflect"
    dx = sobel(hmap, axis=1, mode=mode) * strength
    dy = sobel(hmap, axis=0, mode=mode) * strength

    if invert_y:
        dy = -dy

    # Tangent-space normal vector: N = (-dx, -dy, 1.0)
    z = np.ones_like(hmap)
    normals = np.dstack((-dx, -dy, z))

    # Normalize to unit vectors
    norm = np.linalg.norm(normals, axis=2, keepdims=True)
    norm = np.where(norm == 0, 1.0, norm)
    normals /= norm

    # Remap [-1, 1] -> [0, 255]
    rgb = ((normals * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)
    return rgb


def worley_noise(
    width: int,
    height: int,
    grid_x: int = 8,
    grid_y: int = 8,
    metric: str = "euclidean",
    seed: int = 7,
    periodic: bool = False,
) -> np.ndarray:
    """Generate a vectorized 2D Worley (cellular) noise texture with 3x3 neighborhood search.

    Parameters:
        width: Output texture width.
        height: Output texture height.
        grid_x: Cell columns across the width.
        grid_y: Cell rows across the height.
        metric: Distance metric ('euclidean', 'manhattan', 'chebyshev').
        seed: Random seed for deterministic feature point placement.
        periodic: If True, feature points wrap so the texture tiles seamlessly.

    Returns:
        2D float32 array of shape (height, width) with normalized distances [0, 1].
    """
    rng = np.random.default_rng(seed)
    cell_w = width / max(1, grid_x)
    cell_h = height / max(1, grid_y)

    pixel_y, pixel_x = np.indices((height, width), dtype=np.float32)
    fx = pixel_x / cell_w
    fy = pixel_y / cell_h

    base_cx = np.floor(fx).astype(int)
    base_cy = np.floor(fy).astype(int)

    # Generate feature points with padding (-1 to grid + 2)
    pts_y, pts_x = np.mgrid[-1 : grid_y + 3, -1 : grid_x + 3]
    offsets_x = rng.uniform(0.05, 0.95, size=pts_x.shape)
    offsets_y = rng.uniform(0.05, 0.95, size=pts_y.shape)
    feat_x = pts_x + offsets_x
    feat_y = pts_y + offsets_y

    f1 = np.full((height, width), np.inf, dtype=np.float32)
    base_cx_shifted = base_cx + 1
    base_cy_shifted = base_cy + 1

    for dy in range(-1, 2):
        for dx in range(-1, 2):
            ncx = base_cx_shifted + dx
            ncy = base_cy_shifted + dy
            # Clamp indices
            ncx = np.clip(ncx, 0, feat_x.shape[1] - 1)
            ncy = np.clip(ncy, 0, feat_x.shape[0] - 1)

            if periodic:
                wx = (base_cx + dx) % grid_x
                wy = (base_cy + dy) % grid_y
                fx_n = (base_cx + dx) + offsets_x[wy + 1, wx + 1]
                fy_n = (base_cy + dy) + offsets_y[wy + 1, wx + 1]
            else:
                fx_n = feat_x[ncy, ncx]
                fy_n = feat_y[ncy, ncx]

            if metric == "euclidean":
                dist = np.hypot(fx - fx_n, fy - fy_n)
            elif metric == "manhattan":
                dist = np.abs(fx - fx_n) + np.abs(fy - fy_n)
            elif metric == "chebyshev":
                dist = np.maximum(np.abs(fx - fx_n), np.abs(fy - fy_n))
            else:
                raise ValueError(f"Unknown metric '{metric}'")

            f1 = np.minimum(f1, dist)

    max_val = np.max(f1)
    if max_val > 0:
        f1 /= max_val
    return f1.clip(0.0, 1.0)


def procedural_fabric_weave(
    width: int,
    height: int,
    thread_density: int = 32,
    roughness: float = 0.2,
    seed: int = 7,
) -> np.ndarray:
    """Generate a procedural woven textile pattern (interlaced warp and weft).

    Returns:
        2D float32 array in range [0, 1] suitable as a bump/height or albedo pattern.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    fx = x * (2.0 * np.pi * thread_density / width)
    fy = y * (2.0 * np.pi * thread_density / height)

    # Warp (vertical) and weft (horizontal) threads
    warp = np.cos(fx) * np.sin(fy)
    weft = np.sin(fx) * np.cos(fy)
    weave = (warp - weft) * 0.5 + 0.5

    # Subtle thread fiber roughness
    fiber_noise = rng.uniform(-roughness, roughness, size=(height, width))
    combined = np.clip(weave + fiber_noise * 0.2, 0.0, 1.0).astype(np.float32)
    return combined


def procedural_wood_grain(
    width: int,
    height: int,
    ring_spacing: float = 16.0,
    wobble: float = 4.0,
    seed: int = 7,
) -> np.ndarray:
    """Generate procedural wood growth rings with natural radial turbulence.

    Returns:
        2D float32 array in range [0, 1] representing wood ring density and early/latewood transitions.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)

    cx, cy = width * 0.35, height * 0.5
    dx = x - cx
    dy = (y - cy) * 1.5  # Elliptical eccentricity

    # Low frequency turbulent ray perturbation
    angle = np.arctan2(dy, dx)
    pert = (
        np.sin(angle * 3.0 + seed) * wobble
        + np.sin(angle * 7.0 + seed * 2) * (wobble * 0.5)
    )

    r = np.sqrt(dx**2 + dy**2) + pert
    ring_val = (r / max(1.0, ring_spacing)) % 1.0

    # Asymmetric growth ring profile: gradual earlywood rise, sharp latewood transition
    grain = np.where(ring_val < 0.75, ring_val / 0.75, (1.0 - ring_val) / 0.25)
    return grain.astype(np.float32)



# ---------------------------------------------------------------------------
# Mask / layer helpers (numpy-first drawing; avoids aggdraw's alpha-over "erase" pitfall)
# ---------------------------------------------------------------------------

def ellipse_mask(shape: Tuple[int, int], cx: float, cy: float, rx: float, ry: float) -> np.ndarray:
    """Antialiased filled-ellipse coverage mask (float32 in [0, 1]) of ``shape`` = (H, W)."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    k = np.hypot((x - cx) / rx, (y - cy) / ry)
    dist_px = (k - 1.0) * min(rx, ry)
    return np.clip(0.5 - dist_px, 0.0, 1.0).astype(np.float32)


def polygon_mask(shape: Tuple[int, int], points: Sequence[Tuple[float, float]]) -> np.ndarray:
    """Filled-polygon coverage mask (float32 in [0, 1]); coordinates are in pixels."""
    h, w = shape
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).polygon([tuple(p) for p in points], fill=255)
    return (np.asarray(img, dtype=np.float32) / 255.0)


def inside_depth(mask: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Euclidean distance (pixels) from each interior pixel to the nearest outside pixel."""
    from scipy.ndimage import distance_transform_edt

    return distance_transform_edt(np.asarray(mask) > threshold).astype(np.float32)


def fillet_mask(mask: np.ndarray, radius_px: float) -> np.ndarray:
    """Round concave joins of a unioned mask by blur-and-rethreshold (keeps AA edge)."""
    from scipy.ndimage import gaussian_filter

    blurred = gaussian_filter(np.asarray(mask, dtype=np.float32), radius_px)
    return np.clip((blurred - 0.5) * (2.0 * radius_px) + 0.5, 0.0, 1.0).astype(np.float32)


def new_layer(shape: Tuple[int, int]) -> np.ndarray:
    """Transparent float RGBA layer (H, W, 4); RGB 0..255, alpha 0..1."""
    return np.zeros((shape[0], shape[1], 4), dtype=np.float32)


def over(dst: np.ndarray, rgb: np.ndarray | Sequence[float], alpha: np.ndarray) -> np.ndarray:
    """Straight-alpha 'over' composite of ``rgb``/``alpha`` onto float RGBA ``dst`` (in place).

    ``rgb`` may be a 3-tuple or an (H, W, 3) array; ``alpha`` is (H, W) in [0, 1].
    Use this (or multiply the alpha) instead of drawing transparent shapes to erase.
    """
    a = np.clip(alpha, 0.0, 1.0).astype(np.float32)
    rgb_arr = np.broadcast_to(np.asarray(rgb, dtype=np.float32), dst.shape[:2] + (3,))
    da = dst[..., 3]
    out_a = a + da * (1.0 - a)
    safe = np.where(out_a > 1e-6, out_a, 1.0)[..., None]
    dst[..., :3] = (rgb_arr * a[..., None] + dst[..., :3] * (da * (1.0 - a))[..., None]) / safe
    dst[..., 3] = out_a
    return dst


def lerp_color(c0: Sequence[float], c1: Sequence[float], t: np.ndarray) -> np.ndarray:
    """Per-pixel linear blend between two RGB colors (t is an (H, W) array in [0, 1])."""
    c0a = np.asarray(c0, dtype=np.float32)
    c1a = np.asarray(c1, dtype=np.float32)
    tt = np.clip(t, 0.0, 1.0)[..., None]
    return c0a * (1.0 - tt) + c1a * tt
