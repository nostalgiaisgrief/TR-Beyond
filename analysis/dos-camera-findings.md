# DOS camera restoration — 9 October 2026

## Specification

The original DOS camera behaviour is the target. Modern Windows rendering and
interpolation between original 30 Hz camera states are permitted. Custom
framing, doorway recovery or clearance policies are not substitutes for DOS.
TRX is not the implementation base.

## Evidence and implementation

Reconstructed from the supplied TOMB.EXE (SHA256
99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac):

- InitialiseCamera 0x13560; MoveCamera 0x13608.
- Edge shift 0x13978, BadPosition 0x13aa0, box adjustment 0x13af0.
- ChaseCamera 0x13f54, ShiftClamp 0x14060, FixedCamera 0x14534.
- CalculateCamera 0x145c8 and interpolated bounds 0x1d444.
- LOS 0x183c0, axis walks 0x18464/0x18750, vertical clip 0x18a38.
- Lara control dispatch at 0xc3884 supplies state-specific camera requests.

src/dos_camera.c implements integer camera decisions. src/follow_camera.c
connects original model bounds and requests to the preview. Normal distance is
1536; focus uses original animation bounds and signed target smoothing. Swimming
uses Lara's pitch. Fixed shots use original locations and target objects.
Original sector-boundary sightlines, box expansion and 256-unit insets replace
the provisional 96-unit sweep and unconditional sightline correction. Eye Y and
its vertical display correction remain separate, matching DOS history.

The preview advances movement and camera together at 30 Hz. Drawing linearly
interpolates previous/current eye and target; it does not feed interpolated
coordinates back into camera decisions. Optional arrow-key orbit/zoom and
fixture shortcuts are retained as explicit testing controls. Default play uses
the reconstructed requests. Legacy diagnostic clearance/box helpers are not the
active camera algorithm.

## Validation

Run build-preview.ps1 and build-preview.ps1 -Debug, then test.ps1.
compare_dos_camera.py executes original instructions through Unicorn, including
real bounds, LOS, room/sector and box queries. Only audio and final view-matrix
generation are stubbed in complete camera tests.

Across gym/Caves and release/debug:

- 10,000 LOS comparisons.
- 10,000 box-adjustment comparisons.
- 8,000 movement/vertical-correction comparisons.
- 9,600 complete chase/fixed updates with maintained history and target changes.
- 1,800 additional gym gameplay ticks: walking, turning, jumps, ledge catches,
  pull-ups, vaults and the pool swimming/surface/climb-out sequence.

Comparisons require exact integer eye position/room, target position/room and
vertical correction. Results are in dos-camera-validation.json. Native capture
checks separately compare release/debug output; they are not DOS screenshot
comparisons. Original camera quirks should not be removed merely because a
particular view is awkward.

## Scope

This restoration covers currently used chase, swimming and fixed-shot camera
paths. Combat/look/cinematic modes and camera shake remain unimplemented along
with the gameplay features that need them. The projection audit is now complete: original 80-degree horizontal FOV,
integer focal length and 10/20480 clipping distances. The floating-point view
matrix is a rendering interpolation detail; pixel-identical software rendering
is not claimed. Immediate item-target and speed-one fixed transitions are not
blended by the renderer. See caves-hazard-findings.md.

Gym 05 and Caves 04 package this restoration. Earlier follow-camera and door
camera reports are historical; their provisional modern-camera descriptions
are superseded here.
