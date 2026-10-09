# Playtest 19: swan dive, City steps 2 and 4

Independent C implementations based on the supplied DOS executable. TRX code
was not used as a base. Input bindings remain those requested by the user.

## Executable evidence

- Swan/fast dive controls: 0x26014 and 0x26038; collision 0x27280 and 0x27304.
  Walk during a forward jump selects state 52 (existing forward-air control).
  Fall speed above 131 requests state 53. Fast dive damps speed by 95/100.
  A fast dive landing above speed 133 requests death; other dive landings stop.
  The original animation data supplies the short-dive roll and water transitions.
  Collision must remember which dive routine was dispatched: wall deflection
  can change the actor state before the lethal-landing check.
- Water entry branches at 0x2843a..0x28486: target state 35, advance the original
  animation, double fall speed, pitch -8190 (swan) or -15470 (fast dive).
  Generic water entry's 3/2 fall speed and replacement animation do not apply.
- KeyHoleCollision 0x346c4; PuzzleHoleCollision 0x34904. Bounds are shared with
  the existing switch bounds; aligned local Z is 362 / 327. States 42 / 43
  hold Lara's hands busy. Camera angle -14560, elevation -4550, distance 1024.
  Puzzle frame 3372 replaces hole object 118 with filled object 122.
- KeyTrigger 0x34c50 only consumes status 2 when hands are free, changing it
  to status 4. City floor triggers 201 and 3375 then operate doors 8 and 78.
- The original contact-list tail 0x16277 clears the inventory selection after
  one collision pass. Choosing a quest item out of reach must not queue use.
- Inventory quest descriptors at 0xc302c..0xc31ec provide original models,
  pivots, selected offsets and sort positions. Main/Items ring transfers use
  24 original motion ticks per half, radius 688, half-turn rotation and
  pitch +/-8192 (0x21d36, 0x21e37, 0x22071, 0x22136).
- TrapDoorControl 0x3a47c requests open/closed state from TriggerActive and
  advances the original animation. Objects 65/66 use the existing verified
  floor/ceiling callbacks. City items 27,61,62 are exercised; switch 31 operates 27.

## Validation

Both release and debug builds:

- 4,000 swan controls and 4,000 collision cases compared to DOS instructions.
- Native forward-jump input -> swan -> pool entry, short landing/recovery,
  high-impact death and continued death animation.
- 1,000 quest contacts/consumption cases, 4,000 key gates and 1,000 trapdoor
  controller cases compared to DOS. External menu/audio services are doubled.
- Native actual City pickups -> wrong choice/cancel -> correct insertion ->
  door opening, single consumption, filled idol mesh and reset.
- All three City trapdoors: closed floor and ceiling support, opening/removal
  of support, closing/restoration, reset; second underwater switch opens hatch.
- Windows S/Enter menu selection and Numpad 8/2 main/Items ring navigation.
- Existing movement, camera, combat, inventory, City block boundary, switches,
  sound and Caves tests pass. Targeted object, water, inventory, ring and HUD
  differential suites pass; quest descriptors/closing transfer use DOS data/code.
- Captured and inspected Silver Key/Gold Idol ring models and a swan-dive pose.

This is not a full-route City acceptance pass. Swinging traps, onward level
progression and existing title/options/save limitations remain. The inventory
backdrop retains the existing development presentation.
