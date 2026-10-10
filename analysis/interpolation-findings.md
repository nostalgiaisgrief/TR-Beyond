# Render interpolation

The previous renderer interpolated camera eye/target with `accumulator * 30`,
but rendered Lara and other actors from the newest simulation state. Asset
keyframe interpolation only evaluated poses at the integer gameplay frame;
it did not fill the additional display frames between simulation ticks.
This put camera and actor motion on different presentation timelines.

The renderer now captures an initial pose and a pose after every gameplay
step. Captures run the existing pose assembly under an identity view matrix,
recording mesh transforms without issuing geometry draws or changing gameplay
state. Each entity has a stable track; node identities distinguish mesh changes.
Transforms are stored relative to the parent joint, then interpolated and
recomposed for drawing. This includes existing weapon-arm overrides and
head/torso rotations without duplicating their animation-selection logic.

The camera and model samples use the same accumulator fraction. No positions
are extrapolated and no collision, control, animation or save structures change.
The familiar previous/current interpolation delay remains approximately one
simulation tick. Large relocations, level changes, reset/resume and newly
visible entity lifetimes snap instead of blending unrelated history. Ordinary
room crossings retain history and check visibility from both endpoint rooms.
Transient effects interpolate position while sprite-frame selection remains
discrete. Lighting continues to sample the authoritative 30 Hz state.

Validation includes endpoint and hierarchy tests, a 90-degree rotating parent
whose child remains a fixed distance away, 144 Hz fractions, relative camera
motion, yaw wrap and stale-history rejection. Actual-renderer tests exercise
moving Lara and weapon poses, compare player/item bytes before and after
capture/draw, and draw quarter-tick samples. All 16 selectable start scenes
passed the release check; the first four also run in the debug suite.

## Fixed-camera aim (playtest 34)

A speed-one fixed request was classified as a full camera cut on every tick
in follow_camera.c. Copying current target into previous target discarded aim
interpolation, even during a continuing static shot. This was reproduced by
the real start trigger in Natla's Mines: the new history assertion failed at
tick 1 on target Y before the fix.

Eye and target reset conditions are now separate. Immediate fixed viewpoints
still snap; moving look-at targets retain their tick history unless this is
initial setup or an item-target mode transition. The DOS camera tick is
unchanged. Regression checks cover the real Natla trigger and fixed requests
in both reported levels, including item-target transitions and chase return.
