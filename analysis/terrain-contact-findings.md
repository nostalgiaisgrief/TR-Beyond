# Structural contact classifier: 8 October 2026

`src/terrain.c` reconstructs the terrain path in DOS routine 0x151c0, using
the existing C room and height queries. `src/geometry.c` now also implements
the floor-tilt helper at 0x16020. Addresses use the LE preferred analysis mapping;
the original instructions are saved in `terrain-contact.asm`.

## Behaviour preserved

The routine samples the centre, front and two front corners. Facing selects one
of four quadrants, with the original sine table positioning the front sample.
Room resolution carries the resolved room from one sample to the next. Sampling
uses Lara's top minus 160 units, while floor distances are relative to her feet
and ceiling distances to her top. Missing heights retain the -32512 sentinel.

Slopes and lava can replace a front/corner floor distance according to contact
flags. The classifier then preserves the original priority between missing
floor, insufficient vertical space, ceiling contact, front obstruction, exact
front-ceiling equality, left obstruction and right obstruction. Grid correction
uses the original one-unit boundary margin. Arithmetic wraps and shifts are
explicit; the tilt helper uses the separately supplied global Lara Y coordinate.

The existing TombContact API remains compatible. Extra sample and tilt output
is returned in TombTerrain. A failed query leaves both outputs unchanged.

## Deliberate boundary

The original calls static-mesh collision at 0x158a8 after sampling and before
classification. This service has not been reconstructed. The C API is named
`tomb_terrain_contact` and always sets `static_meshes_pending` on success.
`object_references` also reports unresolved object height references across
the samples. Do not treat success as complete world collision, or feed these
results into a playable loop without resolving the missing services.

The oracle runs the original classifier, room, height, tilt and trigonometric
instructions. Only the static-mesh call is replaced by an explicit no-contact
service; object height callbacks remain unset. Thus the tests establish the
structural path's agreement, not full original collision equivalence.

## Validation

Both debug and optimised Windows DLLs match:

| Data | Cases per build |
| --- | ---: |
| GYM.PHD | 16,016 |
| LEVEL1.PHD | 32,208 |
| Controlled ceiling-boundary geometry | 27 |

Every sector receives eight real-level cases varying position, facing, height,
radius, floor/ceiling limits, flags and slope suppression. Tests compare all
represented contact fields, all four sample triples, centre trigger, quadrant
and signed tilt components. They also check the original return stack, writes
outside modelled state, and that the deferred static-mesh call occurs once.
Targeted geometry covers exact ceiling equality and ceiling priority. Together
the cases cover all seven returned contact types: 0, 1, 2, 4, 8, 16 and 32.
There are no skipped real-level cases. Counts, hashes and limitations are saved
in `c-terrain-validation.json`; `test.ps1` runs this alongside previous suites.

## Next step

Decode static-mesh placements and collision bounds, then reconstruct 0x158a8
and its nearby-room collection helper. Dynamic object height callbacks,
vault/slide services and full-frame integration remain outstanding. No renderer
or playable Windows port is included in this milestone.

Update: static collision and combined terrain/static classification have now
been reconstructed separately. The isolated terrain suite still retains its
documented substitute; the new combined suite executes the original static
service. See [static contact findings](static-contact-findings.md).
