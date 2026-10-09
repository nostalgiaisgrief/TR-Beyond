# Tomb Raider Beyond

An independent C reconstruction of the 1996 Tomb Raider PC release for modern
Windows. The first goal is faithful gameplay and camera behaviour. Future
optional modes will expand how the game can be played while preserving that
original experience.

## Current state

Development build: **playtest 26**. Lara's Home, Caves and City of Vilcabamba
have substantial implemented gameplay, alongside inventory/options, native
save/load, sound effects and CD audio. All campaign levels can be selected;
later-level logic is unfinished. See [the roadmap](PLAYABLE-ROADMAP.md) for
validation limits and remaining work.

The renderer supports a 4:3 startup window and Alt+Enter desktop fullscreen.
Controls are shared across Lara's Home and campaign levels and can be rebound.

## Build and assets

This repository contains source, scripts, tests and development notes. It does
not include the original executable, levels, textures, audio, videos, extracted
assets, toolchain or packaged playtests. Supply your own game files locally.

The current build scripts expect Zig 0.15.2 at
`work/toolchain/zig-x86_64-windows-0.15.2/zig.exe` and prepared assets under
`work/reference-assets/`. Run `./build-preview.ps1` for the Windows executable
and native integration tests; `./build-preview.ps1 -Debug` builds the debug
variant. The broader `./test.ps1` suite compares reconstructed routines against
the supplied original executable using Python/Unicorn.

Setup is still development-oriented: reference paths in tools/tests may need
adjusting for your machine. This is not yet a turnkey installer. The notes below
record earlier milestones and may describe older builds.

## Reconstruction approach

An editable Windows implementation based on analysis of the original DOS
TOMB.EXE. TRX may be consulted to understand behaviour, but is not the project
base. No TRX game implementation is incorporated into this project's code.
Modern graphics, sound and platform services are acceptable. Preserve gameplay
and feel, including movement, animation transitions, collision, combat and camera.
Changes to timing must preserve gameplay simulation semantics.

## Reference executable

The reconstruction uses a DOS TOMB.EXE with the following identifiers:

- SHA-256: `99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac`
- Size: 768,563 bytes.
- Embedded date/time: Nov 05 1996, 14:42:43 (not independent proof of retail revision).
- MZ/LE executable; LE header at `0x2C90`; five objects.
- Entry: object 1, offset `0x3A604`. This is an executable entry, not an identified game function.

Validation results refer to this executable; equivalence with other revisions
has not been established.

## Build and test the first C module

Run `./build.ps1` in PowerShell, then `./build/movement_test.exe` for a small
console example. Run `./test.ps1` to rebuild and compare against the original DOS
machine code. See [build and validation instructions](tests/README.md).

The new C module implements six control handlers (the five identified routines
plus the backward-walk helper required by standing). Both debug and optimised
Windows builds matched the original in 67,210 cases each, including look mode,
input combinations and arithmetic edge cases. See the
[saved validation report](analysis/c-movement-validation.json).

## Next milestone

Animation advancement, collision shift/ceiling/wall responses and the walking
collision decision sequence now have C implementations. Both Windows library
builds match 30,000 additional original-code cases each. See
[animation and collision findings](analysis/animation-collision-findings.md).
Room queries, vaulting, sliding and sound/effect services use controlled substitutes
in these tests; their implementations are not claimed complete.

The PHD loader now reads rooms, sectors, floor data, animation tables and static
object placements/definitions and item placements. Structural room traversal and floor/ceiling queries match
60,280 real-level samples per build across the gym and first level. Another 3,492
animation cases per build use their actual animation tables. See
[level findings and limits](analysis/level-findings.md).

The structural contact classifier now samples Lara's centre, front and corners,
and reproduces terrain collision classification and shifts. Both builds match
48,251 original-code cases, covering every contact type. This isolated suite
keeps static contacts outside its scope. See
[terrain contact findings](analysis/terrain-contact-findings.md).

Static-mesh collision is now implemented and integrated into `tomb_world_contact`.
Both builds match another 27,910 static and 2,540 combined terrain/static cases.
Nearby-room order and first-object priority are preserved. See
[static contact findings](analysis/static-contact-findings.md).

Seven recovered object-height callback types are now implemented. The loader
reads item placements without guessing their runtime state. Explicit runtime
items can be supplied to `tomb_item_heights` and `tomb_active_contact`; unsupported
types or unknown states remain flagged. Both builds match 131,480 direct callback
cases, 18,084 real-level height queries, 2,027 combined contact queries and 210
ordered-dispatch cases. See [item height findings](analysis/item-height-findings.md).

Lara's fresh-start movement state is now initialized from the supplied level.
Both builds match 2,002 original-code startup cases, including ordinary and
underwater room flags. Inventory/weapon/mesh setup remains an explicit service
boundary. See [startup findings](analysis/lara-start-findings.md).

The initial milestones focused on a playable gym. See [the roadmap](PLAYABLE-ROADMAP.md).
Visual data is now decoded: 57 rooms, 389 indexed meshes and 6,418 animation keys
across the gym and first level. Original unarmed/gym Lara mesh selection is also
verified. See [visual asset findings](analysis/visual-findings.md).
The native Windows preview now renders the gym and supports the traversal described below.
General object updates and door sector changes can follow where the prototype
does not need them.

See [movement findings](analysis/movement-findings.md) for the initial identification
evidence and addresses. The C modules and Windows development preview are buildable and tested. Animation and collision decisions are tested as
components; object state updates, remaining object behaviour and full-frame
gameplay remain to be integrated.
The inventory tool is new Python code written for this project and only reads the
source installation/CD. Extracted commercial assets are private working files and
are not included in the source project.

## Native Windows ground movement test

Open `launch-preview.cmd`. The executable loads the private GYM.PHD and original
sine table extracted from your DOS executable. It does not change the game files.

- W: run forward; S: hop backward.
- J (or Alt): jump upward from standing, or jump while running. During standing jump
  preparation, hold W / S / A / D to jump forward / backward / left / right.
- Ctrl: hold during an upward or forward jump to catch a reachable ledge; keep holding
  to hang, release to drop. While hanging, hold Ctrl + A / D to move sideways,
  Ctrl + W to pull up, or Ctrl + Shift + W for a handstand pull-up.
  On the ground, approach a ledge with Ctrl + W to vault/climb it; higher
  reachable ledges trigger an assisted upward jump.
- Shift + W / S: walk forward / backward.
- A / D: turn left / right.
- Camera follows Lara automatically and pulls closer around walls and static obstacles.
- Left/right arrows: temporarily orbit (2 radians/second); release to return behind Lara.
  Up/down arrows: zoom. C: immediately recenter.
- Underwater: hold J / Alt to swim; W angles down, S angles up; A / D turn.
- At the surface: W / S swim forward/backward, Q / E sideways; hold J / Alt
  from treading water to dive. Hold Ctrl while facing a suitable edge to climb out.
- F6: place Lara beside the gym pool for testing. R: reset to the normal start.
- Space: pause; Escape: exit.
- 1 / 2 / 3: switch to standing/walking/running pose viewer; Tab: reset to movement.

This is a constrained development build. Running jumps, forward/backward falls,
nonfatal fast falls, standing jumps in every direction, upward ledge catches, hanging/release, sideways hanging, pull-ups, forward catches, standing vaults/climbs, swimming (including surface
diving and pool exits) and airborne wall impacts now work. Swan dives from land,
sliding and general object interactions remain incomplete. Unsupported states
stop with a title-bar message; R resets. Shift during a forward jump requests the
still-unimplemented swan dive.
Gym tutorial voices now play from the original embedded GYM.PHD samples, with
state-dependent prompts and one-shot latches. The gym's scripted camera trigger
runs for its configured duration and returns to following Lara. Climbing out of
the pool arms the original completion counter; the title shows "Gym complete!"
when it finishes. Fatal falls and drowning animate death; R starts a fresh gym,
clearing tutorial/camera/completion state and restoring health and air. Space
pauses voice playback along with the game. Losing window focus also pauses voice.
To regenerate voice assets, run `python tools/extract_gym_audio.py` with the
project Python dependencies available. Audio errors appear in the window title.
See [gym services](analysis/gym-services-findings.md).
The follow camera smooths its full position using the recovered DOS chase rate,
checks room geometry and static collision boxes,
uses stable actor framing with deliberate climb offsets, and follows Lara's pitch underwater.
Breathing and flip poses do not move the focus. Obstruction handling uses the
reconstructed box-edge adjustment and recomputes clearance through doorway turns.
Smoothing uses the original response factors with modern frame-rate interpolation;
clearance and framing still differ in places, so full DOS camera equivalence is not claimed.
Room and static geometry now use portal-bounded visibility from the camera room.
See [portal visibility](analysis/portal-visibility-findings.md).
Lighting and presentation remain approximate. See [camera findings](analysis/follow-camera-findings.md).

Build with `./build-preview.ps1` (or `-Debug`); it also runs camera and gym
integration tests. If sine.bin is missing, run `python tools/extract_runtime.py`
using the project Python dependencies. The table is extracted from the hash-pinned
original, not approximated with floating-point trigonometry.

Upward ledge catch/hold/release is now connected using original animation bounds.
Normal/handstand pull-ups and lateral hanging are connected, including edge stops
and static obstruction checks. Forward reach catches, standing vaults and the
full pool traversal sequence are now connected. See [vault/swimming findings](analysis/water-vault-findings.md).
Alt no longer activates the Windows keyboard menu and stalls the preview.
See [pull-up and Alt fix](analysis/pullup-findings.md),
[hanging integration](analysis/hanging-findings.md) and
[ledge catch findings](analysis/ledge-findings.md).

See [directional-jump findings](analysis/directional-jump-findings.md),
[standing-jump findings](analysis/standing-jump-findings.md),
[forward-jump findings](analysis/forward-jump-findings.md),
[fast-fall findings](analysis/fast-fall-findings.md),
[backward falling findings](analysis/back-fall-findings.md) and
[ground integration findings](analysis/ground-integration-findings.md) for
binary evidence, validation and precise limitations. No TRX implementation is
incorporated. The earlier renderer reflection is fixed and regression-tested.

The preview now blends joint orientations instead of individual Euler angles,
fixing brief body/limb twists in backflips and swimming. See
[pose interpolation fix](analysis/pose-interpolation-fix.md) for before/after
capture evidence and validation.


## Gym playtest package

Run `dist/gym-playtest-06/Play.cmd`, or extract `dist/gym-playtest-06.zip`
and run its `Play.cmd`. Keep the packaged build/work directories together.
The package includes the local gym assets and tutorial voices; playing it does
not require DOSBox, a CD mount, Python or a compiler.
See `PLAYTEST.txt` for controls, the route checklist and remaining limitations.
Repackage with `./package-gym.ps1 -Name gym-playtest-07` after rebuilding.
The script preserves existing packages. Automated acceptance results are in
`analysis/gym-playtest-01-validation.json`; manual full-route acceptance is pending.

Playtest 02 corrects static visibility flags and railing clipping, verified against
original DOS instructions. See [static renderer findings](analysis/static-render-findings.md).

Playtest 03 connects original gym movement/water effects through a native PCM mixer.
See [sound findings](analysis/gym-sound-findings.md). Samples are loaded directly
from the level; tutorial speech continues independently.

Playtest 04 moves effect playback off the rendering thread and increases output
buffering, following comparison of DOS and native-build recordings. See
[audio recording comparison](analysis/audio-recording-comparison.md).

## Caves doors and switches test

Run `launch-caves.cmd` or `dist/caves-playtest-06/Play.cmd`. The gym launcher
still selects the gym. Caves uses original placement, Lara meshes, geometry,
portals, movement sounds, sliding, wall switches, animated door contact/pushing
and switch camera shots with original timers and targets.
F7/F8 restart the slope fixture; F9/F10/F11 go to the three switches.
Use Ctrl while standing in front of a switch. R resets the level and its objects.
See `CAVES-PLAYTEST.txt` for controls and remaining limitations.

[Slide findings](analysis/slide-findings.md) and
[door/switch findings](analysis/door-switch-findings.md) describe DOS evidence
and bounded comparison tests. [Door contact and camera findings](analysis/door-contact-camera-findings.md)
describe the new comparisons and presentation limits. Caves enemies, traps, pistols, pickups, secrets and completion are connected.
Full-route comparison and original menus/saves remain pending.
Package with a new name, such as `./package-caves.ps1 -Name caves-playtest-08`, after rebuilding.

## DOS camera restoration

Gym playtest 05 and Caves playtest 04 replace provisional camera behaviour with
independently reconstructed DOS chase/swimming/fixed-shot rules. Camera logic
runs at 30 Hz; the renderer interpolates its results. See
[DOS camera findings](analysis/dos-camera-findings.md) for binary evidence,
comparison coverage and remaining modes. Earlier camera reports describe
historical implementations, not the current camera.

Caves playtest 05 fixes Windows F10 system-key routing. F10/F11 position Lara;
press Ctrl to operate the switch and trigger its camera. F9 has no camera shot.

Playtest 06 completes the current camera projection/cut audit and connects
Caves bridges, collapsing floors and dart hazards. F2/F3/F4 reach those test
fixtures; F10/F11 then Ctrl demonstrate switch cameras. See
[hazard/projection findings](analysis/caves-hazard-findings.md) for evidence and
remaining full-level limitations.

## Caves playtest 09

Pickups, inventory counts/healing, Caves secrets and PC music dispatch,
completion statistics and transition to City of Vilcabamba are connected.
Run `dist/caves-playtest-09/Play.cmd`; Tab opens inventory, arrows select,
Enter uses, Escape closes. Space draws/holsters; P pauses. F1/Ctrl+F1 place
Lara at a small/large medipack; Shift+F1 tests the exit. Fixtures reset progress.
City's own level-specific objects remain incomplete. Inventory/statistics use
provisional test screens until the original menus milestone.
See [inventory/progression evidence](analysis/inventory-progression-findings.md).

## Caves playtest 10 — original text

`dist/caves-playtest-10/Play.cmd` uses the original font sprites, gold palette
colours and reconstructed DOS text metrics/alignment. Press Tab to inspect.
See [text findings](analysis/text-findings.md). Original ring/screen design is
still covered by the remaining interface milestones; gameplay is unchanged.

## Caves playtest 11 — inventory ring

`dist/caves-playtest-11/Play.cmd` adds original main-ring motion, rotation,
selection transforms, item animations and the actual compass. Tab opens;
arrows rotate; Enter selects; Escape backs out after the current transition.
See [ring evidence and remaining scope](analysis/ring-findings.md).


## Caves playtest 12 - compass and ring sounds

`dist/caves-playtest-12/Play.cmd` corrects the compass child-mesh rotation and
connects the original ring opening, closing, rotation and selection sounds.
Gameplay audio stays suspended while the inventory effects play.


## Caves playtest 13 - revised controls

`dist/caves-playtest-13/Play.cmd` uses Numpad 8/2 to move, 4/6 to turn,
7/9 to sidestep, A to walk, D to jump/swim, S or Enter for action, and E or
Escape for inventory. Space/P remain weapons/pause. Manual camera controls
and animation-viewer shortcuts are removed from Caves/City. See
[CAVES-PLAYTEST.txt](CAVES-PLAYTEST.txt) for the complete current key list.
Numpad movement works with either Num Lock state. Gym bindings are unchanged.


## Caves playtest 14 - roll and hold-to-look

`dist/caves-playtest-14/Play.cmd` adds W to roll and Numpad 0 to hold look.
While looking, Numpad 8/2/4/6 looks up/down/left/right. Original standing and
surface-treading controls, head/torso limits, release damping and the DOS
look-camera geometry are connected. See [roll/look evidence](analysis/roll-look-findings.md).


## Caves playtest 15 - sidesteps and interface

`dist/caves-playtest-15/Play.cmd` connects original ground sidestepping on
Numpad 7/9, DOS inventory names/count glyphs and medipack health display,
health/air bars, pickup icons, compass interaction and end-level statistics.
The DOS compass does not open a statistics panel. Pistols show no ammo counter.
See [interface evidence](analysis/interface-findings.md) and the current
[Caves controls](CAVES-PLAYTEST.txt).


## Playtest 16 - all-level picker

`dist/caves-playtest-16/Play.cmd` opens a simple native level picker with all
15 original campaign levels plus Lara's Home, using original CD data.
Enter/Play or double-click starts a level; Escape/Cancel exits. Launching the
executable without arguments also opens the picker. `--level 0..15` selects
a level directly for testing; `--caves` and `--city` still bypass the picker.
Later-level controllers/progression are incomplete. Existing Gym controls
remain unchanged. Lost Valley's unanimated model sentinel, underwater startup
and the vertical camera basis are now supported.


## Playtest 17 - City interactions

`dist/caves-playtest-17/Play.cmd` adds DOS push/pull block interaction and both
underwater switch interactions. In City, F1 places Lara at the block, and
F2/F3 place her at the two underwater switches. The second switch's trapdoor
controller remains future work; the first switch's ordinary door works.
See [City evidence and scope](analysis/city-interactions.md).


## Playtest 18 - block room-boundary fix

`dist/caves-playtest-18/Play.cmd` corrects block/switch interaction discovery
to include Lara's current room and its direct portal neighbours, using the
existing item lists. Actual reach bounds and clearance checks are unchanged.
The reproduced City failure had Lara in room 14 and the block in room 0.
Release/debug regression tests now cover pushing and pulling across that
boundary, followed by continued movement into room 14 and reset.

## Playtest 19 - swan dive, City quest items and trapdoors

`dist/caves-playtest-19/Play.cmd` adds swan dives, Silver Key/Gold Idol pickup and insertion,
and City trapdoor controllers.
Hold A + D + Numpad 8 for a swan dive. City F4/F5 test the pickups; F6/F7
provide the matching item at its insertion point. F3 now opens the underwater
hatch. Inventory Numpad 8/2 moves between the main and Items rings.
See [evidence and checks](analysis/city-quest-swan-findings.md).

## Playtest 20 - triggered look, swinging blades and City progression

`dist/caves-playtest-20/Play.cmd` connects DOS target-only point-of-interest
look cues, City's three swinging blades and the City -> Lost Valley transition.
Caves A+F2 resets to the reported look cue; City F8 resets to the blade corridor
and F9 to the exit. At completion press S/Enter to continue. Equipment carries;
quest items, statistics and health reset. Full route acceptance and Lost Valley
controllers remain separate work. See [evidence](analysis/city-next-findings.md).

## Playtest 21

Original title/options/passport flow and versioned saves; see
[front-end evidence](analysis/frontend-save-findings.md). Play.cmd opens title;
Choose-level.cmd keeps the all-level picker. Full route acceptance remains open.
