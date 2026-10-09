# Ledge catch and reach reconstruction

Update: upward catch/hold/release is now connected; see hanging-findings.md.
The following records the earlier isolated-core milestone.

New C core in src/ledge.c and src/ledge.h. These routines are compiled but not
connected to the interactive preview. Action remains disabled until animation
bounds, hanging/release and subsequent traversal are available. This milestone
does not claim playable grabbing or climbing.

Recovered directly from original executable:
- Upward catch: 0x27fa0. Requires front collision, Action, free hands, left/right
  floor difference below 60, front ceiling <=0 and centre ceiling <=-384.
- Forward reach catch: 0x27d4c. Same checks plus centre floor >=200. Both compare
  ledge height with current animation minimum Y and the current fall-speed step.
- Cardinal alignment accepts the original integer angle windows, with the
  original asymmetric boundaries around -32768. Other angles reject the grab.
- Upward catches select animation 96/frame 1505 and realign Y using its bounds.
  Forward catches select animation 150/frame 3974 or 96/frame 1493 according
  to the swing-space service and retain the pre-transition height correction.
  Both apply X/Z contact shifts, zero speeds, clear gravity, enter state 10,
  and set hands busy. Contact Y shift is deliberately not used.
- Reach state 11: control 0x25778 requests camera angle 15470 and goal 9 above
  fall speed 131. Collision 0x2686c sets gravity, queries at height 762 with
  limits +32512/0/192, tries the catch, then deflects and applies landing damage.

Validation: tests/compare_ledge.py runs 36,000 comparisons per build against
original machine code: 24,000 catch cases, 6,000 reach controls, 6,000 reach
collisions. Includes early rejection, catch successes, camera/hands changes,
angle thresholds, signed overflow, service ordering and both swing outcomes.
Bounds, swing-space, query and landing are explicit doubles, not reconstructed
services in this test. Both debug and optimized builds pass. The suite includes
568 successful upward catches and 446 successful forward catches per build.

Evidence: ledge-services.asm contains complete ranges, unlike the initial
ledge-grab.asm discovery dump which ends at the first return of each routine.
Original animation-bounds instructions are also preserved in animation-bounds.asm
for the next implementation step. c-ledge-validation.json records test scope and
source hashes. No TRX implementation used.
