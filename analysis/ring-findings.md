# Inventory ring — 9 October 2026

Interface step 2, Caves playtest 11. The temporary orthographic layout and
wall-clock item spinning are replaced by an independent C inventory ring.
Original EXE/PHD data was used; no TRX source was used for this change.

## Evidence and behaviour

- Initialization 0x240bc: opening radius 0 to 688, camera Y -1536 to -256,
  half-turn into view, over 32 motion ticks. Camera Z is radius + 598 in the
  inventory loop (0x216ef); its look target is (0,-96,radius), from 0x24224.
- 0x242c0 and 0x24484/0x244b4: 24-tick item rotations with signed 16-bit angle
  steps and final alignment to the selected index. Right selects the previous
  list entry, left the next. Input during movement is gated by ring state.
- 0x24304: motion accumulator, target snapping, rotation completion.
- 0x2460c/0x24678: 16-tick item selection/deselection; descriptor-driven pivot,
  tilt and Z translation. Each item retains its original parameters.
- 0x227cc: original animation frame goals, direction, wrapping and delay.
  Model keys are rendered directly for the inventory's 1:1 frame data.
- 0x2179c/0x218e6: selected idle spin, settling during rotation, alignment for
  selection and unselected-item settling. Integer increments are retained.
- Main control states 0x21498..0x22474 govern opening, open, rotation, selection,
  item closing, deselection and closing the ring. Inventory is simulated at
  30 Hz, with two original motion increments per frame, matching normal DOS
  cadence (initial c2590=2). It is independent of render frequency.
- Descriptor records at c2c28..c2ee8 supply frame counts, selected frame,
  transforms, mesh masks and list order. Large medipack precedes small.
- The previous compass placeholder incorrectly used model 95 (graphics
  options). The actual compass is model 72. Its open/close mesh masks and
  needle damping from 0x22b70 are now connected.

Using a pistol or medipack follows its selection/animation and ring-close
sequence before gameplay resumes. Full-health medipack selection closes the
ring without consuming it, matching existing DOS use rules. Compass selection
opens the object and shows the current temporary statistics view. Back plays
its closing animation and returns to the ring. Space/P remain weapons/pause.

## Validation

compare_ring.py executes the original ring helpers and item animation functions
for 108040 ticks across debug/release builds, plus 2000 item-spin and 1000 compass
needle cases per build. Parameters, motion state, target snapping and item state
are compared after each helper step. No original helper logic is stubbed;
the final compass matrix rotation is a test double.

Native lifecycle checks cover open, wraparound rotation, medipack selection/use,
compass open/back and closing. Both preview integration suites pass, including
Win32 Tab/Escape/arrows/Enter routing and delayed medipack consumption.
OpenGL captures check opening, idle ring, selected pistols, medipack animation
and open compass. These are not a complete DOS-rendered pixel comparison or a
full emulation/comparison of the DOS main inventory loop.

## Remaining interface scope

The main inventory ring is connected. Options/passport/key rings will arrive
with their corresponding interfaces and item systems. Text/count layouts,
health/air/ammo bars, final statistics layout, save/load/options/title screens,
and a broader interface timing audit remain subsequent steps. Background treatment
and lighting are still preview presentation. The source of truth stays DOS;
this work does not authorize replacement menu designs.

## Playtest 12 correction

DrawInventoryItem at 0x22b65 checks object 72 and at 0x22b6b checks ESI == 3
(the remaining child mesh count). With the four-mesh compass this is the first
child, the needle. Playtest 11 incorrectly applied the integration and rotation
to all three children. The lid/body now receive only their authored transforms;
needle integration runs once per 30 Hz inventory frame. The oracle now executes
the object/bone gate too: 42 cases per build, including non-compass objects.

Original events 111 (open), 112 (close), 108 (rotate), 113 (compass select) and
114 (weapon select) are dispatched with environment 2 and no distance attenuation.
The gameplay output remains suspended during inventory; an independent menu
output shares the level's original sample bank and remains active. Both outputs
pause on focus loss and are closed before freeing the bank at level transition.
Tests check nonzero PCM for all five Caves samples, Gym's available menu samples,
and live waveOut playback advancing while gameplay output remains paused.
Release/debug native integration and 108040 DOS helper ticks pass. A rendered
open-compass capture was inspected; full DOS pixel comparison remains outside
this validation.
