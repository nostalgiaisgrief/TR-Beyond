# Sideways and backward standing jumps

Recovered directly from the original DOS executable; no TRX bodies used.

State 25 (backward) control 0x25a88 requests camera angle 24570 and switches
the goal to fast fall above fall speed 131. States 26/27 (right/left) control
0x25aa8/0x25ab8 use the same fall threshold without changing camera state.
The preview records the camera request; its manual camera does not consume it.

Collision wrappers 0x26cdc/0x26cf4/0x26d0c set move angle to yaw plus
-32768/+16384/-16384, then call common body 0x2745c. This queries height 762
with floor/ceiling limits +32512/-384/192, applies original airborne deflection,
and checks descending floor contact. Landing requests death or standing,
clears fall speed/gravity and adjusts feet by floor delta. It does not use the
forward jump's extra animation invocation or running landing goal.

The existing original-data animation service supplies takeoff impulses, motion,
and recovery. Preparation now accepts all original directional inputs in its
original priority order. J/Alt with S/A/D during preparation selects back/left/right.
W remains forward and no direction remains upward. Normal A/D turning is unchanged.

Validation:
- 18,000 isolated original-machine-code comparisons per build: all three control
  and collision handlers, signed limits, angle wraparound, deflection types,
  fatal/nonfatal landing-service results, callback ordering and camera request.
- Existing standing preparation/upward suite: 24,000 cases per build.
- Native gym tests: all directions take off, travel relative to facing, land,
  recover controls, and deflect from the window wall without crossing its plane.
- 46 native capture runs: matching debug/optimized tick traces and images.

Query and landing are explicit doubles in isolated comparisons. Full-frame DOS
behaviour is not yet proven; dynamic object services, general triggers and the
original follow camera remain incomplete. Core evidence is directional-jump.asm;
comparison hashes/results are in c-directional-jump-validation.json.
