# Playtest 21: front end, saves and route audit

Independent C work against the supplied DOS executable and original CD assets.
TRX was not used as an implementation base.

## Delivered

- Original TITLE.PHD option models and CD TITLEH.PCX, title music (CD track 2),
  title ring (including its 1024 pitch), original descriptor order and transforms.
- Passport model 81 -> 71, 30 frames, pages at 14/19/24, original per-frame masks,
  five-frame page turns and sound 115. Load / Save-or-New / Exit pages.
- Sixteen save slots. Empty load pages are skipped. New game starts Caves;
  Lara's Home remains available. Exit in-game returns to title.
- Main / Options / Items ring transfers. Sound/music levels, editable keys and
  settings.ini persistence. Existing control bindings remain defaults.
- Modern Detail Levels uses 320/640/window-width rendering. These are renderer
  implementation choices, not an emulation of DOS's software perspective
  correction thresholds. High is the default and keeps the existing renderer.
- Death passport timing from 16dc4: >300 ticks, or input after >60 ticks.
  Auto-select passport, skip Save, retain Load and Exit to Title. R remains a
  development restart shortcut; the normal death flow no longer requires it.
- Frozen inventory background with original light-map rows 16..24; RGB output
  is quantized to the original palette first. This is not framebuffer equality.
- Original CD tracks 2..10 and embedded gym voice files are included in packages.
  Music and effects have separate volume-controlled native PCM outputs.
- Normal Play.cmd opens title. Choose-level.cmd keeps all 16 development entries.

## Save scope

Version 1 is a reconstruction format, not DOS SAVEGAME compatibility. It stores
Lara/animation/movement/water state, inventory and restart baseline, camera,
trigger latches, doors, altered sectors/boxes, moved blocks, runtime item state,
enemy health/activation/room lists/navigation/RNG, darts/effects, secrets and
statistics. Callback pointers and allocation addresses are never written.

Header/version/layout fingerprint, original-level hash, payload length and
checksum are checked. Restore preflights the complete payload and navigation
allocations before committing. The UI loads a separate level before replacing
the current one. Save writes use a temporary file and atomic Windows replacement.
Dead/completed games cannot be saved. Audio playback restarts on load; device
buffers are not serialized. Saves from future incompatible state layouts require
an explicit version change/migration. Support for an unfinished level's missing
controllers is not created by saving that level.

## Evidence

- 21498 inventory modes/options loop; 240bc title pitch and opening.
- c322c/c32ec/c326c/c32ac/c336c original option descriptor data.
- 222b0 animated passport model switch; 22734 page mesh masks.
- 304f8..30a7b passport page actions, frame goals and page sound.
- 20658..2077d enumerates exactly 16 save slots.
- 16dc4..16e2b death-menu timing; 21a37 auto passport selection.
- 1a2c4 / 1a21c / 1a2f8 frozen indexed-frame shade fade.

## Validation and remaining acceptance

Release and debug native suites pass. Twelve real-level save scenarios each
pass byte-identical round-trip and 90-tick deterministic continuation after
reset/restore, plus corruption/wrong-level rejection. Scenarios cover Caves
wolves/bears/bats, City block mid-push, underwater switches, pickups, key/idol
interactions and blades. Native menu integration tests title/new game, main to
options transfer, animated save/load, cross-level restore, death passport/exit,
and binding capture. Title/passport/inventory captures inspected.

compare_frontend.py executes the original machine code for option descriptors,
64 title/game opening increments, 150 passport animation/mask cases and 55
boundary/input combinations for death timing per build. Existing full DOS
component regression suite passes; it does not execute an uninterrupted route.

Route content audit: every referenced floor-data chain in Caves (110 trigger
lists) and City (142 lists) uses implemented action categories/target types,
including bridge height references. Existing integrated hazard, combat, switch,
quest, secret and exit checks pass. An uninterrupted side-by-side DOS traversal
of both complete routes is STILL PENDING. This audit must not be labelled that
acceptance test. Exact option-dialog typography/borders, title attract demos,
intro FMVs and DOS software-renderer pixel equality are also not claimed.

No uninterrupted desktop route comparison was performed for this validation. Packaged executable passes the same front-end flow test and all manifest hashes match.


## Playtest 24: interface fidelity pass

Replaced placeholder option lists and the opaque save-slot rectangle with layouts
reconstructed from DOS 30b7c (detail), 30e30 (sound), 31414/31a74 (controls),
32054 (requester), and 399bc (text/panel geometry). Source is ui_dialog.c plus
the Win32 adapter. No TRX implementation was used.

- Detail: original High/Medium/Low ordering, Select Detail header, 25-unit rows.
  The modern rendering-resolution meaning of those settings is unchanged.
- Sound: Set Volumes header and original music/speaker font glyphs.
- Controls: original two-column baselines, Look before Roll, column navigation.
  Custom mappings and Enter action alias are retained. This editor still
  edits one custom binding set; DOS default/custom preset switching is not added.
- Passport: page label uses bottom alignment (-16), and suppresses the generic
  Game label. No duplicate caption during selection/page transitions.
- Save/load: original high-resolution requester, ten visible rows, 18-unit
  spacing, measured panel widths, selection borders and scrolling indicators.
  Native slot labels/save format remain specific to this reconstruction.
- Panels: indexed shade row 24 from the displayed level's light map; bevel
  lines use DOS palette entries 15/31. RGB-to-palette quantization remains a
  modern renderer adaptation, not software-rasterizer pixel equality.
- Existing ring transitions, passport masks and death/menu timing retained.

compare_dialog.py executes the original option/requester constructors and
Text_Draw, comparing 342 entries across both DLL builds, including all detail
and volume selections, controls and ten requester selection positions.
compare_frontend.py, compare_interface.py and compare_text.py pass again.
Release/debug native suites include new detail-order and controls-column tests,
plus the existing save/load and death flow tests. Captures of the title passport,
detail/sound/controls dialogs and in-game requester are inspected. No direct
interactive DOS screenshot or full-route acceptance is claimed by these checks.
