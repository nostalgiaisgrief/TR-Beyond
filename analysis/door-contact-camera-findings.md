> Historical report: camera presentation described here is superseded by
> [DOS camera restoration](dos-camera-findings.md) in gym 05 / Caves 04.

# Animated doors and switch cameras — 9 October 2026

Independent C reconstruction using the user's DOS executable and LEVEL1.PHD.
TRX source was not used for this change.

## Door contact

DOS `0x163dc` performs vertical/local bounds rejection (`0x167c4`), mesh sphere
intersection (`0x38fb0`, spheres from `0x39130`), then pushes Lara (`0x164a4`).
Spheres use the nearest animation key (`0x1d4b8`), original hierarchy and
14-bit matrix arithmetic, separately from rendering interpolation.
Pushing expands local bounds by the 100-unit Lara radius and selects the
nearest side with the original tie order. Terrain uses the original push-query
limits; failed clearance restores the previous horizontal position.
Contact runs after animation and before state-specific collision, matching
`0x2511b`–`0x25133`. Room traversal starts with the current room, then portal
neighbours; initial room item insertion order is preserved. Future creatures'
active-list/room-list mutations are outside this stationary-door scope.

Moving leaves request directional hit poses (animations 125, 127, 126, 128),
a capped 34-frame reaction and sound 27. Door sectors still block fully closed
doorways. Multiple same-tick hit requests share the presentation reaction.

`compare_door_contact.py` executes actual DOS instructions for 900 sphere
poses, 3,000 pushes, 3,200 single-door contact cases and 10,000 angle cases
per build. Comparisons include disabled push flags, rejection, rollback,
query parameters and hit directions. Terrain/room services are explicit
doubles in these comparisons. Native integration separately tests actual
terrain through closing leaves: 334 displacements and 411 reaction requests.
Existing closed/open passage tests still pass.

## Switch cameras

Trigger processing `0x17d2e`, target action `0x17e1c`, refresh `0x1790c` and
fixed-camera timer `0x14534` establish:

- Switch 42: camera 1, 90 ticks, speed 17, one-shot camera latch.
- Switch 52: camera 0, 90 ticks, speed 1, target item 41 (object 169).
- Refresh precedes switch completion gating. A latched shot keeps refreshing;
  an exhausted timer cannot restart while remaining on its trigger.
- Leaving the trigger releases the view early. Timers use 30 Hz simulation;
  rendering frequency does not consume timers, and pause stops simulation.
- Switch control requests chase angle 14560, elevation -4550, distance 1024.
- `0x14677`–`0x14ab2` selects an item's vertical bounds centre. Leaving an item
  target makes the first chase step immediate; leaving a Lara-target shot uses
  normal chase smoothing.

`compare_switch_camera.py` checks 1,260 ticks per build against original
trigger/refresh/timer instructions: expiry, departure, re-entry, re-pulling,
one-shot flags, speed and target identity. LOS/camera movement and CD playback
are explicit doubles. Native integration checks both 90-tick shots, targets,
30/60 Hz presentation response and chase return.

Presentation retains modern follow-camera and swept geometry clearance. Fixed
movement converts the original speed response to render time. Full DOS
LOS/clearance/render equivalence is not claimed. Reconstruction captures were
reviewed at `build/camera-2-75.ppm`, `camera-3-75.ppm` and their 180-tick chase
return counterparts. These are not live DOS screenshots; binary comparisons
provide the DOS evidence.

## Delivery

Debug/release native checks and the complete existing DOS comparison suite pass.
Package: `dist/caves-playtest-03`; previous packages preserved. Next: remaining
Caves objects/traps, then combat and enemies.
