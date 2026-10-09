# Playtest 15: sidesteps and interface

Reconstructed against the supplied DOS TOMB.EXE; no TRX implementation used.

## Original routines

- Side-step control: 0x25974 / 0x259ec; collision: 0x26b4c / 0x26c08.
  Original lateral movement angle, steering, 128-unit step limits and wall stop.
- Inventory names and encoded counts: 0x22ef0; number conversion: 0x20a88.
  Medipack counts appear only above one; selected medipacks show health.
- Health visibility: 0x209b8; air: 0x20a34; bar primitives: 0x10668 / 0x1083c.
- Pickup icons: 0x20c1c / 0x20ce4, three slots lasting 75 gameplay ticks.
- Compass option handler: 0x30471..0x30496 only handles closing on select/back.
  It does not display statistics. The temporary statistics panel is removed.
- Completion: 0x20124, original title and kills/pickups/secrets/time formatting
  and relative text positions. Continue requires a fresh S/Enter key press.

## Validation

Release/debug C movement matched DOS on 111,605 cases, including both
side-step handlers. Ground collision differential checks and native side-step
movement/release tests passed. Native inventory tests cover pickup queue entry.
compare_interface.py compares original bar line endpoints/palette indices,
health visibility/timer state, inventory count glyphs, and completion strings
and positions against the DOS machine code. Both builds pass.
Rendered inventory/medipack, pickup icon and completion captures inspected.

## Scope

Pistols remain the usable weapon and correctly have no HUD ammo counter.
Inventory ammunition formatting covers other weapon types, whose combat
controllers remain future work. Menu/completion background dimming still
uses the existing native renderer; these checks do not claim full framebuffer
equality with DOS. Title/options, save/load and final route acceptance remain.
