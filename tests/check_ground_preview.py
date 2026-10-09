"""Exercise actual native preview movement/trace/capture path in both builds."""
import csv,hashlib,json,subprocess
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
results=[]
for name,ticks,mask in [('idle',120,0),('walk-wall',120,129),('run',60,1),('turn',30,8),('back',60,130),('wall-hit',40,1),('hop-back',20,2),('back-fall',16,2),('back-land',60,2),('fast-fall',27,0),('fast-land',38,0),('running-jump',35,0),('jump-land',100,0),('standing-up',20,16),('standing-up-land',100,16),('standing-forward',20,17),('standing-forward-land',100,17),('standing-back',20,18),('standing-back-land',100,18),('standing-left',20,20),('standing-left-land',100,20),('standing-right',20,24),('standing-right-land',100,24),('ledge-catch',22,0),('ledge-hold',65,0),('ledge-release',77,0),('ledge-land',140,0),('climb-pull',100,65),('climb-stand',200,65),('climb-handstand',120,193),('climb-handstand-land',350,193),('climb-left',115,68),('climb-right',115,72)]:
    traces=[]; frames=[]
    for suffix in ('','_debug'):
        base=ROOT/'build'/('ground-'+name+suffix)
        subprocess.run([str(ROOT/'build'/('tomb_preview'+suffix+'.exe')),'--simulate',str(ticks),'--input',str(mask),
                        '--trace',str(base.with_suffix('.csv')),'--capture',str(base.with_suffix('.ppm'))]+(['--ledge-test'] if name in ('back-fall','back-land') else [])+(['--fast-fall-test','--orbit','-1.57079633','--distance','600'] if name in ('fast-fall','fast-land') else [])+(['--jump-test','--orbit','-1.57079633','--distance','1200'] if name in ('running-jump','jump-land') else [])+(['--standing-test','--orbit','-1.57079633','--distance','1200'] if name.startswith('standing-') else [])+(['--grab-test','--orbit','0','--distance','1600'] if name.startswith('ledge-') else [])+(['--climb-test','--orbit','-1.57079633','--distance','1200'] if name.startswith('climb-') else []),cwd=ROOT,check=True,timeout=30)
        traces.append(base.with_suffix('.csv').read_bytes())
        frames.append(base.with_suffix('.ppm').read_bytes())
        image=Image.open(base.with_suffix('.ppm'))
        assert len(image.getcolors(image.width*image.height))>512, 'Capture obscured or incomplete'
        if not suffix: image.save(base.with_suffix('.png'))
    assert traces[0]==traces[1] and frames[0]==frames[1]
    rows=list(csv.DictReader(traces[0].decode().splitlines())); assert len(rows)==ticks
    if name.startswith('standing-'):
        assert any(r['state']=='15' for r in rows) and any(int(r['flags'])&8 for r in rows) and all(r['blocked']=='0' for r in rows)
        if name in ('standing-back','standing-left','standing-right'): assert rows[-1]['state']=={'standing-back':'25','standing-left':'27','standing-right':'26'}[name]
        if name.endswith('-land'): assert rows[-1]['state']=='2' and rows[-1]['y']=='0' and not(int(rows[-1]['flags'])&8)
    if name.startswith('ledge-'):
        assert any(r['state']=='10' for r in rows) and all(r['blocked']=='0' for r in rows)
        if name in ('ledge-catch','ledge-hold'): assert rows[-1]['state']=='10' and not(int(rows[-1]['flags'])&8)
        if name=='ledge-release': assert rows[-1]['state']=='28' and int(rows[-1]['flags'])&8
        if name=='ledge-land': assert rows[-1]['state']=='2' and rows[-1]['y']=='1024'
    if name.startswith('climb-'):
        assert any(r['state']=='10' for r in rows) and all(r['blocked']=='0' for r in rows)
        expected={'climb-pull':'19','climb-stand':'2','climb-handstand':'54','climb-handstand-land':'2','climb-left':'30','climb-right':'31'}
        assert rows[-1]['state']==expected[name],(name,rows[-1])
    if name=='idle': assert all((r['x'],r['y'],r['z'])==('37376','-1280','51712') for r in rows)
    if name=='walk-wall': assert 35940<=int(rows[-1]['x'])<36200
    if name=='run': assert int(rows[-1]['x'])<37376
    if name=='running-jump': assert rows[-1]['state']=='3' and int(rows[-1]['flags'])&8 and int(rows[-1]['y'])<0 and all(r['blocked']=='0' for r in rows)
    if name=='jump-land': assert any(r['state']=='3' and int(r['flags'])&8 for r in rows) and rows[-1]['state']=='2' and rows[-1]['y']=='0' and all(r['blocked']=='0' for r in rows)
    if name=='fast-fall': assert rows[-1]['state']=='9' and int(rows[-1]['flags'])&8 and all(r['blocked']=='0' for r in rows)
    if name=='fast-land': assert rows[-1]['state']=='2' and rows[-1]['animation']=='24' and 0<int(rows[-1]['health'])<1000 and all(r['blocked']=='0' for r in rows)
    if name=='back-fall': assert rows[-1]['state']=='29' and int(rows[-1]['flags'])&8 and all(r['blocked']=='0' for r in rows)
    if name=='back-land': assert any(int(r['flags'])&8 for r in rows) and rows[-1]['y']=='-1280' and not(int(rows[-1]['flags'])&8) and all(r['blocked']=='0' for r in rows)
    if name=='hop-back': assert int(rows[-1]['x'])>37376 and any(r['state']=='5' for r in rows) and all(r['blocked']=='0' for r in rows)
    if name=='back': assert int(rows[-1]['x'])>37376 and rows[-1]['state']=='16'
    if name=='wall-hit': assert rows[-1]['state']=='12' and rows[-1]['animation'] in ('53','54') and all(r['blocked']=='0' for r in rows)
    if name=='turn': assert int(rows[-1]['yaw'])>-16384
    results.append(dict(name=name,ticks=ticks,input=mask,last=rows[-1],trace_sha256=hashlib.sha256(traces[0]).hexdigest()))
(ROOT/'analysis/ground-preview-validation.json').write_text(json.dumps(dict(cases=results,builds=2,scope='Native integration checks, not full-frame DOS equivalence'),indent=2)+'\n')
print('PASS: 66 native movement captures; debug/optimized tick traces and frames identical')


for suffix in ('','_debug'):
    subprocess.run([str(ROOT/'build'/('tomb_preview'+suffix+'.exe')),'--window-input-test'],cwd=ROOT,check=True,timeout=10)
print('PASS: native Alt/menu, explicit pause and close message tests in both builds')
