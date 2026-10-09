"""Native rendered checks for gym cameras, death and completion."""
import subprocess,csv,json
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
cases=[('fatal',180,['--gym-test','1']),('drown',90,['--gym-test','2']),('drowned',240,['--gym-test','2']),('tutorial-camera',60,['--gym-test','3']),('camera-return',220,['--gym-test','3']),('gym-complete',530,['--pool-test'])]
sheet=Image.new('RGB',(1440,564));draw=ImageDraw.Draw(sheet);results=[]
for n,(name,ticks,args) in enumerate(cases):
    versions=[]
    for suffix in ('','_debug'):
        base=root/'build'/f'gym-{name}{suffix}'
        subprocess.run([str(root/'build'/f'tomb_preview{suffix}.exe'),'--simulate',str(ticks),'--capture',str(base.with_suffix('.ppm')),'--trace',str(base.with_suffix('.csv'))]+args,cwd=root,check=True,timeout=30)
        rows=list(csv.DictReader(base.with_suffix('.csv').read_text().splitlines()))
        assert all(r['blocked']=='0' for r in rows),name
        if name in ('fatal','drown','drowned'):assert int(rows[-1]['health'])<=0
        versions.append((base.with_suffix('.ppm').read_bytes(),base.with_suffix('.csv').read_bytes()))
        if not suffix:
            im=Image.open(base.with_suffix('.ppm'));assert len(im.getcolors(im.width*im.height))>512
            im.save(base.with_suffix('.png'));im.thumbnail((480,258));sheet.paste(im,((n%3)*480,(n//3)*282+24));draw.text(((n%3)*480+8,(n//3)*282+6),name,fill='white')
            results.append(dict(scene=name,last=rows[-1]))
    assert versions[0]==versions[1],name
sheet.save(root/'build/gym-services-scenes.png')
(root/'analysis/gym-preview-validation.json').write_text(json.dumps(dict(captures=12,debug_optimized_identical=True,scenes=results),indent=2)+'\n')
print('PASS: 12 gym camera/death/completion captures; matching images/traces, no blocked ticks')
