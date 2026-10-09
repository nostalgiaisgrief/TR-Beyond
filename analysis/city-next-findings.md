# Playtest 20: automatic look, City pendulums and progression

Independent C implementations from the user's DOS executable and level data.
No TRX code used as the base.

## Automatic point-of-interest look

CalculateCamera 0x146f8..0x1487b derives half yaw and pitch from Lara's target
height and the interest object's bounds centre. Strict limits are +/-9100 yaw
and +/-15470 pitch; head angles approach by at most 728 per tick. Torso matches
head, the item receives looked-at flag 0x40 and the existing DOS look-camera
path is requested. Manual Look and combat retain priority.

RefreshCamera 0x17997..0x179df retains an already-seen target only while it is
the previous target. Camera tick reset records that previous target. Leaving
and re-entering does not replay the cue. World reset clears the item flag.
Caves room 4 has eight target-only triggers (1000,1005,1038,1043,1078,1085,
1122,1129) pointing at item 4, object 169. Fixed-shot target behaviour remains.

## City swinging blades

Object 36's controller is 0x3a5d8; collision callback 0x16450. TriggerActive
selects state 2 from 0, and inactivity requests 0 from 2. A touching blade in
state 2 damages Lara by 100 and sets her hit flag. Blood uses the original
random offset formulas. Damage consumes the previous Lara collision pass's
sphere contacts. Active traps test contact without pushing; inactive traps
use solid object push without the door hit reaction. Original animations
provide motion and sound events. Items 56/57/58 are triggered at floor lists
3240/3247/3254 and by the later switch-camera sequence.

## Progression

City room 87 floor list 3747 issues finish action 7. The existing finish handler
freezes gameplay and displays statistics. S/Enter now loads LEVEL3A.PHD (Lost
Valley), carrying weapon ownership, ammunition and medipacks. Quest inventory,
level counters, pickup HUD, camera/trigger/enemy state reset; Lara starts healthy.
The carried inventory becomes the restart baseline for the next level.
This extends the existing Caves -> City loader; later progression is not claimed.

## Checks

- Both builds: 182 blade animation-frame/goal combinations match DOS, including
  the original sound event 65. Native contact tests also assert a blood effect.
- Both builds: 4000 automatic-look angle/limit/approach cases and 2000 pendulum
  trigger/timer/damage cases match original x86 instructions. Particle creation
  is outside the isolated pendulum comparison; native tests exercise blood/sounds.
- Real Caves native cue: head/torso movement, continuous tracking while on the
  trigger, leaving/re-entry suppression and reset.
- Every City blade: real trigger activation, animation, sphere-contact injury,
  stopping and reset. Real City exit completion and frozen player state.
- Windows Enter continuation: City exit -> Lost Valley, equipment carry, quest
  and counter reset, health reset and continued simulation.
- Existing release/debug movement, combat, doors, quest items, switches,
  trapdoors, sound, camera and input suites pass. Targeted DOS object, City,
  hazard, progression and camera differential checks pass.
- Captures inspected: snowy-room look cue, moving blade corridor, City
  statistics and Lost Valley after transition.

Full-route playthrough comparison, original menu/save/death presentation and
Lost Valley controllers remain future work.
