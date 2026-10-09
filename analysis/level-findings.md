# Real level data and structural geometry

Implemented in new C code in `src/level.c`, `src/geometry.c` and `src/level.h`.
The baseline remains the installed DOS executable identified in the project README.
No TRX implementation is compiled, linked or copied into this milestone.

## Data loading

The bounds-checked little-endian loader supports the TR1 version-32 prefix through
animation command words. It decodes room headers, sector grids, floor data,
animation records, state changes, transition ranges and commands. It retains
the original bytes for later work. Meshes, lights and other intervening sections
are skipped with checked lengths; sections after commands are not validated or
decoded. This is not a complete level validator or rendering asset loader.

The community [TRosettaStone format documentation](https://opentomb.github.io/TRosettaStone3/trosettastone.html)
was consulted for the file layout. Behaviour was reconstructed from the supplied
DOS executable and checked against its machine code. An independent Python
parser checks the C decoder's fields and arrays against both supplied assets.

## Recovered original routines

Addresses are preferred analysis addresses, not observed runtime addresses.

| Address | Behaviour |
| --- | --- |
| 0x173bc | Resolve sector through horizontal doors and vertical room links |
| 0x1767c | Floor height, slope category and trigger location |
| 0x180e8 | Ceiling height |
| 0x1836c | Read a door room reference from sector floor data |

The reconstruction preserves border-sector clamping, signed 256-unit heights,
1024-unit sector sampling, signed slope arithmetic and the large-slope suppression
flag. Invalid indices and cyclic room traversal fail instead of reading outside
allocated data. The original height callbacks for objects are not reconstructed:
the API exposes unresolved object references so its structural answer cannot be
mistaken for complete gameplay collision.

## Differential validation

The oracle executes the original x86 routines under Unicorn with real room/sector
and floor-data arrays installed in their original runtime layouts. Object height
callbacks are null in the oracle; results therefore validate structural geometry
only. Samples exercise each sector at five positions and height boundaries,
with slope suppression both enabled and disabled. Both debug and optimised C
builds are checked against the same original results.

| Asset | Rooms | Sectors | Geometry cases per build | Animation cases per build |
| --- | ---: | ---: | ---: | ---: |
| GYM.PHD | 19 | 2,002 | 20,020 | 1,460 |
| LEVEL1.PHD | 38 | 4,026 | 40,260 | 2,032 |

All sampled queries succeeded; none were skipped for invalid geometry. Floor,
ceiling, resolved sector, slope category and trigger location matched. First-level
samples include 1,650 queries with deferred object references; their structural
match does not establish the final height once object callbacks are implemented.

Actual animation tables are exercised at boundary frames and with goals drawn
from their state-change records. Sound/effect services remain controlled test
substitutes, including a deterministic test effect, not actual game effects.
Each build also rejects fourteen truncated or unreasonable-count level prefixes.
Hashes, counts and limits are saved in `c-level-validation.json`.

## Next boundary

Reconstruct the contact classifier at 0x151c0 and its tilt helper at 0x16020,
including Lara's radius and terrain samples. Static-mesh contacts, object height
callbacks, vaulting/sliding and full-frame integration still need work. This
milestone supplies real geometry queries; it does not yet make a playable gym.

Update, 8 October: the structural classifier and tilt helper are now implemented
and tested. See [terrain contact findings](terrain-contact-findings.md) for
the completed scope and remaining static-mesh boundary.
