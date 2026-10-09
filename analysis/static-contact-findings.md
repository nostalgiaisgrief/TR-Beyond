# Static object collision: 8 October 2026

New C code in `src/static.c` reconstructs DOS 0x158a8 (static collision),
0x15e50 (nearby-room collection) and 0x15f28 (unique-room insertion).
`tomb_world_contact` in `src/terrain.c` invokes this service at the original
point between terrain sampling and final classification. The original
terrain-only entry remains available with its explicit pending-static flag.

## Loaded data

The PHD loader now decodes room static placements and global static definitions,
including collision bounds and flags. It skips mesh trees, frame words and
moveable model records using checked sizes to reach definitions. The decoded
prefix ends at `static_parsed_bytes`; `parsed_bytes` still marks the animation
command boundary for existing consumers. Later file sections are not validated.

The [TRosettaStone format reference](https://opentomb.github.io/TRosettaStone3/trosettastone.html)
was consulted for the static-definition layout. Placement values and definition
bounds are independently compared against raw level bytes in the loader suite.
Duplicate definition IDs, undefined placement IDs, truncated definitions and
unreasonable counts are rejected. The expanded malformed-input suite rejects
24 fixtures in each build.

## Original behaviour preserved

The nearby-room query starts with the supplied room and samples eight corners,
using radius and height margins of 50 units. Each sample starts in that supplied
room; resolved rooms are appended once in discovery order. At most nine rooms
can result. The combined classifier supplies the room left by its fourth terrain
sample, preserving the original query sequence.

Objects are tested in room/placement order. Flag bit zero disables collision.
Bounds rotate only at exact 90, 180 and 270 degree angles; other angles use the
unrotated bounds. Exact box touches do not count as intersections. The first
intersecting eligible placement wins. Penetration ties choose the positive
direction, and facing determines front/left/right response. Static results may
then be overwritten by later terrain classification, as in the original.

The API commits results only after success. `TombStaticContact` exposes the
ordered room list and hit flag. A successful combined query clears
`static_meshes_pending`; it still exposes unresolved dynamic height references
through `object_references`.

## Validation

Both debug and optimised native Windows DLLs pass comparisons against the
original executable running in Unicorn. The static service, nearby-room helpers,
terrain queries and combined classifier execute original instructions without
static substitutes. Tests check contact outputs, hit flags, room ordering,
sample/tilt metadata, return stack and writes outside permitted state.

| Cases | Per build |
| --- | ---: |
| Gym static probes, across 91 placements | 18,382 |
| First-level static probes, across 44 placements | 8,888 |
| Synthetic rotation, flags and ordering probes | 640 |
| Combined real-level terrain/static queries | 2,540 |
| Total | 30,450 |

Probes include exact horizontal and vertical touches and neighbouring positions,
all four facings, all quarter-turn rotations, a non-cardinal rotation, disabled
objects and reversed overlapping-object order. The combined cases include 387
static hits; 6,568 total queries collect more than one room. Static hit outputs
exercise front and both side classifications. See `c-static-validation.json`
for hashes, counts and limits. The full regression suite also passes.

## Remaining work

Dynamic object height callbacks are still unset in the reference fixtures and
unimplemented in C. Doors, bridges and other active objects therefore remain a
separate collision task. Next, decode runtime item data and recover those
callbacks. Vaulting, sliding, full-frame movement, rendering and gameplay
integration remain outstanding. This milestone is not a playable Windows port.

No TRX source was consulted or incorporated for this milestone. Function addresses
refer to the preferred LE analysis mapping, not observed runtime addresses.

Update: item placements and seven object-height callback pairs have now been
reconstructed. The static-only suite retains its documented callback-free scope;
the new item suite enables the recovered callbacks. See
[item height findings](item-height-findings.md) for the remaining state/update boundary.
