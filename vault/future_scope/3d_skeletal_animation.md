# Future Scope: 3D Skeletal Animation & Rigging Roadmap

Defines the boundary between currently supported procedural generation and the future roadmap for 3D character animation.

---

## 1. Explicit Out-of-Scope Demarcation

> [!IMPORTANT]
> **Procedural 3D Skeletal Animation from Scratch is Strictly Out of Scope.**
> 
> Generating skeletal bone hierarchies, inverse kinematics (IK) solvers, skin weight matrices ($W_{v, j}$ vertex-to-joint influences), and multi-track animation curves purely from scratch in Python is an order of magnitude more complex and error-prone than static mesh or 2D procedural generation. Autonomous agents should **never attempt to author 3D skeletal animations from scratch**.

---

## 2. Why Skeletal Animation from Scratch Fails for Agents

1. **Skinning Weight Non-Linearity**: Assigning $4$ joint weights per vertex ($W_{v, 0..3}$) that smoothly deform a mesh around elbows and knees without severe volume pinching or candy-wrapper collapse requires manual painting or specialized volumetric voxel solvers.
2. **glTF Skin Specification Strictness**: Any slight deviation in inverse bind matrices (`inverseBindMatrices`), joint node indices, or quaternion normalizations corrupts the entire character model in game engines.
3. **Pacing & Timing**: Crafting walking loops or combat strikes requires hundreds of synchronized multi-axis rotation Euler/quaternion keyframes.

---

## 3. The Future Roadmap: Pre-Built Skeleton & Clip Bank

When 3D animation is integrated in future revisions of this repository, it will follow a **modular library and retargeting model**:

1. **Curated Skeleton Vault**:
   - Standardized humanoid rig (`humanoid_standard.glb`): 24-bone hierarchy (hips, spine, chest, neck, head, shoulder, arm, forearm, hand, thigh, calf, foot).
   - Standardized quadruped rig (`quadruped_standard.glb`).
   - Standardized flying/winged creature rig.
2. **Motion Sequence Bank**:
   - Pre-authored, verified animation clips stored as glTF animation tracks:
     - `locomotion_walk_loop`
     - `locomotion_run_loop`
     - `combat_slash_one_shot`
     - `reaction_hit_flinch`
     - `action_jump_rise_fall`
3. **Agent Role**:
   - The agent's role will be **mesh skinning attachment and parameter tuning** (procedurally attaching static armor, clothes, or weapons to pre-existing rigged bones), **never** authoring raw keyframes from vacuum.
