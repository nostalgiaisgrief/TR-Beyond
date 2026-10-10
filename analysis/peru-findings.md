# Lost Valley machinery and Tomb of Qualopec

Implemented directly from the reference DOS executable and original level data.
No TRX implementation was incorporated.

## DOS evidence

| Behaviour | Executable address |
| --- | --- |
| Flip trigger masks and switch toggles | `0x17a40`, `0x17e88..0x17f90` |
| Room swap and occupied floors | `0x18b3c`, `0x18c20`, `0x18c84` |
| Gear controller | `0x30020` |
| Moving pillar | `0x2f288` |
| Rolling boulder and collision | `0x39e38`, `0x3a0a0` |
| Falling ceiling | `0x3a958` |
| Spikes | `0x3a33c` |
| Mummy | `0x3c384` |
| Larson and targetability | `0x327fc`, `0x324e0` |
| Scion alignment/collection | `0x34064` |
| In-game cinematic camera | `0x14fe4` |
| Flood sound | `0x1dfd4` |

Lost Valley contains 22 alternate-room pairs. Three separate socket masks
enable its lever/gear chain. The lever's flip group updates the physical world,
rendered room meshes, portals, room lights, underwater flags and navigation
zones together. The actual room-50 exit triggers continuation into Qualopec.

Qualopec contains six alternate-room pairs. Its Scion pickup trigger activates
music, the door, ceiling sections and escape flip group. The special animation
collects at frame offset 44. Camera records follow the level's light table and
palette; frame position, target, field of view and roll drive the pickup shot.
The Scion inventory descriptor comes from `0xc2fec`.

## Verification and limits

`compare_peru.py` compares 8,000 Larson decisions, 2,000 mummy decisions and
4,000 flip-trigger cases per build with emulated DOS instructions. LOS and
effect allocation are controlled services; animation and actual world changes
are exercised separately through native integration tests.

Native checks cover all cog pickups/sockets, lever masks, gears, repeated
swaps, moving pillars, Scion collection/escape, all six ceiling sections,
boulder travel, both mummies, Larson navigation/shooting and pistol defeat.
Fatal hazard checks inject contact bits; they are not full contact-path proofs.
The shared sphere collision path is used in gameplay. Blood presentation and
complete enemy trajectories have not received frame-by-frame DOS acceptance.

Save/load restores flipped room layout before sector state, including
navigation and object state. Version-three saves include flip masks and Scion
camera progress. GL fixtures exercise both levels, interpolated object poses
and the Scion shot. The Valley exit fixture checks equipment carry and resets.

Still outstanding: uninterrupted side-by-side route comparisons, water-current
trigger forces, and Qualopec's ending cinematic/onward transition. Room water
flags and water-diversion geometry are implemented; current forces are separate.
