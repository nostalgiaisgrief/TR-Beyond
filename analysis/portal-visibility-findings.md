# Room visibility (2026-10-08)

All 19 GYM.PHD rooms have alternate=-1. The reported gym artefacts therefore do
not come from drawing an inactive flipped-room pair. The previous renderer drew
every room without portal bounds, exposing overlapping unrelated geometry.

The DOS drawing entry at 0x1a3f8 initializes room screen bounds. 0x1a510 walks
portal connections recursively; 0x1a588 tests the facing normal, transforms the
four vertices, computes screen bounds and updates the destination room. The
original instruction listing is preserved in portal-visibility.asm.

The new C renderer borrows the original 32-byte portal records and starts at the
camera room. It rejects back-facing/behind-eye portals, projects clipped vertices,
intersects with the parent room's screen rectangle, and grows destination bounds
until stable. Multiple paths and cycles are supported. OpenGL scissor applies the
result to both room meshes and their static placements. Lara is drawn afterward.

This reproduces the portal/screen-bound visibility model, not bit-exact DOS
integer projection. Floating-point eye-plane clipping, a worklist-style fixed
point iteration and modern depth rendering differ from original implementation.
Room flipping remains separate and is not added by this change.

Both builds pass synthetic portal bounds, chained openings, cycles, disconnected
rooms, facing, behind-eye and inside-near-plane tests, plus movement/camera/pose
regressions. 24 native captures match between builds and were visually inspected.
Additional pool/window views were inspected. Gym/Caves visual decoding checks
pass with the extended portal storage.
