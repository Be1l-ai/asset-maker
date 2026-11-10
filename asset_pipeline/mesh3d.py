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
        direction: Optional[Sequence[float]] = None,
    ) -> "MeshBuilder":
        """Add a watertight cone along Z (base at z=0, apex at +height).

        If ``direction`` is given, the cone is tilted so its apex axis points along that
        vector (rotating about the base center) before ``offset`` is applied.
        """
        part = trimesh.creation.cone(radius=radius, height=height, sections=sections)
        if direction is not None:
            d = np.asarray(direction, dtype=np.float64)
            d = d / np.linalg.norm(d)
            part.apply_transform(trimesh.geometry.align_vectors([0.0, 0.0, 1.0], d))
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
        direction: Optional[Sequence[float]] = None,
    ) -> "MeshBuilder":
        """Add a regular pyramid (optionally tilted along ``direction``)."""
        return self.cone(
            radius=base_radius, height=height, sections=sections,
            offset=offset, color=color, direction=direction,
        )

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

    def lathe(
        self,
        profile_2d: Sequence[Sequence[float]],
        sections: int = 24,
        offset: Optional[Sequence[float]] = None,
        color: Optional[Sequence[int]] = None,
        subdivide: int = 1,
    ) -> "MeshBuilder":
        """Add a watertight revolved solid from a 2D [radius, z] profile.

        ``subdivide`` > 1 inserts extra rings along each profile segment so vertical
        gradients (ground AO, lighting) have enough faces to resolve.
        """
        part = revolve_profile(profile_2d, sections=sections, color=color, subdivide=subdivide)
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
    views: Sequence[Tuple[float, float]] = ((35.0, 22.0), (0.0, 0.0), (90.0, 0.0)),
) -> Image.Image:
    """Render a Z-up, upright software preview with several (yaw, elevation) views side by side.

    The default views are a 3/4 perspective, a front elevation, and a side elevation, so
    proportions and orientation can be judged at a glance. All views share one scale.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    raw = mesh.raw if isinstance(mesh, SolidMesh) else mesh
    w, h = size
    ss = 2
    n = len(views)
    canvas = Image.new("RGB", (w * n * ss, h * ss), (18, 22, 32))
    draw = ImageDraw.Draw(canvas)

    verts = np.asarray(raw.vertices, dtype=np.float64)
    center = (verts.max(axis=0) + verts.min(axis=0)) / 2.0
    radius = max(float(np.linalg.norm(verts - center, axis=1).max()), 1e-4)
    scale = min(w, h) * ss * 0.46 / radius

    faces = raw.faces
    face_colors = np.asarray(raw.visual.face_colors)[:, :3].astype(np.float64)
    normals = np.asarray(raw.face_normals)

    for vi, (yaw_deg, elev_deg) in enumerate(views):
        yaw, elev = np.radians(yaw_deg), np.radians(elev_deg)
        cy_, sy_ = np.cos(yaw), np.sin(yaw)
        rz = np.array([[cy_, -sy_, 0.0], [sy_, cy_, 0.0], [0.0, 0.0, 1.0]])
        cam = np.array([0.0, -np.cos(elev), np.sin(elev)])   # direction to camera
        up = np.array([0.0, np.sin(elev), np.cos(elev)])
        fwd = -cam
        right = np.array([1.0, 0.0, 0.0])

        pv = (verts - center) @ rz.T
        sx = pv @ right * scale + (vi + 0.5) * w * ss
        sy2 = -(pv @ up) * scale + h * ss / 2.0
        depth = pv @ fwd

        nrm = normals @ rz.T
        light = right * -0.45 + up * 0.65 + cam * 0.7
        light /= np.linalg.norm(light)
        facing = nrm @ cam
        diffuse = np.clip(nrm @ light, 0.0, 1.0)
        shade = 0.30 + 0.75 * diffuse

        order = np.argsort(-depth[faces].mean(axis=1))   # far to near
        for idx in order:
            if facing[idx] <= 0.0:
                continue
            f = faces[idx]
            col = tuple(int(np.clip(c * shade[idx], 0, 255)) for c in face_colors[idx])
            draw.polygon([(sx[v], sy2[v]) for v in f], fill=col, outline=col)

    preview = canvas.resize((w * n, h), Image.Resampling.LANCZOS)
    preview.save(path)
    return preview


def revolve_profile(
    profile_2d: Sequence[Sequence[float]],
    sections: int = 24,
    color: Optional[Sequence[int]] = None,
    subdivide: int = 1,
) -> trimesh.Trimesh:
    """Revolve a 2D [radius, z] profile around the Z-axis to create a watertight solid.

    Parameters:
        profile_2d: Array-like of shape (N, 2) where column 0 is radial distance (r >= 0)
                    and column 1 is vertical height (z).
        sections: Number of radial angular subdivisions.
        color: Optional RGBA color.
    """
    pts = np.asarray(profile_2d, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"profile_2d must have shape (N, 2), got {pts.shape}")

    # Ensure profile closes on the revolution axis (r=0) at bottom and top to guarantee watertightness
    pts_closed = list(pts)
    if pts_closed[0][0] != 0.0:
        pts_closed.insert(0, [0.0, pts_closed[0][1]])
    if pts_closed[-1][0] != 0.0:
        pts_closed.append([0.0, pts_closed[-1][1]])

    pts_closed = np.array(pts_closed, dtype=np.float64)
    if subdivide > 1:
        dense = [pts_closed[0]]
        for a, b in zip(pts_closed[:-1], pts_closed[1:]):
            for k in range(1, subdivide + 1):
                dense.append(a + (b - a) * (k / subdivide))
        pts_closed = np.array(dense)

    mesh = trimesh.creation.revolve(pts_closed, sections=sections)
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    if color is not None:
        set_mesh_color(mesh, color)
    return mesh


def apply_spherical_normals(
    mesh: trimesh.Trimesh,
    center: Optional[Sequence[float]] = None,
) -> trimesh.Trimesh:
    """Modify vertex normals to point radially outward from a central anchor point.

    Used for stylized foliage, tree canopies, and anime hair to give planar/card
    geometry soft, lush, volumetric lighting rather than flat planar shading.

    Parameters:
        mesh: Target trimesh.
        center: 3D point [x, y, z] to radiate from. If None, uses mesh centroid.
    """
    c = np.asarray(center if center is not None else mesh.centroid, dtype=np.float64)
    disp = mesh.vertices - c
    norms = np.linalg.norm(disp, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    mesh.vertex_normals = disp / norms
    return mesh


def bake_vertex_gradient_ao(
    mesh: trimesh.Trimesh,
    ground_z: Optional[float] = None,
    top_color: Sequence[int] = (255, 255, 255),
    ground_color: Sequence[int] = (60, 65, 80),
) -> trimesh.Trimesh:
    """Bake a stylized ground-contact ambient occlusion vertical gradient into vertex colors.

    Parameters:
        mesh: Target trimesh.
        ground_z: Baseline Z elevation (defaults to mesh minimum Z).
        top_color: RGB tint at the mesh apex.
        ground_color: RGB tint at ground contact.
    """
    verts = mesh.vertices
    z_min = ground_z if ground_z is not None else float(np.min(verts[:, 2]))
    z_max = float(np.max(verts[:, 2]))
    span = max(1e-4, z_max - z_min)

    t = np.clip((verts[:, 2] - z_min) / span, 0.0, 1.0)[:, None]
    top = np.array(top_color[:3], dtype=np.float64)
    ground = np.array(ground_color[:3], dtype=np.float64)

    blended_rgb = ground + t * (top - ground)
    alpha = np.full((len(verts), 1), 255.0)
    v_colors = np.hstack([blended_rgb, alpha]).clip(0, 255).astype(np.uint8)

    mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=v_colors)
    return mesh


def bake_ground_ao(
    mesh: trimesh.Trimesh | SolidMesh,
    height: float = 0.5,
    strength: float = 0.55,
    tint: Sequence[float] = (0.80, 0.85, 1.0),
) -> trimesh.Trimesh:
    """Multiply a ground-contact occlusion falloff into the *existing* face colors.

    Unlike :func:`bake_vertex_gradient_ao`, this preserves the material palette: faces near
    the lowest Z are darkened (and tinted cool) with a smoothstep falloff over ``height``.
    """
    raw = mesh.raw if isinstance(mesh, SolidMesh) else mesh
    colors = np.array(raw.visual.face_colors, dtype=np.float64)
    zc = raw.triangles_center[:, 2]
    t = np.clip((zc - zc.min()) / max(1e-6, height), 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    factor = 1.0 - strength * (1.0 - t)
    tint_arr = np.asarray(tint, dtype=np.float64)
    tint_mix = tint_arr[None, :] * (1.0 - t[:, None]) + t[:, None]
    colors[:, :3] = colors[:, :3] * factor[:, None] * tint_mix
    raw.visual = trimesh.visual.ColorVisuals(
        mesh=raw, face_colors=colors.clip(0, 255).astype(np.uint8)
    )
    return raw


def create_leaf_card(
    width: float = 1.0,
    height: float = 1.0,
    curvature: float = 0.1,
    color: Optional[Sequence[int]] = None,
) -> trimesh.Trimesh:
    """Create a low-poly curved alpha plane quad for foliage branches, leaf cards, and feathers.

    Parameters:
        width: Card width along X.
        height: Card length along Z.
        curvature: Curvature offset along Y for natural organic bend.
        color: Optional RGBA color.
    """
    hw = width * 0.5
    # 6-vertex curved quad (2 triangles per half)
    vertices = np.array([
        [-hw, 0.0, 0.0],
        [hw, 0.0, 0.0],
        [-hw, curvature, height * 0.5],
        [hw, curvature, height * 0.5],
        [-hw, 0.0, height],
        [hw, 0.0, height],
    ], dtype=np.float64)

    faces = np.array([
        [0, 1, 2], [2, 1, 3],
        [2, 3, 4], [4, 3, 5],
    ], dtype=np.int64)

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    if color is not None:
        set_mesh_color(mesh, color)
    return mesh

