# Forward catches, standing vaults and swimming

Implemented in the independently written C reconstruction, using the supplied
hash-pinned DOS executable and original gym data. No TRX implementation is used.

## Connected gameplay

- Forward reach state 11 can catch a ledge, select the swing animation when space
  permits, hold, shimmy, pull up or release through the existing hanging logic.
- Ctrl + forward invokes the original standing approach: two-click (512) and
  three-click (768) vault animations, plus the higher assisted jump/grab branch.
- Falling/running into water changes to the original entry animation and swim
  speed. Underwater tread/swim/glide/dive states use original pitch, yaw, lean,
  acceleration, drag and fixed-point motion.
- Surfacing switches to tread; surface forward/back/left/right movement, dive
  timing and climbing out are implemented. Exit returns to standing with free hands.
- Lara's rendered pitch now follows her underwater pitch. Q/E are surface side
  swim controls; F6 is a development shortcut to the poolside.

## DOS evidence

- Standing vault: `0x27b44`; integer square root: `0x3f0ee`.
- Forward grab/reach: `0x27d4c`, swing space `0x27ee4`, control `0x25778`,
  collision `0x2686c`; previously compared cores are now connected to world data.
- Water height: `0x17570`; water transitions in `0x283b0` (ordinary entry,
  surfacing and leaving water spans through `0x286db`).
- Underwater frame `0x29430`, controls `0x295f8` through `0x29804`, collision `0x298d4`.
- Surface frame `0x29bc0`, controls `0x29dc4` through `0x2a128`, collision `0x2a19c`, exit `0x2a27c`.
- Animation effect 3, `0x1d9f0`, creates cosmetic bubble effects and sound. Its
  requests are counted; bubble rendering and sound playback remain deferred.
  Effect 12 frees Lara's hands at the original animation frame.

Disassemblies are saved alongside this document. Integer wrap, comparison
boundaries and callback ordering are checked directly against original instructions.

## Validation

`compare_water.py`: 59,500 cases per build, including 13,500 controls, 12,000
collision/exit cases, 8,000 motion cases, 8,000 damping cases, 6,000 water
transitions and 12,000 vault cases. Animation/world/room/sound services are
explicit doubles where stated; this does not claim whole-frame DOS equivalence.

`compare_water_height.py`: 11,826 real GYM/LEVEL1 geometry queries per build.

Native gym integration covers running-jump reach/catch/hold/release, both vault
heights, assisted jump/grab, pool entry/swimming/surfacing/exit/standing, surface
side/back swimming and diving/resurfacing. `check_traversal_preview.py` captures
10 traversal scenarios in both builds and requires matching traces and images.
Existing native movement and Alt-menu regression checks are retained.

## Remaining boundaries

General gameplay/audio triggers, currents outside the gym, swan dives from land,
sliding, fatal fall/drowning animation, saves, combat and finished camera behaviour
remain outside this change. Air decreases underwater and recovers on the surface;
fatal drowning stops at the existing development guard rather than implementing
death. R resets, F6 restarts pool testing. The camera still needs manual orbit/zoom
and can intersect walls. Modern presentation remains approximate.
