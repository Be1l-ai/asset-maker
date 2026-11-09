"""3D solid geometry classes and procedural mesh construction helpers."""

from pathlib import Path
from typing import List, Optional, Sequence, Tuple
import numpy as np
from PIL import Image, ImageDraw
import trimesh

Z_TO_Y = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])


class SolidMesh:
    """Class representing a watertight 3D solid mesh with CSG operations."""

    def __init__(self, mesh: trimesh.Trimesh):
        self._mesh = mesh

    @property
    def raw(self) -> trimesh.Trimesh:
        """Access underlying trimesh.Trimesh object."""
        return self._mesh

    @property
    def vertices(self) -> np.ndarray:
        return self._mesh.vertices

    @property
    def faces(self) -> np.ndarray:
        return self._mesh.faces

    @property
    def triangle_count(self) -> int:
        return len(self._mesh.faces)

    def set_color(self, rgba: Sequence[int]) -> "SolidMesh":
        """Assign uniform face color."""
        color = np.array(rgba, dtype=np.uint8)
        self._mesh.visual = trimesh.visual.ColorVisuals(
            mesh=self._mesh,
            face_colors=np.tile(color, (len(self._mesh.faces), 1))
        )
        return self

    def translate(self, offset: Sequence[float]) -> "SolidMesh":
        """Translate mesh in place."""
        self._mesh.apply_translation(offset)
        return self

    def rotate(self, axis: Sequence[float], angle_rad: float) -> "SolidMesh":
        """Rotate mesh around an axis."""
        matrix = trimesh.transformations.rotation_matrix(angle_rad, axis)
        self._mesh.apply_transform(matrix)
        return self

    def scale(self, factor: float | Sequence[float]) -> "SolidMesh":
        """Scale mesh by scalar or 3-vector factor."""
        self._mesh.apply_scale(factor)
        return self

    def union(self, other: "SolidMesh") -> "SolidMesh":
        """Perform solid boolean union via Manifold3D."""
        res = trimesh.boolean.boolean_manifold([self._mesh, other.raw], operation="union")
        return SolidMesh(res)

    def difference(self, other: "SolidMesh") -> "SolidMesh":
        """Perform solid boolean difference (self - other) via Manifold3D."""
        res = trimesh.boolean.boolean_manifold([self._mesh, other.raw], operation="difference")
        return SolidMesh(res)

    def intersect(self, other: "SolidMesh") -> "SolidMesh":
        """Perform solid boolean intersection via Manifold3D."""
        res = trimesh.boolean.boolean_manifold([self._mesh, other.raw], operation="intersection")
        return SolidMesh(res)

    def ensure_watertight(self) -> "SolidMesh":
        """Merge vertices and verify watertightness and positive volume."""
        self._mesh.merge_vertices(merge_tex=True, merge_norm=True)
        if not self._mesh.is_watertight:
            raise ValueError("Mesh is not watertight")
        if self._mesh.volume <= 0:
            raise ValueError("Mesh has non-positive volume")
        return self

    def export_glb(self, path: Path | str, apply_y_up: bool = True) -> Path:
        """Export mesh to glTF Binary (GLB) with optional Z-to-Y conversion."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        export_mesh = self._mesh.copy()
        if apply_y_up:
            export_mesh.apply_transform(Z_TO_Y)
        scene = trimesh.Scene(geometry=export_mesh)
        out.write_bytes(scene.export(file_type="glb"))
        return out

    def export_obj(self, path: Path | str) -> Path:
        """Export mesh to standard Wavefront OBJ."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(trimesh.exchange.obj.export_obj(self._mesh))
        return out

    def render_preview(self, path: Path | str, size: Tuple[int, int] = (512, 512)) -> Image.Image:
        """Render diagnostic multi-angle software preview."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return render_multi_view_preview(self._mesh, path, size=size)


class MeshBuilder:
    """Fluent builder for composing solid 3D models from primitives."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.parts: List[trimesh.Trimesh] = []

    def box(
        self,
        extents: Sequence[float] = (1.0, 1.0, 1.0),
        offset: Optional[Sequence[float]] = None,
        color: Optional[Sequence[int]] = None,
    ) -> "MeshBuilder":
        """Add a watertight box."""
        part = trimesh.creation.box(extents=extents)
        if color:
            set_mesh_color(part, color)
        if offset:
            part.apply_translation(offset)
        self.parts.append(part)
        return self

    def cylinder(
        self,
        radius: float = 0.5,
        height: float = 1.0,
        sections: int = 16,
        offset: Optional[Sequence[float]] = None,
        color: Optional[Sequence[int]] = None,
    ) -> "MeshBuilder":
        """Add a watertight cylinder along Z."""
        part = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
        if color:
            set_mesh_color(part, color)
        if offset:
            part.apply_translation(offset)
        self.parts.append(part)
        return self

    def cone(
        self,
        radius: float = 0.5,
        height: float = 1.0,
        sections: int = 16,
        offset: Optional[Sequence[float]] = None,
        color: Optional[Sequence[int]] = None,
    ) -> "MeshBuilder":
        """Add a watertight cone along Z."""
        part = trimesh.creation.cone(radius=radius, height=height, sections=sections)
        if color:
            set_mesh_color(part, color)
        if offset:
            part.apply_translation(offset)
        self.parts.append(part)
        return self

    def pyramid(
        self,
        base_radius: float = 0.5,
        height: float = 1.0,
        sections: int = 4,
        offset: Optional[Sequence[float]] = None,
        color: Optional[Sequence[int]] = None,
    ) -> "MeshBuilder":
        """Add a regular pyramid."""
        return self.cone(radius=base_radius, height=height, sections=sections, offset=offset, color=color)

    def icosphere(
        self,
        radius: float = 0.5,
        subdivisions: int = 2,
        offset: Optional[Sequence[float]] = None,
        color: Optional[Sequence[int]] = None,
    ) -> "MeshBuilder":
        """Add a watertight icosphere."""
        part = trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)
        if color:
            set_mesh_color(part, color)
        if offset:
            part.apply_translation(offset)
        self.parts.append(part)
        return self

    def add_mesh(self, mesh: trimesh.Trimesh | SolidMesh) -> "MeshBuilder":
        """Add an arbitrary trimesh or SolidMesh."""
        self.parts.append(mesh.raw if isinstance(mesh, SolidMesh) else mesh)
        return self

    def build(self) -> SolidMesh:
        """Concatenate all parts and return a SolidMesh."""
        if not self.parts:
            raise ValueError("MeshBuilder has no parts to assemble")
        combined = trimesh.util.concatenate(self.parts)
        solid = SolidMesh(combined)
        solid.ensure_watertight()
        return solid


# Functional helpers for direct access
def set_mesh_color(mesh: trimesh.Trimesh, rgba: Sequence[int]) -> trimesh.Trimesh:
    color = np.array(rgba, dtype=np.uint8)
    mesh.visual = trimesh.visual.ColorVisuals(
        mesh=mesh,
        face_colors=np.tile(color, (len(mesh.faces), 1))
    )
    return mesh


def create_box(extents: Sequence[float] = (1.0, 1.0, 1.0), color: Optional[Sequence[int]] = None) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=extents)
    if color is not None:
        set_mesh_color(mesh, color)
    return mesh


def create_cylinder(radius: float = 0.5, height: float = 1.0, sections: int = 16, color: Optional[Sequence[int]] = None) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    if color is not None:
        set_mesh_color(mesh, color)
    return mesh


def create_cone(radius: float = 0.5, height: float = 1.0, sections: int = 16, color: Optional[Sequence[int]] = None) -> trimesh.Trimesh:
    mesh = trimesh.creation.cone(radius=radius, height=height, sections=sections)
    if color is not None:
        set_mesh_color(mesh, color)
    return mesh


def create_pyramid(base_radius: float = 0.5, height: float = 1.0, sections: int = 4, color: Optional[Sequence[int]] = None) -> trimesh.Trimesh:
    return create_cone(radius=base_radius, height=height, sections=sections, color=color)


def create_sphere(radius: float = 0.5, subdivisions: int = 2, color: Optional[Sequence[int]] = None) -> trimesh.Trimesh:
    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)
    if color is not None:
        set_mesh_color(mesh, color)
    return mesh


def boolean_union(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.boolean_manifold([a, b], operation="union")


def boolean_difference(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.boolean_manifold([a, b], operation="difference")


def boolean_intersection(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.boolean_manifold([a, b], operation="intersection")


def ensure_watertight(mesh: trimesh.Trimesh) -> None:
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    if not mesh.is_watertight:
        raise ValueError("Mesh is not watertight")
    if mesh.volume <= 0:
        raise ValueError("Mesh has non-positive volume")


def export_glb(mesh: trimesh.Trimesh | SolidMesh, path: Path | str, apply_y_up: bool = True) -> Path:
    if isinstance(mesh, SolidMesh):
        return mesh.export_glb(path, apply_y_up=apply_y_up)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    export_mesh = mesh.copy()
    if apply_y_up:
        export_mesh.apply_transform(Z_TO_Y)
    scene = trimesh.Scene(geometry=export_mesh)
    out.write_bytes(scene.export(file_type="glb"))
    return out


def export_obj(mesh: trimesh.Trimesh | SolidMesh, path: Path | str) -> Path:
    if isinstance(mesh, SolidMesh):
        return mesh.export_obj(path)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(trimesh.exchange.obj.export_obj(mesh))
    return out


def render_multi_view_preview(
    mesh: trimesh.Trimesh | SolidMesh,
    path: Path | str,
    size: Tuple[int, int] = (512, 512),
) -> Image.Image:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    raw = mesh.raw if isinstance(mesh, SolidMesh) else mesh
    preview = Image.new("RGB", size, (18, 22, 32))
    draw = ImageDraw.Draw(preview)
    w, h = size

    angles = [np.pi / 5, -np.pi / 4, 0]
    rot = trimesh.transformations.euler_matrix(*angles)[:3, :3]
    verts = raw.vertices @ rot.T

    center = (verts.max(axis=0) + verts.min(axis=0)) / 2.0
    extents = verts.max(axis=0) - verts.min(axis=0)
    scale = (min(w, h) * 0.75) / max(extents[0], extents[1], 1e-4)

    proj_x = (verts[:, 0] - center[0]) * scale + w / 2.0
    proj_y = -(verts[:, 1] - center[1]) * scale + h / 2.0
    depth = verts[:, 2]

    faces = raw.faces
    face_depths = np.mean(depth[faces], axis=1)
    order = np.argsort(face_depths)

    light_dir = np.array([0.5, 0.7, 0.5])
    light_dir /= np.linalg.norm(light_dir)
    normals = raw.face_normals @ rot.T

    face_colors = getattr(raw.visual, "face_colors", None)

    for idx in order:
        f = faces[idx]
        pts = [(proj_x[v], proj_y[v]) for v in f]
        n = normals[idx]
        diffuse = max(0.2, float(np.dot(n, light_dir)))

        if face_colors is not None and len(face_colors) > idx:
            base = face_colors[idx][:3]
        else:
            base = [140, 180, 220]

        color = tuple(int(np.clip(c * diffuse, 0, 255)) for c in base)
        draw.polygon(pts, fill=color, outline=(25, 30, 42))

    preview.save(path)
    return preview
