# First movement analysis — 7 October 2026

Follow-up: these controls, including standing look mode and its backward-walk
helper, have now been implemented in C. Both debug and optimised Windows builds
match 67,210 original-machine-code cases each. See
[C validation](../tests/README.md). The sections below record the initial analysis
milestone; its statements about implementation status are historical.

## Result and limits

Five control handlers have strong static identification, supported by 40 passing
isolated executions of the original machine code. The reference game was checked
in DOSBox, including Lara's Home, controls and sound.
No reconstructed gameplay code has been implemented or compiled yet.

The new Python analysis tools are original project code. TRX was consulted for
state names and behavioural comparison; it is not the codebase. Reference source
is isolated in work/reference-reading and is not linked or executed by the probes.

## Exact binary and address convention

Target: original DOS TOMB.EXE

SHA-256: 99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac

All analysis addresses below mean LE preferred object base plus object offset.
They are NOT measured DOSBox runtime addresses. Real loader addresses/selectors
may differ. File offsets refer to the original executable.

| Behaviour | State index | Analysis address | Object 1 offset | File offset |
|---|---:|---:|---:|---:|
| Walk control | 0 | 0x2515C | 0x1515C | 0x43F5C |
| Run control | 1 | 0x251EC | 0x151EC | 0x43FEC |
| Stop/standing control | 2 | 0x252F8 | 0x152F8 | 0x440F8 |
| Turn right control | 6 | 0x255BC | 0x155BC | 0x443BC |
| Turn left control | 7 | 0x25644 | 0x15644 | 0x44444 |

## Evidence for identification

- Relocations reveal a contiguous run of 112 code pointers at 0xC3884.
- Caller instructions at 0x24FDA and 0x25133 use two separate bases, 0xC3884
  and 0xC3964, separated by 56 pointers. These are consistent with parallel
  control and collision tables; this is not a table of 112 control states.
- The caller indexes the first table with the signed 16-bit value at item+0x0E.
- Entry 0 changes the goal at item+0x10 to 0, 1 or 2 according to forward/slow
  input, and clamps turning. Entry 1 also handles leaning, jump and roll.
- Entry 2 directly calls entries 0/1 when forward is pressed. Its left/right
  inputs select goals 7/6; table entries 7/6 implement opposite turn adjustments.
- These relations independently match the TR1 state-name catalogue in TRX.
- The probes call these exact addresses with EAX=item and EDX=collision data,
  execute the original instructions, and require a balanced return to a sentinel.
  All 40 cases passed within a 1,000-instruction limit each.

## Recovered fields and inputs

Names describe observed usage; they are not original debug symbols.

| Location | Interpretation | Evidence |
|---|---|---|
| item+0x0E, signed 16-bit | Current animation state | Dispatch index; roll writes 45 |
| item+0x10, signed 16-bit | Goal animation state | Control decisions write state IDs |
| item+0x14, 16-bit | Animation number | Roll writes 146; semantic name reference-assisted |
| item+0x16, 16-bit | Frame number | Roll writes 3857; semantic name reference-assisted |
| item+0x22, signed 16-bit | Health | Non-positive gates movement/death; reference-assisted name |
| item+0x3E, 16-bit | Yaw | Above-water caller adds damped turn rate here |
| item+0x40, signed 16-bit | Lean/roll | Run handler adjusts; caller relaxes toward zero |
| item+0x42 bit 3 | Gravity-active flag | Blocks running jump; reference-assisted name |
| 0xCE92C | Input bitmask | Shared reads across the five control handlers |
| 0xCE9CC, signed 16-bit | Turn rate | Both handler adjustments and caller yaw update |
| 0xCE966, 16-bit | Likely weapon status | Value 4 requests fast turn; not fully traced |

Observed input masks: forward 0x01, back 0x02, left 0x04, right 0x08,
jump 0x10, slow/walk 0x80, look 0x200, step-left 0x400, step-right 0x800,
roll 0x1000. Forward/left/right/jump/slow/roll are directly exercised by probes;
the remaining labels are static/reference-assisted and not exhaustively validated.
This identifies gameplay inputs, not the keyboard scan-code translation routine.

## Gameplay details worth preserving

- Walk and run adjust turn rate by 409 raw angular units per handler invocation.
- Walk clamps it to +/-728; run clamps it to +/-1456.
- Running changes lean by 273 per handler invocation and clamps to +/-2002.
- If left and right are both set, the walk handler takes the left branch.
- No forward input requests stop; forward+slow requests walk; forward without
  slow requests run. A requested state is not necessarily entered immediately:
  animation transition rules remain to be decoded.
- Running jump requests state 3 only when the gravity flag is clear.
- Roll sets current state 45, animation 146 and frame 3857, then requests stop.
- Dead walking requests stop, while dead running/standing requests death (8).
- Stationary turning can request fast-turn state 20; slow input clamps the turn.
- The above-water caller, tentatively beginning at 0x24F90, applies additional
  turn damping after control dispatch: magnitude <=364 becomes zero; otherwise
  364 is removed toward zero. It then adds the result to yaw at item+0x3E.
  It similarly relaxes lean by 182. These observations are static, not full-frame
  probes. Copying the control-handler constants alone would produce wrong feel.

## Loader validation and limits

The mapper loads all 141 enumerated pages across five objects. It consumes every
fixup record exactly to its page boundary. 22,529 32-bit offset records resolve
22,515 unique patch sites (page-crossing duplicates agree). Every applied value
is checked after all patches have been made.

Six selector-dependent fixups are deliberately not applied: three selector16
records at 0x4A8E3, 0x4AA08, 0x4AA1C, and three far-pointer records at 0xC64A2,
0xC64C8, 0xC64EE. None is needed by the isolated probes. This is an analysis image,
not a complete DOS/4G loader. Unsupported fixup/page forms fail explicitly.

The whole-object assembly file is a linear sweep and includes embedded data;
do not assume every decoded instruction or apparent function boundary is valid.
The extracted movement listing instead starts at relocation-backed entry points.

## Reproduce

Use Python 3 with the project-local work/python-deps packages (Capstone 5.0.6,
Unicorn 2.1.4). The scripts add that directory themselves. From the project root:

```powershell
python tools/analyse_le.py "<game-directory>/TOMB.EXE" --out work/analysis
python tools/probe_movement.py "<game-directory>/TOMB.EXE" --out analysis/movement-probes.json
```

Capstone wheel SHA-256: 761c3deae00b22ac697081cdae1383bb90659dd0d79387a09cf5bdbb22b17064

Unicorn wheel SHA-256: d7107500c64ce5c168fbff6bef9485b5db1350050036f4cea568650cf8bdbdf5

Both wheels were downloaded from PyPI and checked against its published hash.
Their bundled package metadata/licenses remain in work/python-deps.

## Reference provenance

- LE format cross-check: https://raw.githubusercontent.com/radareorg/radare2/master/libr/bin/format/le/le_specs.h
- TRX revision: 63fae6e50a2532c300d539dca7442fe2dbe51b6e
- State catalogue: https://github.com/LostArtefacts/TRX/blob/63fae6e50a2532c300d539dca7442fe2dbe51b6e/data/trx/ship/games/tr1/catalog_lara_states.csv
- Behaviour comparison: https://github.com/LostArtefacts/TRX/blob/63fae6e50a2532c300d539dca7442fe2dbe51b6e/src/trx/game/lara/state/land.c
- Also read src/trx/game/lara/enum.h at the same revision. TRX files retain their
  upstream licensing; no reference function bodies were copied into game code.

## Next bounded step

Implement the walk/run/turn control decisions in new C code, and compare their
outputs against these original-machine-code probes over a broader input matrix.
Then decode animation advancement and the walking collision handler. The
standing handler's look mode and backward-walk branch need additional coverage.
This still precedes a gym-level renderer and full playable movement prototype.
