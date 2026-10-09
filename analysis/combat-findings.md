# Caves pistols and creatures — 9 October 2026

Caves playtest 07 connects independently reconstructed pistol combat and the
three species present in LEVEL1.PHD: wolves, bear and bats. TRX is not the base.
The original game executable remains unchanged; package 06 is preserved.

## Behaviour connected

- Pistol draw/holster, hand/holster mesh swaps, independent arm aim, recoil,
  muzzle flash, fire sound, unlimited ammunition and firing head mesh.
- Automatic target selection, retained target while holding action, separate
  arm lock cones, line of sight, original spread and articulated mesh spheres.
- Blood from shot positions and original creature bite joints; ricochet sounds.
- DOS combat camera (including its retained chase-radius value) at 30 Hz.
- Creature placement, trigger activation, eight AI slots and distance eviction.
- Original species state decisions, mood changes, LOT navigation/corridor
  clipping, five-node search budget, radius tests, step/drop limits and flight.
- Touch masks, terrain-validated pushing, attacks, damage, death and reset.
- Original room-list insertion order, including creature room changes.

## Evidence

Original entry points: GunControl 0x2a460; target information/acquisition
0x2a8c0/0x2aa58; target point 0x2ac1c; FireWeapon 0x2ada0; pistol animation
0x2b8a0–0x2be38; CombatCamera 0x141f4; bat/bear/wolf controllers
0x11060/0x111e8/0x3cdc4; creature info/mood 0x11674/0x11eb4; LOT search and
target selection 0x118f0–0x1275b; CreatureAnimation 0x12910;
CreatureCollision 0x16314; GetSpheres 0x39130; joint point 0x393dc.

Debug and release comparisons execute original x86 instructions in Unicorn:

| Comparison | Cases across both builds |
|---|---:|
| Pistol state, separate arms, recoil, sounds and mesh swap timing | 6,000 |
| Species control decisions | 24,000 |
| LOT search/corridor ticks | 2,800 |
| Creature info/mood ticks | 4,200 |
| Animation and terrain movement | 5,600 |
| Full combat camera updates | 4,000 |
| Target point, vector angle, bite joint and weapon ray cases | 5,000 |
| Target selection/retention and LOS | 4,800 |
| Enemy sphere contacts, touch masks and pushes | 7,200 |

Individual tests state their service doubles. Species-control tests isolate
navigation/animation; those are checked separately. Movement tests isolate
other-creature contact/list services. Contact tests isolate terrain correction;
native integration runs actual terrain. Ray tests capture hit/miss services;
targeting tests use real DOS LOS. No whole-game trace equivalence is claimed.

Native integration checks all three species pursuing/attacking/killing Lara,
pistol kills and death completion, draw/holster, sounds, camera requests,
reset, more than eight activated enemies, and room-list integrity. Win32 tests
exercise P and F5/F6/F12. The existing full differential regression suite passes.
Eighteen native rendered captures/traces compare debug and release builds.

## Remaining scope

Manual combat feel and a complete DOS/Caves route comparison are still pending.
Rendering uses modern OpenGL and approximate lighting; captured frames are not
claimed pixel-equivalent to DOS. The Caves fixture shortcuts activate an original
enemy and position Lara nearby for convenient testing. Normal exploration uses
the original floor-trigger activations. This milestone supports pistols and
Caves species; other weapons/species, pickups/inventory, music/secrets/progression,
menus and saves are subsequent work.
