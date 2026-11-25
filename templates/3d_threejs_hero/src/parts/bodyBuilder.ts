import * as THREE from 'three';

export function buildHeroBody(mat: THREE.Material): THREE.Group {
  const group = new THREE.Group();
  group.name = 'Hero_Body';
  const geom = new THREE.LatheGeometry([
    new THREE.Vector2(0.0, 0.0),
    new THREE.Vector2(0.65, 0.25),
    new THREE.Vector2(0.50, 1.20),
    new THREE.Vector2(0.0, 1.55),
  ], 24);
  const mesh = new THREE.Mesh(geom, mat);
  mesh.name = 'Hero_Body_Mesh';
  group.add(mesh);
  return group;
}
