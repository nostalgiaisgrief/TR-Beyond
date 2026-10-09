# Roll and hold-to-look - 9 October 2026

Source: supplied DOS TOMB.EXE, not TRX implementation bodies.

Roll entry was already recovered in standing/run control but filtered out by
playable input. W now sends bit 0x1000. States 45 and 23 use the original null
control (0x25cd8), collision routines 0x27070 and 0x27140, ceiling/slide checks,
200-unit drop threshold and forward/backward fall transitions. Animation 146
starts at frame 3857. Animation 147 commands effect 0 on frame 3865; its actual
DOS callback at 0x1de74 subtracts 0x8000 from yaw. This effect is implemented.

Numpad 0 sends bit 0x200. Standing control (0x252f8) already contained the
original head/torso look decisions but was disconnected. Surface tread uses
0x29f90..0x2a057: 546-unit head steps, half head yaw applied to torso, zero torso
pitch. Underwater/moving look is not added where the recovered DOS handlers do
not request it. Head/torso release uses 0x24fe0..0x25089. The combat interface
shares these angles without applying a second damping step or overriding the
look camera with the combat camera.

LookCamera 0x14334 uses a 1536-unit distance, head+torso angles, original target
offset, 306-unit ShiftClamp, ClipCamera 0x138d4 at box boundaries, and speed 4
(speed 1 when leaving a fixed target). CalculateCamera's higher focus and
arithmetic vertical smoothing are retained. Existing chase/fixed/combat paths
remain intact. Rendering interpolates the resulting camera ticks as before.

Validation:
- 93,847 movement-control cases per release/debug build against DOS, including
  standing look limits and roll priority.
- 18,000 ground collision cases per build now include both roll phases;
  collision query and slide callbacks remain explicitly controlled doubles.
- 4,000 surface look plus release-damping pairs per build execute DOS instructions.
- Complete camera differential: 9,600 updates across Gym/Caves and both builds,
  including 2,160 look updates, entry/exit/fixed-target transitions and real level
  geometry. 28,000 component checks and 1,800 gameplay route ticks also pass.
- Native release/debug suites: complete roll phases/180-degree turn/recovery,
  standing and running roll with pistols holstered/drawn, stationary look,
  directional limits, release, surface look, key routing and Num Lock-off look.
- Render captures inspected for look and mid-roll. This is not a manual DOS
  side-by-side visual acceptance test or a full original gameplay-loop comparison.

Controls: W roll; hold Numpad 0 + 8/2/4/6 to look up/down/left/right. Num Lock
state does not change the physical keypad bindings. Previous packages preserved.
