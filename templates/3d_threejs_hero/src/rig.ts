import * as THREE from 'three';

export function createRigRoot(name: string): THREE.Group {
  const root = new THREE.Group();
  root.name = name;
  return root;
}
