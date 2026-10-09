# Original text rendering — 9 October 2026

Caves playtest 10 replaces Windows Arial/display-list text with the supplied
PHD font sprites. This is interface step 1; ring behaviour and full screen
layouts remain subsequent steps. No TRX source was used for this change.

## Binary and asset evidence

- Sprite sequence 190 is the alphabet: 110 glyphs, starting at sprite 37 in
  LEVEL1.PHD. The sequence is looked up per level rather than hard-coded to 37.
- DOS Text_GetWidth at 0x3985c reads byte-width data at 0xc3ec0 and maps printable
  characters through 0xc3f2e. Default letter spacing is 1, word spacing 6,
  scale 65536 (16.16 fixed point), from text initialization at 0x39689.
- Text_Draw at 0x399bc measures before alignment. Centre/right and middle/bottom
  flags retain original precedence and integer truncation. Measured width is
  rounded down to an even value. The original special accent/overlay symbols
  `$`, `(`, `)` and `~` draw without advancing, although measurement still
  includes them. Low-byte icon mapping also retains DOS rules.
- Screen sprite dispatch at 0x1f6e0 receives shade 4096. Font textures use the
  original level palette through light-map row 16, with palette index zero
  transparent. The gold highlight/shadow is part of the original glyph art;
  there is no invented tint or platform-font smoothing.
- Sprite rectangle offsets are relative to the text baseline. The supplied
  font sprites use e.g. [0,-16,16,0]; original texture UVs are preserved.

## Implementation and validation

src/text.c contains independent measurement/layout; preview.c submits the
resulting glyphs through OpenGL with nearest-neighbour texture sampling.
Windows-resolution scaling is uniform, expressed through the DOS fixed-point
scale parameters. Headers now use the measured centre-alignment path.

compare_text.py executes original DOS x86 width/layout instructions for 2000
strings/styles per debug and release build. Final sprite drawing is captured
as a test double; glyph IDs, baselines, scale and alignment match exactly.
Coverage includes case, punctuation, spaces, icon bytes, overlay symbols,
empty strings, custom spacing, fractional scales and alignment combinations.
Invalid bytes above ASCII 126 are safely ignored in C rather than indexing
outside the original character table; no extended-encoding support is claimed.

Both native preview regression suites pass. OpenGL captures were inspected for
Caves inventory/completion and City inventory after actual next-level loading;
the Gym font/texture load was also exercised. Text validation report:
text-validation.json. Pixel-for-pixel equivalence to the DOS software renderer
is not claimed; font data, colours, metrics and layout rules are reconstructed.

## Remaining interface work

Inventory ring motion/item selection animations, final inventory/HUD/statistics
layouts, passport/save-load/options/title screens and their timing/sounds remain
on the interface list. This change does not alter gameplay or control mappings.
