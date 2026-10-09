# Backward falling and landing - 8 October 2026

The development build now enables state 29, entered when hopping backward over
a drop greater than 200 original units. The real gym window ledge (256 units)
is covered by native integration and capture tests. This is a bounded airborne
milestone, not complete jumping/falling gameplay.

## Original executable evidence

Same pinned TOMB.EXE SHA-256:
99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac.
Addresses are LE analysis addresses. See back-fall.asm.

- State 29 control table pointer -> 0x25AD8. Fall speed >131 requests state 9;
  action input with weapon status 0 overrides that request with state 11.
- State 29 collision -> 0x26DC8. Behind-facing query, limits +32512/-384,
  ceiling tolerance 192, then airborne deflection 0x2793C. Floor<=0 and positive
  fall speed invoke landing; its result selects goal death (8) or stand (2).
  Fall speed is cleared, floor displacement added, gravity cleared. Current
  state and recovery animation transition through actual level animation data.
- Airborne deflection 0x2793C applies shifts first. Front/top-front contacts
  quarter speed toward zero, reverse movement angle, select state 9 animation
  32/frame 481, and ensure positive falling speed. Side contacts turn yaw by
  +/-910. Ceiling contact ensures downward speed. Clamp contact pushes 100 units
  opposite contact facing using the original sine table, clears speed/floor
  displacement and ensures positive falling speed.
- Landing service 0x28300 queries floor and dispatches triggers before damage.
  Its arithmetic tail 0x28346 uses excess=fall_speed-140: excess<=0 no damage;
  excess>14 fatal; otherwise subtract excess^2*1000/196 with original word
  wrapping and integer division. Fatal return is tested only in the damage branch.

## Landing service boundary

The interactive implementation queries the structural floor and records the
floor height before applying the recovered damage arithmetic. It guards unknown
object and trigger behaviour. The gym window landing contains exactly the words
8004 3F00 A01A: ordinary one-shot trigger, single action 8, track 26.

Inspection of the original action table resolves action 8 to 0x17FB0, which calls
0x18CE8 and then 0x18E28 for this track. That path updates audio state and calls
playback. The build records deferred_cd_track=26 instead of playing audio; it does
not claim to implement the original track latch/once semantics. The exception is
restricted to that exact three-word record. Other tracks cannot be assumed safe:
track 50 has a level-completion side effect. See landing-trigger.asm and
landing-audio.asm. Unknown landing triggers remain blocked.

The original height call has additional dynamic behaviour outside this structural
subset. No complete landing-service equivalence is claimed.

## Validation

compare_air.py: 6,000 backward controls, 6,000 airborne deflections, 6,000 backward
collision cases, and 6,000 damage-tail cases match DOS in each O0/O2 build.
Deflection executes original shift and trigonometric routines. Collision tests
use identical controlled query/landing callbacks, comparing call ordering and
actor/contact/movement-angle outputs. Damage-tail tests exclude floor/trigger
services. See c-air-validation.json.

Native gym tests follow the hop -> state 29/gravity -> grounded recovery -> stand
sequence; verify no health loss, floor -1280, and deferred track 26. A mutated
in-memory trigger fixture using track 50 confirms rollback leaves Lara airborne,
with unchanged health and no audio request. Source asset files are not changed.
Eighteen native capture runs produce identical debug/optimized traces and images.
The falling pose was visually inspected. No whole-frame DOS equivalence is claimed.

## Remaining work

State 9 (long/fast fall, also entered by some airborne impacts), grabs, deaths,
forward falls/jumps, sliding and climbing remain guarded. If an airborne candidate
tick requires unsupported behaviour, rollback preserves the previous airborne
state instead of inventing a standing pose in mid-air; R resets the test.
The camera is still a non-colliding orbit offset. Audio remains unimplemented.
Next: recover state 9 and its landing/impact flow, then forward jumping/falling.
