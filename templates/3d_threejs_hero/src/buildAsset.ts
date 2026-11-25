import * as THREE from 'three';
import { createMaterials } from './materials';
import { buildHeroBody } from './parts/bodyBuilder';
import { createRigRoot } from './rig';

export function buildAsset(): THREE.Group {
  const root = createRigRoot('threejs_hero');
  const mats = createMaterials();
  root.add(buildHeroBody(mats.heroPaint));
  const trim = new THREE.Mesh(new THREE.TorusGeometry(0.54, 0.045, 12, 32), mats.brassTrim);
  trim.name = 'Brass_Trim';
  trim.position.set(0, 0.5, 0);
  trim.rotation.x = Math.PI / 2;
  root.add(trim);
  return root;
}
