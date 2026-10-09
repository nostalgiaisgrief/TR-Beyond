# Gym tutorial, completion and death/reset (2026-10-08)

Implemented in the independent C build; original game assets are unchanged.

## Tutorial and completion

- src/gym.c reconstructs DOS 0x18ce8/0x18e28: track flag masks, one-shot latches,
  the 28->29 and 42->43 remaps, state requirements for 37/41/49/50, and the
  track-50 counter. The first eligible pool climb-out (state 55) requests 50;
  120 subsequent evaluations complete the gym. The counter counts evaluations
  of that trigger, not elapsed time away from it.
- tests/compare_gym_audio.py executes 10,000 randomized original instruction
  cases, comparing all 64 latch words, selected audio, playback/stop calls,
  counter and completion state with both C builds. Physical playback services
  are explicit doubles; no full-frame engine equivalence is claimed.
- Ordinary gym trigger lists run after each successful movement/water tick.
  Validation is atomic. Audio, camera and finish actions are supported. General
  object/door/switch dispatch is outside this gym milestone.
- Original DOS playback 0x38cf7 maps tutorial numbers 26..56 to sound IDs +148.
  The gym contains 26..50 as embedded PCM RIFF samples. These are extracted from
  GYM.PHD (not CD-DA); tools/extract_gym_audio.py records sample IDs and hashes.
- Native WinMM MCI playback supports voice replacement, pause/focus-loss resume,
  restart and shutdown. Open/play/pause/resume were verified against Windows.
  No claim of original mixer/SFX behaviour is made.

## Scripted gym camera

- The loader decodes 16-byte fixed-camera placements. Ordinary camera actions
  consume their flags/timer word, use its speed ((flags & 0x3e00)>>6)+1 and
  timer (1 stays 1; otherwise seconds*30). Trigger-entry identity prevents the
  same standing sector from constantly restarting the camera. One-shot camera
  flags are recorded. The existing smoothed follow resumes after the shot.
- This covers the gym's fixed camera. General switch/heavy/look/object-target
  cameras and cinematic behaviour are not implemented or claimed equivalent.

## Death/reset

- Fatal landing damage now commits instead of rolling back the actor. Original
  animation transitions reach state 8; the dead collision uses radius 400,
  step limits +/-384, structural/static contact and floor placement.
- Air depletion commits drowning. State 44 slows propulsion by 8 per tick,
  levels pitch by 364 units, animates the original death pose and rises by 5
  while more than 100 units below the surface, retaining underwater collision.
  Inputs no longer move or turn a dead Lara.
- R restarts at the normal gym start with health/air restored, latches/timers/
  completion cleared, playback stopped, camera reset and pause cleared.
  Completion holds the scene with a restart instruction in the window title.
  These terminal UI flows are modern; no inventory/passport menu is added.

## Validation

- Both preview builds pass existing movement/traversal, camera and 137,370 pose
  checks, plus fatal fall, drowning, ignored death input, reset, camera timer,
  voice non-retrigger and exact 120-evaluation completion checks.
- The real pool-entry/swim/surface/climb-out sequence reaches gym completion.
- Original gym and Caves loader comparisons include all fixed camera records.
- 12 native captures cover fatal/dead/drowning, fixed camera, return-to-follow,
  and completed pool scene. Optimized/debug images and gameplay traces match;
  no tick is blocked. build/gym-services-scenes.png was visually inspected.

Remaining acceptance: a full manual training route with listening and comparison
against DOS. General SFX, swan dives, menus and full-game services remain outside
these completed gym-service items.
