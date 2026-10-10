# C gameplay modules: build and validation

Update: `build.ps1` also builds `step_test.dll` (and its debug variant), containing
the animation updater and collision helpers/orchestration. `test.ps1` runs both
the movement and animation/collision suites. The additional suite compares 30,000
cases per build; see [its findings and limits](../analysis/animation-collision-findings.md)
and [report](../analysis/c-step-validation.json). Native Windows libraries are used
for direct test calls; there is still no game window or playable engine.

`test.ps1` also runs `compare_level.py` against both DLLs. This checks the PHD
loader, 60,280 structural geometry samples and 3,492 animation cases per build
using GYM.PHD and LEVEL1.PHD from `work/reference-assets/DATA`. Thirty-two malformed
prefixes are rejected by each build. See [level findings](../analysis/level-findings.md)
and [report](../analysis/c-level-validation.json). Object height callbacks remain
unimplemented and are explicitly reported as pending in query results.

To run this suite alone after building:

```powershell
python tests/compare_level.py --dll build/step_test.dll build/step_test_debug.dll
```

To run just the added suite after building:

```powershell
python tests/compare_step.py --dll build/step_test.dll build/step_test_debug.dll
```

The sections below describe the original movement-control suite.

The structural terrain suite is also part of `test.ps1`. It compares 48,251
cases per build, including targeted ceiling-boundary cases, with all seven
contact classifications covered. Run it alone with:

```powershell
python tests/compare_terrain.py --dll build/step_test.dll build/step_test_debug.dll
```

Its explicit limits are [documented here](../analysis/terrain-contact-findings.md):
the original static-mesh service is replaced by a no-contact test service, and
object height callbacks are unset. Room queries, tilt, trigonometry and the
classifier itself execute original machine code.

The static suite now runs the original static service as well, with no static
substitute. It checks 27,910 static cases and 2,540 combined classifier cases per
build, including nearby-room order. It loads all 135 placements across both levels.
The loader comparison also checks placement fields and definition collision bounds.

```powershell
python tests/compare_static.py --dll build/step_test.dll build/step_test_debug.dll
```

See [static contact findings](../analysis/static-contact-findings.md) and
[saved report](../analysis/c-static-validation.json). Dynamic height callbacks
remain unset in these tests. All suites are run by `test.ps1`.

The item-height suite enables the seven recovered original callback pairs and
checks their new C equivalents. Item state is explicitly controlled in fixtures;
this does not validate startup initialization or autonomous object updates.

```powershell
python tests/compare_items.py --dll build/step_test.dll build/step_test_debug.dll
```

Per build: 131,480 direct callback cases, 18,084 real-level height queries, 2,027
combined contact cases and 210 ordered-dispatch cases. Unsupported IDs and
unknown required states stay flagged as unresolved. See
[item height findings](../analysis/item-height-findings.md) and
[validation report](../analysis/c-item-validation.json).

Lara startup is now checked by `compare_start.py` and included in `test.ps1`:

```powershell
python tests/compare_start.py --dll build/step_test.dll build/step_test_debug.dll
```

The suite compares 2,002 cases per build against original generic item
initialization followed by Lara reset. Inventory/weapon/mesh setup and scratch
allocation are explicit service doubles. Actual starts for both supplied levels
are saved in [the report](../analysis/c-start-validation.json). See
[startup findings](../analysis/lara-start-findings.md) for the supported scope.

`compare_visual.py` checks the C visual asset views against an independent Python
parser, all 6,418 stored animation keys, malformed visual records and original
Lara mesh selection at 0x29070. It is part of `test.ps1`:

```powershell
python tests/compare_visual.py --dll build/step_test.dll build/step_test_debug.dll
```

These are decoding and mesh-selection checks, not original rendering equivalence.
See [visual findings](../analysis/visual-findings.md).

The first C module implements walk, run, stand, right turn, left turn, and the
backward-walk helper called by standing. The standing implementation includes
look controls and input priority. These are control decisions, not complete
movement frames: animation advancement, damping, position updates and collision
remain outside the module.

## Build on Windows

From the repository root in PowerShell:

```powershell
.\build.ps1
.\build\movement_test.exe
```

The no-argument executable prints one control example and returns success/failure.
It does not open a game window. For full differential validation:

```powershell
.\test.ps1
```

The test script builds optimised (-O2) and debug (-O0) executables, then compares
both with the original executable. It uses the bundled Python at its current
machine path; override with `-Python C:\path\to\python.exe` if necessary.

To specify the original executable location, invoke tests/compare_original.py
directly with `--original PATH --exe PATH...`.
The reference SHA-256 is checked before any emulation; another release will fail.

## Results, 7 October 2026

67,210 cases passed on each of the two builds: 134,420 C/reference comparisons.
See [the saved report](../analysis/c-movement-validation.json) for category counts,
executable and source hashes, and the deterministic random seed.

- Every combination of the low 13 input bits for each of the six handlers.
- Signed 16-bit arithmetic boundaries and clamp thresholds.
- Standing look-angle thresholds, including both directions held together.
- Health, weapon status, gravity/other item flags, and roll/jump priority.
- 12,000 seeded random cases spanning full-width inputs and signed 16-bit fields.

The oracle is original x86 code running in Unicorn, not a second translation of
the movement rules. All represented state fields are compared, including unchanged
fields. Original writes outside the modelled fields and scratch stack fail the
test; the return address and stack balance are also checked. The original
register calling convention is EAX=item, EDX=collision information.

The input matrix includes synthetic/unreachable gameplay states to expose integer
and priority differences. Passing it does not prove full-game equivalence or
validate Unicorn against real hardware. No rendering, audio, animation transitions,
full-frame timing or collision is exercised. Requested goals can differ from
current animation states; the test does not pretend a request takes effect instantly.

## Source and arithmetic

- src/movement.h: typed state model and the callable C API.
- src/movement.c: new implementation derived from DOS disassembly.
- tests/movement_runner.c: Windows batch executable and small console example.
- tests/compare_original.py: original-machine-code comparison harness.

State fields have explicit widths. Word arithmetic wraps before signed comparisons,
as in the original instructions. The implementation avoids relying on signed
overflow, aliasing through packed structures, or out-of-range narrowing to int16_t.
It retains observed quirks, such as look-angle checks before incrementing and
input branches that overwrite earlier state requests.

TRX is only background/reference material stored separately. Neither building nor
testing this module reads, compiles or links TRX. No TRX function body was copied.

## Dependencies and reproduction on another machine

The C module itself only needs standard C11 headers. The console runner uses the
C standard library. A normal C11 compiler can build both source files together
with src on its include path. The validated builds use Zig's bundled Clang driver,
target x86_64-windows-gnu, with -Wall -Wextra -Werror -pedantic.

Portable compiler: Zig 0.15.2, kept in work/toolchain/zig-x86_64-windows-0.15.2.
No global compiler installation or system PATH change was made.

Archive: https://ziglang.org/download/0.15.2/zig-x86_64-windows-0.15.2.zip

SHA-256 (checked before extraction):
3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c

Python validation dependencies are Capstone 5.0.6 and Unicorn 2.1.4, installed
locally in work/python-deps. To recreate them with a working pip installation:

```powershell
python -m pip install --target work/python-deps capstone==5.0.6 unicorn==2.1.4
```

Compiler cache, dependency packages and test input/output files stay under work.
Build outputs stay under build. Upstream tool licenses remain with their packages.

## Batch protocol

`movement_test.exe --batch input.bin output.bin` reads/writes fixed 64-byte records.
Each contains sixteen little-endian 32-bit words, in this order:

handler, input, health, current_state, goal_state, animation, frame, turn_rate,
lean, item_flags, weapon_status, head_yaw, head_pitch, torso_yaw, torso_pitch,
camera_mode.

Signed fields contain sign-extended 16-bit values; flags/camera contain 8-bit values.
Input is a 32-bit mask. The input and handler words are preserved. Input values
for narrower fields are explicitly reduced to the field width. The output holds
the resulting state. Incomplete records, unsupported handlers and I/O failures
produce a nonzero exit code. Use distinct input and output filenames.

## Native renderer smoke test

Run `./build-preview.ps1` and `./build-preview.ps1 -Debug`, then
`python tests/check_preview.py` with Pillow available. The existing bundled
Python runtime has Pillow. Captures are written beneath build, and the report
is analysis/preview-validation.json.

Ten bounded native WGL runs cover standing, two interpolated walking times,
running and the opposite camera angle. Five O0/O2 image pairs match byte for
byte in the test environment. Images must contain substantial colour variation, and
changes in time, animation and camera must change the output. Standing, walking
and front-running PNG captures were also visually inspected. The reverse view
uses a 600-unit camera distance to stay inside the starting room.

This is a smoke test of native rendering, not a pixel comparison with DOS and
not verification of interactive desktop input. Captures run with a hidden native
window and exit; open launch-preview.cmd to use the visible preview.

The preview also supports --capture output.ppm --animation 0|1|11 --time seconds
--orbit radians --distance 600..5000. Other levels are intentionally not exposed
by this gym-specific preview yet. Gameplay source files were not changed by
this renderer milestone.

### Preview orientation correction

The initial renderer applied scale(1,-1,1) before a conventional OpenGL camera.
That has determinant -1 and reflected the complete scene. The camera now directly
maps original world coordinates to OpenGL eye coordinates in preview_camera.c.
Looking along original +Z maps +X right, -Y up and forward to GL -Z. The transform
has determinant +1. Geometry, UVs, animation angles and gameplay coordinates were
not changed. Coordinate background: https://opentomb.github.io/TRosettaStone3/trosettastone.html#_coordinates

Both preview builds run preview_camera_test.c: 16 cases cover cardinal directions,
translated origins and elevation, checking screen-right, screen-up, forward depth,
eye/target alignment and absence of reflection. All pass. Ten new native captures
also pass the smoke checks; corrected standing and front-running images inspected.
The earlier matching-build smoke tests could not detect a shared orientation bug.

## Ground movement integration

The preview now starts in movement mode. W runs, Shift+W walks, A/D turn. Arrows
remain camera controls. R resets; 1/2/3 enter pose viewer; Tab returns to movement.
The ground-only harness blocks unsupported traversal/states and reports the cause.

`build-preview.ps1` builds and runs native gym integration checks in addition to
camera checks. `tests/check_ground_preview.py` runs eight native movement captures
and compares debug/optimized tick traces and frames. `tests/compare_ground.py`
compares 6,000 damping and 8,000 ground-collision cases against original instructions
per build; it is included in test.ps1. compare_original.py now includes state 20,
bringing that suite to 76,089 cases per build. Relevant suites passed this change.

The private sine.bin runtime asset comes from `tools/extract_runtime.py` and the
hash-pinned original executable. It remains under ignored work/reference-assets.
Headless movement runs use --simulate ticks --input original-bit-mask --trace file.csv
alongside --capture file.ppm. These paths test simulation and rendering together,
not desktop keyboard delivery or full-frame DOS equivalence.


Ground reaction follow-up: Shift+S now walks backward; running-wall splat and
recovery are connected. The current suites cover 84,968 control cases and
6,000 damping + 14,000 ground collision cases per build. Native gym tests now
exercise both wall-hit variants, release/recovery and retreat, plus backward
walking/release and bare-S suppression. check_ground_preview.py produces twelve
captures (six matched O0/O2 pairs), including wall-hit and backward motion.
See analysis/ground-integration-findings.md for evidence and remaining limits.


Backward hop follow-up: S now hops backward; Shift+S walks backward. The latest
control suite covers 93,847 cases per build. Ground comparisons cover 6,000 damping
and 18,000 collision cases per build, including the hop's floor>200 fall transition.
Native integration tests cover bare-S movement/recovery, rear wall blocking and
rollback at the window ledge. check_ground_preview.py now checks fourteen captures.
The original transition to backward falling is implemented in the collision routine
but remains guarded in the interactive harness pending airborne reconstruction.


Backward falling follow-up: compare_air.py (also in test.ps1) adds 24,000
original-instruction comparisons per build covering backward control, airborne
deflection, backward collision orchestration and damage arithmetic. Native gym
tests cover the window-ledge hop/fall/landing/recovery and an unknown-trigger
rollback fixture. check_ground_preview.py now performs eighteen captures, with
flags, fall speed and health included in traces. Its --ledge-test CLI option is
restricted to bounded capture/simulation runs. See analysis/back-fall-findings.md
for the exact audio-only trigger exception and remaining airborne guards.


Fast-fall follow-up: compare_fast_fall.py adds 18,000 original-code cases per build
for control, deflection and collision/audio/landing ordering. The existing 24,000
airborne cases also pass. Native tests cover a real-room 3,000-unit nonfatal drop,
backward airborne wall impact/recovery and guarded fatal landing from 5,400 units.
check_ground_preview.py produces twenty-two captures and compares traces/images;
its --fast-fall-test fixture is restricted to bounded simulation/capture calls.
See analysis/fast-fall-findings.md for source addresses, results and limitations.


Forward airborne follow-up: compare_forward_air.py adds 12,000 state-3 control
and 6,000 collision cases per build; the landing-time extra animation call is an
explicit service boundary. Existing 42,000 airborne cases still pass. Native tests
cover a running takeoff/rise/landing/recovery and forward fall with landing back
into a run. Standing jump remains disabled. check_ground_preview.py now checks
26 captures; its --jump-test fixture is restricted to bounded captures and drives
a standing start with 20 run ticks, 20 run+jump ticks, then release. See
analysis/forward-jump-findings.md for evidence and remaining scope.

DOS camera: `compare_dos_camera.py` executes original LOS, box adjustment,
MoveCamera and CalculateCamera instructions, comparing complete integer state
with release/debug C implementations on GYM.PHD and LEVEL1.PHD. Audio and final
view-matrix generation are stubbed. Run `build-preview.ps1` first to generate
`build/dos-camera-route.csv` for the additional 1,800 gameplay-tick comparison;
a missing route is explicitly reported as skipped. `test.ps1` includes the
component/full-update comparisons. `check_follow_camera.py` checks native
release/debug capture equality, not DOS pixel equivalence.

Caves hazard/projection checks: `compare_hazards.py` compares original DOS
projection, moving object animations, collapsing-floor trajectories, emitter
spawn decisions/offsets, dart trajectories/50-point damage/removal and effect
controllers. Native `caves_test` exercises actual triggers and runtime height
callbacks, bridge surfaces, damage, sounds, effects and reset. `check_hazards.py`
compares 12 release/debug rendered fixtures. F2/F3/F4 reach bridge/floor/dart
fixtures; Windows-message integration tests cover the same shortcuts.

Combat/enemy checks: `compare_pistols.py` isolates targeting/rays while executing
DOS GunControl. `compare_combat.py` checks target points, vector angles, articulated
bite points and complete FireWeapon ray decisions, capturing effects/LOS at service
boundaries. `compare_targeting.py` executes real target acquisition/retention and LOS.
`compare_creatures.py` isolates navigation/animation to test species decisions;
`compare_navigation.py` then checks real LOT search/corridor selection and moods.
`compare_creature_move.py` uses original animation/terrain while doubling creature
contact/list services. `compare_enemy_contact.py` checks sphere masks and local
pushes, with terrain-query doubles. `compare_combat_camera.py` runs full DOS camera
updates. Native `combat_test` runs all three species with real terrain, firing,
attacks, death, reset, creature-controller slot pressure and moving room lists. Build-preview also
checks F5/F6/F12 and Space through real Win32 key messages. `check_combat_render.py`
compares deterministic release/debug captures, not original rendered pixels.

Text: `compare_text.py` compares 2000 measured widths and aligned glyph streams
per build against DOS 0x3985c/0x399bc, doubling only final sprite submission.
Caves inventory/completion and City transition captures exercise font textures.

Ring: `compare_ring.py` executes DOS initialization/motion/rotation/select and
item-animation helpers, spin blocks and compass needle integration. It also
runs native use/back lifecycle tests. Window-input checks exercise delayed use.


Roll/look regression (playtest 14): compare_ground.py includes states 45/23;
compare_look.py executes DOS surface-look and release blocks; compare_dos_camera.py
includes complete look-camera updates and transitions. Native playtest/combat
checks cover full roll recovery, look limits/release, surface tread, and armed
versus holstered integration. Win32 input tests include W and Num0/Insert scan codes.

Valley (playtest 30): compare_creatures.py, compare_navigation.py,
compare_creature_move.py and compare_combat.py accept LEVEL3A to test the loaded
wolf/raptor/T. rex animation bases and original DOS controllers. The default
Caves cases remain in the suite. compare_valley_effects.py checks stomp strength
and positive/negative camera bounce against DOS, including RNG consumption.
valley_enemies_test.c exercises every placed creature through activation,
movement and death, both weapons against all three species, attacks and save
continuation through the T. rex fatal bite. Renderer fixtures --level 3
--combat-test 4/5/6 capture raptor/T. rex/fatal bite with --simulate and --capture.

Lighting (playtest 31): compare_lighting.py --dll build/step_test.dll
build/step_test_debug.dll compares room sampling, fog, signed normal lighting
and baked mesh shades with DOS routines. It also verifies loaded room-light
records in Gym, Caves, City and Valley. The renderer's --lighting-test runs
8192 palette checks and indexed-texture/transparency checks on the active GPU.
Use --level to exercise different level palettes.

Playtest 32 extends --lighting-test with 93 constant-shade perspective quads:
all 31 interior palette boundaries and one integer shade on either side.
This catches interpolation noise that row-centre tests miss. A deliberately
single, non-overlapping face isolates the test from depth/portal issues.

Interpolation (playtest 33): render_interpolation_test.c checks rigid joint
hierarchies, shortest rotations, exact endpoints, subframe camera alignment,
room crossings, mesh replacement, missing ticks and teleports. The preview's
--interpolation-test executes 80 gameplay ticks with read-only snapshots and
renders multiple fractions, including weapon poses, checking player/item state
for unintended mutation. Add --capture to inspect its last rendered subframe.
Both checks run from build-preview.ps1; Gym, Caves, City and Valley are included
in the live release/debug checks. Other levels accept --level with the same test.

Playtest 34 adds levels 12 and 13 to the live interpolation suite. Natla's
Mines must activate its real start-camera trigger and preserve target history.
Both levels also exercise fixed-shot tracking, item-target cuts and chase
return, checking that render endpoint changes do not change camera simulation
state. The Natla regression failed before the fix at tick 1, target Y.

Peru gameplay (playtest 35): compare_peru.py runs the original Larson and
mummy controllers and flip-trigger decisions against release/debug DLLs.
LOS and effect allocation are controlled services in that comparison.
tools/test-peru.ps1 builds peru_test.c against the native runtime and checks
both actual levels: cog pickups/insertion, gear masks, room swaps, pillars,
Scion collection and escape, ceiling traps, boulder travel, enemy combat and
flipped save/load. Moving pillars must not regain an occupied floor during
a room swap. Scion inventory and ring descriptors also have DOS comparisons.

The preview's --level 3/4 --peru-test renders the flipped levels and Scion
sequence. --level 3 --transition-test exercises the actual Valley exit and
Qualopec continuation. Both are included in build-preview.ps1. These fixtures
do not constitute complete uninterrupted level playthroughs.
