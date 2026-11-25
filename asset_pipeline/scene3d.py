"""Staged 3D scene and multi-part assembly pipeline (PARSE -> MASS -> RIG -> SKIN -> PACK).

Extends asset_pipeline beyond single-mesh props by preserving:
- Pre-build dimensional & triangle-budget contracts (``SceneSpec`` / ``spec.json``)
- Named glTF 2.0 node hierarchies with per-part pivot origins (RIG)
- Per-surface PBR metallic-roughness and emissive material slots (SKIN)
- Shadow-mapped Z-buffer + atmospheric haze software preview rendering (PACK)

Accepts either ``trimesh.Trimesh`` / ``SolidMesh`` instances or pure-NumPy
``MeshGeometry`` containers, so scenes can be built and validated with or
without optional ``trimesh`` installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import json
import math
from pathlib import Path
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n < 1e-12, 1.0, n)


def _compute_smooth_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    vn = np.zeros_like(vertices, dtype=np.float64)
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    fn = np.cross(v1 - v0, v2 - v0)
    for k in range(3):
        np.add.at(vn, faces[:, k], fn)
    return _normalize(vn)


def compute_box_uvs(vertices: np.ndarray, faces: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Compute per-corner triplanar box-projected UVs of shape (F * 3, 2) in float32."""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    fn = np.abs(np.cross(v1 - v0, v2 - v0))
    dom = np.argmax(fn, axis=1)  # 0=X, 1=Y, 2=Z
    tri_v = vertices[faces]      # (F, 3, 3)
    uvs = np.empty((len(faces), 3, 2), dtype=np.float32)
    m0 = dom == 0
    m1 = dom == 1
    m2 = dom == 2
    if m0.any():
        uvs[m0, :, 0] = tri_v[m0, :, 1] * scale
        uvs[m0, :, 1] = tri_v[m0, :, 2] * scale
    if m1.any():
        uvs[m1, :, 0] = tri_v[m1, :, 0] * scale
        uvs[m1, :, 1] = tri_v[m1, :, 2] * scale
    if m2.any():
        uvs[m2, :, 0] = tri_v[m2, :, 0] * scale
        uvs[m2, :, 1] = tri_v[m2, :, 1] * scale
    return uvs.reshape(-1, 2)


def _encode_png_bytes(img_or_arr: Any) -> bytes:
    """Encode a PIL.Image, numpy array, or file path into PNG bytes for glTF embedding."""
    if isinstance(img_or_arr, (str, Path)):
        return Path(img_or_arr).read_bytes()
    if isinstance(img_or_arr, np.ndarray):
        arr = np.clip(img_or_arr, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
    elif isinstance(img_or_arr, Image.Image):
        img = img_or_arr
    else:
        raise TypeError(f"Unsupported texture type: {type(img_or_arr)}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@dataclass
class MaterialSpec:
    """Declarative PBR metallic-roughness material definition for glTF 2.0 export."""
    name: str
    roughness: float = 0.88
    metallic: float = 0.0
    emissive: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    base_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    double_sided: bool = False
    shading_mode: str = "pbr"  # "pbr" | "emissive" | "cloud" | "sky"
    uv_scale: float = 1.0
    base_color_texture: Any = None
    normal_texture: Any = None
    metallic_roughness_texture: Any = None

    def to_gltf(
        self,
        base_tex_idx: Optional[int] = None,
        normal_tex_idx: Optional[int] = None,
        mr_tex_idx: Optional[int] = None,
    ) -> Dict[str, Any]:
        mat: Dict[str, Any] = {
            "name": self.name,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(self.base_color),
                "metallicFactor": float(self.metallic),
                "roughnessFactor": float(self.roughness),
            },
            "doubleSided": bool(self.double_sided),
        }
        if base_tex_idx is not None:
            mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": int(base_tex_idx)}
        if mr_tex_idx is not None:
            mat["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": int(mr_tex_idx)}
        if normal_tex_idx is not None:
            mat["normalTexture"] = {"index": int(normal_tex_idx)}
        if any(c > 0.0 for c in self.emissive):
            mat["emissiveFactor"] = [float(c) for c in self.emissive]
        return mat


DEFAULT_MATERIALS: Dict[str, MaterialSpec] = {
    "matte": MaterialSpec("StylizedMatte", roughness=0.90, metallic=0.0),
    "bark": MaterialSpec("StylizedBark", roughness=0.94, metallic=0.0),
    "foliage": MaterialSpec("StylizedFoliage", roughness=0.82, metallic=0.0),
    "stone": MaterialSpec("ChiseledStone", roughness=0.86, metallic=0.04),
    "metal": MaterialSpec("BrushedMetal", roughness=0.35, metallic=0.85),
    "emissive_crystal": MaterialSpec("EmissiveCrystal", roughness=0.22, metallic=0.05, emissive=(0.15, 0.55, 0.70)),
    "emissive_sun": MaterialSpec("EmissiveSun", roughness=1.0, metallic=0.0, emissive=(1.0, 0.90, 0.55), shading_mode="emissive"),
    "bright_cloud": MaterialSpec("CumulusCloud", roughness=0.95, metallic=0.0, emissive=(0.45, 0.48, 0.52), shading_mode="cloud"),
    "unlit_sky": MaterialSpec("SkydomeAtmosphere", roughness=1.0, metallic=0.0, emissive=(0.38, 0.42, 0.48), shading_mode="sky"),
}



STYLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "stylized_lowpoly": {
        "min_triangles": 300,
        "max_triangles": 8000,
        "min_nodes": 3,
        "min_part_modules": 2,
        "min_materials": 2,
        "require_uv_textures": False,
        "require_concept_ref": False,
        "recommended_track": "python",
        "notes": "Clean silhouettes, spherical normals, vertex-color ramps, ground AO.",
    },
    "hand_painted_hero": {
        "min_triangles": 10000,
        "max_triangles": 60000,
        "min_nodes": 12,
        "min_part_modules": 4,
        "min_materials": 3,
        "require_uv_textures": True,
        "require_concept_ref": True,
        "recommended_track": "threejs",
        "notes": "Lofted silhouettes, TEXCOORD_0 painted PBR textures, secondary trim & rigging.",
    },
    "voxel": {
        "min_triangles": 200,
        "max_triangles": 25000,
        "min_nodes": 2,
        "min_part_modules": 2,
        "min_materials": 1,
        "require_uv_textures": False,
        "require_concept_ref": False,
        "recommended_track": "python",
        "notes": "Grid-snapped voxels, palette discipline, baked crevice AO.",
    },
    "volumetric_shader": {
        "min_triangles": 0,
        "max_triangles": 15000,
        "min_nodes": 1,
        "min_part_modules": 3,
        "min_materials": 1,
        "require_uv_textures": False,
        "require_concept_ref": True,
        "recommended_track": "threejs",
        "notes": "GLSL volumetric/atmospheric shaders, presets, interactive controls.",
    },
    "web_ui_2d": {
        "min_triangles": 0,
        "max_triangles": 0,
        "min_nodes": 0,
        "min_part_modules": 1,
        "min_materials": 0,
        "require_uv_textures": False,
        "require_concept_ref": True,
        "recommended_track": "web_ui",
        "notes": "React + CSS/Tailwind + SVG captured via headless Playwright to transparent PNG/atlas.",
    },
}


@dataclass
class PartSpec:
    """Single part declaration inside a pre-build ``spec.json``."""
    name: str
    material: str = "matte"
    max_triangles: Optional[int] = None
    pivot: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dimensions_m: Optional[Tuple[float, float, float]] = None


@dataclass
class SceneSpec:
    """Pre-build contract loaded from ``spec.json`` (PARSE stage)."""
    name: str
    max_triangles: int = 25000
    track: str = "python"              # "python" | "threejs" | "web_ui"
    style_profile: str = "stylized_lowpoly"
    quality_tier: str = "standard"     # "standard" | "hero"
    parts: List[PartSpec] = field(default_factory=list)
    materials: Dict[str, MaterialSpec] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path | str) -> "SceneSpec":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        materials: Dict[str, MaterialSpec] = {}
        for mname, mcfg in data.get("materials", {}).items():
            materials[mname] = MaterialSpec(
                name=mcfg.get("name", mname),
                roughness=float(mcfg.get("roughness", 0.88)),
                metallic=float(mcfg.get("metallic", 0.0)),
                emissive=tuple(float(x) for x in mcfg.get("emissive", (0.0, 0.0, 0.0))),
                base_color=tuple(float(x) for x in mcfg.get("base_color", (1.0, 1.0, 1.0, 1.0))),
                double_sided=bool(mcfg.get("double_sided", False)),
                shading_mode=str(mcfg.get("shading_mode", "pbr")),
            )
        parts: List[PartSpec] = []
        for pcfg in data.get("parts", []):
            dims = pcfg.get("dimensions_m")
            parts.append(PartSpec(
                name=str(pcfg["name"]),
                material=str(pcfg.get("material", "matte")),
                max_triangles=int(pcfg["max_triangles"]) if pcfg.get("max_triangles") is not None else None,
                pivot=tuple(float(x) for x in pcfg.get("pivot", (0.0, 0.0, 0.0))),
                dimensions_m=tuple(float(x) for x in dims) if dims is not None else None,
            ))
        profile = str(data.get("style_profile", "stylized_lowpoly"))
        default_budget = STYLE_PROFILES.get(profile, {}).get("max_triangles", 25000)
        return cls(
            name=str(data.get("name", "scene")),
            max_triangles=int(data.get("max_triangles", default_budget)),
            track=str(data.get("track", STYLE_PROFILES.get(profile, {}).get("recommended_track", "python"))),
            style_profile=profile,
            quality_tier=str(data.get("quality_tier", "standard")),
            parts=parts,
            materials=materials,
        )


@dataclass
class MeshGeometry:
    """Engine-agnostic triangle mesh container (Z-up, outward CCW winding)."""
    vertices: np.ndarray        # (V, 3) float64
    faces: np.ndarray           # (F, 3) int32
    face_colors: np.ndarray     # (F, 4) uint8 sRGB
    vertex_normals: Optional[np.ndarray] = None
    uvs: Optional[np.ndarray] = None  # (V, 2) or (F*3, 2) float32

    @classmethod
    def from_any(cls, mesh: Any, default_color: Sequence[int] = (180, 185, 195, 255)) -> "MeshGeometry":
        """Normalize a ``MeshGeometry``, ``SolidMesh``, or ``trimesh.Trimesh``."""
        if isinstance(mesh, cls):
            return mesh
        raw = mesh.raw if hasattr(mesh, "raw") else mesh
        verts = np.asarray(raw.vertices, dtype=np.float64)
        faces = np.asarray(raw.faces, dtype=np.int32)
        if hasattr(raw, "visual") and getattr(raw.visual, "face_colors", None) is not None and len(raw.visual.face_colors) == len(faces):
            fcols = np.asarray(raw.visual.face_colors, dtype=np.uint8)
            if fcols.shape[1] == 3:
                fcols = np.hstack([fcols, np.full((len(fcols), 1), 255, dtype=np.uint8)])
        else:
            fcols = np.tile(np.array(default_color, dtype=np.uint8), (len(faces), 1))
        vnorms = None
        if hasattr(raw, "vertex_normals") and len(raw.vertex_normals) == len(verts):
            vnorms = np.asarray(raw.vertex_normals, dtype=np.float64)
        return cls(vertices=verts, faces=faces, face_colors=fcols, vertex_normals=vnorms)


@dataclass
class SceneNode:
    """Named part node inside a ``SceneBuilder`` hierarchy."""
    name: str
    geometry: MeshGeometry
    material: str = "matte"
    pivot: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    cast_shadow: bool = True
    receive_shadow: bool = True


class SceneBuilder:
    """Staged multi-node 3D scene/prop composer with PBR materials and glTF 2.0 export."""

    def __init__(self, name: str = "scene", seed: Optional[int] = None, spec: Optional[SceneSpec] = None):
        self.name = spec.name if spec is not None else name
        self.rng = np.random.default_rng(seed)
        self.spec = spec
        self.materials: Dict[str, MaterialSpec] = dict(DEFAULT_MATERIALS)
        if spec is not None:
            self.materials.update(spec.materials)
        self.nodes: Dict[str, SceneNode] = {}

    @classmethod
    def from_spec(cls, spec_path: Path | str, seed: Optional[int] = None) -> "SceneBuilder":
        spec = SceneSpec.from_file(spec_path)
        return cls(name=spec.name, seed=seed, spec=spec)

    def define_material(self, mat: MaterialSpec) -> "SceneBuilder":
        self.materials[mat.name] = mat
        return self

    def add_part(
        self,
        name: str,
        mesh: Any,
        material: Optional[str] = None,
        pivot: Optional[Sequence[float]] = None,
        cast_shadow: bool = True,
        receive_shadow: bool = True,
    ) -> "SceneBuilder":
        """Register a named part (preserving local pivot and material assignment)."""
        geom = MeshGeometry.from_any(mesh)
        spec_part = next((p for p in self.spec.parts if p.name == name), None) if self.spec else None
        mat_name = material or (spec_part.material if spec_part else "matte")
        if mat_name not in self.materials:
            raise ValueError(f"Unknown material '{mat_name}' for part '{name}'")
        piv = tuple(float(x) for x in (pivot if pivot is not None else (spec_part.pivot if spec_part else (0.0, 0.0, 0.0))))
        self.nodes[name] = SceneNode(
            name=name,
            geometry=geom,
            material=mat_name,
            pivot=piv,
            cast_shadow=cast_shadow,
            receive_shadow=receive_shadow,
        )
        return self

    @property
    def triangle_count(self) -> int:
        return sum(len(n.geometry.faces) for n in self.nodes.values())

    @property
    def vertex_count(self) -> int:
        return sum(len(n.geometry.vertices) for n in self.nodes.values())

    def validate(self, max_triangles: Optional[int] = None) -> Dict[str, Any]:
        """Validate scene geometry, triangle budgets, and ``spec.json`` part coverage."""
        errors: List[str] = []
        if not self.nodes:
            errors.append("Scene contains no parts")

        per_part: Dict[str, Dict[str, Any]] = {}
        for name, node in self.nodes.items():
            g = node.geometry
            if not len(g.vertices) or not len(g.faces):
                errors.append(f"Part '{name}' has empty geometry")
            if not np.isfinite(g.vertices).all():
                errors.append(f"Part '{name}' contains non-finite vertices")
            per_part[name] = {
                "triangles": int(len(g.faces)),
                "vertices": int(len(g.vertices)),
                "material": node.material,
                "pivot": list(node.pivot),
            }

        budget = max_triangles if max_triangles is not None else (self.spec.max_triangles if self.spec else None)
        if budget is not None and self.triangle_count > budget:
            errors.append(f"Scene has {self.triangle_count} triangles; budget is {budget}")

        if self.spec is not None:
            for sp in self.spec.parts:
                if sp.name not in self.nodes:
                    errors.append(f"Spec part '{sp.name}' was declared in spec.json but never built")
                elif sp.max_triangles is not None:
                    actual = len(self.nodes[sp.name].geometry.faces)
                    if actual > sp.max_triangles:
                        errors.append(f"Part '{sp.name}' has {actual} triangles; spec budget is {sp.max_triangles}")

        if errors:
            raise ValueError("Scene validation failed: " + "; ".join(errors))

        return {
            "scene": self.name,
            "nodes": len(self.nodes),
            "materials": len({n.material for n in self.nodes.values()}),
            "triangles": self.triangle_count,
            "vertices": self.vertex_count,
            "parts": per_part,
        }

    def export_glb(self, path: Path | str, apply_y_up: bool = True) -> Path:
        """Export a multi-node, multi-material glTF 2.0 Binary (.glb) preserving pivots."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)

        used_mats = list(dict.fromkeys(n.material for n in self.nodes.values()))
        mat_idx_map = {m: i for i, m in enumerate(used_mats)}

        bin_chunks: List[bytes] = []
        buffer_views: List[Dict[str, Any]] = []
        accessors: List[Dict[str, Any]] = []
        meshes: List[Dict[str, Any]] = []
        gltf_nodes: List[Dict[str, Any]] = []
        gltf_images: List[Dict[str, Any]] = []
        gltf_textures: List[Dict[str, Any]] = []
        gltf_materials: List[Dict[str, Any]] = []
        cur_offset = 0

        def add_view(data: bytes, target: Optional[int] = None) -> int:
            nonlocal cur_offset
            pad = (4 - (len(data) % 4)) % 4
            padded = data + b"\x00" * pad
            idx = len(buffer_views)
            bv: Dict[str, Any] = {"buffer": 0, "byteOffset": cur_offset, "byteLength": len(data)}
            if target is not None:
                bv["target"] = target
            buffer_views.append(bv)
            bin_chunks.append(padded)
            cur_offset += len(padded)
            return idx

        def add_png_texture(tex_src: Any) -> Optional[int]:
            if tex_src is None:
                return None
            png_bytes = _encode_png_bytes(tex_src)
            bv_idx = add_view(png_bytes, target=None)
            img_idx = len(gltf_images)
            gltf_images.append({"bufferView": bv_idx, "mimeType": "image/png"})
            tex_idx = len(gltf_textures)
            gltf_textures.append({"sampler": 0, "source": img_idx})
            return tex_idx

        for mname in used_mats:
            mspec = self.materials[mname]
            b_idx = add_png_texture(mspec.base_color_texture)
            n_idx = add_png_texture(mspec.normal_texture)
            mr_idx = add_png_texture(mspec.metallic_roughness_texture)
            gltf_materials.append(mspec.to_gltf(base_tex_idx=b_idx, normal_tex_idx=n_idx, mr_tex_idx=mr_idx))

        for name, node in self.nodes.items():
            g = node.geometry
            vnorms = g.vertex_normals if g.vertex_normals is not None else _compute_smooth_normals(g.vertices, g.faces)
            piv = np.asarray(node.pivot, dtype=np.float64)

            # Store vertices relative to node pivot so engine gizmos rotate cleanly around pivot
            local_verts = g.vertices - piv[None, :]
            pos = local_verts[g.faces].reshape(-1, 3).astype(np.float64)
            nrm = vnorms[g.faces].reshape(-1, 3).astype(np.float64)
            cs = np.repeat(g.face_colors, 3, axis=0).astype(np.float64) / 255.0
            cl = np.empty_like(cs)
            cl[:, :3] = np.power(np.clip(cs[:, :3], 0.0, 1.0), 2.2)
            cl[:, 3] = cs[:, 3]

            node_trans = piv.copy()
            if apply_y_up:
                pos = np.column_stack([pos[:, 0], pos[:, 2], -pos[:, 1]])
                nrm = np.column_stack([nrm[:, 0], nrm[:, 2], -nrm[:, 1]])
                node_trans = np.array([piv[0], piv[2], -piv[1]], dtype=np.float64)

            p32 = pos.astype(np.float32)
            n32 = _normalize(nrm).astype(np.float32)
            cu8 = np.clip(np.round(cl * 255.0), 0, 255).astype(np.uint8)
            nv = len(p32)
            i32 = np.arange(nv, dtype=np.uint32)

            bv_p = add_view(p32.tobytes(), 34962)
            bv_n = add_view(n32.tobytes(), 34962)
            bv_c = add_view(cu8.tobytes(), 34962)
            bv_i = add_view(i32.tobytes(), 34963)

            ap = len(accessors)
            accessors.append({
                "bufferView": bv_p, "componentType": 5126, "count": nv, "type": "VEC3",
                "min": p32.min(axis=0).tolist(), "max": p32.max(axis=0).tolist(),
            })
            an = len(accessors)
            accessors.append({"bufferView": bv_n, "componentType": 5126, "count": nv, "type": "VEC3"})
            ac = len(accessors)
            accessors.append({"bufferView": bv_c, "componentType": 5121, "normalized": True, "count": nv, "type": "VEC4"})
            ai = len(accessors)
            accessors.append({"bufferView": bv_i, "componentType": 5125, "count": nv, "type": "SCALAR"})

            attrs: Dict[str, int] = {"POSITION": ap, "NORMAL": an, "COLOR_0": ac}
            mspec = self.materials[node.material]
            has_tex = any(t is not None for t in (mspec.base_color_texture, mspec.normal_texture, mspec.metallic_roughness_texture))
            if g.uvs is not None or has_tex:
                if g.uvs is not None:
                    uv_arr = np.asarray(g.uvs, dtype=np.float32)
                    uv_flat = uv_arr[g.faces].reshape(-1, 2) if len(uv_arr) == len(g.vertices) else uv_arr.reshape(-1, 2)
                else:
                    uv_flat = compute_box_uvs(local_verts, g.faces, scale=mspec.uv_scale)
                bv_uv = add_view(uv_flat.astype(np.float32).tobytes(), 34962)
                auv = len(accessors)
                accessors.append({"bufferView": bv_uv, "componentType": 5126, "count": nv, "type": "VEC2"})
                attrs["TEXCOORD_0"] = auv

            mi = len(meshes)
            meshes.append({
                "name": name,
                "primitives": [{
                    "attributes": attrs,
                    "indices": ai,
                    "material": mat_idx_map[node.material],
                    "mode": 4,
                }],
            })
            gnode: Dict[str, Any] = {"name": name, "mesh": mi}
            if np.linalg.norm(node_trans) > 1e-6:
                gnode["translation"] = [round(float(x), 6) for x in node_trans]
            gltf_nodes.append(gnode)

        blob = b"".join(bin_chunks)
        gltf = {
            "asset": {"version": "2.0", "generator": "asset-maker SceneBuilder"},
            "scene": 0,
            "scenes": [{"name": self.name, "nodes": list(range(len(gltf_nodes)))}],
            "nodes": gltf_nodes,
            "materials": gltf_materials,
            "meshes": meshes,
            "buffers": [{"byteLength": len(blob)}],
            "bufferViews": buffer_views,
            "accessors": accessors,
        }
        if gltf_textures:
            gltf["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
            gltf["images"] = gltf_images
            gltf["textures"] = gltf_textures
        jb = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        jb += b" " * ((4 - (len(jb) % 4)) % 4)
        total = 12 + 8 + len(jb) + 8 + len(blob)
        header = struct.pack("<III", 0x46546C67, 2, total)
        out.write_bytes(header + struct.pack("<II", len(jb), 0x4E4F534A) + jb + struct.pack("<II", len(blob), 0x004E4942) + blob)
        return out

    def export_inspector_json(self, path: Path | str) -> Path:
        """Export lightweight per-node hierarchy & PBR metadata for the gallery Inspector."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        nodes_meta = []
        for name, node in self.nodes.items():
            g = node.geometry
            mspec = self.materials[node.material]
            vmin = g.vertices.min(axis=0).tolist()
            vmax = g.vertices.max(axis=0).tolist()
            nodes_meta.append({
                "name": name,
                "triangles": int(len(g.faces)),
                "vertices": int(len(g.vertices)),
                "material": mspec.name,
                "material_key": node.material,
                "roughness": mspec.roughness,
                "metallic": mspec.metallic,
                "emissive": list(mspec.emissive),
                "has_textures": any(t is not None for t in (mspec.base_color_texture, mspec.normal_texture, mspec.metallic_roughness_texture)),
                "pivot": list(node.pivot),
                "bounds_min": [round(float(x), 4) for x in vmin],
                "bounds_max": [round(float(x), 4) for x in vmax],
            })
        payload = {
            "scene": self.name,
            "total_triangles": self.triangle_count,
            "total_vertices": self.vertex_count,
            "node_count": len(nodes_meta),
            "nodes": nodes_meta,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return out

    def export_obj(self, path: Path | str) -> Path:
        """Export native Z-up Wavefront OBJ with named ``o <PartName>`` groups."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# {self.name} - asset-maker SceneBuilder (Z-up)"]
        v_off = 1
        for name, node in self.nodes.items():
            g = node.geometry
            vnorms = g.vertex_normals if g.vertex_normals is not None else _compute_smooth_normals(g.vertices, g.faces)
            lines.append(f"o {name}")
            for v in g.vertices:
                lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
            for vn in vnorms:
                lines.append(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}")
            for f in g.faces:
                a, b, c = int(f[0]) + v_off, int(f[1]) + v_off, int(f[2]) + v_off
                lines.append(f"f {a}//{a} {b}//{b} {c}//{c}")
            v_off += len(g.vertices)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    def render_preview(
        self,
        path: Path | str,
        cam_pos: Optional[Sequence[float]] = None,
        target: Optional[Sequence[float]] = None,
        fov_deg: float = 46.0,
        size: Tuple[int, int] = (720, 480),
        sun_dir: Sequence[float] = (-0.54, 0.42, 0.73),
        sky_colors: Optional[Tuple[Sequence[float], Sequence[float], Sequence[float]]] = None,
        fog_color: Optional[Sequence[float]] = None,
        point_lights: Optional[Sequence[Tuple[Sequence[float], Sequence[float], float, float]]] = None,
    ) -> Image.Image:
        """Render a per-pixel Z-buffer + shadow-map + hemisphere PBR preview PNG."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        width, height = size

        # Auto-frame non-sky nodes if camera not specified
        fg_verts = [
            n.geometry.vertices for n in self.nodes.values()
            if self.materials[n.material].shading_mode != "sky"
        ]
        all_v = np.vstack(fg_verts) if fg_verts else np.zeros((1, 3))
        ctr = (all_v.max(axis=0) + all_v.min(axis=0)) * 0.5
        rad = max(float(np.linalg.norm(all_v - ctr, axis=1).max()), 1.0)
        eye = np.asarray(cam_pos if cam_pos is not None else [ctr[0], ctr[1] - rad * 2.1, ctr[2] + rad * 0.75], dtype=np.float64)
        tgt = np.asarray(target if target is not None else ctr, dtype=np.float64)

        fwd = _normalize(tgt - eye)
        right = _normalize(np.cross(fwd, np.array([0.0, 0.0, 1.0])))
        up = np.cross(right, fwd)
        f_len = (height * 0.5) / math.tan(math.radians(fov_deg * 0.5))

        s_dir = _normalize(np.asarray(sun_dir, dtype=np.float64))
        s_fwd = -s_dir
        s_right = _normalize(np.cross(s_fwd, np.array([0.0, 0.0, 1.0])))
        s_up = np.cross(s_right, s_fwd)
        sm_res = 256
        sm_ext = max(rad * 1.4, 4.0)

        def to_sm(pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
            rel = pts - ctr[None, :]
            return (
                (rel @ s_right) / sm_ext * (sm_res * 0.5) + sm_res * 0.5,
                -(rel @ s_up) / sm_ext * (sm_res * 0.5) + sm_res * 0.5,
                rel @ s_fwd,
            )

        # Shadow map pass
        sm_depth = np.full((sm_res, sm_res), 1e9, dtype=np.float32)
        for node in self.nodes.values():
            if not node.cast_shadow or self.materials[node.material].shading_mode in ("sky", "emissive", "cloud"):
                continue
            g = node.geometry
            su, sv, sd = to_sm(g.vertices)
            for fi in range(len(g.faces)):
                i0, i1, i2 = int(g.faces[fi, 0]), int(g.faces[fi, 1]), int(g.faces[fi, 2])
                ax, ay, bx, by, cx_, cy_ = su[i0], sv[i0], su[i1], sv[i1], su[i2], sv[i2]
                x0i, x1i = max(0, int(math.floor(min(ax, bx, cx_)))), min(sm_res - 1, int(math.ceil(max(ax, bx, cx_))))
                y0i, y1i = max(0, int(math.floor(min(ay, by, cy_)))), min(sm_res - 1, int(math.ceil(max(ay, by, cy_))))
                if x0i > x1i or y0i > y1i:
                    continue
                area = (bx - ax) * (cy_ - ay) - (by - ay) * (cx_ - ax)
                if abs(area) < 1e-4:
                    continue
                inv_a = 1.0 / area
                xs = np.arange(x0i, x1i + 1, dtype=np.float64)[None, :] + 0.5
                ys = np.arange(y0i, y1i + 1, dtype=np.float64)[:, None] + 0.5
                w0 = ((bx - xs) * (cy_ - ys) - (by - ys) * (cx_ - xs)) * inv_a
                w1 = ((cx_ - xs) * (ay - ys) - (cy_ - ys) * (ax - xs)) * inv_a
                w2 = 1.0 - w0 - w1
                m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
                if not m.any():
                    continue
                zv = (w0 * sd[i0] + w1 * sd[i1] + w2 * sd[i2]).astype(np.float32)
                patch = sm_depth[y0i:y1i + 1, x0i:x1i + 1]
                u = m & (zv < patch)
                patch[u] = zv[u]

        # Sky backdrop (3-stop atmospheric gradient)
        t_y = np.linspace(1.0, 0.0, height, dtype=np.float32)[:, None]
        if sky_colors is not None:
            hor_c, mid_c, zen_c = [np.asarray(c, dtype=np.float32) for c in sky_colors]
        else:
            hor_c = np.array([224.0, 236.0, 246.0], dtype=np.float32)
            mid_c = np.array([138.0, 194.0, 236.0], dtype=np.float32)
            zen_c = np.array([76.0, 146.0, 214.0], dtype=np.float32)
        lo_m = t_y < 0.42
        bg_lo = hor_c + np.clip(t_y / 0.42, 0.0, 1.0)[..., None] * (mid_c - hor_c)
        bg_hi = mid_c + np.clip((t_y - 0.42) / 0.58, 0.0, 1.0)[..., None] * (zen_c - mid_c)
        bg_col = np.where(lo_m[..., None], bg_lo, bg_hi).astype(np.float32)
        fb = np.broadcast_to(bg_col, (height, width, 3)).copy()
        zbuf = np.full((height, width), 1e9, dtype=np.float32)
        fog_col = np.asarray(fog_color, dtype=np.float32) if fog_color is not None else hor_c.copy()
        p_lights = [(np.asarray(lp, dtype=np.float32), np.asarray(lc, dtype=np.float32), float(lr), float(li)) for lp, lc, lr, li in (point_lights or [])]

        # Pre-decode base_color_texture arrays for fast UV sampling
        tex_arrays: Dict[str, np.ndarray] = {}
        for mkey, mspec in self.materials.items():
            if mspec.base_color_texture is not None:
                if isinstance(mspec.base_color_texture, Image.Image):
                    tex_arrays[mkey] = np.asarray(mspec.base_color_texture.convert("RGB"), dtype=np.float32) / 255.0
                elif isinstance(mspec.base_color_texture, np.ndarray):
                    tex_arrays[mkey] = mspec.base_color_texture[:, :, :3].astype(np.float32) / 255.0

        for node in self.nodes.values():
            mspec = self.materials[node.material]
            mode = mspec.shading_mode
            if mode == "sky":
                continue
            g = node.geometry
            tex_arr = tex_arrays.get(node.material)
            tri_uvs = None
            if tex_arr is not None:
                if g.uvs is not None:
                    ua = np.asarray(g.uvs, dtype=np.float32)
                    tri_uvs = ua[g.faces] if len(ua) == len(g.vertices) else ua.reshape(-1, 3, 2)
                else:
                    tri_uvs = compute_box_uvs(g.vertices, g.faces, scale=mspec.uv_scale).reshape(-1, 3, 2)
            vnorms = g.vertex_normals if g.vertex_normals is not None else _compute_smooth_normals(g.vertices, g.faces)
            rel = g.vertices - eye[None, :]
            cx, cy, cz = rel @ right, rel @ up, rel @ fwd
            v0, v1, v2 = g.vertices[g.faces[:, 0]], g.vertices[g.faces[:, 1]], g.vertices[g.faces[:, 2]]
            gnrm = _normalize(np.cross(v1 - v0, v2 - v0))
            facing = np.einsum("ij,ij->i", gnrm, _normalize(eye[None, :] - (v0 + v1 + v2) / 3.0))
            valid = (facing > 0.0) & (cz[g.faces].min(axis=1) > 0.2)
            idxs = np.nonzero(valid)[0]
            if not len(idxs):
                continue
            px = width * 0.5 + (cx / np.where(cz > 0.1, cz, 0.1)) * f_len
            py = height * 0.5 - (cy / np.where(cz > 0.1, cz, 0.1)) * f_len
            smu, smv, smd = to_sm(g.vertices)

            for fi in idxs:
                i0, i1, i2 = int(g.faces[fi, 0]), int(g.faces[fi, 1]), int(g.faces[fi, 2])
                ax, ay, bx, by, cx_, cy_ = px[i0], py[i0], px[i1], py[i1], px[i2], py[i2]
                x0i, x1i = max(0, int(math.floor(min(ax, bx, cx_)))), min(width - 1, int(math.ceil(max(ax, bx, cx_))))
                y0i, y1i = max(0, int(math.floor(min(ay, by, cy_)))), min(height - 1, int(math.ceil(max(ay, by, cy_))))
                if x0i > x1i or y0i > y1i:
                    continue
                area = (bx - ax) * (cy_ - ay) - (by - ay) * (cx_ - ax)
                if abs(area) < 1e-4:
                    continue
                inv_a = 1.0 / area
                xs = np.arange(x0i, x1i + 1, dtype=np.float64)[None, :] + 0.5
                ys = np.arange(y0i, y1i + 1, dtype=np.float64)[:, None] + 0.5
                w0 = ((bx - xs) * (cy_ - ys) - (by - ys) * (cx_ - xs)) * inv_a
                w1 = ((cx_ - xs) * (ay - ys) - (cy_ - ys) * (ax - xs)) * inv_a
                w2 = 1.0 - w0 - w1
                m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
                if not m.any():
                    continue
                iz0, iz1, iz2 = 1.0 / cz[i0], 1.0 / cz[i1], 1.0 / cz[i2]
                iz = w0 * iz0 + w1 * iz1 + w2 * iz2
                zp = (1.0 / np.where(iz > 1e-9, iz, 1e-9)).astype(np.float32)
                zpatch = zbuf[y0i:y1i + 1, x0i:x1i + 1]
                upd = m & (zp < zpatch)
                if not upd.any():
                    continue
                pw0, pw1, pw2 = (w0 * iz0 * zp)[upd], (w1 * iz1 * zp)[upd], (w2 * iz2 * zp)[upd]
                albedo_base = g.face_colors[fi, :3].astype(np.float32)
                if tex_arr is not None and tri_uvs is not None:
                    uv_p = pw0[:, None] * tri_uvs[fi, 0] + pw1[:, None] * tri_uvs[fi, 1] + pw2[:, None] * tri_uvs[fi, 2]
                    th, tw = tex_arr.shape[0], tex_arr.shape[1]
                    tx = np.mod(np.floor(uv_p[:, 0] * tw).astype(np.int32), tw)
                    ty = np.mod(np.floor(uv_p[:, 1] * th).astype(np.int32), th)
                    albedo_px = np.clip(tex_arr[ty, tx] * 255.0 * (0.35 + 0.65 * (albedo_base[None, :] / 255.0)), 0, 255)
                else:
                    albedo_px = np.broadcast_to(albedo_base, (len(pw0), 3))
                if mode == "emissive":
                    rgb = np.clip(albedo_px, 0, 255).copy()
                else:
                    npix = _normalize(pw0[:, None] * vnorms[i0] + pw1[:, None] * vnorms[i1] + pw2[:, None] * vnorms[i2]).astype(np.float32)
                    ndotl = np.clip(npix @ s_dir.astype(np.float32), 0.0, 1.0)
                    if mode == "cloud":
                        rgb = np.clip(albedo_px * (0.78 + 0.24 * ndotl)[:, None], 0, 255)
                    else:
                        vis = np.ones(len(pw0), dtype=np.float32)
                        if node.receive_shadow:
                            su_p = np.round(pw0 * smu[i0] + pw1 * smu[i1] + pw2 * smu[i2]).astype(np.int32)
                            sv_p = np.round(pw0 * smv[i0] + pw1 * smv[i1] + pw2 * smv[i2]).astype(np.int32)
                            sd_p = (pw0 * smd[i0] + pw1 * smd[i1] + pw2 * smd[i2]).astype(np.float32) - 0.14
                            ins = (su_p >= 1) & (su_p < sm_res - 1) & (sv_p >= 1) & (sv_p < sm_res - 1)
                            if ins.any():
                                vis[ins] = 0.42 + 0.58 * (sd_p[ins] <= sm_depth[sv_p[ins], su_p[ins]]).astype(np.float32)
                        hemi_t = np.clip(0.5 + 0.5 * npix[:, 2], 0.0, 1.0)[:, None]
                        hemi = np.array([0.42, 0.46, 0.54], dtype=np.float32) * (1.0 - hemi_t) + np.array([0.58, 0.62, 0.70], dtype=np.float32) * hemi_t
                        fill_l = np.clip(npix @ (-s_dir * np.array([1.0, 1.0, -0.5])).astype(np.float32), 0.0, 1.0)[:, None] * 0.18
                        lit = hemi + fill_l + (ndotl * vis * 0.62)[:, None] * np.array([1.06, 1.00, 0.92], dtype=np.float32)
                        if mspec.roughness < 0.65:
                            hvec = _normalize(s_dir - fwd).astype(np.float32)
                            shininess = max(4.0, (1.0 - mspec.roughness) * 48.0)
                            spec = (np.clip(npix @ hvec, 0.0, 1.0) ** shininess * vis * (0.25 + 0.55 * mspec.metallic))[:, None]
                            lit = lit + spec
                        if p_lights:
                            wpos = (pw0[:, None] * g.vertices[i0] + pw1[:, None] * g.vertices[i1] + pw2[:, None] * g.vertices[i2]).astype(np.float32)
                            for lpos, lcol, lrad, lint in p_lights:
                                dvec = lpos[None, :] - wpos
                                dist = np.linalg.norm(dvec, axis=1)
                                att = np.clip(1.0 - dist / lrad, 0.0, 1.0) ** 2 * lint
                                ldir = dvec / np.where(dist[:, None] < 1e-5, 1.0, dist[:, None])
                                pnd = np.clip(np.einsum("ij,ij->i", npix, ldir), 0.15, 1.0)
                                lit = lit + (att * pnd)[:, None] * lcol[None, :]
                        rgb = np.clip(albedo_px * lit, 0, 255)
                        fog = np.clip((zp[upd] - rad * 2.4) / (rad * 4.0), 0.0, 0.32)[:, None]
                        rgb = rgb * (1.0 - fog) + fog_col[None, :] * fog
                zpatch[upd] = zp[upd]
                fb[y0i:y1i + 1, x0i:x1i + 1][upd] = rgb

        img = Image.fromarray(np.clip(fb, 0, 255).astype(np.uint8), mode="RGB")
        img.save(out)
        return img
