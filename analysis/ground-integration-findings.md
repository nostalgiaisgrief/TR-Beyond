# Ground movement integration - 8 October 2026

A native ground-only development build now combines the recovered controls,
turn/lean damping, animation transitions, original sine table, room geometry,
static contacts and state-specific ground collision at 30 ticks per second.
The renderer reads the live actor state. Camera is still a simple orbit offset
following position, without collision; it is not the recovered camera.

## New binary evidence

Addresses below are LE preferred analysis addresses from the hash-pinned
99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac executable.

- 0x25928: fast turning (state 20). Preserves sign of the previous turn rate;
  sets magnitude 1456, requests stop on release or non-positive health.
- 0x25089..0x2511b: lean relaxes by 182, turn rate by 364, then yaw advances.
- 0x26234: running collision, including front-wall reactions, step-up frames,
  falling threshold and downward floor correction capped at 50 per tick.
- 0x263b8: standing/fast-turn collision. Ceiling response, falling at floor>100,
  slide service, contact shift, then floor correction.
- 0x26618: slow-turn collision. Unlike standing, no ceiling/shift call here.
- 0x27b52: vault returns false without action input (0x40).
- 0x28128: slide returns false when both absolute floor tilts are <=2.

Extracts: ground-integration.asm and ground-extra.asm. The first listing retains
some surrounding disassembly for context; only the entry ranges above are used.
No additional TRX code was read or used for this implementation.

## Ordering

The development harness snapshots old position, dispatches control, damps lean
and turn, advances yaw, advances animation using the previous movement angle,
then dispatches collision based on the resulting current state. The updated
movement angle is retained for the next tick. Room lookup uses Y-381.
The original move angle starts at zero, not initial yaw; that detail is preserved.

Input: W forward, A/D turn, Shift slow, Shift+S backward walk, S backward hop. Space pauses; R or Tab resets the movement
test. Arrow keys adjust the temporary camera. 1/2/3 enter the old pose viewer.
Focus loss stops simulation. Large frame gaps are capped to avoid catch-up bursts.
This intentionally means a prolonged stall slows this development build; no
claim of original scheduler equivalence is made.

## Explicit limits

This is a constrained movement harness, not completed above-water control.
Jump, roll, sidestep, action and look are not accepted.
Falls, swimming, steep slopes, unresolved object references, unknown animation
effects, and unimplemented collision/control states roll back the candidate
position and reset to standing. The title reports why movement was stopped.
Running-wall splat is now simulated through recovery, and backward walking is
connected. See the follow-up below for its binary evidence and checks.
Ground tests may step up/down using original walking/running animations.

Sound commands are counted but not played. Object collision pass 0x160c0,
weapon services and trigger dispatch are not connected. Geometry collision is
not a replacement for those services. The room query is reconstructed; vault
and slide early-outs are used only under the proven input/tilt restrictions.
Full-frame equivalence to the DOS game has not been established.

## Validation

- 76,089 control cases per build, now including fast turn, match original code.
- 6,000 damping and 8,000 ground collision cases per build match original code.
  Collision query/vault/slide callbacks are controlled doubles in these tests.
- Existing 30,000 animation/walking collision cases per build still pass.
- Native gym checks: idle position, walk/run speed relationship, release to stop,
  left/right turns, window wall blocking and unsupported-state rejection.
- Eight actual native movement captures: all debug/optimized tick traces and
  images match. Ten pose captures and camera orientation checks also pass.

Next: traversal (jump/fall/land/slide/climb), complete frame sequencing validation,
camera and manual playtesting.


## Ground reactions follow-up - 8 October 2026

The new build accepts Shift+S for original backward walking (state 16). S without
Shift is filtered because it requests hop-back, which remains unimplemented.
Both controls and collisions now allow running-wall splat (state 12) and its
animation-driven recovery. No presentation-side substitute for the reaction is used.

New evidence in ground-reactions.asm:

- Control dispatch table 0xC3884, state 12 -> 0x25798: immediate return. Recovery
  follows the actual animation links rather than a fabricated timer/control rule.
- Collision table 0xC3964, state 12 -> 0x26918: query using facing yaw, limits
  +/-384, ceiling limit 0 and flags OR 3, then apply contact shift. This handler
  does not clear gravity, reset fall speed or add the floor displacement.
- Collision state 16 -> 0x26A28: clear gravity/fall speed; query behind Lara using
  yaw-32768 with word wrapping; retain that direction as the movement angle.
  Handle ceiling and wall response, then backward step-down for 128<floor<384.
  Frames 964..993 select animation 62/frame 930; other frames select 61/frame 899.
  Finish with slide dispatch and floor correction when it returns false.

Updated validation:

- 84,968 control cases per build match DOS, including the no-op splat control.
- 6,000 damping + 14,000 ground collision cases per build match DOS. Cases include
  the backward floor/frame thresholds, signed yaw wrapping, contact flags,
  callback ordering and actor mutations. Query/vault/slide remain controlled doubles
  for these isolated routine comparisons, as before.
- Native gym checks exercise both running-wall animation variants (53 and 54),
  recovery after releasing input, and retreating afterward. Backward walking,
  release-to-stop, unchanged facing and disabled bare-S hop-back are checked too.
- Twelve native captures give matching debug/optimized tick traces and images.
  Captured wall-hit and backward-walk frames were visually inspected.

These checks establish the new routines and bounded integrations, not complete
above-water/full-game equivalence. Existing traversal/service guards remain.


## Backward hop follow-up - 8 October 2026

S without Shift now requests original state 5. Shift+S still requests state 16.
Evidence saved in hop-back.asm, with control/collision table pointers read from
the original executable:

- State 5 control 0x2555C always requests stop (2), then steers by 409 with a
  signed wrapping turn-rate clamp of +/-1092. It does not test health or require
  back input to finish the current hop. Left takes precedence over right.
- Collision 0x26540 clears gravity and fall speed, sets limits +32512/-384 and
  ceiling 0, flags OR 3, and queries behind Lara at yaw-32768 with word wrapping.
  Ceiling response comes first. Floor displacement >200 enters state 29,
  animation 93/frame 1473 with gravity enabled and fall speed zero; this branch
  precedes wall response. Otherwise wall response can select stand animation
  11/frame 185, and floor displacement is added. This handler does not call slide.
- On supported level ground, vertical pose motion comes from original animation
  data; this is not a synthetic gravity jump. Stop/recovery follows original
  animation transitions. General falling/landing is not enabled by this change.

Validation now includes 93,847 control cases and 6,000 damping + 18,000 ground
collision cases per build, all matching original instructions. Collision tests
include floor 199/200/201 and preserve callback ordering. Native gym tests check
backward displacement, release-to-stop, the wall behind Lara, and the 256-unit
window ledge guard. Fourteen captures have matching debug/optimized traces and
images; the backward-hop image was visually inspected.

The recovered collision routine contains the original falling transition, but the
interactive harness still rolls back that candidate tick because state 29 remains
unimplemented. No full airborne or landing equivalence is claimed.
