import * as THREE from 'three';
import { createPaintedCanvasTexture } from './textures';

export function createMaterials() {
  return {
    heroPaint: new THREE.MeshStandardMaterial({ map: createPaintedCanvasTexture(), roughness: 0.72, metalness: 0.08 }),
    brassTrim: new THREE.MeshStandardMaterial({ color: 0xd4a84f, roughness: 0.32, metalness: 0.88 }),
  };
}
