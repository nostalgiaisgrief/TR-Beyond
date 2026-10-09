# Pull-ups, lateral hanging and Alt menu fix

The Windows preview now supports Ctrl+A/D while hanging to move sideways,
Ctrl+W to pull up, and Ctrl+Shift+W for the original handstand pull-up. Ctrl
release still drops. Forward-jump catches and standing vaults remain pending.

Recovered original logic:
- Hang control 0x25728, shimmy controls 0x25b00/0x25b38. Preserve direction
  priority, goal persistence, camera requests and collision-flag changes.
- Lateral wrappers 0x26e60/0x26e90: set yaw +/-16384 before maintenance and
  restore that lateral angle afterward, including when an edge stops the move.
- Pull-up eligibility tail 0x26800: after maintenance, require goal 10, Forward,
  front floor strictly between -850 and -650, sufficient ceiling clearance at
  front/left/right, and no static obstruction. Slow chooses state 54; otherwise 19.
- Pull-up collision 0x26b18/0x27398 samples with limits +384/-384/0. It does not
  snap feet onto the floor during the animation. Shared control clears flags 0x18.
- Animation effect 12 at 0x1e238 clears hands status. Gym animation 97 invokes
  it at frame 1574; animation 159 invokes it at frame 4358. Their movement and
  transition commands remain supplied by original level animation data.

Native fixture: exercise platform approached from room 9 at
(50076,2560,39424), yaw 16384. Tests catch, pull up using either animation,
recover hands/controls, shimmy both ways, stop at edges and release safely.
The balcony railing fixture remains un-climbable: its static obstruction blocks
pull-up as in the original eligibility check. No platform or rail assets changed.

Alt fix: preview window procedure consumes Alt key system messages and
SC_KEYMENU instead of passing keyboard menu activation to DefWindowProc. Other
system commands retain normal handling. Microsoft documents that Alt release
can generate SC_KEYMENU, which enters system-menu handling:
https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-syskeyup
https://learn.microsoft.com/en-us/windows/win32/menurc/wm-syscommand

Validation: 27,000 original-code comparisons per build for hanging controls,
pull-up eligibility and collision; 36,000 for hanging/release/lateral collision,
plus 9,158 real bounds frames. External maintenance/query services are explicit
doubles where stated by each test. Debug and optimized native integration tests
pass both pull-ups, shimmy/edge stops, blocked railings and previous movement.
Capture and window-message validation is recorded by check_ground_preview.py.
No full-frame DOS equivalence or complete follow-camera behaviour is claimed.
