# Visual asset decoding

`src/visual.c` and `src/visual.h` provide checked visual views over the loaded PHD
bytes. The original `TombLevel` must remain alive and immutable while its visual
views are used. `tomb_visual_free` releases the view arrays, not the level.

Available data includes room vertices and lighting, room textured faces/sprites,
indexed object meshes, mesh normals or per-vertex lights, textured and coloured
mesh faces, texture tiles, texture coordinates, sprite textures, palette, model
definitions, mesh-tree records and animation keys. Mesh pointer aliases are
preserved as indexed views. Each mesh parser is bounded by the next distinct
mesh offset or the mesh-data end. Face vertex/texture references and static mesh
references are validated.

The [TRosettaStone format reference](https://opentomb.github.io/TRosettaStone3/trosettastone.html)
was consulted for layout. The C parser is new project code. No TRX implementation
was used. Raw tree records, texture coordinates and palette values are preserved
for renderer interpretation; no material or lighting approximation is baked in.

## Animation keys

`tomb_visual_key` decodes a stored TR1 animation key into bounds, root translation
and local X/Y/Z angles in original 16-bit turn units. TR1's two-word angle packing
and explicit rotation count are handled. This implementation supports up to 64
rotations per key; the supplied levels need at most 26. All keys in both levels
are checked for size and consistent counts within each animation.

Animation tick-to-key interpolation, hierarchy matrix composition and additional
runtime head/torso/weapon rotations are not implemented here. Those are required
when drawing animated Lara. The original movement animation updater remains a
separate component.

## Lara mesh selection

Original routine 0x29070 selects meshes from model 0 for an unarmed standard
profile. Profile flag 0x20 selects model 5 for the gym body, then replaces its
last mesh with model 0's head. In both supplied files this gives:

- Standard: mesh indices 0 through 14.
- Gym: mesh indices 75 through 88, then index 14.

The C selection helper is compared directly against that original routine under
Unicorn, using model starts decoded from each file and identifiable mesh pointers.
Return-stack balance and writes are checked. Other weapon/profile swaps remain
outside this helper's scope; callers explicitly choose the gym profile.

## Validation

Both debug and optimised DLLs match an independent parser of the source bytes:

| Asset | Rooms | Indexed meshes | Room vertices | Room faces | Animation keys |
| --- | ---: | ---: | ---: | ---: | ---: |
| GYM.PHD | 19 | 172 | 3,967 | 3,423 | 2,426 |
| LEVEL1.PHD | 38 | 217 | 8,349 | 7,459 | 3,992 |

The gym has nine texture tiles and 926 texture records; the first level has
eleven tiles and 897 records. Tests compare every room/mesh array, model record,
texture and palette byte, and every decoded key's bounds, root and angles.
Malformed vertex counts, mesh offsets, tile references, frame rates and rotation
counts are rejected: ten corrupted asset fixtures per build across both levels.
Hashes and counts are recorded in `c-visual-validation.json`.

Only mesh selection is an original-machine-code differential test in this suite.
The other checks validate decoding against independently parsed data; they do
not establish renderer, interpolation or pixel equivalence. There is no game
window yet. Next is the Windows renderer and visual inspection of actual rooms
and articulated Lara, followed by connecting movement and input.
