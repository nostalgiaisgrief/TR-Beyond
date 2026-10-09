# Static visibility and staircase railing clipping (2026-10-08)

The requested DOS comparison was performed before renderer changes by inspecting
and executing the hash-pinned original TOMB.EXE instructions. Live DOS screenshots
could not be obtained: the Computer Use JavaScript helper failed to initialise
with "failed to write kernel assets: The system cannot find the path specified"
even after a reset. This is instruction-level evidence, not a live visual match.

## Table objects

GYM room 7 contains exactly two placements of static ID 17 (mesh 163):
(43520,-1280,52736) and (45568,-1280,52736). Its flags are zero. DOS at 0x1aa4d
requires flag bit 2 before drawing any static; 0x1aa54 skips this object. Our
renderer had ignored that flag. All 21 gym static definitions were checked by
executing the original branch; both ID 17 placements are disabled. Preview now
honours the flag. No asset data or collision flags were changed.

## Railing cropping

The original static loop at 0x1aa84 calls 0x10090 with the drawing bounds (not
collision bounds). It projects their eight corners and rejects an object whose
rectangle misses the room's visible bounds. Objects which pass go to 0x3e3b0.
Both paths through that mesh routine initialise polygon clipping to the full
viewport, not the room rectangle. The oracle executes both clip setup paths with
an artificially narrow room rectangle and verifies full viewport results. Vertex
transformation is a controlled test boundary; lighting/rasterisation are not run.

Our portal renderer incorrectly retained the room scissor while drawing statics.
It could cut an individual railing partway across a polygon as the portal edge
moved. Room geometry still uses portal scissoring. Statics now load the original
separate drawing bounds, test their projected overlap with the room rectangle,
and draw against the full viewport. Hidden rooms remain excluded. Projection
remains modern floating point; DOS integer edge rounding and whole-object popping
are not claimed identical. No claim is made that DOS never has any railing pop.

## Validation

- Original instructions recorded in static-render-dos.asm; executable assertions
  in tools/check_dos_static_render.py and results in dos-static-render-check.json.
- Debug and optimised preview builds pass movement, camera, pose and portal tests.
- Added static visibility tests for flags, drawing-vs-collision bounds, partial
  portal overlap, disconnected/empty bounds, and behind-camera rejection.
- Gym/Caves loader, real-level query, malformed data, visual asset decoding and
  original static collision comparisons pass in both builds after the structure
  extension.
- 24 native table/staircase captures across 12 camera angles are byte-identical
  between builds. Contact sheet inspected: build/static-render-scenes.png.
- These checks establish the two implementation differences and corrected native
  views; a live DOS screenshot comparison at the user's exact positions remains
  unperformed.

Packaged as dist/gym-playtest-02; the previous playtest is preserved.
