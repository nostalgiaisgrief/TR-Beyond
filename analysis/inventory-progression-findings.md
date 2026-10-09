# Inventory and Caves progression — 09 October 2026

Independent C reconstruction from the supplied TOMB.EXE; no TRX source used
for this change. Existing Windows renderer remains the presentation layer.

## DOS evidence

- PickupCollision 0x33e80: local bounds, land alignment (0,0,-100), underwater
  offset (0,-200,-350), approach speed 16 and angle step 364. Collection occurs
  in state 39 at global frame 3443 on land or 2970 underwater. Hands free is
  required on land. Collected items are hidden and counted once.
- Inventory add/request/remove: 0x2371c/0x23cc0/0x23d64. World IDs 84–94 map
  to inventory models 99–109. Ammo boxes convert to rounds when a gun is owned;
  shotgun 12 pellets, magnums 50, uzis 100 per pickup. Existing counts follow
  the original increment-before-dispatch rule.
- UseItem 0x28afc: medipacks heal 500/1000 capped at 1000; no consumption at
  full health or death. Effect 116 accompanies successful healing.
- Fresh Caves start 0x353c8: pistols, 1000 nominal pistol ammo, no medipacks.
- Trigger dispatcher 0x17a40: action 7 completes, action 10 sets a one-shot
  secret bit and calls track 13. Caves has three secret bits.
- PlayTrack 0x38f70/0x38ca0: 13 plays embedded sound 173; IDs 3–21 otherwise
  return silently. Caves cues 5/11/8/12/16/9 are therefore silent in this PC EXE.
  No console soundtrack has been added. Other CD/voice-track playback outside
  Caves is not expanded by this milestone.

## Validation

Both debug and release are compared with executable DOS x86 instructions in
Unicorn: 2800 inventory operations, 2500 pickup contacts and 3500 progression
cases per build. UI/list/device services are doubles; pickup animation, bounds,
alignment, inventory arithmetic, trigger masks and actual PC playback dispatch
execute original instructions. Reports: inventory-validation.json and
progression-validation.json. No live DOS manual playthrough is claimed.

Native integration covers land pickup animation entry/collection/recovery,
no duplicate collections, healing and full-health refusal, all three actual
Caves secret triggers/chimes, completion freeze, next-level initialization and
inventory retention. Win32 messages exercise inventory selection/use and escape.
OpenGL captures inspect test inventory, completion and real next-level loading.

## Remaining scope

The independent inventory/statistics screens are temporary test UI. Original
ring opening/selection animations, fonts, option/passport menus and saves remain
milestone 8. This is not approval to replace DOS menu design.

Caves completion loads City of Vilcabamba with carried inventory and restored
health. City-specific push blocks, keys/puzzles, trapdoors and other new object
controllers are not complete. Additional weapon combat is not implemented;
Caves only supplies medipacks and starts Lara with pistols. Full Caves route
acceptance and DOS feel comparison remain milestone 7.


## Playtest 26: level-start CD audio

The trigger dispatcher was present, but the preview omitted level-start music.
DOS 367d1..367eb selects from the word table at c3e0c:
0,57,57,57,57,59,59,59,58,58,59,59,59,58,60,60 (Gym plus 15 campaign levels).
Added tomb_music_level_track and connected fresh startup, title/picker loads,
onward progression and R restart. Existing save restoration retains its stored
music state; this does not silently replace an intentionally stopped track.

DOS CD completion polling at 47898..47991 restarts the last physical CD track.
The native PCM voice now loops for physical CD sources, including level music;
embedded gym voice remains one-shot. Native looping is seamless rather than
reproducing the DOS driver's periodic device polling delay.

Both DLL builds match all 16 original table entries and the existing 3500
trigger/secret/completion cases. Release/debug native suites pass. Frontend
integration checks Caves/City track 57, opens the real cd03 WAV through the
Windows audio adapter (suspended), verifies 44100 Hz stereo 16-bit PCM and the
looping voice mode, then closes the output. This is not a subjective listening
test. The prior restrictions on console-only music triggers remain unchanged.
