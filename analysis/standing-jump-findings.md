# Standing jump preparation and upward jump

Recovered from the hash-pinned original TOMB.EXE; no TRX implementation used.
See standing-jump.asm and c-standing-jump-validation.json.

- State 15 control: 0x2579c. Probe forward, left, right, back in that priority;
  accept a signed-word floor delta >= -384, set the corresponding goal and
  move angle, then override the goal with fast fall if fall speed > 131.
- Floor probe 0x2828c samples 256 units along the selected direction, at
  feet minus 762 for sector lookup, then returns floor minus feet (or -32512).
  The preview uses original integer sine data and structural floor queries;
  unresolved dynamic object heights remain guarded.
- State 15 collision: 0x26978. Clear gravity/fall speed, query height 762 with
  limits +32512/-32512/0 using move angle. Centre ceiling delta > -100 cancels
  to standing animation 11/frame 185 and restores the pre-tick position.
- State 28 control/collision: 0x25ac8/0x26d28. Fast-fall threshold 131;
  query height 870, check grab, apply original fast-fall deflection, then land
  if descending and the floor delta is nonpositive. Landing damage uses the
  existing service. The preview disables Action; original grab routine
  0x27fa0 returns false without that input. Grabbing is not implemented.

The gym animation data supplies compression animation 73, upward takeoff 91,
and subsequent animation/velocity/command transitions. No substitute jump
arc was introduced. Upward jump animation includes horizontal root movement;
it is not assumed to stay at exactly the same coordinate.

Connected controls: J/Alt from standing for up, W during preparation for forward,
existing J/Alt while running. Side/back choices are reconstructed in isolated
preparation control but deliberately filtered out of the preview until their
airborne collision states are ready. Camera left/right now uses 2 rad/s instead
of 1 rad/s; zoom and simulation tick rate are unchanged.

Validation: 24,000 isolated DOS control/collision comparisons per build, with
explicit probe/query/grab/landing doubles. Both debug and optimized native
integration suites pass standing up/forward takeoff and recovery, low-ceiling
cancellation, and existing movement/audio-trigger regressions. 34 native capture
runs produce identical debug/optimized images and tick traces. This is not a
claim of full-frame original gameplay equivalence. Standing jump grabs, side/back
jump integration and general trigger/camera services remain incomplete.
