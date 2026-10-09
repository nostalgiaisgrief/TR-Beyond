# Caves door/switch milestone — 2026-10-09

Independent C implementation, original DOS EXE SHA256
99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac.
No TRX implementation incorporated. Disassembly is in `dos-doors-switches.asm`.

## Recovered behaviour

- 0x17a40 object-action path: timer conversion (1 special, otherwise x30),
  five activation-mask bits, switch XOR, antipad clearing, one-shot latch and
  non-intelligent active-list admission. Pad and antipad require Lara on the floor.
- 0x18060: reverse activation flag and signed timer including -1 expiry.
- 0x34bd8: switch completion consumes deactivated state; timed switches reactivate
  for the supplied interval, untimed switches leave the active list.
- 0x344c4: Ctrl, standing, grounded, hands-free, inactive switch and local bounds
  gate interaction; Lara faces the switch, animates into state40/41, then returns
  to stop. No position snap. Original Caves cardinal switch bounds at 0xc3d74:
  X +/-200, Y exactly0, Z312..512, pitch/roll +/-1820, yaw +/-5460 (inclusive).
- 0x34ba0 updates switch timers; 0x16ff4 supplies stationary object animation
  transition/end-command handling, including command4 deactivation, goal reset
  at animation end and per-frame sounds. Non-stationary commands are rejected.
- 0x2f5bc caches sector records on both sides of doors (and alternates if present),
  replaces closed sectors with no-height/no-links data and marks blockable boxes.
  0x2fb30 uses current animation state and trigger activity to restore/block them
  at the original ticks. Door geometry is visible using its model/animation keys.
- Actual DOS setup 0x38488 confirms switch55 and doors57..64 have null floor and
  ceiling callbacks. Geometry queries now recognize those references as resolved:
  their mere presence in a trigger list must not block the camera. This fixed an
  observed camera failure at the timed switch; native camera clearance guards it.

## Integration

Caves has three switches (items10,42,52) and eight door placements. The first
switch opens item9; item42 times doors43/44 for22 seconds; item52 latches doors35/36
one-shot. Pad2854 activates door28 for two seconds. Antipad2416 cannot undo the
later switch's one-shot latch, matching the DOS object's early return.

Active objects advance before Lara, including during blocked movement; successful
Lara movement is followed by switch interaction and floor trigger dispatch.
R and F7..F11 restore sectors, boxes, object animations, masks and timers. Runtime
resources restore original geometry on destruction. The renderer uses the original
single-mesh switch/door animations; original static room assets are not modified.
F9..F11 place Lara in front of each switch for convenient Ctrl testing. The default
gym path does not install the door/switch runtime and retains its tutorial services.

## Validation

`tests/compare_objects.py` executes original machine code, with explicit allocation,
active-list and physical sound services as doubles. Each C build checks 18,000
mask/timer/switch cases, all eight real door initializations (saved sector records,
links, boxes and resulting room geometry), 2,400 complete door-control ticks
(open/close/reopen with all room sectors/box flags compared), and1,178 real
stationary animation cases. Results are in `object-validation.json`.

`tests/caves_test.c` exercises all three actual interactions, closed-door blocking,
open-door passage, timed paired-door closure/reset, one-shot protection, grounded
pad/antipad gates, malformed-list rejection before switch consumption, bounds
edges, camera clearance and door sound events. Existing gym tests remain in the
preview build. Captures of switch interaction and the opened first door were
visually inspected; no live DOS screenshot comparison is claimed.

## Limits

This is door/switch progression, not complete general object simulation. Other
trigger actions are decoded safely but deferred: enemy/trap/pickup activation,
fixed/object-target cameras, CD music, secrets, effects and level completion.
The ending doors with no ordinary door trigger are not given invented activation.
Original moving door-leaf sphere contact/push/hit reaction (0x163dc) is still
pending; current movement collision is the original sector block/restore path.
Follow camera remains modern; Lara switch controls currently use the shared null
input control and original query-only collision, without applying its dedicated
DOS camera angle/elevation/distance requests. Active objects use stable item order;
original linked-list ordering is not claimed for future interacting object types.
