# Lara fresh-start movement state

`src/lara_start.c` and `src/lara_start.h` provide `tomb_lara_start` for a fresh
ordinary Lara placement. It creates a movement-state snapshot without changing
the loaded level. The implementation derives from generic item initialization
at 0x24870 and Lara reset at 0x28d38. The object-0 setup installs callback
0x28d14 at 0x368c3, and level initialization invokes Lara reset at 0x36780.
All addresses use the LE preferred analysis mapping.

## Supported state

The function requires exactly one object-0 placement, zero file placement flags,
a valid starting sector and the expected animation state/frame in loaded data.
It rejects unsupported or inconsistent input without modifying its output.

Position, room and yaw remain at their file values. Generic item initialization
sets speed, fall speed, pitch and lean to zero and caches the raw sector floor.
Lara reset sets health to 1000 and air to 1800, clears turn/movement angles and
head/torso rotations, and selects animation according to room flag bit zero:

| Starting room | Current/goal state | Animation | Frame | Water status |
| --- | ---: | ---: | ---: | ---: |
| Ordinary | 2 | 11 | 185 | 0 |
| Underwater | 13 | 108 | 1736 | 1 |

The move angle is initialized to zero even when Lara faces another direction.
The raw sector floor is preserved here; it is not replaced by a sloped or
object-adjusted height query. Frame-by-frame queries handle that later.

## Supplied starts

| Asset | Item | Room | Position X,Y,Z | Yaw |
| --- | ---: | ---: | --- | ---: |
| GYM.PHD | 0 | 7 | 37376, -1280, 51712 | -16384 |
| LEVEL1.PHD | 0 | 0 | 75264, 3072, 3584 | 0 |

Both use the ordinary standing state. Full snapshots are in
`c-start-validation.json`.

## Validation and boundaries

The test oracle executes original generic item initialization, object-0 pointer
registration and Lara reset. The inventory/weapon/mesh service at 0x28e9c and
scratch allocation at 0x2d11c are controlled substitutes. Their invocation order
is checked. The C snapshot marks both services pending, rather than inventing
inventory or runtime mesh pointers. Room item-list maintenance is exercised in
the original but is not implemented by this snapshot API.

Both debug and optimised Windows DLLs match 2,002 cases: the two supplied starts
plus variations in initial Y, yaw and room flags. Comparisons cover every exposed
state field, original pointer/index registration, return-stack balance and writes
outside the permitted initialization state. Invalid placement, missing Lara,
unsupported file flags and missing animation data are also rejected with output
preserved. Tests do not validate save restoration, inventory or a live playthrough.

This completes the starting movement-state portion of the first playable gym
roadmap. Next is visual asset decoding and Lara mesh/pose setup. No renderer or
playable loop is introduced by this milestone. No TRX implementation was used.
