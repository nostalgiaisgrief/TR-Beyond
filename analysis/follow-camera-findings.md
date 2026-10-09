> Historical report: camera presentation described here is superseded by
> [DOS camera restoration](dos-camera-findings.md) in gym 05 / Caves 04.

# Following camera

The Windows preview now uses a modern following camera by default. This is
presentation code for the reconstructed gym; no claim of exact DOS camera
behaviour is made, and gameplay state is not changed by the camera.

- Computes the desired view from Lara's facing direction, then smooths the full
  eye position with the recovered DOS chase response. No separate yaw filter.
- Focuses on Lara's world position with stable height offsets, independent of
  breathing, joint poses and flip rotation. Deliberate animation-progress offsets
  keep pull-ups and pool exits in frame without inheriting mesh-bound wobble.
  Uses a clear nearby focus height when necessary.
- Sweeps from focus to the desired view against original room floors, ceilings,
  walls and static collision boxes. Samples at most 32 units apart with 96-unit
  clearance and refines the first obstruction. Recomputes the view from the
  current focus rather than pinning the eye along its previous movement path.
- Adjusts the desired position using original level boxes: neighbor expansion,
  256-unit boundary insets and the reconstructed edge-shift routine. This replaces
  the eight-direction side search, retention timer and emergency reposition.
  The adjusted destination is smoothed, then checked from the current focus.
- Underwater, Lara's pitch controls camera elevation and horizontal distance,
  clamped to +/-15470 angle units (about 85 degrees). Surface swimming uses the
  recovered -4004 elevation offset. Reset/pool teleport clear camera history.
- Left/right arrows temporarily orbit at 2 radians/second, then ease back behind
  Lara after a 1.25-second hold. Up/down zoom. C immediately recenters.

Explicit --orbit captures retain the old fixed camera placement for visual
regression comparisons; --follow-camera selects the new camera after that option.
The normal launcher requires no new arguments.

Validation (both debug and optimized builds):

- Synthetic wall contraction, clear doorway extension, thin and rotated static
  obstacles, low ceilings and continuous rotation.
- 1,800 gym traversal ticks: window/corridor movement, turning, full pool sequence,
  ledge catch/pull-up and vault. Each tick checks clear camera placement and samples
  the line of sight, and rejects a degenerate view.
- 24 native captures across 12 scenes: start, wall, turn, backflip, catch, pull-up,
  vault, water entry, swim, surface, climb out and pool bank. Images and gameplay
  traces match between builds. Contact sheet visually inspected after the
  stability fixes, including pull-up and pool-exit framing.
- Stability regressions: 300 idle breathing ticks and stationary flip poses
  leave the camera unchanged; a moving turn through a synthetic doorway recovers
  the rear view; 300 ticks holding Back against the gym window wall settle without
  repeated zoom. Clearance and sightline checks remain active.
- Native C recenter/F6 pool/R reset/Alt/pause/close checks pass. Backflip and swim
  gameplay traces match the previous manual-camera captures exactly.
- Existing movement, traversal, camera orientation and 137,370 pose interpolation
  checks pass in both builds.

Sources: src/follow_camera.c, src/follow_camera.h, src/preview.c.
Tests: tests/follow_camera_test.c, tests/check_follow_camera.py.
Visual evidence: build/follow-camera-scenes.png.

Scope: original gym structural and static geometry. Dynamic object cameras,
scripted trigger cameras and original cinematic camera behaviours remain pending.

Swimming pitch investigation (2026-10-08):

- Full native gameplay updates in open water turn by 364 angle units per tick,
  approximately 60 degrees per second at 30 Hz, matching the DOS control code.
- Added an integration regression for both pitch directions in underwater tread.
  The DOS water differential suite also passed 59,500 cases per build.
- No swimming speed change was made. The missing camera pitch response was
  identified as the source of the slower feel. That response is now implemented;
  the controls remain unchanged.

Position smoothing update (2026-10-08):

- Direct executable evidence is in camera-smoothing.asm. The normal chase caller
  at 0x1404c passes divisor 12 to 0x13608. Each coordinate receives signed integer
  (destination - previous eye) / divisor. Destination adjustment (0x13af0) occurs
  before this update; floor/ceiling and conditional sightline checks follow it.
- Normal target X/Z follows the actor directly (0x14912). Target Y approaches by
  one quarter per tick (0x149b5). Stable height offsets are retained so animation
  breathing and flips do not reintroduce wobble.
- New C implementation uses alpha = 1 - (11/12)^(30*dt) for full eye position and
  1 - (3/4)^(30*dt) for target Y. These match the response factors at 30 Hz and
  interpolate smoothly at modern render rates. Floating arithmetic deliberately
  omits DOS integer truncation; this is not bit-exact camera reconstruction.
- No old-eye movement sweep is restored. Clearance correction is from the current
  target to the smoothed eye, avoiding the previous doorway pin. The 96-unit
  clearance and stable framing remain modern approximations. The later obstacle
  update below replaces candidate side selection and emergency recovery.
- 4,000 original instruction-span executions verify signed coordinate arithmetic.
  Native tests verify lateral-step and turn response plus equal elapsed-time
  settling at 30, 60 and 144 Hz for a fixed destination. Doorway recovery, breathing,
  flip, wall-hop and all 1,800 gym traversal checks pass in both builds.
- 24 refreshed native captures have matching optimized/debug images and gameplay
  traces; their contact sheet was visually inspected. These are framing checks,
  not a recorded side-by-side DOS camera comparison.

Run tests/check_dos_camera_smoothing.py for the original arithmetic probe;
build-preview.ps1 runs the native smoothing and collision regressions.

Obstacle and water update (2026-10-08):

- The loader now decodes original 20-byte boxes (Z min/max, X min/max, height and
  overlap index). Both gym and Caves box arrays are checked against raw PHD bytes.
- 0x13af0 selects a box using target/destination sectors, expands bounds through
  unobstructed neighboring sectors, insets by 256 and adjusts across an edge.
  New C follows this structure. The 0x13978 two-coordinate adjustment matches
  12,000 original instruction executions per build, including its square-root
  rounding and branch boundaries sampled by randomized inputs.
- 0x13f54 adds Lara's pitch before computing the spherical chase destination.
  Underwater uses pitch with no added elevation; surface control 0x29c11 sets
  -4004. 1,010 DOS projections were checked: floating trigonometry differs by
  at most 2.83 world units from the original lookup arithmetic at distance 1800.
- Native tests check both pitch directions, clamp limits, gradual pitch response,
  720 real-pool pitch/yaw updates, and a box-edge wall case. Existing doorway,
  wall-hop, idle/flip stability and 1,800 traversal updates pass in both builds.
- 24 updated rendered captures match across builds and were visually inspected.
- Limits: the 96-unit swept/static-mesh clearance replaces original line-of-sight
  and some floor/ceiling correction details. Land framing/distance and stable
  focus heights remain modern choices. Full camera equivalence is not claimed.

Evidence: camera-obstacles.asm, camera-obstacle-validation.json.
Run tests/compare_camera_obstacles.py after building both core DLLs.
