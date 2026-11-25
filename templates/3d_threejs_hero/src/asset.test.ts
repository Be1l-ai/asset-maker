import { buildAsset } from './buildAsset';

const root = buildAsset();
if (root.children.length < 2) {
  throw new Error('Expected at least 2 named subsystem groups');
}
console.log('✓ Three.js hero asset structure verified:', root.children.map(c => c.name));
