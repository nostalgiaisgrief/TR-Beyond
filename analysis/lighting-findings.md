# Model lighting

Reference: original DOS executable SHA-256
`99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac`.

- `0x104a8`: sample room ambient and the brightest attenuated point light.
  Attenuation uses intensity times squared falloff divided by squared distance
  plus squared falloff, with the original integer shifts and 32-bit products.
  The midpoint between ambient and brightest light determines the shade adder
  and directional divider. Depth beyond 12288 adds distance shading.
- `0x1063c`: placed intensity minus 4096, plus distance shading. It retains
  the previous directional parameters; baked-shade meshes do not use them.
- `0x1bba8`: moving models sample the rotated first animation key's bounds
  centre, translated into world coordinates. Nonnegative item intensity
  selects static lighting instead. Fog uses the object's origin depth.
- `0x3ecac`: convert the light vector through yaw/pitch and the original sine
  table, then rotate it into view space.
- `0x3e6a4`: transform the direction into each mesh's local frame, combine it
  with signed vertex normals, or add the mesh's precomputed vertex shades.
  Clamp the result to 0–8191. This is signed directional shading, not a new
  clamped Lambert-light implementation.
- `0x24284` and ring initialization at `0x24201`: inventory light position
  (-1536, 256, 1024), divider 24576, selected shade 4096 and other shade 5120.

PHD room lighting consists of an ambient word and 18-byte light records:
three signed coordinates, signed intensity, and signed 32-bit falloff.
These are retained as borrowed views alongside portal data. Existing level
structures and save files do not change.

The old renderer ignored object normals, baked shades and placed intensity.
It also multiplied room palette RGB by `1 - shade/8192`. The original shade
table is neutral at 4096, so that multiplier incorrectly halved neutral
brightness. The compatibility shader now samples indexed textures and the
original 32-by-256 palette lookup. Index zero remains transparent only for
masked textures; ordinary opaque textures and flat-colour faces retain it.
Room and object vertices share this palette path. UI sprites retain their
existing dedicated neutral-shade textures.

Validation: release/debug comparisons against the unmodified DOS routines
cover 1,200 room samples across Gym, Caves, City and Valley, 400 static shades,
and 32,000 normal/baked vertex shades. Loader checks cover every lighting
record in these levels. An actual-driver renderer test compares all 8192
palette entries and indexed texture transparency for each level palette.

Rendering still uses OpenGL projection, depth buffering, texture interpolation
and smoothly interpolated camera/pose matrices. These checks establish the
lighting calculations and palette mapping, not software-rasterizer pixel
identity. Water shimmer and additional effect-specific lighting remain outside
this model-lighting change. The renderer requires OpenGL 2.0 shader support.

## Palette boundary correction (playtest 32)

The first shader used `floor(shade * 32)`. Perspective interpolation of a
constant varying can produce a value slightly below its mathematical value.
At exact row boundaries this selected the preceding shade row, causing
triangular speckling without any overlapping geometry. The previous GPU
checks sampled row centres and therefore missed this condition.

A single perspective quad with unequal clip-space W values reproduced 3,790
wrong pixels out of 8,192 at shade 256 on the test graphics driver. Adding
0.00001 row units before truncation corrects the rounding noise; this is
0.00256 original shade units. New GPU checks cover all 31 boundaries and
adjacent integer shades (93 cases per level per build). The palette contents,
vertex lighting calculations and room geometry remain unchanged.
