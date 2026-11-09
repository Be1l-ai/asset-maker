import argparse
import hashlib
import json
import platform
import shutil
from importlib.metadata import version
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont


def build_model(seed=7) -> trimesh.Trimesh:
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    rng = np.random.default_rng(seed)

    def box(size, center):
        return trimesh.creation.box(extents=size).apply_translation(center)

    def cone(radius, height, z, angle, inverted=False):
        transform = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
        if inverted:
            transform = transform @ trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
        transform[:3, 3] = [0, 0, z]
        return trimesh.creation.cone(radius, height, sections=6, transform=transform)

    outer = box([1.2, 1.2, 1.65], [0, 0, 1.005])
    cutters = [box([0.9, 0.9, 1.9], [0, 0, 1.0])]
    for axis in ([1, 0, 0], [0, 1, 0]):
        transform = trimesh.transformations.rotation_matrix(np.pi / 2, axis)
        transform[:3, 3] = [0, 0, 1.17]
        cutters.append(trimesh.creation.cylinder(0.36, 1.6, sections=12, transform=transform))
    cutters.extend([box([0.72, 1.6, 0.78], [0, 0, 0.78]),
                    box([1.6, 0.72, 0.78], [0, 0, 0.78])])
    frame = trimesh.boolean.difference([outer, *cutters], engine="manifold")
    roof_transform = trimesh.transformations.rotation_matrix(np.pi / 4, [0, 0, 1])
    roof_transform[:3, 3] = [0, 0, 1.80]
    roof = trimesh.creation.cone(1.08, 0.48, sections=4, transform=roof_transform)
    finial = trimesh.creation.cylinder(0.10, 0.16, sections=8).apply_translation([0, 0, 2.30])
    frame = trimesh.boolean.union(
        [frame, box([1.38, 1.38, 0.20], [0, 0, 0.10]), roof, finial], engine="manifold")
    colors = np.tile([65, 112, 107, 255], (len(frame.faces), 1))
    colors[frame.triangles_center[:, 2] > 1.79] = [171, 123, 65, 255]
    colors[frame.triangles_center[:, 2] < 0.21] = [48, 65, 66, 255]
    frame.visual.face_colors = colors
    angle = rng.uniform(0, np.pi / 3)
    crystal = trimesh.boolean.union(
        [cone(0.23, 0.46, 0.79, angle), cone(0.23, 0.29, 0.79, angle, True)],
        engine="manifold")
    crystal.visual.face_colors = np.column_stack([
        rng.integers(65, 100, len(crystal.faces)), rng.integers(205, 236, len(crystal.faces)),
        np.full(len(crystal.faces), 245), np.full(len(crystal.faces), 255)])
    mesh = trimesh.util.concatenate([frame, crystal])
    mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])
    mesh.metadata.update(units="m", up_axis="Z", seed=seed)
    return mesh


def preview_mesh(mesh) -> Image.Image:
    size, supersample = 400, 2
    image = Image.new("RGB", (size * 3 * supersample, 420 * supersample), "#edf0e9")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=14 * supersample)
    light = np.array([-0.4, -0.6, 1.0])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.maximum(0, mesh.face_normals @ light)
    colors = np.clip(mesh.visual.face_colors[:, :3] * shade[:, None], 0, 255).astype(np.uint8)
    for panel, (label, eye) in enumerate([
            ("FRONT", [0, -1, 0]), ("SIDE", [1, 0, 0]), ("THREE-QUARTER", [1, -1, 0.7])]):
        forward = np.array(eye, dtype=float)
        forward /= np.linalg.norm(forward)
        right = np.cross([0, 0, 1], forward)
        right /= np.linalg.norm(right)
        up = np.cross(forward, right)
        projected = mesh.vertices @ np.column_stack([right, up, forward])
        low, high = projected[:, :2].min(axis=0), projected[:, :2].max(axis=0)
        scale = 330 / max(high - low)
        xy = (projected[:, :2] - (low + high) / 2) * [scale, -scale]
        xy += [panel * size + size / 2, 215]
        polygons = xy[mesh.faces] * supersample
        depths = projected[mesh.faces, 2].mean(axis=1)
        for face in np.argsort(depths):
            if mesh.face_normals[face] @ forward > 0:
                draw.polygon([tuple(p) for p in polygons[face]], fill=tuple(colors[face]))
        draw.text(((panel * size + size / 2) * supersample, 18 * supersample),
                  label, fill="#3b514c", font=font, anchor="mt")
    return image.resize((size * 3, 420), Image.Resampling.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description="Build a low-poly arched lantern without a renderer.")
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.seed < 0:
        parser.error("--seed must be nonnegative")
    try:
        args.out.mkdir(parents=True, exist_ok=False)
        mesh = build_model(args.seed)
        # glTF is Y-up; build_model and OBJ remain Z-up, in meters.
        z_to_y = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
        exported = mesh.copy().apply_transform(z_to_y)
        exported.metadata.update(source_up_axis="Z", up_axis="Y")
        exported.unmerge_vertices()  # Preserve face colors instead of averaging at shared vertices.
        exported.export(args.out / "prop.glb", include_normals=False)
        mesh.export(args.out / "prop.obj", include_color=False, include_texture=False,
                    include_normals=False, header="")
        reloaded = trimesh.load_scene(args.out / "prop.glb").to_mesh()
        reloaded.apply_transform(np.linalg.inv(z_to_y))
        preview_mesh(reloaded).save(args.out / "preview.png")
        shutil.copyfile(Path(__file__).resolve(), args.out / "recipe.py")
        # Face colors can split GLB vertices; weld a copy for topology checks.
        welded = reloaded.copy()
        welded.merge_vertices(merge_tex=True, merge_norm=True)
        if len(mesh.faces) >= 3000 or not welded.is_watertight:
            raise ValueError("mesh must be watertight and have fewer than 3000 triangles")
        outputs = ["prop.glb", "prop.obj", "preview.png", "recipe.py"]
        manifest = {
            "parameters": {"seed": args.seed}, "units": "m", "up_axis": "Z",
            "axes": {"source": "Z", "glb_export": "Y", "obj_export": "Z", "preview": "Z"},
            "format_notes": {
                "glb": "Y-up, meters, face colors exported as vertex colors; no UVs or rigging.",
                "obj": "Z-up geometry only: vertex colors omitted for portable OBJ; no MTL.",
                "preview": "Reloaded GLB returned to Z-up; Pillow orthographic painter sorting, diffuse shading.",
                "topology": "Hollow boolean-cut frame and separate closed crystal; no emissive material.",
            },
            "versions": {"python": platform.python_version(), **{
                name: version(name) for name in ("numpy", "Pillow", "trimesh", "manifold3d")}},
            "mesh": {"vertices": len(mesh.vertices), "triangles": len(mesh.faces),
                     "bounds": mesh.bounds.tolist(), "watertight": bool(mesh.is_watertight)},
            "glb_reloaded_z_up": {"vertices": len(reloaded.vertices),
                                  "welded_vertices": len(welded.vertices),
                                  "triangles": len(reloaded.faces), "bounds": reloaded.bounds.tolist(),
                                  "watertight_after_weld": bool(welded.is_watertight)},
            "sha256": {name: hashlib.sha256((args.out / name).read_bytes()).hexdigest() for name in outputs},
        }
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}: {len(mesh.faces)} triangles")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
