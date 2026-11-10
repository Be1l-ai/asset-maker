# Bevels, Chamfers, and Edge Weight

How stylized modeling uses exaggerated chamfers and weighted edges to catch broad specular highlights without complex normal maps.

---

## 1. Why Photoreal Bevels Fail in Stylized Art

In photorealistic PBR pipelines, bevels are kept microscopic ($0.1\text{--}1.0\text{ mm}$) to simulate real-world milled steel, relying on dense $4\text{K}$ normal map bakes to catch hair-thin reflections.

In stylized and low-poly art (*World of Warcraft*, *Torchlight*, *Ghibli*):
- Micro-bevels disappear entirely when viewed from game cameras, degenerating into razor-sharp aliased pixels.
- Instead, artists model **chunky, exaggerated chamfers** ($45^\circ$ planar cuts) directly into the polygon geometry.

---

## 2. The Mechanics of the Stylized Bevel

A stylized bevel serves three distinct graphic purposes:
1. **Highlight Catcher**: Broad $45^\circ$ bevel faces reflect directional key-light into the camera, automatically outlining 3D forms with natural rim highlights.
2. **Clay / Sculpted Feel**: Softens harsh $90^\circ$ computer-generated corners, giving solids a hand-carved stone, sculpted clay, or cast resin physical presence.
3. **Silhouette Break**: Breaks up monotonous straight polygon edges with intentional facets.

---

## 3. Geometric Guidelines for Agents

- **Cylinders & Columns**: Use 8 to 16 radial subdivisions. Add an octagonal chamfer collar at top and bottom rims.
- **Chests & Wooden Planks**: Chamfer the outer edge of planks by $10\text{--}15\%$ of their thickness.
- **Obelisks & Monuments**: Taper the corners of square shafts with an angled 4-point bevel to soften the silhouette.
