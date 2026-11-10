#!/usr/bin/env python3
"""Export a separate collection of eight code-only gameplay studies."""
from __future__ import annotations

import argparse
import json
import platform
import sys
import zipfile
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image

SOURCE = Path(__file__).resolve()
ROOT = next(p for p in SOURCE.parents if (p / "requirements-code-assets.txt").is_file())
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from asset_pipeline import generate_gallery as base
from asset_pipeline import gallery_expansion_effects as effects
from asset_pipeline import gallery_expansion_visuals as visuals

RECIPE = "asset_pipeline/generate_gallery_expansion.py"
SOURCES = [RECIPE, "asset_pipeline/gallery_expansion_visuals.py", "asset_pipeline/gallery_expansion_effects.py",
           base.RECIPE, "asset_pipeline/__init__.py", "requirements-code-assets.txt", *base.STARTERS.values()]
DEFINITIONS = [
    ("pine-tree", "3d", visuals.pine_tree),
    ("treasure-chest", "3d", visuals.treasure_chest),
    ("shield-icon", "2d", visuals.shield_icon),
    ("dialog-panel", "2d", visuals.dialog_panel),
    ("dust-puff", "vfx", effects.dust_puff_frame),
    ("forked-lightning", "vfx", effects.lightning_frame),
    ("gravel-step", "sfx", effects.gravel_step),
    ("charge-release", "sfx", effects.charge_release),
]


def archive_collection(out, assets):
    files = [ROOT / relative for relative in SOURCES] + [out / "catalog.json"]
    for asset in assets:
        files.extend(p for p in (out / "assets" / asset["id"]).iterdir() if p.is_file())
    with zipfile.ZipFile(out / "asset-collection.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), (2026, 11, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(out / "asset-collection.zip") as archive:
        base.require(archive.testzip() is None, "Collection ZIP failed integrity check")
        base.require(set(archive.namelist()) == {p.relative_to(ROOT).as_posix() for p in files}, "ZIP allowlist mismatch")


def nine_slice(image, width, height, inset=64):
    base.require(min(width, height) >= 2 * inset, "Target is smaller than fixed corners")
    source_x, source_y = [0, inset, image.width - inset, image.width], [0, inset, image.height - inset, image.height]
    target_x, target_y = [0, inset, width - inset, width], [0, inset, height - inset, height]
    result = Image.new("RGBA", (width, height))
    for row in range(3):
        for col in range(3):
            size = (target_x[col + 1] - target_x[col], target_y[row + 1] - target_y[row])
            if min(size) == 0:
                continue
            patch = image.crop((source_x[col], source_y[row], source_x[col + 1], source_y[row + 1]))
            if patch.size != size:
                patch = patch.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
            result.paste(patch, (target_x[col], target_y[row]))
    return result


def depth_preview(mesh, size=512):
    n = size * 2
    eye = np.array([4., -8., 4.5])
    eye /= np.linalg.norm(eye)
    right = np.cross([0, 0, 1], eye)
    right /= np.linalg.norm(right)
    up = np.cross(eye, right)
    projected = mesh.vertices @ np.column_stack([right, up, eye])
    low, high = projected[:, :2].min(axis=0), projected[:, :2].max(axis=0)
    xy = (projected[:, :2] - (low + high) / 2) * [n * .83 / max(high - low), -n * .83 / max(high - low)] + [n / 2, n * .48]
    pixels = np.zeros((n, n, 4), dtype=np.uint8)
    depth = np.full((n, n), -np.inf)
    light = np.array([-3., -5., 8.])
    light /= np.linalg.norm(light)
    shades = .61 + .39 * np.maximum(0, mesh.face_normals @ light)
    for index, indices in enumerate(mesh.faces):
        if mesh.face_normals[index] @ eye <= 0:
            continue
        a, b, c = xy[indices]
        xmin, ymin = np.maximum(0, np.floor(np.min([a, b, c], axis=0)).astype(int))
        xmax, ymax = np.minimum(n - 1, np.ceil(np.max([a, b, c], axis=0)).astype(int))
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-10 or xmin > xmax or ymin > ymax:
            continue
        yy, xx = np.mgrid[ymin:ymax + 1, xmin:xmax + 1] + .5
        wa = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / denominator
        wb = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / denominator
        wc = 1 - wa - wb
        z = wa * projected[indices[0], 2] + wb * projected[indices[1], 2] + wc * projected[indices[2], 2]
        region = depth[ymin:ymax + 1, xmin:xmax + 1]
        mask = (wa >= -1e-7) & (wb >= -1e-7) & (wc >= -1e-7) & (z > region)
        region[mask] = z[mask]
        color = np.r_[np.clip(mesh.visual.face_colors[index, :3] * shades[index], 0, 255), 255].astype(np.uint8)
        pixels[ymin:ymax + 1, xmin:xmax + 1][mask] = color
    return Image.fromarray(pixels).convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


def generate(out, seed=19):
    out = out.resolve()
    base.require(out.is_relative_to(ROOT) and out != ROOT, "--out must be a child of the repository or extracted pack")
    base.require(isinstance(seed, int) and seed >= 0, "Seed must be a nonnegative integer")
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {out}; choose a new --out directory")
    versions = {"python": platform.python_version(), **{p: version(p) for p in base.PACKAGES}}
    source_hashes = {relative: base.sha256(ROOT / relative) for relative in SOURCES}
    (out / "assets").mkdir(parents=True)
    assets = []
    for identifier, category, render in DEFINITIONS:
        metadata = (visuals.RECIPES if category in ("3d", "2d") else effects.RECIPES)[identifier]
        directory = out / "assets" / identifier
        directory.mkdir()
        prefix = directory.relative_to(ROOT).as_posix()
        review = metadata["review"]
        if isinstance(review, dict):
            review = review["observed"] + " " + review["limitations"][0]
        elif isinstance(review, list):
            review = " ".join(review)
        entry = {"id": identifier, "name": metadata["name"], "category": category,
                 "description": metadata["description"], "tags": metadata["tags"],
                 "seed": seed, "recipe": RECIPE, "manifest": prefix + "/manifest.json", "review": review}
        parameters = {**metadata["parameters"], "seed": seed}
        if category == "3d":
            mesh, repeat = render(seed=seed), render(seed=seed)
            base.require(np.array_equal(mesh.vertices, repeat.vertices)
                         and np.array_equal(mesh.faces, repeat.faces)
                         and np.array_equal(mesh.visual.face_colors, repeat.visual.face_colors), "Mesh rerender changed")
            metrics = base.export_model(directory, mesh, identifier)
            exported = base.trimesh.load_scene(directory / "model.glb").to_mesh()
            exported.apply_transform(np.linalg.inv(base.Z_TO_Y))
            depth_preview(exported).save(directory / "preview.png")
            base.check_png(directory / "preview.png", (512, 512))
            entry["yaw"] = float(np.pi - .65) if identifier == "treasure-chest" else .65
            entry.update(file=prefix + "/model.glb", preview=prefix + "/preview.png", model=prefix + "/mesh.json",
                         meta=f"{metrics['triangles']} tris · GLB / OBJ",
                         stats={"Triangles": str(metrics["triangles"]), "Vertices": str(metrics["welded_vertices"]),
                                "Formats": "GLB / OBJ", "Units": "meters", "Materials": "Vertex colors; no UVs"})
            details = {"mesh": metrics, "axes": {"source": "Z", "glb_export": "Y", "obj_export": "Z", "mesh_json": "Z"},
                       "pivot": "ground level", "preview_method": "NumPy depth buffer from reloaded GLB, flat diffuse shading; not PBR",
                       "format_notes": "GLB flat vertex colors; OBJ geometry only. Separate closed components may overlap; not collision proxies."}
        elif category == "2d":
            image = render(size=384, seed=seed)
            image.save(directory / "image.png")
            pixels = base.check_png(directory / "image.png", (384, 384))
            base.require(np.array_equal(pixels, np.asarray(render(size=384, seed=seed))), "Raster rerender changed")
            entry.update(file=prefix + "/image.png", preview=prefix + "/image.png", meta="384 × 384 · RGBA",
                         stats={"Resolution": "384 × 384", "Format": "RGBA PNG", "Tiling": "None"})
            details = {"format": "RGBA PNG", "size": [384, 384], "alpha": "straight"}
            if identifier == "dialog-panel":
                entry["nineSlice"] = {"left": 64, "top": 64, "right": 64, "bottom": 64}
                entry["stats"]["9-slice insets"] = "64 px each side"
                nine_slice(image, 768, 256).save(directory / "preview-wide.png")
                base.check_png(directory / "preview-wide.png", (768, 256))
                entry["panelPreview"] = prefix + "/preview-wide.png"
                details["nine_slice"] = {**entry["nineSlice"], "units": "source pixels", "minimum_size": [128, 128],
                                         "preview_size": [768, 256], "preview": "preview-wide.png"}
        elif category == "vfx":
            details = base.export_effect(directory, lambda size, phase, unused: render(size, phase, seed), False)
            entry.update(file=prefix + "/atlas.png", preview=prefix + "/preview.png", atlas=prefix + "/atlas.png",
                         frameSize=128, frames=16, columns=4, fps=16, loop=False, posterFrame=details["peak_frame"], meta="16 frames · 128 × 128",
                         stats={"Frames": "16", "Frame size": "128 × 128", "Atlas": "512 × 512", "FPS": "16", "Playback": "One-shot"})
            parameters.update(frame_size=128, frames=16, columns=4, fps=16)
            if identifier == "dust-puff":
                details["blend"] = "straight alpha; additive blending is unsuitable for opaque dust"
        else:
            samples = render(seed=seed, rate=48000)
            base.require(np.array_equal(samples, render(seed=seed, rate=48000)), "Audio rerender changed")
            details, waveform = base.export_sound(directory, samples)
            entry.update(file=prefix + "/sound.wav", waveform=waveform, duration=details["duration_seconds"],
                         meta=f"{details['duration_seconds']:.2f} s · 48 kHz / 16-bit",
                         stats={"Duration": f"{details['duration_seconds']:.2f} s", "Sample rate": "48 kHz", "Encoding": "PCM16 mono",
                                "Peak": f"{details['peak_dbfs']:.2f} dBFS", "RMS": f"{details['rms_dbfs']:.2f} dBFS"})
            parameters["sample_rate"] = 48000
        base.copy_new(SOURCE, directory / "generate_gallery_expansion.py")
        module_name = "gallery_expansion_visuals.py" if category in ("3d", "2d") else "gallery_expansion_effects.py"
        base.copy_new(ROOT / "asset_pipeline" / module_name, directory / module_name)
        manifest = {"id": identifier, "category": category, "parameters": parameters, "versions": versions,
                    "recipe": RECIPE, "source_snapshot": "generate_gallery_expansion.py",
                    "source_dependencies_sha256": source_hashes,
                    "reproduce": {"command": f"python {RECIPE} --out new-studies --seed {seed}",
                                  "requirements": "requirements-code-assets.txt",
                                  "note": "Run from repository or extracted ZIP; use a new output directory."},
                    "review": review, "engine_import_tested": False, "human_listening_tested": False,
                    "deterministic_rerender": True, **details,
                    "sha256": {p.name: base.sha256(p) for p in sorted(directory.iterdir()) if p.is_file()}}
        base.write_json(directory / "manifest.json", manifest)
        for key in ("file", "preview", "model", "atlas", "manifest", "recipe"):
            if key in entry:
                base.require((ROOT / entry[key]).is_file(), f"Missing catalog artifact: {entry[key]}")
        assets.append(entry)
    base.write_json(out / "catalog.json", {"name": "Gameplay studies", "seed": seed, "assets": assets})
    archive_collection(out, assets)
    return {"output": str(out), "assets": len(assets), "seed": seed,
            "zip_bytes": (out / "asset-collection.zip").stat().st_size,
            "validated": [{"id": a["id"], **a["stats"]} for a in assets]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("gallery/expansion"))
    parser.add_argument("--seed", type=int, default=19)
    args = parser.parse_args()
    try:
        print(json.dumps(generate(ROOT / args.out, args.seed), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Expansion generation failed: {error}\n")


if __name__ == "__main__":
    main()
