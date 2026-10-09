# City pushable block and underwater switches

Independent C reconstruction from the supplied DOS executable.

## Evidence

- Block initial floor change 0x2eb00; control 0x2eb34; interaction 0x2ec7c.
- Push/pull clearance 0x2eefc / 0x2f00c, including raw sector floors/ceilings,
  static geometry and extra space for Lara while pulling.
- Floor and navigation changes 0x2f380; block standing changes floor by -1024,
  moving restores it, finishing installs it at the destination. Reset restores
  the occupied floor and the original placement.
- Ready pose state 38, movement states 36/37 and original camera requests
  0x25b80 / 0x25bac / 0x25bd8. Original model animation commands move the
  block by a tile and play its scraping sounds; clearance is checked first.
- Underwater switch 0x345d4: original bounds, 16-unit approach, 364-unit angle
  approach, state 40 interaction, switch toggle, activation and trigger gate.
- The animation-to-water bridge now preserves weapon-status end commands.

## Validation

compare_city.py executes the original x86 instructions for 2400 bounds cases,
20 floor mutations, 480 push/pull clearance cases, 800 underwater switch contacts
and 571 object animation frames per release/debug build. All match.
Native City tests cover push, pull, ready-pose cancellation, reset, scrape sounds,
both switches, swimming afterwards and first switch opening door item 32.
Existing object and water differential suites pass; release/debug native
Gym/Caves movement, combat, inventory and progression tests pass.
Rendered push and both switch animations inspected.

## Limits

City switch item 31 targets trapdoor item 27 (type 65). Its lever interaction
and trigger gate work, but the target controller remains deferred until the
trapdoor milestone. Item 30 targets ordinary door 32, which is connected.
No new key/idol, trapdoor, swinging-blade or City exit controller is claimed.
General block falling presentation (including original camera shake) and
other block variants/levels still need validation beyond this City milestone.
Full DOS route comparison and user playtesting remain.

## Playtest 18: cross-room interaction

Reproduced the reported failure by pulling the original block three tiles:
Lara was in room 14 (z=25499) and the block remained in room 0 (z=26112).
The previous current-room-only filter rejected it before bounds checks.
Interaction discovery now visits the current room then direct portal rooms,
using synced room item lists and the existing near-object/active bounds.
The native regression failed before the fix and passes afterwards, including
a push from this split-room position, pulling it back, and a further pull
that transfers the block into room 14. Release/debug builds and the original
City differential comparisons pass.
