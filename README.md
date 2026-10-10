# Tomb Raider Beyond

## About

An independent C reconstruction of the 1996 Tomb Raider PC release for modern
Windows. The first goal is faithful gameplay and camera behaviour. Future
optional modes will expand how the game can be played while preserving that
original experience.

## Current State

**Development playtest 35** includes substantial gameplay in Lara's Home, Caves and City of
Vilcabamba, Lost Valley's enemies and cog machinery, and Tomb of Qualopec's puzzles,
hazards, Scion escape and Larson encounter. Pistols and shotgun combat,
DOS-derived model lighting, interpolated movement, inventory, menus, save/load, sound effects and CD music are available. New Game offers all
15 campaign levels and Lara's Home, but later-level gameplay is unfinished.
Full playthrough comparisons against DOS and Qualopec's ending cinematic remain pending. Detailed
development notes are in [HISTORY.MD](HISTORY.MD).

## Installation Instructions

### Release

Requires 64-bit Windows, Python 3 for one-time asset setup, and an original PC
copy of the game. No original game assets are included in the download.

1. Download `TR-Beyond-playtest-26-windows-x64.zip` from [GitHub Releases](https://github.com/nostalgiaisgrief/TR-Beyond/releases/tag/playtest-26) and extract it into a writable folder.
2. Install Python 3 if needed. Locate the installed DOS `TOMB.EXE` and the original CD's single-file CUE/BIN image; keep the CUE and BIN together.
3. Open PowerShell in the extracted folder and run the following command, replacing both example paths:

   ```powershell
   python tools/prepare_assets.py --exe "C:/Games/TombRaider/TOMB.EXE" --cue "C:/Games/TombRaider/CD/tombeng.cue"
   ```

4. Open `Play.cmd` for the title screen or `Choose-level.cmd` to select a level. Keep the extracted folders together.

The importer reads the originals without changing them and prepares levels,
textures, the sine table, tutorial speech and CD music in `work/reference-assets/`.
It supports the original raw Mode 1 CUE/BIN layout and the DOS executable revision
identified in [HISTORY.MD](HISTORY.MD#reference-executable). Other editions and
multi-file CD images are not yet supported. No compiler is needed to play.
See [CAVES-PLAYTEST.txt](CAVES-PLAYTEST.txt) for controls and current limitations.

### Source

Current source builds require a graphics driver with OpenGL 2.0 support.

1. Clone or download this repository and install Python 3.
2. Extract Zig 0.15.2 for Windows x86-64 so its executable is at `work/toolchain/zig-x86_64-windows-0.15.2/zig.exe`.
3. From the repository root, run the asset-import command in the Release instructions above. No Python packages are needed for asset import.
4. Create the build folder with `New-Item -ItemType Directory -Force build`, then run `./build-preview.ps1` to compile the game and run native checks.
5. Open `launch-caves.cmd` for the title screen or `choose-level.cmd` to select a level.

Additional original-code comparison tests have separate Python dependencies;
see [tests/README.md](tests/README.md). To package a build without original assets,
run `./package-release.ps1 -Executable build/tomb_preview.exe -Name TR-Beyond-local-windows-x64`.

## Milestones

Checked milestones indicate implemented features; complete game-wide DOS fidelity is still pending.

- [x] Original executable analysis and component comparison tests.
- [x] Level loading, room geometry, textures, meshes and animation decoding.
- [x] Native Windows renderer, lighting and portal visibility.
- [x] Lara startup, ground movement, animation and collision.
- [x] Jumping, falling, landing, climbing, hanging and sliding.
- [x] Swimming, water exits, swan dives, rolling and hold-to-look.
- [x] DOS-derived chase, swimming, fixed, combat and point-of-interest cameras.
- [x] Lara's Home tutorial triggers, speech, completion and death/reset.
- [x] Native sound effects, inventory sounds and level CD music.
- [x] Caves switches, doors, bridges, collapsing floors and dart traps.
- [x] Pistol and shotgun combat; wolf, bear and bat behaviour.
- [x] Pickups, healing, secrets, statistics and Caves-to-City progression.
- [x] Original font, inventory ring, compass and gameplay HUD.
- [x] City push/pull blocks, underwater switches and trapdoors.
- [x] City quest items, swinging blades and Lost Valley transition.
- [x] Title/options menus, animated passport, save/load and death flow.
- [x] DOS-derived interface layout and configurable controls shared across levels.
- [x] All-level development picker and local playtest packaging.
- [x] Fixed vertical framing, 4:3 startup and desktop fullscreen.
- [ ] Complete Lara's Home, Caves and City playthrough comparisons against DOS.
- [ ] Finish interface visual validation and DOS control preset switching.
- [ ] Implement intro FMVs, cinematic sequences and title attract demos.
- [x] Lost Valley wolves, raptors and T. rex, including attacks and death animations.
- [x] Lost Valley cog machinery, water-diversion room swaps and Qualopec progression.
- [x] Qualopec moving pillars, boulder, falling ceilings, mummies, Larson and Scion escape.
- [ ] Complete Valley/Qualopec route comparisons and Qualopec's ending cinematic/onward progression.
- [ ] Complete the remaining campaign levels and their gameplay systems.
- [ ] Finish whole-game fidelity checks, regression coverage and DOS detail behaviour.
- [ ] Provide a streamlined installation and release process.
- [ ] Add optional expanded gameplay modes after the faithful baseline is complete.
