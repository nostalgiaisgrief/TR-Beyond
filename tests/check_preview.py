"""Native WGL smoke checks; these do not establish equivalence to DOS rendering."""
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
results = []
for animation, seconds, orbit in [(11, 0, 0), (1, .25, 0), (1, .3, 0), (0, .35, 0), (0, .35, 3.14159265)]:
    hashes = []
    for suffix in ['', '_debug']:
        name = f'preview-{animation}-{seconds}-{orbit}{suffix}'
        destination = ROOT / 'build' / (name + '.ppm')
        subprocess.run([str(ROOT / 'build' / f'tomb_preview{suffix}.exe'),
                        '--capture', str(destination), '--animation', str(animation),
                        '--time', str(seconds), '--orbit', str(orbit), '--distance', '600' if orbit else '1800'],
                       cwd=ROOT, check=True, timeout=30)
        data = destination.read_bytes()
        hashes.append(hashlib.sha256(data).hexdigest())
        image = Image.open(destination)
        assert image.width >= 1000 and image.height >= 600
        colours = image.getcolors(image.width * image.height)
        assert colours and len(colours) > 1000, 'Blank or incomplete frame'
        assert max(count for count, _ in colours) < image.width * image.height * .9
        if not suffix:
            image.save(destination.with_suffix('.png'))
    assert hashes[0] == hashes[1], 'Debug/optimized render mismatch'
    results.append(dict(animation=animation, seconds=seconds, orbit=orbit, sha256=hashes[0]))
assert len({r['sha256'] for r in results}) == len(results), 'Pose/camera change not visible'
(ROOT / 'analysis' / 'preview-validation.json').write_text(json.dumps({
    'scope': 'Native OpenGL smoke checks, not original-renderer equivalence',
    'matching_builds': ['O0', 'O2'], 'captures': results}, indent=2) + '\n')
print('PASS: 10 native captures; 5 matching debug/optimized pairs; pose and camera changes visible')
