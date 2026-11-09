#!/usr/bin/env python3
"""Generate a new seed-7 collection and reproducible source ZIP without replacing existing assets."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import zipfile
from importlib.metadata import version
from pathlib import Path

# Importing the supplied starters must not modify their directories.
sys.dont_write_bytecode = True

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy.io import wavfile

SEED = 7
PACKAGES = ("numpy", "scipy", "Pillow", "aggdraw", "trimesh", "manifold3d")
STARTERS = {
    "3d": ".qoder/skills/create-3d-assets/scripts/build.py",
    "2d": ".qoder/skills/create-2d-assets/scripts/draw.py",
    "vfx": ".qoder/skills/create-vfx/scripts/render.py",
    "sfx": ".qoder/skills/create-sfx/scripts/synthesize.py",
}
RECIPE = "fx_pipeline/generate_gallery.py"
SOURCE = Path(__file__).resolve()
# Also let the per-asset source snapshots run inside the extracted collection.
ROOT = next((p for p in SOURCE.parents
             if (p / "requirements-code-assets.txt").is_file()
             and all((p / s).is_file() for s in STARTERS.values())), SOURCE.parents[1])
Z_TO_Y = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data, compact=False):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=None if compact else 2,
                  separators=(",", ":") if compact else None,
                  ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def copy_new(source, destination):
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def load_starters():
    modules = {}
    for kind, relative in STARTERS.items():
        spec = importlib.util.spec_from_file_location("gallery_starter_" + kind,
                                                     ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[kind] = module
    return modules


def paint(mesh, rgb, variation=0, seed=SEED):
    rng = np.random.default_rng(seed)
    values = np.tile(np.asarray(rgb, dtype=float), (len(mesh.faces), 1))
    if variation:
        # One value per planar facet, not an arbitrary contrasting triangle split.
        normals = np.round(mesh.face_normals, 4)
        _, indices = np.unique(normals, axis=0, return_inverse=True)
        values += rng.uniform(-variation, variation, (indices.max() + 1, 1))[indices]
    mesh.visual.face_colors = np.column_stack([
        np.clip(values, 0, 255).astype(np.uint8), np.full(len(values), 255)])
    return mesh


def ring_solid(rings, sides=6, angle=np.pi / 6):
    """Closed polygonal solid with radius/height rings and fan caps, Z-up."""
    theta = angle + np.arange(sides) * 2 * np.pi / sides
    vertices = [[r * np.cos(t), r * np.sin(t), z] for r, z in rings for t in theta]
    faces = []
    for level in range(len(rings) - 1):
        for j in range(sides):
            a, b = level * sides + j, level * sides + (j + 1) % sides
            faces.extend([[a, b, b + sides], [a, b + sides, a + sides]])
    for j in range(1, sides - 1):
        faces.append([0, j + 1, j])
        top = (len(rings) - 1) * sides
        faces.append([top, top + j, top + j + 1])
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def crystal(radius, height, center, lean, angle, seed):
    rng = np.random.default_rng(seed)
    mesh = ring_solid([(radius * .77, 0), (radius, height * .12),
                       (radius * .91, height * .72)], angle=angle)
    # Replace the ring caps with a bottom fan and six terminal facets.
    vertices = mesh.vertices.tolist() + [[radius * .10, -radius * .07, height]]
    faces = mesh.faces[:24].tolist()
    faces.extend([[0, j + 1, j] for j in range(1, 5)])
    faces.extend([[12 + j, 12 + (j + 1) % 6, 18] for j in range(6)])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.vertices[:, :2] += mesh.vertices[:, 2:3] / height * np.asarray(lean)
    mesh.apply_translation(center)
    palette = np.array([[30, 139, 107], [57, 193, 142], [140, 244, 195],
                        [73, 217, 166], [24, 109, 91], [100, 231, 178]])
    colors = []
    for index in range(len(mesh.faces)):
        side = (index // 2) % 6 if index < 24 else (index - 28) % 6
        color = palette[side].astype(float)
        if index >= 28:
            color = color * .72 + np.array([188, 255, 223]) * .28
        colors.append([*np.clip(color + rng.uniform(-3, 3), 0, 255).astype(int), 255])
    mesh.visual.face_colors = colors
    return mesh


def crystal_cluster():
    pieces = [
        paint(ring_solid([(1.21, 0), (1.34, .065), (1.34, .145), (1.26, .205)]),
              [29, 44, 49], 4),
        paint(ring_solid([(1.20, .205), (1.20, .235)]), [83, 152, 126], 3),
        paint(ring_solid([(1.15, .235), (1.15, .34), (1.04, .41)]), [38, 57, 60], 4),
    ]
    arrangements = [
        (.40, 2.65, (-.10, .18, .39), (-.12, .07), .23),
        (.31, 1.90, (.48, .21, .39), (.31, .06), .63),
        (.32, 1.68, (-.52, .04, .39), (-.30, .01), .05),
        (.28, 1.48, (.12, -.40, .39), (.10, -.22), .43),
        (.23, 1.03, (-.43, -.47, .39), (-.21, -.17), .22),
        (.22, .87, (.60, -.34, .39), (.25, -.15), .72),
        (.18, 1.34, (-.47, .49, .39), (-.19, .19), .36),
        (.13, .48, (.04, -.78, .39), (.04, -.10), .17),
        (.11, .41, (.78, .06, .39), (.10, .02), .54),
    ]
    pieces.extend(crystal(r, h, c, lean, angle, SEED + i)
                  for i, (r, h, c, lean, angle) in enumerate(arrangements))
    return trimesh.util.concatenate(pieces)


def beveled_hexahedron(corners, bevel=.065):
    """Truncate each vertex of an eight-corner solid along its three edges."""
    points = []
    for index, vertex in enumerate(corners):
        for bit in (1, 2, 4):
            neighbor = corners[index ^ bit]
            points.append(vertex * (1 - bevel) + neighbor * bevel)
    return trimesh.convex.convex_hull(np.asarray(points))


def basalt_arch():
    rng = np.random.default_rng(SEED)
    pieces = []
    for side in (-1, 1):
        for course in range(3):
            half = np.array([.285, .39, .278])
            corners = np.array([[(-1 if i & 1 else 1) * half[0],
                                 (-1 if i & 2 else 1) * half[1],
                                 (-1 if i & 4 else 1) * half[2]] for i in range(8)])
            corners += rng.uniform(-.016, .016, corners.shape)
            block = beveled_hexahedron(corners, .075)
            block.apply_translation([side * 1.18, 0, .32 + course * .568])
            pieces.append(paint(block, [80 + 4 * course, 89 + 4 * course, 87 + 4 * course], 9,
                                seed=SEED + course))
        foot = ring_solid([(.45, 0), (.48, .06), (.45, .14)], sides=4, angle=np.pi / 4)
        foot.apply_translation([side * 1.18, 0, 0])
        pieces.append(paint(foot, [58, 67, 64], 5))
    spring = 1.74
    for index in range(9):
        a = index * np.pi / 9 + .006
        b = (index + 1) * np.pi / 9 - .006
        outer = 1.48 + rng.uniform(-.025, .025)
        corners = np.array([[radius * np.cos(theta), depth, spring + radius * np.sin(theta)]
                            for depth in (-.37, .37)
                            for radius in (.90, outer)
                            for theta in (a, b)])
        block = beveled_hexahedron(corners, .075)
        rgb = [115, 121, 109] if index == 4 else [85, 96, 92]
        paint(block, rgb, 10, seed=SEED + index)
        colors = block.visual.face_colors.copy()
        moss = (block.face_normals[:, 2] > .55) & (block.triangles_center[:, 2] > 2.5)
        colors[moss] = [78, 108, 66, 255]
        block.visual.face_colors = colors
        pieces.append(block)
    return trimesh.util.concatenate(pieces)


def preview_model(mesh, size=512, eye=(4, -8, 4.5)):
    """Text-free orthographic diffuse preview of the reloaded export, not PBR."""
    ss = 2
    image = Image.new("RGBA", (size * ss, size * ss))
    draw = ImageDraw.Draw(image)
    forward = np.asarray(eye, dtype=float)
    forward /= np.linalg.norm(forward)
    right = np.cross([0, 0, 1], forward)
    right /= np.linalg.norm(right)
    up = np.cross(forward, right)
    projected = mesh.vertices @ np.column_stack([right, up, forward])
    low, high = projected[:, :2].min(axis=0), projected[:, :2].max(axis=0)
    scale = size * .83 / max(high - low)
    xy = (projected[:, :2] - (low + high) / 2) * [scale, -scale] + [size / 2, size * .48]
    light = np.array([-3, -5, 8], dtype=float)
    light /= np.linalg.norm(light)
    shade = .61 + .39 * np.maximum(0, mesh.face_normals @ light)
    colors = np.clip(mesh.visual.face_colors[:, :3] * shade[:, None], 0, 255).astype(np.uint8)
    polygons = xy[mesh.faces] * ss
    depth = projected[mesh.faces, 2].mean(axis=1)
    for face in np.argsort(depth, kind="stable"):
        if mesh.face_normals[face] @ forward > 0:
            draw.polygon([tuple(p) for p in polygons[face]], fill=(*colors[face], 255))
    return image.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


def rune_token(size=384):
    n = size * 3
    y, x = np.mgrid[:n, :n] / n - .5
    radius = np.hypot(x, y)
    light = np.clip(.65 - .55 * x - .65 * y, 0, 1)
    grain = .014 * np.sin(x * 760 + np.sin(y * 190)) * np.sin(y * 630)
    t = np.clip(light + grain, 0, 1)[..., None]
    rgb = np.array([109, 57, 23]) * (1 - t) + np.array([244, 195, 91]) * t
    inner = radius < .335
    rgb[inner] *= .76
    image = Image.fromarray(np.dstack([rgb, (radius < .43) * 255]).astype(np.uint8))
    d = ImageDraw.Draw(image)

    def circle(r, color, width):
        d.ellipse(((.5 - r) * n, (.5 - r) * n, (.5 + r) * n, (.5 + r) * n),
                  outline=color, width=max(1, round(width * n)))

    circle(.428, (74, 39, 19, 255), .012)
    circle(.414, (249, 205, 116, 255), .013)
    circle(.391, (121, 72, 29, 255), .008)
    circle(.352, (252, 199, 91, 255), .009)
    circle(.336, (68, 40, 23, 255), .009)
    circle(.322, (211, 146, 55, 255), .004)

    def engraved(points, width=.015):
        xy = [((px + .5) * n, (py + .5) * n) for px, py in points]
        d.line([(px, py + .006 * n) for px, py in xy], fill=(255, 208, 116, 255),
               width=round(width * n), joint="curve")
        d.line(xy, fill=(77, 43, 25, 255), width=round(width * n), joint="curve")
        d.line([(px, py + .001 * n) for px, py in xy], fill=(137, 81, 32, 255),
               width=max(1, round(width * n * .35)), joint="curve")

    # A geometric sigil, not lettering or a baked-in caption.
    engraved([(0, -.255), (.11, -.065), (0, .065), (-.11, -.065), (0, -.255)], .018)
    engraved([(0, -.13), (0, .25)], .019)
    engraved([(-.195, -.14), (-.175, .075), (0, .20), (.175, .075), (.195, -.14)])
    engraved([(-.25, .005), (-.14, .19), (0, .265), (.14, .19), (.25, .005)], .010)
    for side in (-1, 1):
        engraved([(side * .15, -.21), (side * .21, -.24), (side * .24, -.18)], .010)
    rng = np.random.default_rng(SEED)
    for i in range(32):
        angle = i * 2 * np.pi / 32
        length = .015 if i % 4 else .025
        engraved([(.366 * np.cos(angle), .366 * np.sin(angle)),
                  ((.366 + length) * np.cos(angle), (.366 + length) * np.sin(angle))], .004)
    for _ in range(42):
        angle, r = rng.uniform(0, 2 * np.pi), rng.uniform(.285, .40)
        x0, y0 = (.5 + r * np.cos(angle)) * n, (.5 + r * np.sin(angle)) * n
        d.line((x0, y0, x0 + n * .008, y0 - n * .002), fill=(238, 179, 80, 130), width=2)
    return image.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


def periodic_noise(x, y, seed, high=7):
    rng = np.random.default_rng(seed)
    result = np.zeros_like(x)
    weight = 0
    for _ in range(20):
        a, b = rng.integers(1, high + 1, 2)
        amplitude = 1 / np.sqrt(a * a + b * b)
        result += amplitude * np.sin(2 * np.pi * (a * x + b * y) + rng.uniform(0, 2 * np.pi))
        weight += amplitude
    return result / weight


def moss_tile(size=256, offset=(0, 0)):
    axis = (np.arange(size) + .5) / size
    x, y = np.meshgrid((axis + offset[0]) % 1, (axis + offset[1]) % 1)
    broad = periodic_noise(x, y, SEED)
    fine = periodic_noise(x, y, SEED + 1, high=50)
    wx = x + .021 * np.sin(2 * np.pi * y * 3) + broad * .035
    wy = y + .018 * np.sin(2 * np.pi * x * 4) + broad * .032
    rng = np.random.default_rng(SEED)
    distances = []
    for row in range(5):
        for col in range(5):
            cx, cy = (np.array([col + .5, row + .5]) + rng.uniform(-.28, .28, 2)) / 5
            dx, dy = (wx - cx + .5) % 1 - .5, (wy - cy + .5) % 1 - .5
            distances.append(np.hypot(dx, dy))
    distances = np.stack(distances)
    nearest = np.argmin(distances, axis=0)
    ordered = np.partition(distances, 1, axis=0)
    gap = ordered[1] - ordered[0]
    height = np.clip((gap - .009) / .035, 0, 1)
    slope = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
             + np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0))
    tone = np.clip(.51 + .16 * height + broad * .55 + fine * .30 - slope * .20
                   + rng.uniform(-.07, .07, 25)[nearest], 0, 1)[..., None]
    stone = np.array([43, 51, 45]) * (1 - tone) + np.array([152, 159, 130]) * tone
    moss_amount = np.clip((.020 - gap + broad * .065 + fine * .032) * 52, 0, 1)
    moss_tone = np.clip(.42 + broad + fine * 1.7, 0, 1)[..., None]
    moss = np.array([24, 49, 28]) * (1 - moss_tone) + np.array([118, 151, 61]) * moss_tone
    rgb = stone * (1 - moss_amount[..., None]) + moss * moss_amount[..., None]
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.full(x.shape, 255)]).astype(np.uint8))


def effect_rgba(energy, hot, edge, warm=True):
    alpha = np.clip(energy, 0, 1) * edge
    heat = np.clip(hot, 0, 1)
    rgb = np.stack([245 + heat * 10, 74 + heat * 160, 17 + heat * 133], axis=-1)
    rgba = np.rint(np.dstack([rgb, alpha * 255])).astype(np.uint8)
    rgba[rgba[..., 3] == 0, :3] = 0
    return Image.fromarray(rgba)


def ember_frame(size, phase, seed=SEED):
    axis = (np.arange(size) + .5) / size * 2 - 1
    x, y = np.meshgrid(axis, axis)
    h = (.80 - y) / 1.58
    turn = 2 * np.pi * phase
    energy, hot = np.zeros_like(x), np.zeros_like(x)
    for index, (offset, height, width) in enumerate([(-.16, .73, .14), (0, 1., .20), (.16, .61, .12)]):
        level = h / height
        bend = offset + .06 * np.sin(9 * h - turn + index * 2) * h
        spread = width * np.clip(1 - level, 0, 1) ** .72 + .007
        spread *= 1 + .18 * np.sin(18 * h - 2 * turn + index)
        body = np.exp(-((x - bend) / spread) ** 2)
        envelope = np.clip(h * 15, 0, 1) * np.clip((1 - level) * 7, 0, 1)
        energy += body * envelope * .90
        hot += body ** 2 * envelope * (1 - np.clip(level, 0, 1))
        energy += .16 * np.exp(-((x - bend) / (spread * 1.8)) ** 2) * envelope
    rng = np.random.default_rng(seed)
    for _ in range(24):
        age = (phase + rng.uniform(0, 1)) % 1
        origin, drift, radius, sway = rng.uniform(-.27, .27), rng.uniform(-.30, .30), rng.uniform(.009, .019), rng.uniform(0, 2 * np.pi)
        px = origin + drift * age + .055 * np.sin(2 * np.pi * age + sway)
        py = .71 - age * 1.55
        particle = np.exp(-(((x - px) / radius) ** 2 + ((y - py) / (radius * 1.8)) ** 2))
        particle *= np.sin(np.pi * age) ** 1.3
        energy += particle * 1.2
        hot += particle * .7
    edge = np.clip((.96 - np.maximum(np.abs(x), np.abs(y))) / .07, 0, 1)
    return effect_rgba(energy, hot, edge)


def shockwave_frame(size, phase, seed=SEED):
    axis = (np.arange(size) + .5) / size * 2 - 1
    x, y = np.meshgrid(axis, axis)
    radius, angle = np.hypot(x, y), np.arctan2(y, x)
    envelope = np.sin(np.pi * phase) ** .85
    ring = .08 + .76 * (1 - (1 - phase) ** 1.25)
    warped = radius + .006 * np.sin(angle * 9 + phase * 3)
    core = np.exp(-((warped - ring) / (.014 + .014 * (1 - phase))) ** 2)
    glow = np.exp(-((warped - ring) / .065) ** 2)
    echo = np.exp(-((radius - ring * .84) / .009) ** 2) * (.5 + .5 * np.sin(angle * 12)) ** 4
    energy = envelope * (.94 * core + .30 * glow + .22 * echo)
    rng = np.random.default_rng(seed)
    for _ in range(18):
        theta = rng.uniform(0, 2 * np.pi)
        r = ring * rng.uniform(1.04, 1.13)
        energy += envelope * .65 * np.exp(-((x - r * np.cos(theta)) ** 2
                                           + (y - r * np.sin(theta)) ** 2) / .00015)
    edge = np.clip((.96 - radius) / .055, 0, 1)
    return effect_rgba(energy, core * .95 + glow * .15, edge)


def ui_confirm(rate=48000):
    rng = np.random.default_rng(SEED)
    t = np.arange(round(.78 * rate)) / rate
    samples = np.zeros_like(t)
    for frequency, onset, decay in [(659.255, 0, .12), (830.609, .105, .15), (987.767, .21, .22)]:
        time = np.maximum(t - onset, 0)
        envelope = (1 - np.exp(-time / .003)) * np.exp(-time / decay)
        phase = 2 * np.pi * frequency * time
        samples += .34 * envelope * (np.sin(phase) + .14 * np.sin(2 * phase + rng.uniform(-.1, .1)))
    samples -= samples.mean()
    fade = round(rate * .045)
    samples[:160] *= np.linspace(0, 1, 160)
    samples[-fade:] *= np.linspace(1, 0, fade) ** 2
    samples *= min(1., 10 ** (-3 / 20) / np.max(np.abs(samples)))
    return np.rint(samples * 32767).astype(np.int16)


def inspect_mesh(mesh):
    require(0 < len(mesh.faces) < 3000, "Mesh triangle budget exceeded")
    require(np.isfinite(mesh.vertices).all(), "Nonfinite mesh positions")
    require(np.min(mesh.area_faces) > 1e-10, "Degenerate mesh triangles")
    require(mesh.faces.min() >= 0 and mesh.faces.max() < len(mesh.vertices), "Invalid face index")
    require(np.allclose(np.linalg.norm(mesh.face_normals, axis=1), 1), "Invalid face normals")
    colors = mesh.visual.face_colors
    require(colors.shape == (len(mesh.faces), 4) and (colors[:, 3] == 255).all(), "Invalid mesh colors")
    require(len(np.unique(colors, axis=0)) > 3, "Missing face palette")
    welded = mesh.copy()
    welded.merge_vertices(merge_tex=True, merge_norm=True)
    require(welded.is_watertight and welded.is_winding_consistent and welded.volume > 0,
            "Mesh must be closed, consistently wound, and positive-volume after welding")
    return {"triangles": len(mesh.faces), "vertices": len(mesh.vertices),
            "welded_vertices": len(welded.vertices), "watertight_after_weld": True,
            "winding_consistent": True, "volume_m3": float(welded.volume),
            "bounds_z_up": mesh.bounds.tolist(), "face_colors": len(np.unique(colors, axis=0))}


def aperture_clear(mesh, x, z):
    """Intersect a front-to-back ray with triangles, without optional rtree."""
    origin, direction = np.array([x, -3, z]), np.array([0., 1., 0.])
    triangles = mesh.triangles
    e1, e2 = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    h = np.cross(np.broadcast_to(direction, e2.shape), e2)
    det = np.einsum("ij,ij->i", e1, h)
    valid = np.abs(det) > 1e-9
    inv = np.divide(1., det, out=np.zeros_like(det), where=valid)
    s = origin - triangles[:, 0]
    u = inv * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    v = inv * (q @ direction)
    distance = inv * np.einsum("ij,ij->i", e2, q)
    hit = valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (distance > 0) & (distance < 6)
    return not hit.any()


def check_png(path, size, transparent=True):
    with Image.open(path) as image:
        image.load()
        require(image.mode == "RGBA" and image.size == size, f"Invalid RGBA image: {path.name}")
        pixels = np.asarray(image)
        require(pixels[..., 3].max() > 0, f"Empty image: {path.name}")
        if transparent:
            require(pixels[..., 3].min() == 0 and np.any((pixels[..., 3] > 0) & (pixels[..., 3] < 255)),
                    f"Missing transparent or antialiased pixels: {path.name}")
        return pixels.copy()


def export_model(directory, mesh, identifier):
    inspect_mesh(mesh)
    exported = mesh.copy().apply_transform(Z_TO_Y)
    exported.metadata.update(units="m", source_up_axis="Z", up_axis="Y")
    exported.unmerge_vertices()
    exported.vertex_normals = np.repeat(exported.face_normals, 3, axis=0)
    exported.export(directory / "model.glb", include_normals=True)
    mesh.export(directory / "model.obj", include_color=False, include_texture=False,
                include_normals=False, header="")
    # Browser payload and preview are made from the actual GLB, never the source mesh.
    reloaded = trimesh.load_scene(directory / "model.glb").to_mesh()
    require(np.allclose(reloaded.bounds, exported.bounds, atol=1e-6), "GLB Y-up bounds changed")
    reloaded.apply_transform(np.linalg.inv(Z_TO_Y))
    metrics = inspect_mesh(reloaded)
    require(np.allclose(reloaded.bounds, mesh.bounds, atol=1e-6), "GLB Z-up round-trip changed bounds")
    require(np.array_equal(reloaded.visual.face_colors, mesh.visual.face_colors), "GLB face colors changed")
    obj = trimesh.load_scene(directory / "model.obj").to_mesh()
    require(len(obj.faces) == len(mesh.faces) and np.allclose(obj.bounds, mesh.bounds, atol=1e-6),
            "OBJ geometry or Z-up bounds changed")
    if identifier == "basalt-arch":
        samples = [(0, .5), (0, 1.5), (-.5, 1.3), (.5, 1.3), (0, 2.3)]
        require(all(aperture_clear(reloaded, x, z) for x, z in samples), "Arch opening is obstructed")
        require(not aperture_clear(reloaded, 0, 3.0), "Arch crown missing")
        metrics["opening_rays_clear"] = len(samples)
    payload = {"vertices": reloaded.vertices.tolist(), "faces": reloaded.faces.tolist(),
               "colors": reloaded.visual.face_colors.tolist(), "normals": reloaded.face_normals.tolist()}
    write_json(directory / "mesh.json", payload, compact=True)
    eye = (3, -9, 3.7) if identifier == "basalt-arch" else (4, -8, 4.5)
    preview_model(reloaded, eye=eye).save(directory / "preview.png")
    check_png(directory / "preview.png", (512, 512))
    return metrics


def export_effect(directory, render, loop):
    phases = [i / 16 if loop else i / 15 for i in range(16)]
    frames = [render(128, p, SEED) for p in phases]
    arrays = [np.asarray(image) for image in frames]
    require(all(np.array_equal(array, np.asarray(render(128, p, SEED)))
                for array, p in zip(arrays, phases)), "VFX rerender differs")
    if loop:
        require(np.array_equal(np.asarray(render(128, 0, SEED)), np.asarray(render(128, 1, SEED))),
                "VFX field is not periodic at phase 0/1")
    else:
        require(arrays[0][..., 3].max() == 0 and arrays[-1][..., 3].max() == 0,
                "One-shot must start and end transparent")
    atlas = Image.new("RGBA", (512, 512))
    for i, frame in enumerate(frames):
        atlas.paste(frame, ((i % 4) * 128, (i // 4) * 128))
    atlas.save(directory / "atlas.png")
    peak = int(np.argmax([a[..., 3].sum() for a in arrays]))
    frames[peak].save(directory / "preview.png")
    reopened = check_png(directory / "atlas.png", (512, 512))
    check_png(directory / "preview.png", (128, 128))
    for i, array in enumerate(arrays):
        y, x = (i // 4) * 128, (i % 4) * 128
        require(np.array_equal(reopened[y:y + 128, x:x + 128], array), "Atlas changed frame alpha")
        require(np.concatenate([array[0, :, 3], array[-1, :, 3], array[:, 0, 3], array[:, -1, 3]]).max() == 0,
                "VFX touches frame border")
        if loop or 0 < i < 15:
            require(array[..., 3].max() > 0, "Unexpected empty VFX frame")
    steps = [float(np.mean(np.abs(arrays[i].astype(float) - arrays[i - 1].astype(float))))
             for i in range(1, 16)]
    return {"frame_size": [128, 128], "frame_count": 16, "grid": [4, 4], "fps": 16,
            "duration_seconds": 1.0, "loop": loop, "order": "row-major, top-left",
            "padding_pixels": 0, "alpha": "straight", "blend": "alpha; additive optional in engine",
            "sample_phases": phases, "peak_frame": peak, "peak_measure": "maximum integrated alpha",
            "deterministic_rerender": True, "periodic_endpoint_checked": loop,
            "mean_adjacent_rgba_delta": float(np.mean(steps)),
            "wrap_rgba_delta": float(np.mean(np.abs(arrays[0].astype(float) - arrays[-1].astype(float))))}


def export_sound(directory, samples):
    wavfile.write(directory / "sound.wav", 48000, samples)
    rate, reopened = wavfile.read(directory / "sound.wav")
    require(rate == 48000 and reopened.dtype == np.int16 and reopened.ndim == 1, "Expected mono 48 kHz PCM16")
    require(np.array_equal(samples, reopened), "WAV PCM changed on export")
    normalized = reopened.astype(np.float64) / 32768
    peak, rms = np.max(np.abs(normalized)), np.sqrt(np.mean(normalized ** 2))
    require(0.001 < peak <= 10 ** (-3 / 20) + 1 / 32768 and rms > .0001,
            "WAV must be non-silent with at least 3 dB headroom")
    require(abs(normalized.mean()) < .001 and normalized[0] == normalized[-1] == 0,
            "WAV DC or endpoint check failed")
    bins = np.array([np.sqrt(np.mean(part ** 2)) for part in np.array_split(normalized, 96)])
    waveform = np.round(bins / bins.max(), 6).tolist()
    return {"format": "PCM16 WAV", "sample_rate": rate, "channels": 1,
            "frames": len(reopened), "duration_seconds": len(reopened) / rate,
            "peak_dbfs": float(20 * np.log10(peak)), "rms_dbfs": float(20 * np.log10(rms)),
            "dc": float(normalized.mean()), "loop": False,
            "waveform": "96 RMS bins, normalized by maximum bin RMS"}, waveform


def archive_collection(out, assets):
    # Explicit allowlist: no frontend, legacy exports, environment, or private files.
    files = [ROOT / RECIPE, ROOT / "requirements-code-assets.txt"]
    files.extend(ROOT / s for s in STARTERS.values())
    files.append(out / "catalog.json")
    for asset in assets:
        files.extend(p for p in (out / "assets" / asset["id"]).iterdir() if p.is_file())
    with zipfile.ZipFile(out / "asset-collection.zip", "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in sorted(files, key=lambda p: p.relative_to(ROOT).as_posix()):
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), (2026, 11, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(out / "asset-collection.zip") as archive:
        require(archive.testzip() is None, "ZIP integrity failure")
        require(set(archive.namelist()) == {p.relative_to(ROOT).as_posix() for p in files},
                "ZIP allowlist mismatch")


def generate(out):
    out = out.resolve()
    require(out.is_relative_to(ROOT) and out != ROOT, "--out must be a child directory of the repository/extracted pack")
    for name in ("assets", "catalog.json", "asset-collection.zip"):
        path = out / name
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite {path}; choose --out new-dir")
    starters = load_starters()
    versions = {"python": platform.python_version(), **{p: version(p) for p in PACKAGES}}
    # Existing gallery parent (including independently authored frontend) is allowed.
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=False)
    definitions = [
        ("crystal-cluster", "Emerald Spire", "3d", "Mint-emerald crystal facets rise from a dark, stepped hexagonal plinth.", ["crystal", "faceted", "hero prop", "mint"]),
        ("lantern", "Wayfinder Lantern", "3d", "An open arched metal lantern with a brass roof and a suspended cyan crystal.", ["lantern", "low-poly", "hollow", "prop"]),
        ("basalt-arch", "Basalt Passage", "3d", "Beveled basalt blocks and moss-capped voussoirs frame a genuine open passage.", ["stone", "arch", "modular", "moss"]),
        ("potion", "Tidal Elixir", "2d", "A curved glass potion icon with cyan liquid, bubbles, a cork, and a cool metal collar.", ["icon", "potion", "RGBA", "cyan"]),
        ("rune-token", "Sunward Token", "2d", "A warm gold medallion with concentric rims and an inset geometric sigil.", ["icon", "gold", "engraved", "token"]),
        ("moss-tile", "Overgrown Flagstone", "2d", "Periodic stone cells, beveled edges, and moss-filled joints form a repeating RGBA tile.", ["tile", "seamless", "moss", "stone"]),
        ("arcane-portal", "Arcane Aperture", "vfx", "A looping azure field with a warped energy ring and stable orbiting sparks.", ["portal", "loop", "magic", "blue"]),
        ("ember-plume", "Ember Plume", "vfx", "Three flowing flame tongues and seeded rising embers in a periodic warm plume.", ["fire", "embers", "loop", "warm"]),
        ("shockwave", "Solar Shockwave", "vfx", "A one-shot expanding amber ring with a trailing echo and radial sparks.", ["impact", "ring", "one-shot", "amber"]),
        ("metal-impact", "Forged Impact", "sfx", "A seeded modal metal strike with a short filtered transient and a damped tail.", ["metal", "impact", "mono", "modal"]),
        ("glass-chime", "Glass Harmonic", "sfx", "High-pitched inharmonic glass modes with a soft onset and a decaying tail.", ["glass", "chime", "mono", "bright"]),
        ("ui-confirm", "Quiet Affirmation", "sfx", "Three ascending major-triad tones with gentle attacks and overlapping decays.", ["UI", "confirm", "ascending", "three-tone"]),
    ]
    assets, summaries = [], []
    for identifier, name, category, description, tags in definitions:
        directory = out / "assets" / identifier
        directory.mkdir()
        prefix = directory.relative_to(ROOT).as_posix()
        entry = {"id": identifier, "name": name, "category": category, "description": description,
                 "tags": tags, "seed": SEED, "recipe": RECIPE, "manifest": prefix + "/manifest.json"}
        parameters = {"seed": SEED}
        starter = None
        if category == "3d":
            if identifier == "crystal-cluster":
                mesh = crystal_cluster()
                parameters.update(crystals=9, base="three stepped hexagonal tiers", tallest_crystal_m=2.65)
            elif identifier == "lantern":
                mesh = starters["3d"].build_model(SEED)
                starter = "3d"
            else:
                mesh = basalt_arch()
                parameters.update(voussoirs=9, courses_per_pier=3, inner_radius_m=.90, spring_height_m=1.74)
            metrics = export_model(directory, mesh, identifier)
            entry.update(file=prefix + "/model.glb", preview=prefix + "/preview.png", model=prefix + "/mesh.json",
                         meta=f"{metrics['triangles']} tris · GLB / OBJ",
                         stats={"Triangles": str(metrics["triangles"]), "Vertices": str(metrics["welded_vertices"]),
                                "Formats": "GLB / OBJ", "Colors": str(metrics["face_colors"]), "Units": "meters"})
            details = {"mesh": metrics, "axes": {"source": "Z", "glb_export": "Y", "obj_export": "Z", "mesh_json": "Z"},
                       "format_notes": {"glb": "Face colors as split vertex colors; flat normals, meters, no UVs or rig.",
                                        "obj": "Z-up geometry only; no colors, textures or MTL.",
                                        "mesh_json": "Reloaded GLB inverse-rotated to Z-up; RGBA bytes per face, unit normals.",
                                        "preview": "512px transparent Pillow orthographic diffuse preview; no text, not PBR.",
                                        "topology": "Separate closed components; watertightness measured after positional welding."}}
        elif category == "2d":
            if identifier == "potion":
                image = starters["2d"].draw_icon(384, SEED, 185)
                repeat = starters["2d"].draw_icon(384, SEED, 185)
                parameters.update(size=384, hue=185)
                starter = "2d"
            elif identifier == "rune-token":
                image, repeat = rune_token(), rune_token()
                parameters.update(size=384, palette="warm gold", supersampling=3)
            else:
                image, repeat = moss_tile(), moss_tile()
                parameters.update(size=256, stone_grid=[5, 5], periodic_axes=["x", "y"])
                require(np.array_equal(np.asarray(image), np.asarray(moss_tile(offset=(1, 1)))), "Moss field failed periodic shift")
            image.save(directory / "image.png")
            pixels = check_png(directory / "image.png", image.size, transparent=identifier != "moss-tile")
            require(np.array_equal(pixels, np.asarray(repeat)), "Raster rerender differs")
            size = image.width
            entry.update(file=prefix + "/image.png", preview=prefix + "/image.png", meta=f"{size} × {size} · RGBA",
                         stats={"Resolution": f"{size} × {size}", "Format": "RGBA PNG", "Tiling": "XY periodic" if identifier == "moss-tile" else "None"})
            details = {"format": "RGBA PNG", "size": list(image.size), "alpha": "straight",
                       "deterministic_rerender": True, "tileable": identifier == "moss-tile"}
            if identifier == "moss-tile":
                tile_preview = Image.new("RGBA", (size * 3, size * 3))
                for row in range(3):
                    for col in range(3):
                        tile_preview.paste(image, (col * size, row * size))
                tile_preview.save(directory / "preview.png")
                rgb = pixels[..., :3].astype(float)
                details.update(preview_note="preview.png is a 3x3 tiling check; catalog displays the single tile.",
                               alpha_note="Opaque RGBA color texture, not a cutout.", periodic_shift_checked=True,
                               seam_delta_xy=[float(np.abs(rgb[:, 0] - rgb[:, -1]).mean()), float(np.abs(rgb[0] - rgb[-1]).mean())],
                               adjacent_delta_xy=[float(np.abs(np.diff(rgb, axis=1)).mean()), float(np.abs(np.diff(rgb, axis=0)).mean())])
        elif category == "vfx":
            render = {"arcane-portal": starters["vfx"].frame, "ember-plume": ember_frame, "shockwave": shockwave_frame}[identifier]
            loop = identifier != "shockwave"
            starter = "vfx" if identifier == "arcane-portal" else None
            details = export_effect(directory, render, loop)
            parameters.update(frame_size=128, frames=16, columns=4, fps=16)
            entry.update(file=prefix + "/atlas.png", preview=prefix + "/preview.png", atlas=prefix + "/atlas.png",
                         frameSize=128, frames=16, columns=4, fps=16, loop=loop, meta="16 frames · 128 × 128",
                         stats={"Frames": "16", "Frame size": "128 × 128", "Atlas": "512 × 512", "FPS": "16", "Playback": "Loop" if loop else "One-shot"})
        else:
            if identifier == "ui-confirm":
                samples, repeat = ui_confirm(), ui_confirm()
                parameters.update(frequencies_hz=[659.255, 830.609, 987.767], onsets_seconds=[0, .105, .21], duration=.78)
            else:
                starter = "sfx"
                frequency, material, duration, gain = (420., "metal", 1.2, .62) if identifier == "metal-impact" else (1250., "glass", 1.8, .55)
                parameters.update(frequency=frequency, material=material, duration=duration, rate=48000, gain=gain)
                samples = starters["sfx"].synthesize(SEED, duration, 48000, frequency, material, gain)
                repeat = starters["sfx"].synthesize(SEED, duration, 48000, frequency, material, gain)
            require(np.array_equal(samples, repeat), "Audio rerender differs")
            details, waveform = export_sound(directory, samples)
            details["deterministic_rerender"] = True
            entry.update(file=prefix + "/sound.wav", waveform=waveform, duration=details["duration_seconds"],
                         meta=f"{details['duration_seconds']:.2f} s · 48 kHz / 16-bit",
                         stats={"Duration": f"{details['duration_seconds']:.2f} s", "Sample rate": "48 kHz", "Encoding": "PCM16 mono",
                                "Peak": f"{details['peak_dbfs']:.2f} dBFS", "RMS": f"{details['rms_dbfs']:.2f} dBFS"})
        copy_new(SOURCE, directory / "generate_gallery.py")
        if starter:
            copy_new(ROOT / STARTERS[starter], directory / "starter.py")
        manifest = {"id": identifier, "category": category, "parameters": parameters, "versions": versions,
                    "recipe": RECIPE, "source_snapshot": "generate_gallery.py",
                    "starter": STARTERS[starter] if starter else None,
                    "reproduce": {"requirements": "requirements-code-assets.txt",
                                  "command": "python fx_pipeline/generate_gallery.py --out new-dir",
                                  "note": "Run from extracted pack with pinned dependencies. Existing collections are never overwritten."},
                    "review": "Structural checks only; listening, animation playback, and target-engine review remain pending.",
                    **details,
                    "source_dependencies_sha256": {RECIPE: sha256(SOURCE), "requirements-code-assets.txt": sha256(ROOT / "requirements-code-assets.txt"),
                                                   **{rel: sha256(ROOT / rel) for rel in STARTERS.values()}},
                    "sha256": {p.name: sha256(p) for p in sorted(directory.iterdir()) if p.is_file()}}
        write_json(directory / "manifest.json", manifest)
        for key in ("file", "preview", "model", "atlas", "manifest", "recipe"):
            if key in entry:
                require((ROOT / entry[key]).is_file(), f"Broken catalog path: {entry[key]}")
        require(all(isinstance(v, str) for v in entry["stats"].values()), "Catalog stats must be strings")
        assets.append(entry)
        summaries.append({"id": identifier, **entry["stats"]})
    require(len(assets) == 12 and all(sum(a["category"] == c for a in assets) == 3 for c in ("3d", "2d", "vfx", "sfx")),
            "Expected exactly three assets in each category")
    write_json(out / "catalog.json", {"assets": assets})
    archive_collection(out, assets)
    return {"output": str(out), "assets": len(assets), "seed": SEED,
            "zip_bytes": (out / "asset-collection.zip").stat().st_size, "validated": summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("gallery"), help="New collection directory relative to repository root; parent may exist")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        result = generate(out)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Gallery generation failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
