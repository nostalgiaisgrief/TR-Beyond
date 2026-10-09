# Forward airborne movement - 8 October 2026

Running jumps and forward falls now use original state 3 in the development
build. J (or Alt) supplies the jump bit while running. Standing jump preparation
is deliberately not enabled yet; pressing jump while standing does nothing.

## Evidence from the supplied DOS executable

Same pinned executable as prior milestones. See forward-jump.asm; addresses are
LE preferred analysis addresses. State 3 control is 0x25494; collision is 0x26484.

Control resets prior reach/dive goals (11/52) to 3. Unless the goal is death/stop,
action with free hands requests reach, slow with free hands requests dive, and
fall speed >131 overrides those with fast fall. Steering still runs for stop/death
goals: +/-409 increments with signed wrapping, clamped to +/-546. Left wins.

Collision sets facing/movement angle to actor yaw, limits +32512/-384 and ceiling
192, queries then applies the existing airborne deflection. On floor<=0 with
positive fall speed, landing chooses death, running (forward without slow) or
standing. It clears speed, fall speed and gravity, applies floor displacement,
and advances animation AGAIN. That immediate extra advance is required to match
the original landing transition and position. It uses the collision-updated
movement angle, including any deflection reversal.

The takeoff is driven by original running control and actual animation change
ranges/commands. No invented launch timer or velocity was introduced. Frame
integration connects the additional landing advance to the real animation code.

## Validation

- 12,000 control cases and 6,000 collision cases per O0/O2 build match DOS. All
  low 13-bit input combinations are represented in control checks, with signed
  turn-rate boundaries, goals and fall-speed edges. Collision checks compare
  callback ordering and actor/contact state, including the extra animation call.
  Query, landing and landing-time animation are explicit controlled doubles in
  this isolated test. See c-forward-air-validation.json.
- Existing 24,000 backward-air/damage and 18,000 fast-fall cases per build pass
  after extending the shared context.
- Native real-room tests start standing, run into a jump, rise, land and stop.
  A forward-fall test with forward held resumes running on landing. Existing
  backward/fast falls, impacts, health and fatal/trigger guards continue to pass.
- Twenty-six bounded native captures have matching O0/O2 tick traces and images.
  The running-jump capture was visually inspected. No whole-frame equivalence
  against the complete DOS main loop is claimed.

## Remaining work

Standing jump preparation (state 15) queries clearance in each requested direction
and has a separate ceiling response. Its evidence was inspected, but it is not
implemented or enabled here. Side/backward jumps, reach/grab, dive, slides, climbing,
death and general trigger/audio services also remain incomplete. Unsupported
states are guarded. Holding Shift during a forward jump may request the still-
unimplemented dive; this is not treated as ordinary grounded walking input.
Next: standing jump preparation/clearance and its forward takeoff.
