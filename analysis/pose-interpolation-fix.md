# Animation pose interpolation fix

Reproduced the reported brief pose corruption in native captures of the standing
backflip and underwater swimming, without a user video.

The preview interpolated the three packed Euler angles independently. The
original keyframes sometimes encode nearby orientations using different Euler
representations. For example, swim animation 86 changes Lara's root rotation
from (49408,32704,32768) at frame 1394 to (49152,0,0) at frame 1397.
Those orientations are close; interpolating their individual angles produced
large, unwanted rotations at frames 1395 and 1396. Backflip animation 75 contains
similar representation changes, including the root interval 1204 to 1206.

The renderer now converts Y-X-Z rotations into unit quaternions and interpolates
the shortest orientation path, producing a rigid OpenGL matrix. Keyframe poses,
root translations, gameplay animation selection and timing are unchanged. This
is a modern presentation fix; it does not claim the original DOS renderer's
matrix interpolation or pixel equivalence.

Validation:
- Both builds pass 137,370 real-asset joint interpolation checks across GYM.PHD
  and LEVEL1.PHD: independent Euler endpoint matrices, shortest-path distances,
  orthonormality and determinant. An equivalent-orientation regression explicitly
  checks that a 180-degree Euler representation change introduces no spin.
- 30 native captures: five consecutive backflip frames and five swim frames,
  each in the old, fixed optimized and fixed debug executables. Gameplay traces
  are identical across all three; fixed images match between builds.
- Visually inspected the before/after sequences. The swim body flips at ticks
  58/59 and backflip root twist at tick 25 disappear.
- Existing native movement/traversal and camera checks pass in both builds.

Sources: src/preview_pose.c, src/preview_pose.h, renderer rotate_pose call.
Tests: tests/preview_pose_test.c, tests/check_pose_preview.py.
Captures: build/pose-backflip-comparison.png, build/pose-swim-comparison.png.
The old executable is preserved as build/tomb_preview_before_pose_fix.exe for
these comparison captures; the normal launcher starts the fixed executable.
