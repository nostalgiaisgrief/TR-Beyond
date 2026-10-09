# Upward ledge catch, hold and release

Connected original upward catch (0x27fa0) and hanging maintenance (0x2769c)
to the Windows preview. Ctrl supplies Action only in upward-jump/hanging states;
forward reach, vault, lateral hang and pull-up controls are still gated. This
is a usable catch/hold/drop milestone, not complete climbing.

Animation bounds: tomb_visual_bounds executes integer interpolation recovered
from 0x1d380/0x1d444. It uses model-0 mesh count for frame stride, original rate,
frame offset and truncation toward zero. It preserves the original absolute
last-frame denominator comparison. Invalid data returns failure without changing
output. The preview borrows its existing visual data; resets do not allocate it.

Hanging maintenance samples twice: first using the previous move angle with
wide floor limits, then after the original two-unit cardinal nudge with Lara's
facing and the narrower upward floor limit. Valid holds adjust the facing-axis
contact shift and permit bounded vertical alignment. Invalid edges restore the
previous position. Releasing Action sets upward-fall animation 28/frame 448,
uses its real bounds to position Lara, sets speed 2/fall speed 1 and frees hands.
The existing falling and landing implementation then takes over.

Tick rollback also restores hands status and preserves an existing hang instead
of resetting it to standing. General trigger/object/death limitations still apply.
A borrowed TombVisual is now required by tomb_playtest_init.

Validation:
- 12,000 hanging-maintenance comparisons per build with explicit query/bounds
  doubles: both queries, hold/release/death-release branches, edge rejection,
  signed arithmetic, angle quadrants, correction limits and hand state.
- 9,158 real animation frames in GYM.PHD and LEVEL1.PHD: C bounds match original
  machine-code frame selection and interpolation with the actual frame bytes.
- Native gym ledge fixture: room 9, (47616,1024,35940), yaw -32768. Upward jump
  catches at tick 15; holding is stable, releasing drops and lands at Y=1024.
  The same jump without Action does not catch. Controls recover after landing.
- Debug and optimized integration suites pass. 54 native capture runs produce
  identical traces and images, including catch, hold, release and landing.

The hanging pose was visually inspected. These checks do not establish complete
frame-by-frame DOS equivalence. Pull-ups, sideways hanging and forward catches
remain the next integration work. Evidence: animation-bounds.asm and the complete
ledge-services.asm. Tests: compare_hang.py and playtest_test.c. No TRX bodies used.
