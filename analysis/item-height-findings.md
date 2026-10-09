# Item data and object height callbacks

Implemented in `src/item_height.c`, with ordered dispatch in `src/geometry.c`
and combined collision through `tomb_active_contact` in `src/terrain.c`.
Original instructions are saved in `item-height.asm`. No TRX implementation
was consulted or incorporated in this milestone.

## Evidence and reconstructed scope

The original floor and ceiling dispatchers index item records at stride 68 and
object records at stride 50. Floor callback slots start at 0xcc074; ceiling
slots start at 0xcc078. Absolute addresses below use the preferred LE mapping.
Object setup writes identify these seven callback pairs:

| Object ID | Floor | Ceiling | Recovered rule |
| ---: | --- | --- | --- |
| 35 | 0x3a848 | 0x3a878 | Surface 512 above item Y, active in states 0 or 1 |
| 41 | 0x2fe88 | 0x2febc | Two-sector footprint, active in state 1 |
| 65, 66 | 0x3a4c0 | 0x3a4f8 | Two-sector footprint, state 0, compare existing height |
| 68 | 0x2ff18 | 0x2ff2c | Flat bridge height |
| 69 | 0x2ff8c | 0x2ffb0 | Quarter-gradient bridge height |
| 70 | 0x2ffd8 | 0x2fffc | Half-gradient bridge height |

Setup evidence: assignments at 0x377a3/0x377a9, 0x37b9b through 0x37bbe,
0x37bf6/0x37bff and 0x37e6b through 0x37e82. Helpers at 0x2fdd4, 0x2ff44
and 0x3a530 determine footprints and slope offsets. The implementation retains
original signed comparisons, word wrapping, orientation fallbacks and the
256-unit underside offset. Descriptive names describe observed behaviour;
the ID-to-function addresses are the binary evidence.

Floor-data object actions invoke callbacks in their original order. Floor
callbacks interleave with slope entries; ceiling callbacks traverse the bottom
sector's object actions after the structural ceiling calculation. Camera action
extra words retain their original end-bit handling. The combined classifier
passes the original query Y coordinate to these services.

## Placement data versus runtime state

The loader now validates the prefix through item placements. It reads object ID,
room, position, yaw, lighting and file flags; it does not equate those flags with
animation state. Each loaded item has `state_known = 0`. The gym contains one
item; the first level contains 60. Both sets match an independent byte parser.

The [TRosettaStone file-layout reference](https://opentomb.github.io/TRosettaStone3/trosettastone.html)
was consulted to reach the 22-byte item records. Intervening texture, camera,
sound-source, navigation and animated-texture data is skipped with bounds checks.
It is not decoded for gameplay. The loader ends at `item_parsed_bytes`; previous
prefix markers remain available. Thirty-two malformed fixtures are rejected,
including truncated items, unreasonable item counts and invalid room/object IDs.

Callers supply an explicit runtime item array. The seven known callback IDs are
handled when their required state is known; other types and unknown states remain
counted in `object_references`. Unknown types are not silently assumed to have no
height callback. Invalid trigger indices fail without committing output.

## Validation

Both debug and optimised Windows builds pass comparisons against original
machine code running in Unicorn:

| Test | Cases per build |
| --- | ---: |
| Direct callbacks, all seven IDs | 131,480 |
| Real-level dispatched height queries | 18,084 |
| Real-level combined terrain/static/item contacts | 2,027 |
| Multiple callbacks with preceding slope data and reversed order | 210 |

Direct cases cover states, cardinal/non-cardinal orientations, sector boundaries,
surface equality, signed height boundaries and full-width random coordinates.
Every callback ID changes height in the test matrix. Real-level tests use
controlled runtime states, and 78 first-level queries change height due to the
callbacks. Integrated tests compare samples, classifications, shifts, tilt,
triggers, static hits and nearby-room order. Unknown-state/type flags and output
preservation on invalid indices are checked separately.

These fixtures do not establish the original startup state or reproduce a live
playthrough. The oracle enables only the recovered callback pairs; unclassified
object callbacks remain null there and explicitly unresolved in C. Full suite
results are saved by `test.ps1`; callback details are in `c-item-validation.json`.

## Next boundary

Recover item initialization and autonomous object updates. In particular, door
collision may involve changing sector data rather than a height callback; that
path is not reconstructed here. Trigger execution, object animation control,
vaulting, sliding, full-frame integration and rendering remain outstanding.
The project is still a buildable collection of reconstructed components, not a
playable Windows port.
