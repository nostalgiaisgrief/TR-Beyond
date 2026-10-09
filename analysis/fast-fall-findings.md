# Fast falling - 8 October 2026

State 9 now runs in the development build, extending backward falls and allowing
short backward falls that hit a wall to continue through their original rebound
and landing path. This does not enable forward jumping or death behaviour.

## Binary evidence

Same pinned TOMB.EXE SHA-256 99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac.
LE analysis addresses and extracts are in fast-fall.asm.

- State 9 control pointer -> 0x256E0: horizontal speed becomes speed*95/100,
  signed division toward zero. Fall speed >=154 requests sound 30 each invocation.
- Deflection 0x27A74 shifts position first. Side contacts turn yaw +/-910;
  ceiling/top-front ensure positive fall speed; clamped space pushes back 100
  units using contact facing, sets horizontal speed and floor displacement to
  zero, and ensures downward speed 16 if needed. A front contact does not use
  the jump/backward-fall rebound rule. Movement angle remains unchanged.
- State 9 collision -> 0x2674C: sets gravity, samples using the retained movement
  angle, limits +32512/-384 and ceiling tolerance 192. Applies fast-fall deflection.
  Floor<=0 invokes landing even when fall speed is not positive (unlike state 29).
  A surviving landing sets current/goal 2, animation 24/frame 358. Fatal landing
  requests goal 8. Both call sound-stop 30 before adding floor displacement and
  clearing fall speed/gravity. Ordering is included in differential checks.

Sound play and stop calls are represented by callbacks (event kinds 5 and 7).
The development harness counts them; no audio is played. Landing still uses the
previous structural/explicitly deferred tutorial-track-26 service boundary.
Unknown landing triggers remain guarded.

## Validation

compare_fast_fall.py: 6,000 control, 6,000 deflection and 6,000 collision cases
per build match original instructions. It checks signed arithmetic, contact
responses, position overflow, landing results and audio/landing callback order.
Query, landing and audio are controlled doubles; this is not full-frame equivalence.
The existing 24,000 airborne comparisons also pass with the extended context.

Native gym integrations pass in O0/O2:
- A scripted 3,000-unit drop in real room 9 transitions state 29 -> 9 -> landing
  animation 24 -> standing. Landing health is 955 and sound-stop occurs once.
- A backward fall into the starting room's window wall enters state 9, rebounds
  and lands without damage.
- A 5,400-unit drop reaches the fatal-landing guard. Previous airborne state and
  health are preserved; the build does not invent a living grounded state.
- Previous ground movement, wall-hit recovery, short-drop and trigger guards pass.

Twenty-two native captures produce identical O0/O2 traces and images. Fast-fall
and landing poses were visually inspected. The tall-room test camera is positioned
along the hallway because the temporary orbit camera does not avoid walls.
The test additionally rejects captures with too little colour variation.

## Remaining scope

Fatal landings/death, forward jumping/falling, grabs, slides and climbing remain
unimplemented in the interactive harness. R resets a guarded state. Frame sequence
and service integration are not yet a complete equivalent of the DOS main loop.
Next: forward jump/fall control and collision, followed by other traversal.
