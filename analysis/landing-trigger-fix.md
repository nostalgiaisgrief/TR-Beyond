# Audio-trigger landing freeze (2026-10-08)

The landing callback previously accepted only the exact ordinary trigger
`8004 3f00 a01a` (track 26). Every other trigger rolled the candidate tick back,
leaving an airborne actor in its last falling pose indefinitely. This was a
limitation of the reconstruction harness, not original DOS landing behaviour.

The original GYM.PHD contains ordinary audio-only records for tracks 27, 28,
31 and others, including different audio setup flags. The fix validates the
complete ordinary, terminal trigger list, accepting only action 8 with tracks
2 through 63 except 50. It records the last request only after the list passes;
a rolled-back tick restores the previous request. No original asset is edited.

Evidence: original dispatcher 0x17fb0 calls 0x18ce8. That routine and helper
0x18e28 change audio state for these tracks, including conditional tutorial
requests. Track 50 also changes a completion counter/level-complete state and
remains guarded. See landing-trigger.asm and landing-audio.asm. Audio playback,
conditional remapping and audio latches are still deferred, not reconstructed
by this classifier. Non-ordinary triggers, mixed camera/object lists, hazards,
invalid tracks and incomplete records are not silently accepted. In particular,
the gym track-30 records include a camera action and remain unsupported.

Validation: debug and optimized preview builds each pass 183 landing/recovery
cases (61 audio tracks times forward air, fast fall and backward fall), plus
multi-audio acceptance and mixed/invalid-action rejection. Existing movement,
running jump, damage and gameplay-trigger guard tests pass in both builds.
These are native integration regressions, not full-frame DOS equivalence.

## Platform mixed-trigger recovery (2026-10-08)

The screenshot's title reports the landing-service guard. Reproduced on the four
GYM room 9 sectors at X 50688/51712/52736/53760, Z 46592, floor Y 0.
Their records are `8004 3f00 201e 0400 8406`: audio 30 plus camera 0,
with the end-of-list bit on the camera flags/timer word. The previous audio-only
classifier rejected these and rolled the landing back, retaining the airborne
pose while allowing yaw changes.

Ordinary lists consisting only of supported audio requests and valid camera
requests now allow physical landing. The camera index is checked against the PHD
camera count. Requests are published only after the entire list validates, and
are restored on a rolled-back tick. Camera flags/timer words are consumed as data,
not as another action. Tutorial playback, scripted camera cuts, conditions and
one-shot latches remain deferred; this fix does not implement those services.
Object actions, level completion (including track 50) and malformed lists still
remain guarded.

Both native builds exercise all four original sectors through forward-air,
fast-fall and backward-fall landing, followed by actual walking displacement
(12 recovery cases). Invalid camera indices and gameplay actions after camera
payloads are rejected without publishing partial requests. Existing 183 audio
landings and movement/camera/pose regressions remain passing.

Subsequent update: gym audio/camera/completion services are now connected; see
[gym services](gym-services-findings.md). The earlier deferred-service notes above
describe the prior landing-only fix. Track 50 no longer blocks landing.
