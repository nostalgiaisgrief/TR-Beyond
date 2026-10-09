# Animation advancement and walking collision — 7 October 2026

## Implemented milestone

New C code now implements Lara's animation updater, its transition search, the
collision shift/ceiling/wall responses, and walking collision orchestration.
This extends the previous control decisions with frame advancement and motion.
It is still a component-level reconstruction, not a playable game or complete
world collision system.

Both optimised and debug Windows libraries pass 30,000 original-code comparisons
per build: 6,000 animation cases, 18,000 helper cases and 6,000 walking orchestration
cases. See [the report](c-step-validation.json). Existing movement control tests
remain available in the combined `test.ps1` suite.

## Binary identity and evidence

Reference SHA-256:
99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac

Addresses are LE preferred-base analysis addresses, not measured DOSBox addresses.
All functions below are in object 1; file offset = analysis address + 0x1EE00.

| Routine | Analysis address | Evidence |
|---|---|---|
| Lara animation updater | 0x28820 | Above-water caller at 0x2511B; increments frame, follows animation tables, updates position |
| Animation transition search | 0x172B8 | Called at 0x2884F, matches goal and inclusive frame ranges |
| Relative animation translation | 0x17354 | Command 1 callback at 0x288DD; rotates local offset by actor yaw |
| Sine / cosine | 0x3F0BB / 0x3F0B6 | Original quadrant fold and 1025-word lookup table at 0xC50C4 |
| Apply contact shift | 0x15F84 | Adds three contact offsets to position, then clears all three offsets |
| Ceiling response | 0x27620 | Types 8/32 restore old position and reset standing animation |
| Wall response | 0x278D0 | Types 1/16 stop; types 2/4 shift and change yaw by +/-910 |
| Walking collision | 0x26084 | First collision-table pointer at 0xC3964; queries contacts then chooses walking/step/fall responses |

Fresh disassembly extracts are saved in [animation-collision.asm](animation-collision.asm).
No additional TRX source was needed for this step; implementations were derived
from the supplied executable and validated by executing its instructions.

## Recovered animation layout

Global pointers: animations 0xCC03C; command words 0xCC048; transition ranges
0xCC04C; state-change records 0xCC054.

Animation records occupy 32 bytes in the DOS image. Relevant fields:

| Offset | Type | Meaning |
|---|---|---|
| 0x06 | signed 16-bit | Animation state |
| 0x08 | signed 32-bit | Velocity, fixed-point |
| 0x0C | signed 32-bit | Acceleration, fixed-point |
| 0x10 / 0x12 | signed 16-bit | First / last frame |
| 0x14 / 0x16 | signed 16-bit | Next animation / next frame |
| 0x18 / 0x1A | signed 16-bit | Change count / first change index |
| 0x1C / 0x1E | signed 16-bit | Command count / first command-word index |

Change records are three 16-bit words: requested goal, range count, range index.
Range records are four 16-bit words: inclusive first/last frame, destination
animation, destination frame. The first matching range wins; a matching change
with no eligible range does not prevent searching later changes.

## Ordering that affects feel

1. Increment the signed 16-bit frame with wrapping.
2. If the current animation has changes and current state differs from requested
   goal, search for a valid transition using the incremented frame.
3. If it transitions, reload the animation and copy its state to current state.
4. If the resulting frame exceeds the animation end, execute its end commands,
   follow its next animation/frame link, and update current state again.
5. Execute timed commands for the selected animation and frame.
6. Update forward speed using fixed-point velocity and acceleration. Airborne
   movement preserves the existing speed contribution and applies the change
   between two adjacent animation velocities.
7. Airborne fall speed increases by 6 below 128, otherwise 1; then update Y.
8. Move X/Z using forward speed, global movement angle and quantised sine/cosine.

All relevant 16-bit and 32-bit arithmetic explicitly wraps; arithmetic right
shift uses defined C operations with the original negative-value rounding.
The original sine table is provided as data, not replaced with floating-point sin.
It is read directly from the DOS executable for the tests. Production asset
initialisation of that table remains to be wired.

The Lara updater handles command 1 as local translation; command 2 sets jump
velocities/gravity with an optional fall-speed override; command 3 clears weapon
status; command 4 has no action in this updater. Commands 5/6 produce timed
sound/effect callbacks. Relative translation uses actor yaw, while ordinary
movement uses the separate movement angle at 0xCE9CE.

## Walking collision

The C code performs the original initialisation (clear gravity/fall speed,
positive/negative step limits +/-384, ceiling limit zero, height 762), then:

1. Request contacts from the room-query service.
2. Stop early for a ceiling response or successful vault.
3. Apply wall deflection/stop and choose the correct stop animation by frame.
4. Enter falling when floor displacement exceeds 384.
5. Choose step-down or step-up animations at the original thresholds and frames.
6. Attempt sliding; otherwise add floor displacement to Y.

The core requires query, vault and slide services; missing callbacks fail instead
of silently pretending the ground is flat or disabling those behaviours.
Those three services are not yet reconstructed. Sound playback and specific
animation effects are also services rather than implemented game subsystems.

## Validation boundaries

Tests execute the original updater, transition search, relative translation,
sine/cosine, shift, ceiling response, wall response and walking decision code.
Synthetic animation, transition, command and contact records are supplied to both
versions. Both versions use identical controlled doubles at sound/effect and
room-query/vault/slide boundaries. Event order and actor/contact state at those
boundaries are compared, as well as final states, context globals, return values
where meaningful, stack balance and unexpected original-memory writes.

Fixtures cover negative and overflowing frame/position values, acceleration,
gravity, inclusive transition ranges, end links, command ordering, timed effects,
step-height and animation-frame boundaries, contact types and early returns.
The harness also verifies native C/ctypes struct sizes before calling the libraries.

This does not establish full gameplay equivalence. It does not test real gym
animation data, actual geometry sampling, implemented vault/slide/effect behaviour,
PHD loading, rendering, audio output, or full-frame integration and turn damping.

## Next milestone

Read the gym's PHD animation and room data, then reconstruct the room contact
query and its floor/ceiling dependencies. Replace the controlled query fixtures
with real geometry before attempting a playable walking prototype. Vault/slide
services and full-frame integration must follow; do not silently disable them.
