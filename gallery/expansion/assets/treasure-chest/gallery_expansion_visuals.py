"""Seeded Z-up solid assemblies in meters and straight-alpha inventory/UI artwork."""
from __future__ import annotations

import aggdraw
import numpy as np
import trimesh
from PIL import Image, ImageDraw

from asset_pipeline.generate_gallery import paint, ring_solid, beveled_hexahedron

__all__ = ["pine_tree", "treasure_chest", "shield_icon", "dialog_panel", "RECIPES"]


def _rng(seed):
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    return np.random.default_rng(seed)


def _canvas(size):
    if isinstance(size, bool) or not isinstance(size, int) or not 32 <= size <= 1024:
        raise ValueError("size must be an integer in 32..1024")
    return Image.new("RGBA", (size * 3, size * 3))


def _finish(image, size):
    image = image.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    # Remove invisible RGB and any ringing at the frame boundary.
    pixels = np.asarray(image).copy()
    pixels[0] = pixels[-1] = 0
    pixels[:, 0] = pixels[:, -1] = 0
    pixels[pixels[..., 3] == 0] = 0
    return Image.fromarray(pixels)


def _block(extents, center, color, bevel=.045):
    half = np.asarray(extents) / 2
    corners = np.array([[(-1 if i & 1 else 1) * half[0],
                         (-1 if i & 2 else 1) * half[1],
                         (-1 if i & 4 else 1) * half[2]] for i in range(8)])
    mesh = beveled_hexahedron(corners, bevel)
    mesh.apply_translation(center)
    return paint(mesh, color)


def _assembly(parts, seed, name):
    # Validate components individually: a positive aggregate can hide an inverted part.
    for part in parts:
        if not part.is_volume or np.min(part.area_faces) <= 1e-10:
            raise ValueError("Recipe produced a non-solid or degenerate component")
    mesh = trimesh.util.concatenate(parts)
    if len(mesh.faces) >= 3000:
        raise ValueError("Recipe exceeded its triangle budget")
    mesh.metadata.update(units="m", up_axis="Z", pivot="ground center", seed=seed,
                         name=name, components=len(parts), topology="overlapping closed solids")
    return mesh


def _bough_whorl(rng, radius, base, height, lobes, phase, lean, tier):
    """Star-shaped, drooping branch skirt with tucked underside and ridged shoulders."""
    n = lobes * 2
    theta = phase + np.arange(n) * np.pi / lobes
    lengths = np.repeat(rng.uniform(.88, 1.12, lobes), 2)
    tips = np.arange(n) % 2 == 0
    spread = lengths * np.where(tips, 1., .60)
    droop = np.repeat(rng.uniform(.015, .085, lobes), 2)
    # Unlike a cone, the section turns outward, then folds into uneven hanging tips.
    profiles = [(.32 * lengths, np.full(n, base + height * .09)),
                (spread, base + height * np.where(tips, -droop, .17)),
                (spread * .76, base + height * np.where(tips, .32, .51)),
                (lengths * .075, np.full(n, base + height))]
    vertices = []
    for radii, zs in profiles:
        for r, z, angle in zip(radii, zs, theta):
            vertices.append([radius * r * np.cos(angle) + lean[0] * z,
                             radius * r * np.sin(angle) + lean[1] * z, z])
    vertices.extend([np.mean(vertices[:n], axis=0), np.mean(vertices[-n:], axis=0)])
    faces, colors = [], []
    greens = np.array([[33, 79, 66], [39, 102, 78], [51, 121, 85], [70, 139, 93]])
    branch_tones = rng.integers(-7, 8, lobes)
    for level in range(3):
        for j in range(n):
            a, b = level * n + j, level * n + (j + 1) % n
            faces.extend([[a, b, b + n], [a, b + n, a + n]])
            rgb = greens[level] + tier * np.array([2, 3, 1]) + branch_tones[j // 2]
            colors.extend([[*rgb, 255]] * 2)
    for j in range(n):
        faces.extend([[4 * n, (j + 1) % n, j],
                      [4 * n + 1, 3 * n + j, 3 * n + (j + 1) % n]])
        colors.extend([[27, 63, 53, 255], [83, 145, 99, 255]])
    return trimesh.Trimesh(vertices=vertices, faces=faces, face_colors=colors, process=False)


def pine_tree(seed=19) -> trimesh.Trimesh:
    """Five irregular bough whorls, a tapered trunk, and exposed roots at roughly 3.6m."""
    rng = _rng(seed)
    lean = rng.uniform(-.025, .025, 2)
    height_scale = rng.uniform(.96, 1.07)
    trunk = ring_solid([(.245, 0), (.18, .23), (.122, 1.35), (.045, 3.25)], sides=9)
    trunk.vertices[:, :2] += trunk.vertices[:, 2:3] * lean
    parts = [paint(trunk, [104, 70, 44], variation=12, seed=seed)]
    for angle in np.arange(4) * np.pi / 2 + rng.uniform(0, .6):
        root = _block([.50, .135, .16], [.19, 0, .08], [89, 59, 38], .13)
        # Broad buttress wedge, grounded at its outer end.
        root.vertices[:, 2] *= np.clip(1.2 - root.vertices[:, 0] * 2.1, .25, 1.2)
        root.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 0, 1]))
        parts.append(root)
    tiers = [(1.04, .72, 1.03, 8), (.91, 1.30, .96, 7),
             (.70, 1.87, .88, 7), (.51, 2.38, .77, 6), (.32, 2.84, .71, 5)]
    phase = rng.uniform(0, 2 * np.pi)
    for tier, (radius, base, height, lobes) in enumerate(tiers):
        phase += .43 + rng.uniform(-.16, .16)
        parts.append(_bough_whorl(rng, radius, base, height, lobes, phase, lean, tier))
        if tier < 2:
            for angle in phase + np.arange(3) * 2 * np.pi / 3:
                start = np.array([lean[0] * base, lean[1] * base, base + .11])
                end = start + [radius * .70 * np.cos(angle), radius * .70 * np.sin(angle), -.01]
                branch = ring_solid([(.053, 0), (.023, np.linalg.norm(end - start))], sides=5)
                branch.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], (end - start) / np.linalg.norm(end - start)))
                branch.apply_translation(start)
                parts.append(paint(branch, [102, 72, 43]))
    for part in parts:
        part.vertices[:, 2] *= height_scale
    return _assembly(parts, seed, "Windward Pine")


def _arch_band(x, width, ry, rz, spring, thickness, color):
    """Continuous closed iron strap, not ten abutting wedges with internal faces."""
    vertices = []
    for angle in np.linspace(0, np.pi, 11):
        for dx, r_y, r_z in [(-width / 2, ry, rz), (width / 2, ry, rz),
                              (width / 2, ry - thickness, rz - thickness),
                              (-width / 2, ry - thickness, rz - thickness)]:
            vertices.append([x + dx, r_y * np.cos(angle), spring + r_z * np.sin(angle)])
    faces = []
    for k in range(10):
        for j in range(4):
            a, b = 4 * k + j, 4 * k + (j + 1) % 4
            faces.extend([[a, b, b + 4], [a, b + 4, a + 4]])
    faces.extend([[0, 2, 1], [0, 3, 2], [40, 41, 42], [40, 42, 43]])
    # Cross sections run clockwise around the arch: invert the known inward winding.
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.invert()
    return paint(mesh, color)


def _stud(center, direction, color, radius=.023):
    # Six-sided forged heads: readable hardware without spending bevels on tiny bolts.
    mesh = ring_solid([(radius, 0), (radius * .72, .023)], sides=6)
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction))
    mesh.apply_translation(center)
    return paint(mesh, color)


def treasure_chest(seed=19) -> trimesh.Trimesh:
    """Static plank chest with a stave lid, iron bands, and brass lock, front facing -Y."""
    rng = _rng(seed)
    width, depth = rng.uniform(1.68, 1.86), rng.uniform(.94, 1.04)
    ry, rz, spring = depth / 2 + .018, rng.uniform(.36, .43), .875
    iron, iron_edge, brass = [39, 51, 54], [67, 81, 80], [190, 137, 66]
    wood = np.array([151, 84, 39]) + rng.integers(-8, 9) * np.array([1, 1, .5])
    parts = [_block([width - .07, depth - .04, .69], [0, 0, .52], [65, 39, 26])]
    for x in (-width * .38, width * .38):
        for y in (-depth * .34, depth * .34):
            parts.append(_block([.235, .235, .235], [x, y, .1175], [85, 51, 29], .12))
            parts.append(_block([.251, .251, .082], [x, y, .045], iron, .09))
    for row in range(4):
        z = .27 + row * .157
        tone = wood + rng.uniform(-13, 13)
        for y in (-depth / 2, depth / 2):
            parts.append(_block([width, .072, .146], [0, y, z], tone, .019))
        for x in (-width / 2, width / 2):
            parts.append(_block([.068, depth - .05, .146], [x, 0, z], tone * .91, .025))
    # A dark closed dome behind spaced staves prevents light-through cracks.
    for x, length, color in [(0, width - .06, [69, 41, 27]),
                              (-width / 2, .045, wood * .89),
                              (width / 2, .045, wood * .89)]:
        profile = [[x + dx, ry * .975 * np.cos(t), spring + rz * .975 * np.sin(t)]
                   for dx in (-length / 2, length / 2) for t in np.linspace(0, np.pi, 11)]
        parts.append(paint(trimesh.convex.convex_hull(np.array(profile)), color))
    for i in range(10):
        a, b = i * np.pi / 10 + .009, (i + 1) * np.pi / 10 - .009
        corners = np.array([[x, (ry - inset) * np.cos(t), spring + (rz - inset) * np.sin(t)]
                            for x in (-width / 2, width / 2)
                            for inset in (.045, 0) for t in (a, b)])
        parts.append(paint(beveled_hexahedron(corners, .022), wood + rng.uniform(-16, 16)))
    for z in (.193, .842):
        for y in (-depth / 2 - .017, depth / 2 + .017):
            parts.append(_block([width + .07, .061, .066], [0, y, z], iron_edge, .04))
        for x in (-width / 2 - .018, width / 2 + .018):
            parts.append(_block([.064, depth + .037, .066], [x, 0, z], iron, .04))
    strap_x = width * rng.uniform(.275, .315)
    for x in (-strap_x, strap_x):
        parts.append(_arch_band(x, .125, ry + .027, rz + .029, spring, .032, iron_edge))
        for sign in (-1, 1):
            y = sign * (depth / 2 + .047)
            parts.append(_block([.125, .038, .665], [x, y, .53], iron, .045))
            for z in (.28, .72):
                parts.append(_stud([x, y + sign * .018, z], [0, sign, 0], brass))
        for t in (np.pi * .25, np.pi * .75):
            normal = np.array([0, np.cos(t) / ry, np.sin(t) / rz])
            normal /= np.linalg.norm(normal)
            parts.append(_stud([x, (ry + .028) * np.cos(t), spring + (rz + .030) * np.sin(t)], normal, brass))
        hinge = trimesh.creation.cylinder(radius=.044, height=.19, sections=8)
        hinge.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0]))
        hinge.apply_translation([x, depth / 2 + .049, spring])
        parts.append(paint(hinge, iron_edge))
    front = -depth / 2 - .085
    parts.append(_block([.25, .052, .31], [0, front, .70], iron, .12))
    parts.append(_block([.195, .029, .265], [0, front - .030, .71], brass, .11))
    parts.append(_block([.088, .065, .20], [0, front + .018, .922], iron_edge, .06))
    parts.append(_stud([0, front - .05, .74], [0, -1, 0], [29, 32, 29], .028))
    parts.append(_block([.027, .018, .053], [0, front - .062, .708], [29, 32, 29], .03))
    return _assembly(parts, seed, "Cinderwood Coffer")


def _shield_path(n, scale, shoulder, crown, dy=0):
    path = aggdraw.Path()

    def xy(x, y):
        return ((192 + (x - 192) * scale) * n / 384,
                (192 + (y - 192) * scale + dy) * n / 384)

    path.moveto(*xy(192, 38))
    for x, y in [(224, crown), (shoulder, 58), (311, 87), (295, 207)]:
        path.lineto(*xy(x, y))
    path.curveto(*xy(285, 270), *xy(240, 310), *xy(192, 345))
    path.curveto(*xy(144, 310), *xy(99, 270), *xy(89, 207))
    for x, y in [(73, 87), (384 - shoulder, 58), (160, crown)]:
        path.lineto(*xy(x, y))
    path.close()
    return path


def _path_fill(image, path, color):
    draw = aggdraw.Draw(image)
    draw.path(path, aggdraw.Brush(color))
    draw.flush()


def _gradient_path(image, path, top, bottom):
    mask = Image.new("L", image.size)
    _path_fill(mask, path, 255)
    n = image.width
    yy, xx = np.mgrid[:n, :n] / n
    t = np.clip(.75 * yy + .25 * xx, 0, 1)[..., None]
    rgb = np.asarray(top) * (1 - t) + np.asarray(bottom) * t
    layer = Image.fromarray(np.dstack([rgb, np.asarray(mask)]).astype(np.uint8))
    return Image.alpha_composite(image, layer)


def shield_icon(size=384, seed=19) -> Image.Image:
    """Copper kite shield with blue enamel, pale heraldry, and a centered inventory pivot."""
    rng = _rng(seed)
    image = _canvas(size)
    n, q = image.width, image.width / 384
    shoulder, crown = rng.uniform(270, 288), rng.uniform(67, 80)
    blue_shift = int(rng.integers(-9, 10))
    _path_fill(image, _shield_path(n, 1, shoulder, crown, 4), (18, 28, 33, 255))
    image = _gradient_path(image, _shield_path(n, .967, shoulder, crown),
                           [251, 183, 111], [137, 65, 42])
    _path_fill(image, _shield_path(n, .863, shoulder, crown), (255, 206, 144, 255))
    _path_fill(image, _shield_path(n, .837, shoulder, crown), (61, 47, 43, 255))
    enamel_path = _shield_path(n, .802, shoulder, crown)
    image = _gradient_path(image, enamel_path,
                           [45, 130 + blue_shift, 162], [17, 57 + blue_shift, 85])
    # Clip the broad facet to the enamel: a changing crown must not paint over the rim.
    mask = Image.new("L", image.size)
    _path_fill(mask, enamel_path, 255)
    facet = Image.new("RGBA", image.size)
    points = [(192, 77), (192, 304), (152, 268), (121, 207), (108, 115)]
    ImageDraw.Draw(facet).polygon([(x * q, y * q) for x, y in points],
                                  fill=(53, 130 + blue_shift, 154, 255))
    pixels = np.asarray(facet).copy()
    pixels[..., 3] = np.minimum(pixels[..., 3], np.asarray(mask))
    image = Image.alpha_composite(image, Image.fromarray(pixels))
    draw = ImageDraw.Draw(image)

    def polygon(points, fill):
        draw.polygon([(x * q, y * q) for x, y in points], fill=fill)

    wing = rng.uniform(50, 63)
    lift = rng.uniform(145, 164)
    emblem = [(192, 116), (207, 174), (192 + wing, lift), (237, 193),
              (207, 215), (192, 276), (177, 215), (147, 193),
              (192 - wing, lift), (177, 174)]
    polygon([(x, y + 5) for x, y in emblem], (13, 46, 65, 255))
    polygon(emblem, (255, 224, 159, 255))
    polygon([(192, 126), (192, 264), (207, 215), (237, 193),
             (192 + wing - 6, lift + 8), (207, 181)], (211, 143, 76, 255))
    polygon([(192, 177), (205, 196), (192, 215), (179, 196)], (34, 67, 79, 255))
    polygon([(192, 183), (200, 196), (192, 207), (184, 196)], (129, 215, 219, 255))
    # Three large rivets survive as accents at 64px; not essential at 32px.
    for x, y in [(94, 106), (290, 106), (192, 321)]:
        draw.ellipse(((x - 5) * q, (y - 5) * q, (x + 5) * q, (y + 5) * q), fill=(83, 46, 34, 255))
        draw.ellipse(((x - 3) * q, (y - 4) * q, (x + 3) * q, (y + 2) * q), fill=(255, 218, 159, 255))
    return _finish(image, size)


def dialog_panel(size=384, seed=19) -> Image.Image:
    """Flat gold/green UI rails with nine-slice insets of round(size / 6) on every edge."""
    rng = _rng(seed)
    image = _canvas(size)
    q = image.width / 384
    draw = ImageDraw.Draw(image)
    green = int(rng.integers(-8, 13))

    def polygon(points, color):
        draw.polygon([(x * q, y * q) for x, y in points], fill=color)

    def chamfer(inset, cut, color):
        a, b = inset, 384 - inset
        polygon([(a + cut, a), (b - cut, a), (b, a + cut), (b, b - cut),
                 (b - cut, b), (a + cut, b), (a, b - cut), (a, a + cut)], color)

    chamfer(13, 22, (12, 23, 23, 255))
    chamfer(17, 20, (99, 76, 40, 255))
    chamfer(19, 19, (222, 183, 106, 255))
    chamfer(23, 17, (75, 59, 34, 255))
    chamfer(26, 15, (40, 91 + green, 70, 255))
    chamfer(31, 13, (19, 48, 42, 255))
    chamfer(34, 12, (160, 140, 81, 255))
    chamfer(36, 11, (7, 18, 19, 255))
    chamfer(41, 9, (15, 29, 29, 228))
    length, breadth = rng.uniform(9, 13), rng.uniform(4, 6)
    for sx, sy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]:
        def mirror(points):
            return [(x if sx == 1 else 384 - x, y if sy == 1 else 384 - y) for x, y in points]

        # An architectural elbow and diagonally set leaf jewel, wholly inside 64px.
        polygon(mirror([(24, 53), (24, 34), (34, 24), (53, 24),
                        (53, 29), (37, 29), (29, 37), (29, 53)]), (242, 204, 123, 255))
        polygon(mirror([(32, 52), (32, 40), (40, 32), (52, 32),
                        (52, 35), (42, 35), (35, 42), (35, 52)]), (9, 34, 30, 255))
        jewel = [(40 - length, 40 - length), (40 + breadth, 40 - breadth),
                 (40 + length, 40 + length), (40 - breadth, 40 + breadth)]
        polygon(mirror(jewel), (14, 37, 31, 255))
        jewel = [(40 - length + 3, 40 - length + 3), (40 + breadth - 1, 40 - breadth + 1),
                 (40 + length - 3, 40 + length - 3), (40 - breadth + 1, 40 + breadth - 1)]
        polygon(mirror(jewel), (107, 167 + green, 113, 255))
        polygon(mirror([(40 - length + 3, 40 - length + 3), (40, 40),
                        (40 - breadth + 1, 40 + breadth - 1)]), (188, 217, 145, 255))
    pixels = np.asarray(_finish(image, size)).copy()
    inset, middle = round(size / 6), size // 2
    end = size - inset
    # Extend flat rails to the slice cuts so Lanczos ringing cannot leak corner colors.
    pixels[:inset, inset:end] = pixels[:inset, middle:middle + 1]
    pixels[end:, inset:end] = pixels[end:, middle:middle + 1]
    pixels[inset:end, :inset] = pixels[middle:middle + 1, :inset]
    pixels[inset:end, end:] = pixels[middle:middle + 1, end:]
    pixels[inset:end, inset:end] = pixels[middle, middle]
    return Image.fromarray(pixels)


RECIPES = {
    "pine-tree": {
        "name": "Windward Pine",
        "description": "Five ragged, folded evergreen whorls above a tapered cinnamon trunk and exposed buttress roots.",
        "tags": ["3d", "pine", "low-poly", "foliage", "Z-up", "meters"],
        "parameters": {"seed": 19},
        "review": {
            "intent": "Alternating tips and valleys create tiered branch silhouettes rather than plain cones.",
            "observed": "Front, side and depth-buffered obliques show pointed, folded boughs and a readable trunk; foliage looks origami-like.",
            "limitations": ["Faceted solid foliage reads as stylized clumps, not botanical needles.",
                            "Whorls, branches and trunk overlap; internal faces remain and summed volume is not union volume.",
                            "Legacy painter-sorted previews can show false overlap streaks; depth-buffer diagnostics are cleaner, not PBR.",
                            "No wind animation, UVs, LODs or collision proxy; engine import untested."]},
    },
    "treasure-chest": {
        "name": "Cinderwood Coffer",
        "description": "Warm plankwork and a ten-stave curved lid framed by cool iron bands, four feet and a brass lock plate.",
        "tags": ["3d", "chest", "wood", "iron", "closed", "meters"],
        "parameters": {"seed": 19},
        "review": {
            "intent": "Broad plank seams, a barrel profile and contrasting hardware establish the chest at prop scale.",
            "observed": "Depth-buffered front/back obliques clearly show both straps, planks, feet and latch; side lid caps look plain.",
            "limitations": ["Closed static assembly: solid backing, no usable interior, separate lid rig or working hinges.",
                            "Keyhole is dark relief, not a cutout; wood has color bands but no grain texture.",
                            "Overlapping closed solids retain internal faces; not a boolean union or collision mesh.",
                            "Legacy export_model painter preview visibly misorders long overlapping faces; depth-buffer review is necessary.",
                            "No UV/PBR materials; portable OBJ loses colors; engine import untested."]},
    },
    "shield-icon": {
        "name": "Tidewatch Aegis",
        "description": "Crowned copper kite silhouette, split blue enamel and a pale winged spear with a sea-glass heart.",
        "tags": ["2d", "icon", "shield", "copper", "blue", "RGBA"],
        "parameters": {"size": 384, "seed": 19},
        "review": {
            "intent": "Large bright heraldry and a thick copper rim preserve the shield read at inventory size.",
            "observed": "Light/dark 32px and 64px reviews retain the crowned shield and bright spear; tiny fasteners lose definition.",
            "limitations": ["At 32px the jewel and rivets merge into accents; the winged spear is deliberately simplified.",
                            "Painted highlights are fixed, not responsive lighting; raster PNG only, not editable SVG.",
                            "Not pixel art or an engine-tested UI sprite."]},
    },
    "dialog-panel": {
        "name": "Verdant Charter",
        "description": "Gold and green chamfered rails with four leaf jewels around a uniform translucent dark inset.",
        "tags": ["2d", "UI", "panel", "9-slice", "gold", "green", "RGBA"],
        "parameters": {"size": 384, "seed": 19},
        "nine_slice": {"insets_at_384": [64, 64, 64, 64], "order": "left, top, right, bottom",
                       "scaled_inset": "round(size / 6)", "minimum_target_at_384": [128, 128],
                       "center_rgba": [14, 29, 29, 228], "alpha": "straight"},
        "review": {
            "intent": "Uniform center and translation-invariant edge strips can stretch without stretching ornaments.",
            "observed": "384px light/dark and wide/tall sliced previews preserve straight rails and corner proportions.",
            "limitations": ["Must use the declared slices; uniform whole-image resizing also scales the border.",
                            "No baked text, layout, focus/hover states or engine nine-slice configuration.",
                            "Corner gems need normal UI scale; a 32px whole panel is only a thumbnail.",
                            "Translucent center appearance depends on the background; no engine import tested."]},
    },
}
