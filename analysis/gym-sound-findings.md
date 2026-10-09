# Gym sound effects (2026-10-08)

Independent C implementation based on the supplied, hash-pinned DOS executable
and its GYM.PHD. No TRX implementation is incorporated.

## Connected

- Original animation command 5 now submits sound requests at its recorded frame:
  footsteps, exertion/jump, landing, ledge/climb and water animation effects.
- Fast-fall sound 30 is requested above water; repeated requests do not restart
  the active sample. Landing and water entry stop it.
- Water entry submits sound 33 (above-water camera), surfacing submits 36
  (either environment). The first entry/surface animation frames also submit
  these IDs in the original data. Their wait mode prevents doubled playback.
- Bubble effect 3 uses the original random count gate before requesting sound 37
  for an underwater camera. Cosmetic bubble particles remain unimplemented.
- Tutorial speech remains on its separate MCI stream, allowing overlapping effects.
- Space/focus loss pauses playback. R/F6 reset flushes queued output and voices;
  shutdown resets/unprepares/closes the device before freeing borrowed level data.
- Failed/rolled-back gameplay ticks discard their effect requests. The queue is
  bounded and reports overflow rather than silently dropping requests.

## Original evidence and rules

`analysis/gym-sound-dos.asm` records the relevant instructions:

- 0x289bc..0x289d1: Lara animation commands request sounds with environment 2.
- 0x2571d: fall scream 30, environment 0; 0x28435 stops it on water entry.
- 0x1dc50: splash 33, environment 0; 0x285c3: surfacing 36, environment 2.
- 0x1d9f0..0x1da2f: random bubble count (3*random/32768), sound 37 if nonzero.
- 0x2d2b4..0x2d50d: environment filtering, sound map lookup, chance threshold,
  volume attenuation by four times distance, random volume reduction, 90..109%
  pitch variation, contiguous sample variations and volume cap.
- 0x2044c: unsigned wrapping random recurrence 1103515245*seed+12345;
  result (seed>>10)&32767.
- 0x2d50d onwards: mode 0 waits for the existing source/ID sample; mode 1
  restarts it. All the gym's available definitions use these two modes.

The new loader validates the level's sound map, 69 detail records, 76 embedded
PCM RIFF samples, chunk boundaries and sample ranges. PCM is borrowed directly
from the loaded level. Nothing needs extraction or downloading to play effects.

## Modern output and limits

24 software voices, 44.1 kHz stereo PCM, linear sample resampling and waveOut
output with three 512-frame blocks (about 35 ms maximum queued output). Effects
have modest mix headroom and final saturation. Player effects are centred;
attenuation uses the follow-camera target. This does not reproduce DOS soundcard
resampling, stereo pan, master gain or exact device latency. The random algorithm
and per-request consumption match, but the presentation seed is independent:
omitted particle effects and other original random-number consumers mean the complete game
random stream is not reproduced. General ambient/source-object sound scheduling
outside this gym milestone is not connected. These are deliberate scope limits,
not claims of bit-exact sound output.

## Validation

- `tests/compare_sound.py`: 10,000 cases per build run the actual DOS sound routine
  through parameter selection, including its real RNG and distance math. Chance,
  environment rejection, volume, pitch, sample choice and final seed match C.
  This excludes original channel allocation and soundcard output.
- `tests/sound_test.c`: parses all embedded samples and rejects truncated audio;
  runs walking/running/jumping, real gym ledge catch/pull-up, fatal fall and the
  full pool/completion route. Confirms expected effect requests, wait/restart,
  simultaneous voices, stop/reset, no queued events on failed ticks and no drops.
- The resulting 39.5-second PCM recording is byte-identical between debug and
  optimised builds, contains audible-range signal and no saturated samples.
  Report: `analysis/sound-integration-validation.json`. Audio: `build/gym-sounds.wav`.
- Native waveOut open/queue/pause/resume/reset/close passed on this Windows host.
- Existing native gameplay, camera, pose and portal tests pass in both builds.

No subjective listening comparison with a live DOS reference is claimed.
Listening through the gym is the remaining acceptance check.
