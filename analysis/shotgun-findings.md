# Shotgun - playtest 28

Independent reconstruction from the hash-pinned DOS executable. No TRX
implementation code was used.

## Original evidence

- Gun control and weapon switching: 0x2a460..0x2a8bf; shotgun is type 4.
- Draw: 0x2b200, frames 13..46, hand/back mesh transfer at 23, ready at 47.
- Holster: 0x2b2a4, frames 80..113, mesh transfer at 101. Interrupted aim,
  firing and lowering take the original transition paths.
- Ready/aim/pump: 0x2b52c..0x2b7d3; linked arm frames, left-arm aim,
  torso half-angle response, pump sound 9 at frame 57.
- Six-pellet firing: 0x2b7d4, spread factor 3640, two random draws per pellet.
- FireWeapon: 0x2ada0, ammo per pellet, four damage per hit, 500-unit muzzle
  height and zero additional spread. Its two random draws are still consumed.
- Target acquisition/retention: 0x2a8c0 / 0x2aa58 retain the 650-unit targeting
  origin; shotgun angle limits come from the table at 0xc3afc.
- Empty ammo: 0x2b0fb, sound 48 and requested weapon becomes pistols.
- Rendering: 0x1b98a..0x1bae5 uses both shotgun arm keyframes under the torso,
  without the pistols' independent arm orientation or muzzle-flash drawing.
- Original model 2 supplies hands/back meshes; animations 164..168 cover all
  127 gun frames. Firing sound is 3; draw and holster mesh-transfer sound is 6.

## Integration

Inventory item 100 equips the shotgun; 99 selects pistols. Space toggles the
selected weapon. Drawing, holstering and the automatic pump cycle retain DOS
frame timings. The existing inventory stores six pellets per shell; the HUD
shows shells. Water holsters the weapon; death stops gun control.

Native save version 2 adds current/requested weapon fields. Version-1 saves
retain their former payload layout and load with pistols selected. Original
DOS save compatibility is not implied.

## Validation

Release and debug builds each pass:

- 8,000 DOS gun-control comparisons with targeting and pellet emission doubled.
- 1,500 six-pellet spread comparisons against the original firing loop.
- 2,500 original target-point/angle/pellet-ray cases, including RNG state.
- 2,400 original shotgun target acquisition/retention cases with real geometry.
- Native Lost Valley pickup, all 127 arm poses, ammo use, fire/pump sounds,
  switching, empty fallback, water/death and save/replay checks.
- Actual wolf damage and kill checks using four damage per pellet.
- Frontend inventory selection and rendering of every shotgun arm frame.

The pre-shotgun version-1 City save was also loaded successfully. Six rendered
shotgun draw/aim/fire/pump captures are identical between release and debug;
the contact sheet was visually inspected. This is not a DOS pixel comparison.
Existing pistol, target-lock and ring comparisons pass, as do the release/debug
native gameplay, frontend and save suites. Raptors, T. rex and Valley mechanisms
remain outside this milestone.
