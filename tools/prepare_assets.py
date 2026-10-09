"""Prepare locally owned DOS game assets for TR-Beyond; Python standard library only."""
import argparse
import hashlib
import io
import re
import struct
import wave
from pathlib import Path

from inspect_reference import Disc

EXE_SHA256 = '99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'


def sine_table(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXE_SHA256:
        raise ValueError('Unsupported TOMB.EXE revision; see HISTORY.MD for the required SHA-256.')
    def word(at):
        return struct.unpack_from('<I', raw, at)[0]
    le = word(60)
    page_size = word(le + 40)
    for n in range(word(le + 68)):
        size, base, _, first, pages, _ = struct.unpack_from('<6I', raw, le + word(le + 64) + n * 24)
        offset = 0xc50c4 - base
        if not 0 <= offset < size:
            continue
        mapped = bytearray()
        for j in range(pages):
            at = le + word(le + 72) + 4 * (first - 1 + j)
            physical = int.from_bytes(raw[at:at + 3], 'big')
            if raw[at + 3] != 0 or physical == 0:
                raise ValueError('Unsupported executable page')
            at = word(le + 128) + (physical - 1) * page_size
            mapped.extend(raw[at:at + page_size])
        result = bytes(mapped[offset:offset + 2050])
        if len(result) != 2050:
            raise ValueError('Truncated sine table')
        return result
    raise ValueError('Sine table not found')


def gym_voices(data):
    at = 0
    def read(fmt):
        nonlocal at
        values = struct.unpack_from('<' + fmt, data, at)
        at += struct.calcsize('<' + fmt)
        return values
    def skip(size):
        nonlocal at
        if size < 0 or at + size > len(data):
            raise ValueError('Truncated GYM.PHD')
        at += size
    if read('I')[0] != 32:
        raise ValueError('Expected original PC PHD format')
    skip(read('I')[0] * 65536)
    skip(4)
    for _ in range(read('H')[0]):
        skip(16)
        skip(read('I')[0] * 2)
        skip(read('H')[0] * 32)
        nz, nx = read('HH')
        skip(nz * nx * 8)
        skip(2)
        skip(read('H')[0] * 18)
        skip(read('H')[0] * 18)
        skip(4)
    for width in (2, 2, 4, 32, 6, 8, 2, 4, 2, 18, 32, 20, 16, 8, 16, 16):
        skip(read('I')[0] * width)
    boxes = read('I')[0]
    skip(boxes * 20)
    skip(read('I')[0] * 2)
    skip(boxes * 12)
    skip(read('I')[0] * 2)
    skip(read('I')[0] * 22)
    skip(8192 + 768)
    for width in (16, 1):
        skip(read('H')[0] * width)
    mapping = read('256h')
    details = [read('4H') for _ in range(read('I')[0])]
    size = read('I')[0]
    samples = data[at:at + size]
    skip(size)
    indices = read(str(read('I')[0]) + 'I')
    if at != len(data):
        raise ValueError('Unexpected GYM.PHD sound layout')
    result = {}
    for track in range(26, 51):
        detail = mapping[track + 148]
        if detail < 0:
            raise ValueError('Missing gym voice')
        offset = indices[details[detail][0]]
        size = struct.unpack_from('<I', samples, offset + 4)[0] + 8
        sample = samples[offset:offset + size]
        with wave.open(io.BytesIO(sample)) as audio:
            if audio.getcomptype() != 'NONE':
                raise ValueError('Expected PCM gym voice')
        result[f'track{track:02}.wav'] = sample
    return result


def prepare(exe, cue, destination):
    sine = sine_table(exe)
    text = cue.read_text()
    files = re.findall(r'^\s*FILE\s+"([^"]+)"\s+BINARY\s*$', text, re.M | re.I)
    if len(files) != 1:
        raise ValueError('Expected a single-file raw CUE/BIN image')
    binary = cue.parent / files[0]
    tracks = []
    for number, kind, body in re.findall(r'TRACK (\d+) (\S+)(.*?)(?=\s+TRACK|\Z)', text, re.S):
        indexes = {int(i): (int(m) * 60 + int(s)) * 75 + int(f)
                   for i, m, s, f in re.findall(r'INDEX (\d+) (\d+):(\d+):(\d+)', body)}
        tracks.append((int(number), kind, indexes))
    if not tracks or tracks[0][1] != 'MODE1/2352':
        raise ValueError('Expected Mode 1/2352 data track')
    disc = Disc(binary)
    assets = {}
    try:
        for entry in disc.walk(*disc.root):
            name = entry['path'].upper()
            if re.fullmatch(r'DATA/(GYM\.PHD|TITLE\.PHD|LEVEL[^/]*\.PHD|TITLEH\.PCX)', name):
                assets[name] = disc.read(entry['sector'], entry['size'])
    finally:
        disc.file.close()
    required = {'DATA/GYM.PHD', 'DATA/TITLE.PHD', 'DATA/LEVEL1.PHD', 'DATA/LEVEL2.PHD', 'DATA/TITLEH.PCX'}
    if not required.issubset(assets):
        raise ValueError('CD image is missing required PC game data')
    assets['sine.bin'] = sine
    assets.update({'audio/' + name: data for name, data in gym_voices(assets['DATA/GYM.PHD']).items()})
    with binary.open('rb') as source:
        found = set()
        for index, (number, kind, indexes) in enumerate(tracks):
            if not 2 <= number <= 10:
                continue
            if kind != 'AUDIO' or 1 not in indexes:
                raise ValueError('Invalid CD audio track')
            next_indexes = tracks[index + 1][2] if index + 1 < len(tracks) else {1: binary.stat().st_size // 2352}
            begin = indexes[1] * 2352
            end = next_indexes.get(0, next_indexes[1]) * 2352
            if end <= begin:
                raise ValueError('Invalid CD audio extent')
            source.seek(begin)
            pcm = source.read(end - begin)
            if len(pcm) != end - begin:
                raise ValueError('Truncated CD audio')
            output = io.BytesIO()
            with wave.open(output, 'wb') as audio:
                audio.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
                audio.writeframes(pcm)
            assets[f'audio/cd{number:02}.wav'] = output.getvalue()
            found.add(number)
    if found != set(range(2, 11)):
        raise ValueError('CD image must contain audio tracks 2 through 10')
    for name, data in assets.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f'Prepared {len(assets)} files in {destination}. Original files were read only.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', required=True, type=Path, help='Original installed DOS TOMB.EXE')
    parser.add_argument('--cue', required=True, type=Path, help='Original single-file CUE/BIN image')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'work/reference-assets')
    args = parser.parse_args()
    try:
        prepare(args.exe, args.cue, args.output)
    except (OSError, ValueError, IndexError, KeyError, struct.error, wave.Error) as error:
        parser.exit(1, f'Asset preparation failed: {error}\n')
