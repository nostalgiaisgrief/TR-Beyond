# Lost Valley creatures

Independent reconstruction from the original PC executable. TRX source was
not needed for this change.

## Original routines and constants

- Wolf initialize `0x3cd70`: frame 96, then common creature initialization.
- Wolf control `0x3cdc4`: model animation base + 20 + RNG / 11000 for death.
- Raptor control `0x19770`: 20 health, pivot 400, radius 341, 100 bite damage,
  touch mask `0xff7c00`, death base + 9 + RNG / 16200, bite joint 22 at
  local (0, 66, 318), head joint 22. Violent mood selection, smartness 16384.
- T. rex control `0x19b1c`: 100 health, pivot 2000, radius 341, navigation
  blocking mask `0x8000`, violent mood, smartness 32767. Contact damage is
  10 while running and 1 otherwise. Bite mask `0x3000` starts the fatal kill.
  Half the desired head turn is applied at both joints 11 and 12.
- T. rex kill `0x19dd4`: align Lara with the creature, extra model 5 animation
  + 1, Lara state 46, health/air -1, gravity off; camera angle 30940,
  elevation -4550 and follow-centre flag.
- Stomp `0x1de7c`, camera movement `0x13608`: animation effect 1 selects the
  distance-scaled bump. Positive values shift eye/target Y once; negative
  values consume three control-RNG samples and recover by 5 per update.

## Wolf regression

LEVEL1.PHD wolf animation base is 172; LEVEL3A.PHD uses 174. The old constant
192 could enter a walking transition after a kill in Valley. The runtime now
looks up the model base, retaining the original selection arithmetic and frame
96 startup. No new steering or sliding corrections were added.

## Validation boundaries

Per release/debug build: 12,000 species decisions; 1,300 navigation search/
target ticks; 1,950 info/mood ticks; 2,600 movement cases; 2,500 articulated
weapon-ray cases; 4,000 stomp-strength and 1,000 camera-bounce cases against
original instructions. Decision tests isolate navigation/animation services;
movement and navigation comparisons use Valley's real geometry.

Native tests exercise all six wolves, six raptors and the T. rex from their
placed positions, corpse retirement, both weapons, attacks and deterministic
save continuation into the fatal bite. Visual fixtures cover all species and
the fatal animation. These checks do not constitute a full Valley playthrough
or completion of its machinery, room-flip and puzzle systems.
