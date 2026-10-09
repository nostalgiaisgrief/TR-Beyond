# Reconstruction roadmap

## Current status after playtest 24

Interface layout pass completed in playtest 24: original dialog baselines,
panel dimensions, bevel borders, volume glyphs, two-column controls and
requester rows are reconstructed and compared against DOS machine code.
Passport label placement/overlap corrected. Modern resolution presets and
native saves remain intentional adaptations; pixel-identical rasterization
and DOS Default/User control preset switching are not claimed.
Playtest 22 added fixed vertical framing; 23 added 4:3 startup and Alt+Enter.

### Campaign and frontend status

1. **Full Caves/City DOS route comparison — still pending acceptance.**
   All 252 referenced trigger lists audited; existing DOS component and native
   gameplay checks pass. This is not an uninterrupted side-by-side traversal.
2. **Title/options - implemented; layout pass verified in playtest 24.** Original
   title art/models/music, option ring, sound levels and key configuration.
   Modern detail settings select rendering resolution. Development level picker
   remains in Choose-level.cmd. Intro FMVs and attract demos remain outstanding.
3. **Passport/save/load — implemented and tested.** Original animated pages,
   sixteen slots, cross-level loading and gameplay-state restoration. Saves use
   a versioned reconstruction format, not the DOS save-file format.
4. **Death/restart and interface - core flow and layout pass verified.** DOS death timing and passport flow, original light-map inventory
   backdrop fade, load/exit actions. Dialog spacing/borders are now verified against DOS code. Direct full-screen
   DOS visual acceptance remains available as a separate manual check.

See analysis/frontend-save-findings.md for exact evidence and validation limits.
Lost Valley's gameplay controllers and later-level progression remain future work.
All prior Caves/City gameplay through playtest 20 is retained.

## Historical milestones



Agreed target: explore Lara's Home with walking, running, turning, jumping,

falling, landing, basic climbing, swimming and a following camera. Preserve

gameplay and feel. Use a new C implementation; TRX is reference only.



1. **Lara starting movement state â€” implemented and tested.** Placement, room,

   orientation, standing/underwater animation, health, air and movement controls.

   Inventory/weapon/mesh services remain marked pending; meshes belong to the

   next milestone. This is fresh startup, not save restoration.

2. **Visual assets â€” decoded and tested.** Room geometry, texture/palette data,

   mesh data, skeleton hierarchy records and local animation keys are available.

   Original unarmed/gym mesh selection is verified, including the standard head

   on the gym body. Pose interpolation and skeleton transformation are renderer

   work; no rendered-frame equivalence is claimed.

3. **Windows renderer â€” implemented and smoke-tested.** Native Win32/OpenGL preview shows the textured gym, static meshes and animated gym Lara. Presentation interpolation and approximate lighting; no original rendered-frame equivalence claim.

4. **Controls and movement - development build connected.** Forward/backward

   walking, backward hopping, running, turning and wall-hit recovery use the recovered animation

   and ground-collision routines at 30 ticks per second. Full-frame sequencing

   still needs validation; unsupported traversal and services remain guarded.

5. **Basic traversal - started.** Backward drops, fast falling, airborne wall

   responses and nonfatal landing are connected. Forward falls and running jumps are now

   connected, along with upward, forward, backward and sideways standing jumps.

   Original animation bounds, upward ledge catches, hanging and release are now

   connected and tested. Normal/handstand pull-ups and lateral hanging with edge

   stops are connected. Forward catches, standing vaults/climbs, underwater and

   surface swimming, diving from the surface and climbing out are connected and

   tested in the gym. Fatal falls, drowning and clean reset are now connected.

   Sliding is now connected for the Caves movement test, with direct DOS comparisons.

6. **DOS chase/swimming/fixed cameras — implemented and compared.** Original
   position/target rules, integer smoothing, object-height callbacks, projection
   and shot transitions. Render interpolation preserves immediate cuts. Combat camera is now connected and compared. Look and cinematic modes
   accompany their later gameplay features.

7. **Package and playtest.** Launchable executable and comparison against the

   DOS reference for movement and feel.



These are milestones, not guaranteed one-turn tasks. Rendering assets and

movement integration may expose missing details requiring additional work.

Gym tutorial triggers/audio, the scripted camera, completion and death/reset are

implemented and tested. The first playtest package is built and verified. Final manual full-route

acceptance remains.



Gym movement/water sound effects are connected and have received user listening feedback.

Menus, saves, FMVs and other levels' object/environment audio can follow.

General door/object control can be deferred where the gym does not need it.

Caves playtest 07 connects original placement, standard Lara meshes, rendering,
player/door sounds, DOS-reconstructed slopes, all three wall switches and eight

animated doors. Door trigger masks, timers, switch completion and sector changes

are connected. Animated door contact, terrain-validated pushing, hit reactions
and switch camera requests/timers/targets are connected and tested.
Bridges, collapsing floors and dart traps (collision, damage, effects and sounds)
are connected and tested. Pistol combat and wolves/bear/bats are connected, including floor-trigger
activation, original navigation and attacks/deaths. Pickup, inventory and Caves progression actions are now connected.


Current Caves order:
1. DOS chase/swimming/fixed/combat and manual Look cameras: implemented;
   triggered point-of-interest look was added in package 20 (see current list above).
2. Bridges/floors/darts: implemented and accepted.
3. Pistols: implemented and accepted.
4. Wolves/bear/bats: implemented and accepted.
5. Pickups/inventory: implemented in package 09; manual acceptance pending.
6. Caves secrets/music/completion/City transition: implemented in package 09;
   manual acceptance pending. City itself is not complete.
7. Full Caves route comparison with DOS.
8. Original menu/ring presentation and saves. Current inventory/statistics
   screens are temporary test controls, not the final menu design.



Combat/enemy milestone (09 October): automated component comparisons and native
integration pass in debug/release. Space draws/holsters, Ctrl fires; F5/F6/F12 offer
wolf/bear/bat fixtures. Manual combat acceptance is pending. Evidence and limits:
analysis/combat-findings.md. Caves package 07 preserves package 06 for comparison.

Interface step 1 (package 10): original font sprites, palette colours,
character mapping, spacing and alignment are implemented and compared with DOS.
Next interface step: original inventory ring behaviour and animations.

Interface step 2 (package 11): main inventory ring motion, rotation, selection,
item animations and compass mesh/needle behaviour are connected and tested.
Next interface step: inventory information (names, counts, ammo/medipack display).

Package 12 corrects the compass needle/lid transform and connects DOS ring sounds.

Package 13 applies requested Caves/City controls; interface step 3 remains next.

Package 14 connects rolling and DOS standing/surface look on W and Numpad 0.


Package 15 completes the requested five steps: ground sidesteps, inventory
information, gameplay HUD/pickup icons, original compass interaction, and
end-level statistics. Original code confirms the compass has no in-game
statistics panel; the earlier temporary panel is removed. Remaining interface
work: title/options, save/load/passport, death/restart presentation and final
background/presentation fidelity review. Full Caves route acceptance remains.


Package 19: swan/fast dive with original landing and water-entry behaviour;
City step 2 Silver Key/Gold Idol collection, Items ring, insertion and door
triggers; City step 4 all three trapdoor controllers and collision surfaces.
Both builds pass native integration and targeted original-executable checks.
Remaining City scope: swinging traps, onward progression, then full route
comparison/acceptance. Existing interface/save/title limitations remain.
