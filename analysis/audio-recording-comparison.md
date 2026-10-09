# Supplied recording comparison and output timing fix (2026-10-09)

Inputs: the user's build 2026.10.08 - 23.53.51.02.mp4 and
DOS 2026.10.08 - 23.55.41.03.mp4. Both contain 48 kHz stereo AAC.
Decoded locally through Windows Media Foundation (tools/decode_audio.c) to
build/comparison-build.wav and build/comparison-dos.wav. No uploads were used.
Video snapshots establish jumping/running in the same gym area, but recordings
have different inputs/durations and random sound choices. Whole-recording
lengths or average pitch are therefore not valid speed comparisons.

## Evidence

Source-sample correlation identifies individual original PCM effects and searches
for their playback pitch. Most clean footsteps correlate strongly at the original
90..109% random pitch choices. A long effect (sound 27, sample 15) gives useful
local timing evidence: in the build's event around 2.84 s, clean interior windows
match 100% source pitch but the inferred source onset steps from 2.8402 to
2.8438, 2.8457 and 2.8493 s. These are accumulated interruptions, not uniform
slower playback. A second occurrence around 6.64 s at 103% pitch shows similar
2..4 ms offset steps. The comparable DOS event around 7.58 s is 108% pitch and
maintains a stable ~7.584 s onset across its clean interior. Pitch differences
between individual occurrences are expected from the original random rules.

This supports a real timing discontinuity in the build recording which can sound
like crackling or slight slowing. It does not establish a global playback-pitch
error. AAC encoding and source waveform differences limit interpretation of tiny
residuals. No subjective listening claim is made by this analysis.

Analysis scripts: work/analyse_recordings.py, work/match_recordings.py and
work/track_audio_windows.py. Reports: recording-audio-matches.json and
audio-recording-comparison.json. Matching outliers/overlapping bursts are not
used as evidence of an overall pitch change.

## Fix

The previous output depended on render-thread polling and three 512-frame buffers.
Move PCM generation/refill to a dedicated waveOut completion-event thread,
requesting Windows Audio scheduling via MMCSS. Protect mixer requests, reset,
pause and stats with a critical section. Stop/join the worker before releasing
output buffers or borrowed sample data. Tutorial speech stays independent.

Hardware testing also rejected the original small buffer configuration and a
reduced two-buffer configuration: submitted/played sample throughput fell short
of the expected clock even when queued-header counters did not report empty.
The final three 1024-frame buffers preserve the 44.1 kHz format, with about 70 ms
maximum queued audio. This increases buffering rather than changing sample pitch,
randomisation, gameplay tick rate or animation command timing.

## Validation

- Both preview builds pass the existing native movement, pose, camera, portal and
  sound integration tests.
- In both builds, an automated device test deliberately withholds all rendering
  updates for three seconds. Playback continues at the expected sample clock and
  reports no empty-queue wakeups. The release test passed twice. It additionally
  checks pause halts submissions and exercises resume/reset/event/close.
- Recorded device rates: 132994 samples / 3.0157 s (debug), 132521 / 3.0049 s
  (release), 132551 / 3.0056 s (repeat), consistent with 44100 samples/s.
- The offline 39.5-second mixed audio remains byte-identical to playtest 03 in
  both builds: the sound-generation rules have not changed.
- No new full gameplay differential run was required: gameplay and sound-selection
  code are unchanged. The affected native builds/integration/device tests ran.

Packaged as playtest 04. A new listening pass/recording is still needed to confirm
that the user-observed crackling is resolved in their normal recording setup.
