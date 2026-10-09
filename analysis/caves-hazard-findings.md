# Caves hazards and camera projection — 9 October 2026

## Scope and binary evidence

Independent C reconstruction, using original LEVEL1.PHD and TOMB.EXE. No TRX
implementation was used. Object inventory: twelve bridge sections (IDs 68–70),
two collapsing floors (35), and ten dart emitters (40), spawning darts (39).
There is no drawbridge (41) placement in Caves; these bridges are fixed sections.

Original routines:

- InitWindow 0x3ef3c and AlterFOV 0x3f01c. The call at 0x19fff supplies 80
  degrees, near 10 and far 20480. Original sine/cosine values for 80*91 are
  10529/12553. Focal length is `(width/2)*12553/10529` with integer division.
- Collapsing floor control 0x3a728 and floor/ceiling callbacks 0x3a848/0x3a878.
- Dart emitter 0x3ac80, dart control 0x3ae20, ordinary ObjectCollision 0x16388.
- AnimateItem 0x16ff4 and original bridge callbacks 0x2ff18–0x30020.
- Blood controller 0x1d660, emitter smoke 0x3af54, impact sprite 0x1d7dc.

## Camera changes

Rendering, portal projection and static drawing bounds now share the original
integer focal length. Near/far clipping distances match the original setup.
Wide windows use the same horizontal-FOV formula; no extra wide-screen FOV rule
is introduced. The view transform uses floating-point rendering arithmetic and
continuous interpolation; software rasterization and pixel identity are not
claimed. Immediate item-target changes and speed-one fixed shots are no longer
blended across by the renderer. Continuous chase and eased fixed movement still
interpolate between original 30 Hz states. Look/combat/cinematic modes belong to
later features and remain unimplemented.

## Object integration

Runtime height callbacks are now used by movement, jumping, landing and camera
queries. Bridge sections render their original meshes and provide original
flat/sloped surfaces. Collapsing-floor animation state is published to height
queries before the next collision query. Standing at the original surface
activates the floor; stepping away before its controller runs cancels startup.
It progresses through its original wait/fall/impact states and sounds, including
the seven-mesh break-up animation. The original final-frame retrigger behaviour
is retained rather than hidden with a new one-shot rule.

Emitters follow original trigger masks and animation windows. Darts move at the
original animation speed, resolve rooms and floors, apply 50-point damage from
prior-tick sphere contact, and leave the active pool on hitting terrain. Collision
uses original bounds, spheres and terrain-checked push arithmetic. The unusual
+0x3fec spawn-offset comparison is retained verbatim in behaviour: +0x4000 does
not receive that offset. Original blood, smoke and impact sprites use their
reconstructed effect controllers. Impact-frame randomness uses the original LCG
in a local effects stream; whole-game RNG sequencing is not yet reconstructed.

Object sounds include floor activation/fall/impact (66–68) and dart firing (151).
Fixture shortcuts and restart clear darts, effects, object states and sounds.
C uses a bounded pool of 256 darts/effects; original allocator/list operations
are replaced by native storage. This capacity is well above these Caves fixtures.

## Validation

`compare_hazards.py`, per release/debug build:

- 3,937 viewport widths: integer focal length equals original instructions.
- 320 moving-object animation cases.
- 1,200 emitter control/spawn cases including the offset quirk.
- 176 complete collapsing-floor ticks with original room geometry.
- 284 dart trajectory ticks across all ten emitters, including injected touch
  bits, original 50-point damage and terrain removal.
- 300 blood/smoke/impact effect updates.

Allocation, active-list, room-list and particle-spawn services are explicit test
doubles; animation and geometry execute as original instructions. Native tests
separately exercise actual floor triggers, all twelve bridge surfaces, dart
spawning, sphere hits, sounds, effects, impact and reset. A corridor run produced
six darts, one hit (health 950), and five wall impacts. The collapse route reached
floor impact at Y=3840 and emitted all three floor sounds.

Twelve hazard captures/traces match release/debug. Twenty-four existing camera
captures also match release/debug. These are renderer consistency tests, not DOS
video comparisons. The full existing DOS regression suite also passes.

## Playtest

Caves playtest 06: F2 bridge, F3 collapsing floor, F4 dart corridor. Stay on the
floor to trigger collapse; run across the bridge; stand in or cross the dart
path. F10/F11 then Ctrl still test switch cameras. All shortcuts reset state.
Gym playtest 06 receives the projection and cut changes.

Enemies, combat, pickups, music/progression, menus and saves remain future work.
This is a hazard-capable Caves exploration build, not a complete Caves playthrough.
