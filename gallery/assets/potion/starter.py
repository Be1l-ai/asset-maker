import argparse
import colorsys
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import aggdraw
import numpy as np
from PIL import Image, ImageDraw


def draw_icon(size=256, seed=7, hue=185.0):
    scale = size * 2
    rng = np.random.default_rng(seed)
    image = Image.new("RGBA", (scale, scale))
    path = aggdraw.Path()
    path.moveto(0.40 * scale, 0.19 * scale)
    path.lineto(0.60 * scale, 0.19 * scale)
    path.lineto(0.60 * scale, 0.36 * scale)
    path.curveto(0.61 * scale, 0.43 * scale, 0.82 * scale, 0.48 * scale, 0.82 * scale, 0.68 * scale)
    path.curveto(0.82 * scale, 0.86 * scale, 0.69 * scale, 0.91 * scale, 0.50 * scale, 0.91 * scale)
    path.curveto(0.31 * scale, 0.91 * scale, 0.18 * scale, 0.86 * scale, 0.18 * scale, 0.68 * scale)
    path.curveto(0.18 * scale, 0.48 * scale, 0.39 * scale, 0.43 * scale, 0.40 * scale, 0.36 * scale)
    path.close()
    shell = aggdraw.Draw(image)
    shell.path(path, aggdraw.Brush((27, 43, 61, 235)))
    shell.flush()
    mask = Image.new("L", image.size)
    drawer = aggdraw.Draw(mask)
    drawer.path(path, aggdraw.Brush(255))
    drawer.flush()
    yy, xx = np.mgrid[0:scale, 0:scale] / scale
    surface = 0.53 + 0.012 * np.sin(14 * xx)
    fill = (yy >= surface) & (np.asarray(mask) > 0)
    top = np.array(colorsys.hsv_to_rgb((hue % 360) / 360, 0.65, 0.95))
    bottom = np.array(colorsys.hsv_to_rgb(((hue + 25) % 360) / 360, 0.85, 0.32))
    gradient = np.clip((yy - 0.53) / 0.38, 0, 1)[..., None]
    rgb = 255 * (top * (1 - gradient) + bottom * gradient)
    rgba = np.dstack([rgb, fill * 255]).astype(np.uint8)
    rgba[:, :, 3] = np.minimum(rgba[:, :, 3], np.asarray(mask))
    image = Image.alpha_composite(image, Image.fromarray(rgba))
    details = ImageDraw.Draw(image)
    for _ in range(9):
        x, y, radius = rng.uniform(0.32, 0.68), rng.uniform(0.60, 0.81), rng.uniform(0.006, 0.014)
        details.ellipse(((x - radius) * scale, (y - radius) * scale,
                         (x + radius) * scale, (y + radius) * scale),
                        outline=(165, 246, 245, 210), width=max(1, round(scale * 0.004)))
    outline = aggdraw.Draw(image)
    outline.path(path, None, aggdraw.Pen((11, 21, 35, 255), scale * 0.018))
    highlight = aggdraw.Path()
    highlight.moveto(0.37 * scale, 0.48 * scale)
    highlight.curveto(0.25 * scale, 0.56 * scale, 0.24 * scale, 0.63 * scale, 0.27 * scale, 0.73 * scale)
    outline.path(highlight, None, aggdraw.Pen((198, 239, 250, 230), scale * 0.025))
    outline.flush()
    details = ImageDraw.Draw(image)
    details.rounded_rectangle((0.405 * scale, 0.10 * scale, 0.595 * scale, 0.225 * scale),
                              radius=0.025 * scale, fill=(148, 92, 52),
                              outline=(32, 24, 29), width=round(scale * 0.016))
    details.line((0.435 * scale, 0.13 * scale, 0.54 * scale, 0.13 * scale),
                 fill=(222, 162, 92), width=round(scale * 0.01))
    details.rounded_rectangle((0.37 * scale, 0.215 * scale, 0.63 * scale, 0.285 * scale),
                              radius=0.025 * scale, fill=(71, 110, 127),
                              outline=(11, 21, 35), width=round(scale * 0.014))
    details.line((0.40 * scale, 0.235 * scale, 0.58 * scale, 0.235 * scale),
                 fill=(164, 217, 223), width=round(scale * 0.009))
    result = image.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    # Keep resampling ringing out of the one-pixel transparent gutter.
    ImageDraw.Draw(result).rectangle((0, 0, size - 1, size - 1), outline=(0, 0, 0, 0))
    return result


def main():
    parser = argparse.ArgumentParser(description="Study and customize a code-drawn curved potion icon.")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--hue", type=float, default=185)
    args = parser.parse_args()
    if not (32 <= args.size <= 1024 and args.seed >= 0 and np.isfinite(args.hue)):
        parser.error("Use size 32..1024, a nonnegative seed, and a finite hue")
    try:
        image = draw_icon(args.size, args.seed, args.hue)
        preview = Image.new("RGB", (args.size * 2, args.size))
        for i, color in enumerate([(20, 24, 36), (235, 237, 242)]):
            background = Image.new("RGBA", image.size, color + (255,))
            preview.paste(Image.alpha_composite(background, image).convert("RGB"), (i * args.size, 0))
        args.out.mkdir(parents=True, exist_ok=False)
        image.save(args.out / "potion.png")
        preview.save(args.out / "preview.png")
        (args.out / "recipe.py").write_text(Path(__file__).read_text())
        metadata = {
            "asset": "potion.png", "format": "RGBA PNG", "alpha": "straight",
            "size": [args.size, args.size], "pivot_normalized": [0.5, 0.91],
            "parameters": {k: v for k, v in vars(args).items() if k != "out"},
            "versions": {p: version(p) for p in ["numpy", "Pillow", "aggdraw"]},
            "sha256": {name: hashlib.sha256((args.out / name).read_bytes()).hexdigest()
                       for name in ["potion.png", "preview.png", "recipe.py"]},
        }
        (args.out / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps({"output": str(args.out), "size": list(image.size)}))
    except (OSError, ValueError) as error:
        parser.exit(1, f"2D generation failed: {error}\n")


if __name__ == "__main__":
    main()
