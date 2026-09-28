# Enemy rig — bone match guide

Operation Ink enemies use **`public/models/stickman.glb`** as a skinned mesh.  
Animation clips are **built in TypeScript** (`src/lab/clips/*`), not baked into the GLB.

## Required bones (`src/lab/rig.ts`)

```
hips, spine, chest, neck, head
shoulder.L, shoulder.R
upper_arm.L, upper_arm.R
forearm.L, forearm.R
hand.L, hand.R
thigh.L, thigh.R
shin.L, shin.R
```

GLTFLoader sanitizes names (`upper_arm.L` → node often `upper_armL`). The loader looks up by sanitized name.

## Conventions

| Item | Value |
|------|--------|
| Facing | World **+Z** |
| Feet | y ≈ 0 |
| Head top | ~1.74 m |
| Hips rest | ~(0, 0.82, 0) |
| Pose units | Degrees on rest pose; Euler order matches Blender XYZ → Three `ZYX` |
| Hand attach | Weapon mounts on **`hand.R`** |

## Swapping to another mesh (Sketchfab, etc.)

1. Keep **identical bone names** (or rename in Blender to match the list).
2. Bind in **same rest T-pose** family (arms roughly T or A as current stickman).
3. Export GLB, replace or add next to `stickman.glb`.
4. Point `loadStickman()` / `stickmanSource()` at the new file.
5. **Do not** rely on Mixamo clip names — mission still uses lab `makeClip` poses.

If bones cannot match, write a **name map** in `loadStickman` before `BONE_NAMES` lookup — still one humanoid skeleton, not a second animation system.

## Current visual experiment (in-engine)

- Solid black body (`penPalette.character`), **fog disabled**
- **Inverted-hull outline** shell re-enabled for silhouette at range
- Same skeleton / clips / weapon mount — zero retarget risk
