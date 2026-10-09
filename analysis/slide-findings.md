# Caves and DOS sliding — 2026-10-09

New C implementation; no TRX implementation incorporated. Source evidence is
`dos-slide.asm`, disassembled from the user's original DOS EXE (SHA256
99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac).

Original entries: 0x28128 selects slide direction/animation; 0x25a64 and
0x25b70 handle forward/backward controls; 0x26cc8 and 0x26eb8 select movement
angle and call 0x2751c for collision. Contact shift, ceiling and wall helpers
execute as original machine code in the comparison oracle.

Tilts above absolute 2 slide. The dominant axis sets downhill direction;
equal axes prefer X. Relative yaw within +/-90 degrees selects forward slide
(state24, animation70/frame1133), otherwise backwards (32,104/1677). Original
last-angle state avoids resetting the animation on every tick. Jump requests
state3 or25; actual animation transitions supply movement and launch velocity.
Sliding collision uses +32512/-512 step bounds, falls when floor offset exceeds
200, and requests stop on flat ground. Existing original wall/ceiling responses
are reused. Front collision can change the state before the fall choice, as DOS does.

`tests/compare_slide.py` compares all actor/contact fields, movement/last-slide
angles, camera requests, query call ordering and return values: 6000 entry,
6000 collision and 1000 control cases per build, including signed tilt/yaw
boundaries. Query data is controlled; this is not full-frame DOS equivalence.
Results: `slide-comparison.json`.

`tests/caves_test.c` uses actual LEVEL1.PHD: startup/idle/run, forward/backward
slide, both jump-outs, edge fall/landing/recovery, no accidental gym tutorial
requests, and embedded sound bank/player sample modes. Debug and release pass.
Renderer captures of the opening corridor and both sliding poses were inspected.
Native gym movement, water, camera, pose, visibility and audio regressions pass.

Caves is selected explicitly with --caves, including normal Lara mesh selection.
The default and pool shortcut remain gym-specific. R retains the selected mode;
F7/F8 and --slide-test 1/2 select a reproducible nearby slope fixture. A separate
package includes LEVEL1.PHD and sine table, without gym tutorial WAVs.

Movement-only mode skips dynamic-object trigger guards and trigger dispatch so
Lara can explore static terrain. It does not simulate/render doors, switches,
enemies, traps or pickups. Camera obstacle conservatism around unresolved object
references is unchanged; camera remains modern presentation (the DOS slide
camera request is recorded but not applied). Ambient/object audio and Caves
music/gameflow remain pending. These limitations are explicit in the playtest notes.
