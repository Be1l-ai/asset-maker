# Stylized Character Paws, Head UVs & Cel-Shading

Organic stylized characters (such as cel-shaded cats, mascots, and creatures) break immediately when built from disconnected primitives. Follow these rules before writing character geometry:

## 1. Unified Sculpted Paws (No Detached Toe Blobs)
* **Never jam separate sphere/tube toes onto a cylinder ankle.** Under cel-shading or crease detection, detached toes produce harsh black rings and broken silhouettes.
* **Unified Fluted Paw Cushion**: Loft the ankle continuously down into a rounded paw pad (`loft_cross_sections`) whose front perimeter uses a smooth 3-lobe cosine wave (`1.0 + 0.08 * max(0, sin(a)) * cos(3 * a)`) to form subtle sculpted toe knuckles in a single watertight mesh.
* **Painted Toe-Cleft Lines**: Paint subtle dark-espresso toe-divider curves directly into the paw's albedo texture + slight indentation in the paw's normal map, keeping the silhouette clean and adorable at low triangle counts.

## 2. Painted Head Markings & Baked Fur Normals
* **Never model stripes or facial markings as 3D tubes.** Assign clean spherical/frontal UVs to the head cranium (`u = atan2(x, y)/(2*pi) + 0.5`, `v = 0.5 - z / (2*rz)`) and paint forehead tabby stripes ("M" mark), eyebrow dots, and cheek blush directly into the 512×512 head albedo map.
* **Fur Directionality via Normal Map**: Attach a tangent-space normal map from `asset_pipeline.baking.generate_fur_normal_map()` to `MaterialSpec.normal_texture` so light catches soft fur sheen without adding thousands of fur spikes.
* **Integrated Silhouette Tufts**: Only sculpt silhouette-breaking fur tufts (ears, cheek flares, chest ruff) as smooth, wide-base lofted shapes deeply embedded into the skull/chest so no cone seams appear in side profile.

## 3. Expressive Anime Eyes & Cel-Shading
* **Outward Winding Check**: When generating custom UV-mapped eye lenses (`MeshGeometry`), verify triangle normals point outward (`+Y` on front-facing characters) so backface culling never hides the irises.
* **Real-Time Inverted-Hull Ink Outlines**: Export an optional `Cel_Ink_Outlines` node (vertices offset `+0.007–0.010m` along smooth normals, flipped triangle winding, `double_sided=False`, dark warm espresso ink color) so glTF viewers and game engines render crisp silhouette outlines automatically.
