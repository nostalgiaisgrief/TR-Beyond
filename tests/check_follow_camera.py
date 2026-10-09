"""Native follow-camera scenes in debug/optimized builds; no manual camera placement."""
import subprocess,json,csv
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
scenes=[('start',1,[]),('wall',120,['--input','129']),('turn',30,['--input','8']),('backflip',25,['--standing-test','--input','18']),('catch',75,['--forward-test']),('pullup',110,['--climb-test','--input','65']),('vault',30,['--vault-test','2']),('pool-entry',45,['--pool-test']),('swim',90,['--pool-test']),('surface',150,['--pool-test']),('pool-exit',250,['--pool-test']),('pool-bank',350,['--pool-test'])]
sheet=Image.new('RGB',(4*480,3*282));draw=ImageDraw.Draw(sheet);results=[]
for n,(name,ticks,args) in enumerate(scenes):
    versions=[]
    for suffix in ('','_debug'):
        base=ROOT/'build'/f'follow-{name}{suffix}'
        subprocess.run([str(ROOT/'build'/f'tomb_preview{suffix}.exe'),'--simulate',str(ticks),'--capture',str(base.with_suffix('.ppm')),'--trace',str(base.with_suffix('.csv')),'--follow-camera']+args,cwd=ROOT,check=True,timeout=30)
        versions.append((base.with_suffix('.ppm').read_bytes(),base.with_suffix('.csv').read_bytes()))
        im=Image.open(base.with_suffix('.ppm'));assert len(im.getcolors(im.width*im.height))>512,name
        if not suffix:
            im.save(base.with_suffix('.png'));im.thumbnail((480,258));sheet.paste(im,((n%4)*480,(n//4)*282+24));draw.text(((n%4)*480+8,(n//4)*282+6),name,fill='white')
    assert versions[0]==versions[1],name
    results.append(dict(name=name,ticks=ticks,last=list(csv.DictReader(versions[0][1].decode().splitlines()))[-1]))
sheet.save(ROOT/'build/follow-camera-scenes.png')
(ROOT/'analysis/follow-camera-validation.json').write_text(json.dumps(dict(captures=24,cases=results,debug_optimized_identical=True),indent=2)+'\n')
print('PASS: 24 native follow-camera captures, identical debug/optimized images and gameplay traces')
